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
from fastembed import TextEmbedding
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
