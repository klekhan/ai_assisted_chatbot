"""
Public chat endpoint. Deliberately returns ONLY the generated answer —
no filenames, chunk text, scores, or any retrieval metadata. This isn't
just hidden in the UI; it's never present in the API response at all, so
there's nothing for a curious user to find in the browser's Network tab.

For retrieval debugging, see app/routers/admin.py's /admin/debug-chat,
which requires the separate admin key.
"""
from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.services import embeddings, vectorstore, llm
from app.models.schemas import ChatRequest, ChatResponse
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    query_vector = embeddings.embed_query(request.question)

    vectorstore.ensure_collection()
    results = vectorstore.search(query_vector, top_k=settings.top_k)

    answer = llm.generate_answer(request.question, results)

    return ChatResponse(answer=answer)
