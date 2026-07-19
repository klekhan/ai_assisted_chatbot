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
    # get_client() previously left this unset, which falls back to the SDK's
    # short internal default (a few seconds). A single upsert() call for an
    # entire document's points — especially now that each point carries both
    # a dense AND sparse vector under the hybrid schema — can genuinely take
    # longer than that on a free-tier cluster once a document has more than
    # a couple dozen chunks. This is the actual cause of "some PDFs upload
    # fine, larger ones time out": it was never about size, correctness, or
    # schema — just an unset timeout meeting a big enough single request.
    qdrant_timeout_seconds: int = 60
    # upsert_chunks() previously sent ALL of a document's points in one
    # request regardless of count. Batching keeps every single request small
    # and fast regardless of how large the source document is, and means a
    # failure only has to retry/redo one batch, not the entire document.
    qdrant_upsert_batch_size: int = 64

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
    top_k: int = 5                # how many chunks are finally handed to the LLM
    min_score: float = 0.15       # discard retrieved chunks below this similarity — avoids
                                   # answering off a weak, barely-related match

    # --- Hybrid search (dense + sparse BM25, fused with Qdrant's RRF) ---
    # BM25 catches exact keywords/IDs/names that embeddings sometimes blur;
    # dense catches paraphrases/meaning. Fusing both beats either alone.
    # "Qdrant/bm25" is a plain statistical model (~10MB, no neural network),
    # so this stays within the same tight-memory budget as the rest of the app.
    enable_hybrid_search: bool = True
    sparse_model: str = "Qdrant/bm25"
    retrieval_fetch_k: int = 20   # candidates pulled from EACH of dense/sparse before fusion

    # --- Feedback-driven re-ranking ("gets smarter over time") ---
    # Each net 👍/👎 a chunk has accumulated (see feedback_store.chunk_feedback)
    # shifts its similarity score by this much per point when ranking search
    # results — small enough that a wildly irrelevant chunk still can't win,
    # but enough to reorder close calls and let a track record matter.
    chunk_boost_weight: float = 0.01
    chunk_boost_cap: int = 10   # ignore any further boost beyond +/-10 net votes

    # --- Confidence / "don't know" handling ---
    # Separate from min_score (which filters individual chunks). This looks
    # at the TOP chunk's score after retrieval: if even the best match is
    # this weak, the question is treated as effectively unanswered — logged
    # and (optionally) emailed to the admin — even if the LLM still produces
    # some hedged answer text.
    low_confidence_score: float = 0.35

    # --- Verified-answer cache (semantic cache / "learns" from feedback) ---
    # When a user marks an answer 👍, it's embedded and stored here. Future
    # questions that are near-duplicates of a verified one are answered
    # straight from this cache — skipping retrieval + generation entirely —
    # so the bot gets faster AND more consistent on repeat questions over
    # time, without ever touching model weights.
    verified_qa_collection: str = "verified_answers"
    verified_qa_score_threshold: float = 0.92

    # --- Unanswered-question logging + admin email alert ---
    # Postgres (Supabase) connection string — replaces the old local SQLite
    # file, which lived on Render's ephemeral disk and was wiped on every
    # redeploy/restart, and could also fill up the free tier's small disk
    # quota over time since it grew with every chat message logged.
    # Use Supabase's "Connection Pooling" URI (port 6543), not the direct
    # connection (port 5432) — Render can open many short-lived connections
    # and Supabase's free tier caps direct connections fairly low.
    supabase_db_url: str = ""
    notify_admin_on_low_confidence: bool = True
    # Same question won't re-trigger an email more than once within this
    # window, so one confused topic doesn't spam the inbox.
    notify_cooldown_minutes: int = 60

    smtp_host: str = ""            # empty = notifications are logged only, never sent
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = ""
    admin_notify_email: str = ""   # where "please update the docs" emails go

    # --- App / security ---
    api_key: str = "change-me"     # shared key the public frontend uses to call /chat
    admin_key: str = "change-me-admin"   # separate, stronger key for the admin dashboard
    cors_origins: str = "*"        # comma-separated list in production

    # --- Knowledge assistant branding (shown on the public empty-state) ---
    kb_topics: str = "Admissions,Fees,Placements,Hostel,Courses"
    institution_name: str = "PES University"


settings = Settings()
