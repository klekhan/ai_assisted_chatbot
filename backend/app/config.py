"""
Central configuration. All secrets/config come from environment variables
(loaded from a .env file locally, or from the host's env-var settings in
production e.g. Render).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Qdrant (vector database) ---
    qdrant_url: str          # e.g. https://xxxx.cloud.qdrant.io
    qdrant_api_key: str
    qdrant_collection: str = "documents"

    # --- Groq (LLM) ---
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Embedding model (runs locally via sentence-transformers) ---
    embedding_model: str = "all-MiniLM-L6-v2"   # 384-dim, fast, good quality
    embedding_dim: int = 384

    # --- Chunking ---
    chunk_size: int = 800        # characters per chunk
    chunk_overlap: int = 150     # overlap between consecutive chunks

    # --- Retrieval ---
    top_k: int = 5               # how many chunks to retrieve per query

    # --- App / security ---
    api_key: str = "change-me"   # simple shared-secret auth for the API itself
    cors_origins: str = "*"      # comma-separated list in production


settings = Settings()
