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
