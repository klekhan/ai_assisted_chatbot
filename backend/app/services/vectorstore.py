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


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def document_id_for_filename(filename: str) -> str:
    """Deterministic ID so the same filename always maps to the same document."""
    normalized = filename.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def ensure_collection():
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        )
        # Index document_id so we can filter/delete/list by document efficiently
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )


def upsert_chunks(document_id: str, filename: str, chunks: list[str], vectors: list[list[float]]):
    client = get_client()
    points = [
        qmodels.PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunks[i],
            },
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def search(query_vector: list[float], top_k: int) -> list[dict]:
    client = get_client()
    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "text": r.payload["text"],
            "filename": r.payload["filename"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload.get("chunk_index"),
            "point_id": str(r.id),
            "score": r.score,
        }
        for r in results
    ]


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


def replace_document(document_id: str, filename: str, chunks: list[str], vectors: list[list[float]]):
    """Atomically-enough replace: delete any existing points for this
    document_id, then insert the fresh ones. Because document_id is derived
    from the filename, this is what makes re-uploading a file a clean
    replace instead of a duplicate."""
    delete_document(document_id)
    upsert_chunks(document_id, filename, chunks, vectors)


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
