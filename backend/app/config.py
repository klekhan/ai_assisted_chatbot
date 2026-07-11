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
    embedding_model: str = "BAAI/bge-small-en-v1.5"   # 384-dim, ONNX, low memory
    embedding_dim: int = 384

    # --- Chunking ---
    chunk_size: int = 800        # characters per chunk
    chunk_overlap: int = 150     # overlap between consecutive chunks

    # --- Retrieval ---
    top_k: int = 5               # how many chunks to retrieve per query

    # --- App / security ---
    api_key: str = "change-me"     # shared key the public frontend uses to call /chat
    admin_key: str = "change-me-admin"   # separate, stronger key for the admin dashboard
    cors_origins: str = "*"        # comma-separated list in production

    # --- Knowledge assistant branding (shown on the public empty-state) ---
    kb_topics: str = "Admissions,Fees,Placements,Hostel,Courses"
    institution_name: str = "PES University"


settings = Settings()
