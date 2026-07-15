"""
Everything here requires the admin key (X-Admin-Key header), never the
public API key. This is where documents get added/replaced/deleted, and
where retrieval internals (chunks, scores, stats) are exposed for
debugging — none of which the public /chat endpoint ever reveals.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.auth import require_admin_key
from app.services import parsing, chunking, embeddings, vectorstore, llm
from app.models.schemas import (
    UploadResponse,
    DocumentInfo,
    ChatRequest,
    DebugChatResponse,
    DebugSourceChunk,
    CollectionStats,
)
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_key)])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE_MB = 20


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '.{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_SIZE_MB}MB.")

    sections = parsing.extract_sections(file.filename, file_bytes)
    plain_text = parsing.sections_to_plain_text(sections)
    if not plain_text.strip():
        raise HTTPException(400, "No extractable text found in this document.")

    chunks = chunking.chunk_sections(sections)
    if not chunks:
        raise HTTPException(400, "Document produced no usable chunks.")

    vectors = embeddings.embed_texts(chunks)

    vectorstore.ensure_collection()

    # Deterministic ID from filename: re-uploading "FAQs.pdf" always targets
    # the same document, so this is a clean replace, never a duplicate.
    document_id = vectorstore.document_id_for_filename(file.filename)
    existing = {d["document_id"] for d in vectorstore.list_documents()}
    is_replace = document_id in existing

    vectorstore.replace_document(document_id, file.filename, chunks, vectors)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        chunk_count=len(chunks),
        status="replaced" if is_replace else "created",
    )


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    vectorstore.ensure_collection()
    return vectorstore.list_documents()


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    vectorstore.delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}


@router.post("/debug-chat", response_model=DebugChatResponse)
async def debug_chat(request: ChatRequest):
    """Same retrieval + generation as public /chat, but returns full
    retrieval internals — for verifying the knowledge base is answering
    from the right sources, not for end users."""
    standalone_question = llm.condense_question(request.question, request.history)

    query_vector = embeddings.embed_query(standalone_question)
    vectorstore.ensure_collection()
    results = vectorstore.search(query_vector, top_k=settings.top_k, min_score=settings.min_score)
    answer = llm.generate_answer(standalone_question, results)

    return DebugChatResponse(
        answer=answer,
        standalone_question=standalone_question,
        sources=[DebugSourceChunk(**r) for r in results],
    )


@router.get("/stats", response_model=CollectionStats)
async def stats():
    return vectorstore.collection_stats()
