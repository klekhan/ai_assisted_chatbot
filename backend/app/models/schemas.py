from pydantic import BaseModel


# --- Public chat (no retrieval metadata ever included) ---
class ChatRequest(BaseModel):
    question: str


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
    sources: list[DebugSourceChunk]


class CollectionStats(BaseModel):
    collection_name: str
    total_points: int
    total_documents: int
    vector_size: int
    status: str
