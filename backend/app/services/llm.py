"""
Calls Groq's free-tier API to generate the final answer, grounded in the
chunks retrieved from Qdrant. This is the "Generation" half of RAG.
"""
from groq import Groq
from functools import lru_cache
from app.config import settings

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the provided context from the user's uploaded documents.

Rules:
- If the answer is not contained in the context, say you don't have enough information in the uploaded documents to answer — do not make anything up.
- Always cite which document(s) you used, by filename.
- Be concise and direct.
"""


@lru_cache(maxsize=1)
def get_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def generate_answer(question: str, retrieved_chunks: list[dict]) -> str:
    context_blocks = []
    for c in retrieved_chunks:
        context_blocks.append(f"[Source: {c['filename']}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no relevant context found)"

    user_prompt = f"""Context from uploaded documents:

{context}

Question: {question}

Answer using only the context above."""

    client = get_client()
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return completion.choices[0].message.content
