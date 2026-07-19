"""
Public chat endpoint. Deliberately returns ONLY the generated answer (plus
an opaque message_id for feedback) — no filenames, chunk text, scores, or
any retrieval metadata. This isn't just hidden in the UI; it's never
present in the API response at all, so there's nothing for a curious user
to find in the browser's Network tab.

For retrieval debugging, see app/routers/admin.py's /admin/debug-chat,
which requires the separate admin key.

Request flow, in order:
1. Condense the question using conversation history (unchanged).
2. Check the verified-answer cache — a near-duplicate of a previously
   👍'd question is answered straight from there, skipping retrieval and
   the LLM call entirely (faster, and consistent with the approved answer).
3. Otherwise, run hybrid (dense + BM25) retrieval — ranking here is also
   nudged by any accumulated 👍/👎 history on individual chunks (see
   vectorstore.search()'s feedback-boost step) — then generate an answer.
4. If the best retrieved match is weak (or there's no match at all), log
   the question as "unanswered" and kick off a background email to the
   admin — this is the auto-flagging behaviour.
5. Every answer is logged with the chunk ids that produced it, so a later
   POST /chat/feedback call can attribute a 👍/👎 back to those specific
   chunks (see submit_feedback below) — this is the "learns from
   interactions over time" loop.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from app.auth import require_api_key
from app.services import embeddings, vectorstore, llm, feedback_store, notifications
from app.models.schemas import ChatRequest, ChatResponse, FeedbackRequest
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(require_api_key)])


def _flag_if_low_confidence(background_tasks: BackgroundTasks, question: str, standalone_question: str, top_score: float | None):
    if top_score is not None and top_score >= settings.low_confidence_score:
        return  # confident enough — nothing to flag

    entry_id = feedback_store.log_unanswered(question, standalone_question, top_score)

    if settings.notify_admin_on_low_confidence and feedback_store.should_notify(standalone_question):
        feedback_store.mark_notified(entry_id)
        background_tasks.add_task(
            notifications.notify_unanswered_question, question, standalone_question, top_score
        )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    standalone_question = llm.condense_question(request.question, request.history)

    query_vector = embeddings.embed_query(standalone_question)

    # 1. Verified-answer cache: skip retrieval + generation on a
    #    near-duplicate of a question that was already answered and 👍'd.
    vectorstore.ensure_verified_collection()
    cached = vectorstore.search_verified_answer(query_vector)
    if cached:
        message_id = feedback_store.log_message(
            request.question, standalone_question, cached["answer"], cached["score"]
        )
        return ChatResponse(answer=cached["answer"], message_id=message_id)

    # 2. Hybrid retrieval + generation.
    vectorstore.ensure_collection()
    results = vectorstore.search(
        query_vector,
        top_k=settings.top_k,
        min_score=settings.min_score,
        query_text=standalone_question,
    )

    answer = llm.generate_answer(standalone_question, results)

    top_score = results[0]["score"] if results else None
    source_point_ids = [r["point_id"] for r in results]
    message_id = feedback_store.log_message(
        request.question, standalone_question, answer, top_score, source_point_ids
    )

    # 3. Auto-flag + notify admin if this was a weak/no match.
    _flag_if_low_confidence(background_tasks, request.question, standalone_question, top_score)

    return ChatResponse(answer=answer, message_id=message_id)


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    if request.rating not in ("up", "down"):
        raise HTTPException(400, "rating must be 'up' or 'down'")

    message = feedback_store.get_message(request.message_id)
    if not message:
        raise HTTPException(404, "Unknown message_id")

    feedback_store.log_feedback(request.message_id, request.rating)

    # Nudge every chunk that fed this answer: +1 net vote on 👍, -1 on 👎.
    # vectorstore.search() reads these back and lets a proven track record
    # tip close ranking calls in future queries — this is what makes
    # retrieval keep improving from real conversations, without retraining
    # the embedding model or the LLM.
    delta = 1 if request.rating == "up" else -1
    feedback_store.apply_chunk_boost(message["source_point_ids"], delta)

    # A 👍 additionally promotes this exact Q&A pair into the verified-answer
    # cache, so the next near-duplicate question is answered instantly and
    # consistently from here instead of re-running retrieval + generation.
    if request.rating == "up":
        vectorstore.ensure_verified_collection()
        question_vector = embeddings.embed_query(message["standalone_question"])
        vectorstore.upsert_verified_answer(message["standalone_question"], message["answer"], question_vector)

    return {"status": "recorded"}
