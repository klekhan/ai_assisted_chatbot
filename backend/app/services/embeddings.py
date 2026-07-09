"""
Turns text into vectors (embeddings) using a local, free, open-source model
run via fastembed (ONNX runtime) — deliberately NOT sentence-transformers,
because that pulls in PyTorch, which is too heavy for free-tier hosts like
Render's 512MB memory limit. fastembed does the same job in a fraction of
the memory, with no GPU/PyTorch dependency.

The model downloads once (~130MB) on first run and is cached afterwards.
"""
from functools import lru_cache
from fastembed import TextEmbedding
from app.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    # Cached so the (relatively slow) model load only happens once per process.
    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedder()
    vectors = list(model.embed(texts))
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
