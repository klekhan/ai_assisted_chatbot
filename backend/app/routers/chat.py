from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.services import embeddings, vectorstore, llm
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. Embed the user's question
    query_vector = embeddings.embed_query(request.question)

    # 2. Retrieve the most relevant chunks from Qdrant
    vectorstore.ensure_collection()
    results = vectorstore.search(query_vector, top_k=settings.top_k)

    # 3. Generate an answer grounded in those chunks
    answer = llm.generate_answer(request.question, results)

    return ChatResponse(
        answer=answer,
        sources=[SourceChunk(**r) for r in results],
    )
