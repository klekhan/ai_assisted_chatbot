from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    filename: str
    document_id: str
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str
