"""
Turns extracted document sections into chunks for embedding.

Two strategies:

1. STRUCTURAL — used when parsing.py found real headings (DOCX heading
   styles, PDF font-size-detected headings, or Markdown '#' syntax). Each
   section becomes its own chunk, with its heading kept as part of the
   chunk's text, so a question about one topic retrieves that whole topic
   coherently instead of an arbitrary character-count slice of it.

2. RECURSIVE (fallback) — the general-purpose paragraph/sentence-aware
   splitter. Used whenever a document has too few detected headings (e.g.
   plain .txt, which has no structural signal at all, or a PDF/DOCX that
   genuinely isn't broken into headed sections). This is what keeps every
   document type working correctly, not just well-structured ones.

Why overlap in recursive mode? If a sentence's meaning spans a chunk
boundary, overlap ensures that meaning still appears whole in at least one
chunk, so retrieval doesn't "lose" information that fell on a boundary.
Structural mode doesn't need overlap — each chunk is already a complete,
real section, not an arbitrary window.
"""
from app.config import settings
from app.services.parsing import Section

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

# A document needs at least this many REAL detected headings before
# structural mode is used. Below this, there isn't enough genuine structure
# to justify it, and the recursive fallback does a safer job.
MIN_HEADINGS_FOR_STRUCTURAL_MODE = 2

# If a section's body is still bigger than this multiple of chunk_size, it
# gets sub-split with the recursive splitter instead of becoming one
# oversized chunk.
_STRUCTURAL_SLACK_FACTOR = 1.4


def chunk_sections(sections: list[Section], chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    heading_count = sum(1 for heading, _ in sections if heading)

    if heading_count >= MIN_HEADINGS_FOR_STRUCTURAL_MODE:
        return _chunk_structurally(sections, chunk_size)

    # Not enough real structure — flatten everything and use the
    # general-purpose recursive splitter instead.
    full_text = "\n\n".join(
        (f"{heading}\n{body}" if heading else body)
        for heading, body in sections
        if body.strip() or heading
    ).strip()

    if not full_text:
        return []

    chunks = _split(full_text, SEPARATORS, chunk_size)
    return _add_overlap(chunks, overlap) if overlap > 0 else chunks


def _chunk_structurally(sections: list[Section], chunk_size: int) -> list[str]:
    chunks = []
    max_size = int(chunk_size * _STRUCTURAL_SLACK_FACTOR)

    for heading, body in sections:
        if not body.strip():
            continue
        combined = f"{heading}\n{body}" if heading else body
        if len(combined) <= max_size:
            chunks.append(combined)
        else:
            # Section too big for one chunk — sub-split its body, keeping
            # the heading on each piece so every chunk still carries its
            # topic context.
            for piece in _split(body, SEPARATORS, chunk_size):
                chunks.append(f"{heading}\n{piece}" if heading else piece)

    return chunks


def _split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    sep = separators[0]
    remaining_seps = separators[1:]

    if sep == "":
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
