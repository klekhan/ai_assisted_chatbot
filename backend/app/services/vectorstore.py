"""
Wraps Qdrant Cloud: a managed, free-tier vector database.

Each chunk is stored as one "point" with:
  - a vector (the embedding)
  - a payload (metadata: document_id, filename, chunk_text, chunk_index)

Deduplication strategy: document_id is DERIVED from the filename (a stable
hash), not randomly generated. This means re-uploading a file with the same
name always maps to the same document_id — so "upload" and "replace" are
the same operation: delete any existing points for that document_id, then
insert the new ones. This is what prevents the "FAQs.pdf / FAQs.pdf / FAQs.pdf"
duplication problem: there is structurally only ever one document_id per
filename.

We don't need a separate SQL database to track uploaded documents — Qdrant's
payload index lets us list distinct documents directly from the vectors
themselves, which keeps the whole system to a single moving part.
"""
import hashlib
import uuid
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.config import settings
from app.services import embeddings

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    # timeout was previously unset here, which is the actual root cause of
    # "write operation timed out" on larger PDFs — see config.py's
    # qdrant_timeout_seconds docstring for the full explanation.
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout_seconds,
    )


def document_id_for_filename(filename: str) -> str:
    """Deterministic ID so the same filename always maps to the same document."""
    normalized = filename.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def ensure_collection():
    """Creates the main documents collection with BOTH a dense vector
    ("dense") and a sparse BM25 vector ("sparse"), so search() can run
    hybrid retrieval. If a collection from before this change already
    exists with the old single unnamed vector, it's left as-is — see
    README's "Migrating an existing collection" note for how to move to
    the hybrid schema."""
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                DENSE_VECTOR_NAME: qmodels.VectorParams(
                    size=settings.embedding_dim,
                    distance=qmodels.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: qmodels.SparseVectorParams(
                    modifier=qmodels.Modifier.IDF,
                ),
            },
        )
        # Index document_id so we can filter/delete/list by document efficiently
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )


def _sparse_vector(sparse: dict | None) -> qmodels.SparseVector | None:
    if not sparse:
        return None
    return qmodels.SparseVector(indices=sparse["indices"], values=sparse["values"])


def upsert_chunks(
    document_id: str,
    filename: str,
    chunks: list[str],
    vectors: list[list[float]],
    sparse_vectors: list[dict] | None = None,
):
    """Batches points into fixed-size upsert() calls instead of one request
    for the whole document. This is the fix for the write-timeout failure:
    previously a single request carried every point in the document — for a
    small file that's fine, but for a larger document (more chunks, and
    each point now carrying both a dense AND sparse vector under the hybrid
    schema) that single request's payload and server-side indexing work
    could exceed even a generous timeout. Fixed-size batches keep every
    individual request's cost roughly constant regardless of how large the
    source document is, so upload time scales with document size instead of
    risking an all-or-nothing timeout on big ones."""
    client = get_client()
    batch_size = settings.qdrant_upsert_batch_size

    for batch_start in range(0, len(chunks), batch_size):
        batch_end = batch_start + batch_size
        batch_points = []
        for i in range(batch_start, min(batch_end, len(chunks))):
            vector: dict = {DENSE_VECTOR_NAME: vectors[i]}
            if sparse_vectors:
                vector[SPARSE_VECTOR_NAME] = _sparse_vector(sparse_vectors[i])
            batch_points.append(
                qmodels.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": i,
                        "text": chunks[i],
                    },
                )
            )
        client.upsert(collection_name=settings.qdrant_collection, points=batch_points)


def search(
    query_vector: list[float],
    top_k: int,
    min_score: float = 0.0,
    query_text: str | None = None,
    fetch_k: int | None = None,
) -> list[dict]:
    """Hybrid retrieval: fetches fetch_k candidates by dense similarity AND
    fetch_k candidates by BM25 keyword match, fuses them with Qdrant's
    built-in Reciprocal Rank Fusion, then returns the top_k fused results
    with any below min_score discarded.

    Dense catches paraphrases and meaning; BM25 catches exact keywords, IDs,
    names, and acronyms that an embedding can under-weight. Fusing both is a
    lightweight, no-extra-model way to noticeably improve retrieval quality
    over dense-only search — this is the "improve retrieval accuracy" fix.

    A small pool beyond top_k is pulled so accumulated user feedback
    (chunk_feedback in feedback_store.py) has room to actually reorder
    results — see _apply_feedback_boost below. This is what lets retrieval
    keep improving from real usage, without retraining any model.

    Falls back to plain dense search if hybrid search is disabled, the
    sparse model isn't available, or no query_text was given (e.g. legacy
    callers) — so this is backward compatible.
    """
    client = get_client()
    fetch_k = fetch_k or max(top_k, settings.retrieval_fetch_k)
    # Pool a bit past top_k so boost-based re-ranking has candidates to
    # promote — pointless to fetch more than fetch_k though.
    pool_k = min(fetch_k, max(top_k * 3, top_k + 5))

    sparse_query = embeddings.embed_sparse_query(query_text) if query_text else None

    if sparse_query:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[
                qmodels.Prefetch(
                    query=query_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=fetch_k,
                ),
                qmodels.Prefetch(
                    query=_sparse_vector(sparse_query),
                    using=SPARSE_VECTOR_NAME,
                    limit=fetch_k,
                ),
            ],
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            limit=pool_k,
            with_payload=True,
        ).points
    else:
        # Dense-only fallback (hybrid disabled/unavailable, or legacy
        # single-vector collection from before this change).
        try:
            results = client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vector,
                using=DENSE_VECTOR_NAME,
                limit=pool_k,
                with_payload=True,
            ).points
        except Exception:
            # Legacy collection created with an unnamed vector.
            results = client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vector,
                limit=pool_k,
                with_payload=True,
            ).points

    candidates = [
        {
            "text": r.payload["text"],
            "filename": r.payload["filename"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload.get("chunk_index"),
            "point_id": str(r.id),
            "score": r.score,
        }
        for r in results
        if r.score >= min_score
    ]

    candidates = _apply_feedback_boost(candidates)
    return candidates[:top_k]


def _apply_feedback_boost(candidates: list[dict]) -> list[dict]:
    """Nudges each candidate's score by its accumulated net 👍/👎 votes
    (capped, and scaled small — see chunk_boost_weight/chunk_boost_cap in
    config.py), then re-sorts. Ranking only ever shifts among chunks that
    already cleared min_score on raw similarity — a chunk with a great
    track record still can't out-rank a genuinely irrelevant one, it can
    only win close calls against similarly-relevant chunks."""
    if not candidates:
        return candidates

    # Local import avoids a circular import (feedback_store doesn't import
    # vectorstore, but importing it at module load time here isn't needed
    # either — keeps this dependency visible right where it's used).
    from app.services import feedback_store

    boosts = feedback_store.get_chunk_boosts([c["point_id"] for c in candidates])
    if not boosts:
        return candidates

    cap = settings.chunk_boost_cap
    for c in candidates:
        raw_boost = boosts.get(c["point_id"], 0)
        clamped = max(-cap, min(cap, raw_boost))
        c["score"] = c["score"] + clamped * settings.chunk_boost_weight

    return sorted(candidates, key=lambda c: c["score"], reverse=True)


def list_documents() -> list[dict]:
    """Returns one entry per unique document, with its chunk count."""
    client = get_client()
    seen: dict[str, dict] = {}

    next_offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            with_payload=True,
            with_vectors=False,
            limit=200,
            offset=next_offset,
        )
        for p in points:
            doc_id = p.payload["document_id"]
            if doc_id not in seen:
                seen[doc_id] = {
                    "document_id": doc_id,
                    "filename": p.payload["filename"],
                    "chunk_count": 0,
                }
            seen[doc_id]["chunk_count"] += 1
        if next_offset is None:
            break

    return list(seen.values())


def delete_document(document_id: str):
    client = get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))]
            )
        ),
    )


def replace_document(
    document_id: str,
    filename: str,
    chunks: list[str],
    vectors: list[list[float]],
    sparse_vectors: list[dict] | None = None,
):
    """Atomically-enough replace: delete any existing points for this
    document_id, then insert the fresh ones. Because document_id is derived
    from the filename, this is what makes re-uploading a file a clean
    replace instead of a duplicate.

    This is also the mechanism behind "flag unanswered question → admin
    uploads a new/updated doc → bot can answer it next time": there's no
    separate re-indexing step needed. The moment the new document lands
    here, the next matching query's search() call finds it, because
    retrieval always queries this live collection — nothing needs to be
    retrained or redeployed."""
    delete_document(document_id)
    upsert_chunks(document_id, filename, chunks, vectors, sparse_vectors)


def collection_stats() -> dict:
    """Basic embedding/KB status info for the admin dashboard."""
    client = get_client()
    ensure_collection()
    info = client.get_collection(settings.qdrant_collection)
    documents = list_documents()
    return {
        "collection_name": settings.qdrant_collection,
        "total_points": info.points_count,
        "total_documents": len(documents),
        "vector_size": settings.embedding_dim,
        "status": str(info.status),
    }


# --- Verified-answer cache ---------------------------------------------
#
# A separate, small collection: one point per user-approved (👍) Q&A pair.
# This is what lets the bot get visibly better from feedback without any
# retraining — repeat/near-duplicate questions get served straight from
# here, skipping retrieval + generation entirely. See routers/chat.py's
# /chat/feedback endpoint, which is what writes into this collection.

def ensure_verified_collection():
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.verified_qa_collection not in collections:
        client.create_collection(
            collection_name=settings.verified_qa_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        )


def upsert_verified_answer(question: str, answer: str, question_vector: list[float]) -> str:
    client = get_client()
    point_id = str(uuid.uuid4())
    client.upsert(
        collection_name=settings.verified_qa_collection,
        points=[
            qmodels.PointStruct(
                id=point_id,
                vector=question_vector,
                payload={"question": question, "answer": answer},
            )
        ],
    )
    return point_id


def search_verified_answer(question_vector: list[float]) -> dict | None:
    """Returns the closest verified Q&A pair if it's a near-duplicate of the
    current question (score above verified_qa_score_threshold), else None.
    A high threshold is deliberate — this is a cache for genuinely repeated
    questions, not a general similarity search, so it should only fire on
    near-exact restatements."""
    client = get_client()
    results = client.query_points(
        collection_name=settings.verified_qa_collection,
        query=question_vector,
        limit=1,
        with_payload=True,
    ).points
    if not results or results[0].score < settings.verified_qa_score_threshold:
        return None
    r = results[0]
    return {"point_id": str(r.id), "question": r.payload["question"], "answer": r.payload["answer"], "score": r.score}


def list_verified_answers() -> list[dict]:
    client = get_client()
    points, _ = client.scroll(
        collection_name=settings.verified_qa_collection,
        with_payload=True,
        with_vectors=False,
        limit=200,
    )
    return [{"point_id": str(p.id), "question": p.payload["question"], "answer": p.payload["answer"]} for p in points]


def delete_verified_answer(point_id: str):
    client = get_client()
    client.delete(
        collection_name=settings.verified_qa_collection,
        points_selector=qmodels.PointIdsList(points=[point_id]),
    )
