"""
Turns text into vectors (embeddings) using a local, free, open-source model
run via fastembed (ONNX runtime) — deliberately NOT sentence-transformers,
because that pulls in PyTorch, which is too heavy for free-tier hosts like
Render's 512MB memory limit. fastembed does the same job in a fraction of
the memory, with no GPU/PyTorch dependency.

Two extra constraints here specifically for tight-memory hosting:
1. threads=1 — ONNX Runtime defaults to sizing its thread pool and memory
   arenas for the host machine, which can massively overshoot a 512MB box.
   Pinning it to 1 thread keeps memory use predictable, at a small speed cost.
2. Batched embedding — embedding an entire large document's chunks in a
   single call spikes memory proportionally to document size. Processing in
   small fixed-size batches keeps peak memory roughly constant regardless of
   how big the uploaded document is.

The model downloads once (~130MB) on first run and is cached afterwards.
"""
from functools import lru_cache
from fastembed import TextEmbedding, SparseTextEmbedding
from app.config import settings

BATCH_SIZE = 16


@lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    # Cached so the (relatively slow) model load only happens once per process.
    return TextEmbedding(model_name=settings.embedding_model, threads=1)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedder()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        vectors.extend(v.tolist() for v in model.embed(batch))
    return vectors


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


# --- Sparse (BM25) embeddings, for hybrid search ---
#
# "Qdrant/bm25" is plain term-frequency/IDF statistics, not a neural model —
# no extra PyTorch/ONNX model weights beyond a small tokenizer file, so this
# adds negligible memory on top of the dense embedder above. If it can't be
# loaded for any reason (e.g. no network on first boot), hybrid search is
# disabled automatically and retrieval falls back to dense-only, rather than
# crashing the app.
@lru_cache(maxsize=1)
def get_sparse_embedder() -> "SparseTextEmbedding | None":
    if not settings.enable_hybrid_search:
        return None
    try:
        return SparseTextEmbedding(model_name=settings.sparse_model, threads=1)
    except Exception:
        return None


def sparse_available() -> bool:
    return get_sparse_embedder() is not None


def embed_sparse_texts(texts: list[str]) -> list[dict] | None:
    """Returns one {"indices": [...], "values": [...]} dict per text — the
    format Qdrant's SparseVector expects — or None if hybrid search is
    unavailable. Uses `.embed()` (document-side BM25 weighting)."""
    model = get_sparse_embedder()
    if model is None or not texts:
        return None
    out: list[dict] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for v in model.embed(batch):
            out.append({"indices": v.indices.tolist(), "values": v.values.tolist()})
    return out


def embed_sparse_query(text: str) -> dict | None:
    """Query-side BM25 weighting (`.query_embed()`) is intentionally
    different from document-side (`.embed()`) — that asymmetry is how BM25
    is meant to be used."""
    model = get_sparse_embedder()
    if model is None:
        return None
    v = next(iter(model.query_embed(text)))
    return {"indices": v.indices.tolist(), "values": v.values.tolist()}
