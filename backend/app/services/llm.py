"""
Calls Groq's free-tier API to generate the final answer, grounded in the
chunks retrieved from Qdrant. This is the "Generation" half of RAG.

Two things matter here for the assistant to sound natural instead of like
a retrieval demo:

1. The retrieved chunks are handed to the model as plain, unlabeled text —
   no "[Source: filename.pdf]" tags. This isn't just a prompt instruction
   asking the model to stay quiet about sources; it removes the filename
   from what the model ever sees, so there's nothing for it to accidentally
   repeat back.
2. The system prompt defines a persona (a specific institution's assistant)
   and explicitly forbids retrieval/document language, with an example of
   how to phrase "I don't know" without mentioning documents or context.
"""
from groq import Groq
from functools import lru_cache
from app.config import settings


def _system_prompt() -> str:
    return f"""You are the official AI Assistant for {settings.institution_name}. You speak with the warmth, confidence, and knowledge of a helpful admissions counselor talking to a student — not like a search engine or a document lookup tool.

How you answer:
- Answer naturally and conversationally, in complete sentences.
- Be concise by default. Only go long if the question genuinely needs it.
- Use clean Markdown formatting (headings, bold, bullet lists) where it helps readability — but don't over-format simple answers.
- Speak with the confidence of someone who actually knows this information, not someone summarizing a source.

What to NEVER do, under any circumstances:
- Never say phrases like "according to the provided context," "the documents state," "based on the retrieved information," or anything similar.
- Never mention documents, PDFs, files, filenames, chunks, retrieval, or extraction, in any form.
- Never explain how you found or generated an answer.
- Never mention "context" as a concept the user should be aware of.

When you don't have enough information to answer:
- Do NOT say the context/documents don't contain the answer.
- Instead say something like: "I don't currently have enough information to answer that accurately." or "That level of detail isn't something I have yet — I'd recommend checking with the admissions office directly."
- Only say this when the information genuinely isn't available below — don't hedge on things you do know.

You will be given some background information to answer from. Treat it as your own knowledge, not as an external source you're citing."""


# Rewrites a follow-up question ("what about the deadline for that?") into a
# standalone one ("what is the deadline for ISA?") using recent conversation
# history, before retrieval runs. Without this, a follow-up question is
# embedded and searched on its own — "that" carries no meaning on its own,
# so retrieval pulls irrelevant chunks even though a human would know
# exactly what "that" refers to. Adapted from a technique sometimes called
# "query condensing" in conversational RAG systems.
_CONDENSE_PROMPT = """You are deciding whether a student's latest question depends on the previous conversation.

Rules:
1. If the latest question is already complete and understandable by itself, RETURN IT EXACTLY AS WRITTEN.
2. Do NOT improve wording.
3. Do NOT add extra information.
4. Do NOT merge it with previous discussion.
5. ONLY rewrite if the latest question contains references like:
   "it", "its", "that", "this", "those", "them", "they", "same", "again", "continue", "above", or "previous".

Conversation:
{history}

Latest question:
{question}

Return ONLY the final standalone question.
No explanations.
No quotes.
"""


def _format_history(history: list) -> str:
    # Keep only the last few turns — plenty for resolving pronouns/implicit
    # references, keeps this extra call short and cheap.
    lines = []
    for h in history[-6:]:
        speaker = "Student" if h.role == "user" else "Assistant"
        lines.append(f"{speaker}: {h.content}")
    return "\n".join(lines)



FOLLOW_UP_WORDS = {
    "it", "its", "it's",
    "that", "this", "these", "those",
    "they", "them",
    "same", "again", "continue",
    "above", "previous",
}

def _looks_like_follow_up(question: str) -> bool:
    q = question.lower().strip()
    if q.startswith("what about"):
        return True
    words = set(q.replace("?", "").replace(",", "").split())
    return any(word in words for word in FOLLOW_UP_WORDS)

def condense_question(question: str, history: list) -> str:
    """Rewrite only genuine follow-up questions."""
    if not history:
        return question

    if not _looks_like_follow_up(question):
        return question

    client = get_client()
    prompt = _CONDENSE_PROMPT.format(
        history=_format_history(history),
        question=question,
    )
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=120,
    )
    standalone = (completion.choices[0].message.content or "").strip()
    return standalone if standalone else question


@lru_cache(maxsize=1)
def get_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def generate_answer(question: str, retrieved_chunks: list[dict]) -> str:
    # Deliberately no filename/source labels here — see module docstring.
    context = "\n\n---\n\n".join(c["text"] for c in retrieved_chunks) if retrieved_chunks else ""

    if context:
        user_prompt = f"""Background information:

{context}

Question: {question}"""
    else:
        # No relevant chunks at all — let the persona's "don't know" phrasing handle it.
        user_prompt = f"""No relevant background information is available for this question.

Question: {question}"""

    client = get_client()
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return completion.choices[0].message.content
