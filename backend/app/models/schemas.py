from pydantic import BaseModel


# --- Public chat (no retrieval metadata ever included) ---
class HistoryMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    # Recent conversation turns, oldest first. Used only to rewrite follow-up
    # questions ("what about that?") into standalone ones before retrieval —
    # never shown to the end user. Optional and defaults to empty, so old
    # clients / a fresh conversation work unchanged.
    history: list[HistoryMessage] = []


class ChatResponse(BaseModel):
    answer: str
    # Opaque id for this specific answer, used only to attach 👍/👎 feedback
    # to it afterwards via POST /chat/feedback. Not a retrieval/debug field —
    # it never carries chunk text, filenames, or scores.
    message_id: str


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str   # "up" or "down"


# --- Admin: document management ---
class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str   # "created" or "replaced"


# --- Admin: debugging / retrieval inspection ---
class DebugSourceChunk(BaseModel):
    filename: str
    document_id: str
    chunk_index: int | None
    point_id: str
    text: str
    score: float
    # Net accumulated 👍/👎 votes this specific chunk has received across
    # all past answers it contributed to. 0 if it's never been rated.
    # Visible only here, in the admin debug panel — never on public /chat.
    boost: int = 0


class DebugChatResponse(BaseModel):
    answer: str
    # The question actually used for retrieval, after conversation-history
    # rewriting. Same as the original question if there was no history, or
    # if nothing needed rewriting. Shown only in the admin debug panel — this
    # is exactly the kind of "why did it retrieve that" detail that belongs
    # there and nowhere else.
    standalone_question: str
    sources: list[DebugSourceChunk]


class CollectionStats(BaseModel):
    collection_name: str
    total_points: int
    total_documents: int
    vector_size: int
    status: str


# --- Admin: feedback-driven chunk re-ranking ---
class ChunkBoost(BaseModel):
    point_id: str
    boost: int
    updated_at: float


# --- Admin: low-confidence / unanswered questions ---
class UnansweredQuestion(BaseModel):
    id: str
    question: str
    standalone_question: str
    top_score: float | None
    created_at: float
    notified_at: float | None
    resolved: bool


# --- Admin: feedback log ---
class FeedbackEntry(BaseModel):
    id: str
    rating: str
    created_at: float
    question: str
    standalone_question: str
    answer: str


# --- Admin: verified-answer cache (built from 👍 feedback) ---
class VerifiedAnswer(BaseModel):
    point_id: str
    question: str
    answer: str
