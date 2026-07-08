"""
Splits long text into overlapping chunks.

Why overlap? If a sentence's meaning spans a chunk boundary, overlap ensures
that meaning still appears whole in at least one chunk, so retrieval doesn't
"lose" information that happened to fall on a boundary.

This is a simple, dependency-free recursive splitter: it tries to break on
paragraph breaks first, then sentences, then falls back to hard character
cuts, so chunks stay as semantically coherent as possible.
"""
from app.config import settings

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    text = text.strip()
    if not text:
        return []

    chunks = _split(text, SEPARATORS, chunk_size)
    return _add_overlap(chunks, overlap) if overlap > 0 else chunks


def _split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    sep = separators[0]
    remaining_seps = separators[1:]

    if sep == "":
        # Last resort: hard cut
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        candidate = (current + sep + part) if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                # This single part is still too big; recurse with a finer separator
                chunks.extend(_split(part, remaining_seps, chunk_size))
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    if len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        overlapped.append(prev_tail + " " + chunks[i])
    return overlapped
