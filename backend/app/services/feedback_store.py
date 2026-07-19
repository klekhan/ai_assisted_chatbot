"""
Postgres (Supabase) store for things the vector DB isn't suited for:

1. unanswered_questions — every question that came back low-confidence
   (see chat.py), so an admin can see what the knowledge base is missing.
   This is what /admin/unanswered and the low-confidence email are backed by.

2. chat_feedback — every 👍/👎 a user gives an answer. 👍 promotes the
   answer into the verified-answer cache (vectorstore.py); 👎 stays here
   for an admin to review — a concrete, low-effort signal for which docs
   need fixing.

3. chunk_feedback — a running per-chunk score derived from (2): every chunk
   that contributed to a 👍'd answer gets +1, every chunk in a 👎'd answer
   gets -1. vectorstore.search() reads this table and nudges ranking
   accordingly. This is the mechanism behind "RAG gets smarter over time
   without retraining" — retrieval itself adapts from real usage, on top
   of (unchanged) embeddings and an (unchanged) LLM.

Originally SQLite on local disk. Moved to Postgres (Supabase's free tier)
because Render's disk is ephemeral — every redeploy wiped this data — and
had a small quota that chat logging could fill up over time since every
single chat message was being written to it with no pruning.

Uses a connection pool (opened once at startup, reused across requests)
rather than connecting per call — this data now lives over the network on
Supabase, not a local file, so a fresh TCP+TLS handshake on every chat
message would add real, avoidable latency to every response.
"""
import json
import time
import uuid
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None


def init_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.supabase_db_url,
            min_size=1,
            max_size=5,
            open=True,
        )


def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def _connect():
    if _pool is None:
        init_pool()
    with _pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn


def init_db():
    init_pool()
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unanswered_questions (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                standalone_question TEXT NOT NULL,
                top_score DOUBLE PRECISION,
                created_at DOUBLE PRECISION NOT NULL,
                notified_at DOUBLE PRECISION,
                resolved INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                standalone_question TEXT NOT NULL,
                answer TEXT NOT NULL,
                top_score DOUBLE PRECISION,
                source_point_ids TEXT,
                created_at DOUBLE PRECISION NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_feedback (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                rating TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunk_feedback (
                point_id TEXT PRIMARY KEY,
                boost INTEGER NOT NULL DEFAULT 0,
                updated_at DOUBLE PRECISION NOT NULL
            )
        """)
        conn.commit()


# --- Chat message log (needed so /chat/feedback can look up what a
#     message_id actually refers to when a rating comes in later) ---

def log_message(
    question: str,
    standalone_question: str,
    answer: str,
    top_score: float | None,
    source_point_ids: list[str] | None = None,
) -> str:
    message_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, question, standalone_question, answer, top_score, source_point_ids, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                message_id, question, standalone_question, answer, top_score,
                json.dumps(source_point_ids or []), time.time(),
            ),
        )
        conn.commit()
    return message_id


def get_message(message_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM chat_messages WHERE id = %s", (message_id,)).fetchone()
        if not row:
            return None
        msg = dict(row)
        msg["source_point_ids"] = json.loads(msg["source_point_ids"] or "[]")
        return msg


# --- Unanswered / low-confidence questions ---

def log_unanswered(question: str, standalone_question: str, top_score: float | None) -> str:
    entry_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO unanswered_questions (id, question, standalone_question, top_score, created_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (entry_id, question, standalone_question, top_score, time.time()),
        )
        conn.commit()
    return entry_id


def should_notify(standalone_question: str) -> bool:
    """True unless this same question was already flagged (and notified)
    within the cooldown window — keeps one confused topic from spamming
    the admin's inbox with a separate email per near-identical question."""
    cutoff = time.time() - settings.notify_cooldown_minutes * 60
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM unanswered_questions "
            "WHERE standalone_question = %s AND notified_at IS NOT NULL AND notified_at >= %s LIMIT 1",
            (standalone_question, cutoff),
        ).fetchone()
    return row is None


def mark_notified(entry_id: str):
    with _connect() as conn:
        conn.execute("UPDATE unanswered_questions SET notified_at = %s WHERE id = %s", (time.time(), entry_id))
        conn.commit()


def list_unanswered(include_resolved: bool = False) -> list[dict]:
    query = "SELECT * FROM unanswered_questions"
    if not include_resolved:
        query += " WHERE resolved = 0"
    query += " ORDER BY created_at DESC LIMIT 200"
    with _connect() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


def resolve_unanswered(entry_id: str):
    with _connect() as conn:
        conn.execute("UPDATE unanswered_questions SET resolved = 1 WHERE id = %s", (entry_id,))
        conn.commit()


def resolve_unanswered_group(standalone_question: str) -> int:
    """Resolves every open row that shares the same standalone_question in
    one statement, instead of the frontend making one call per duplicate —
    duplicates are extremely common here by design (the same confused topic
    gets asked many times before someone notices and fixes it)."""
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE unanswered_questions SET resolved = 1 WHERE standalone_question = %s AND resolved = 0",
            (standalone_question,),
        )
        count = cursor.rowcount
        conn.commit()
        return count


# --- Feedback (👍 / 👎) ---

def log_feedback(message_id: str, rating: str) -> str:
    feedback_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_feedback (id, message_id, rating, created_at) VALUES (%s, %s, %s, %s)",
            (feedback_id, message_id, rating, time.time()),
        )
        conn.commit()
    return feedback_id


def list_feedback(rating: str | None = None) -> list[dict]:
    query = """
        SELECT chat_feedback.id, chat_feedback.rating, chat_feedback.created_at,
               chat_messages.question, chat_messages.standalone_question, chat_messages.answer
        FROM chat_feedback
        JOIN chat_messages ON chat_messages.id = chat_feedback.message_id
    """
    params: tuple = ()
    if rating:
        query += " WHERE chat_feedback.rating = %s"
        params = (rating,)
    query += " ORDER BY chat_feedback.created_at DESC LIMIT 200"
    with _connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


# --- Per-chunk feedback boost -------------------------------------------
#
# This is what makes retrieval itself improve from usage over time, without
# retraining anything: every chunk that helped produce a 👍'd answer earns
# +1, every chunk in a 👎'd answer earns -1. vectorstore.search() reads
# these boosts back and nudges ranking on the next query that retrieves the
# same chunk — so chunks that have proven useful in practice keep floating
# up, and ones that keep leading to bad answers keep sinking, purely from
# real conversations.

def apply_chunk_boost(point_ids: list[str], delta: int):
    if not point_ids:
        return
    now = time.time()
    with _connect() as conn:
        for point_id in point_ids:
            conn.execute(
                """
                INSERT INTO chunk_feedback (point_id, boost, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (point_id) DO UPDATE SET
                    boost = chunk_feedback.boost + EXCLUDED.boost,
                    updated_at = EXCLUDED.updated_at
                """,
                (point_id, delta, now),
            )
        conn.commit()


def get_chunk_boosts(point_ids: list[str]) -> dict[str, int]:
    if not point_ids:
        return {}
    placeholders = ",".join("%s" for _ in point_ids)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT point_id, boost FROM chunk_feedback WHERE point_id IN ({placeholders})",
            point_ids,
        ).fetchall()
    return {r["point_id"]: r["boost"] for r in rows}


def list_chunk_boosts(nonzero_only: bool = True) -> list[dict]:
    query = "SELECT point_id, boost, updated_at FROM chunk_feedback"
    if nonzero_only:
        query += " WHERE boost != 0"
    query += " ORDER BY boost DESC LIMIT 200"
    with _connect() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]
