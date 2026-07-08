"""
Turns text into vectors (embeddings) using a local, free, open-source model.
The model downloads once (~90MB) on first run and is cached afterwards, so
there is no per-request cost or API key needed for embeddings.
"""
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    # Cached so the (relatively slow) model load only happens once per process.
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
