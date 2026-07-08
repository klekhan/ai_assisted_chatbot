import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.auth import require_api_key
from app.services import parsing, chunking, embeddings, vectorstore
from app.models.schemas import UploadResponse, DocumentInfo

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE_MB = 20


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '.{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_SIZE_MB}MB.")

    # 1. Extract raw text
    text = parsing.extract_text(file.filename, file_bytes)
    if not text.strip():
        raise HTTPException(400, "No extractable text found in this document.")

    # 2. Split into overlapping chunks
    chunks = chunking.chunk_text(text)
    if not chunks:
        raise HTTPException(400, "Document produced no usable chunks.")

    # 3. Embed each chunk locally
    vectors = embeddings.embed_texts(chunks)

    # 4. Store in Qdrant
    vectorstore.ensure_collection()
    document_id = str(uuid.uuid4())
    vectorstore.upsert_chunks(document_id, file.filename, chunks, vectors)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        chunk_count=len(chunks),
        status="indexed",
    )


@router.get("", response_model=list[DocumentInfo])
async def list_documents():
    vectorstore.ensure_collection()
    return vectorstore.list_documents()


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    vectorstore.delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}
