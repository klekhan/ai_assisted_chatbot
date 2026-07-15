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
