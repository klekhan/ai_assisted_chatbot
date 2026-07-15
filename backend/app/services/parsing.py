"""
Extracts text from uploaded documents — and, where the format actually
supports it, extracts real STRUCTURE (headings + the body text under them),
not a regex guess at structure.

Each format has a different amount of real structural signal available:

- DOCX: Word's own "Heading 1/2/3" paragraph styles. This is ground truth —
  python-docx exposes it directly, no guessing involved.
- PDF: no explicit "this is a heading" flag exists in the format, but font
  size is a very reliable proxy — headings are almost always visibly larger
  and/or bolder than body text in professionally formatted documents. We
  extract per-line font sizes via PyMuPDF and compare each line against the
  document's own median body-text size.
- Markdown: '#' syntax is unambiguous, no detection needed.
- TXT: plain text has no structural signal at all — there is nothing to
  extract here. Callers should expect a single unheaded section and let the
  chunker's recursive fallback handle it.

extract_sections() returns a list of (heading_or_None, body_text) tuples in
document order. chunking.py turns this into chunks, using structural mode
when enough real headings were found, and falling back to plain recursive
splitting otherwise.
"""
import io
import statistics
import re
import fitz  # PyMuPDF
from docx import Document

Section = tuple[str | None, str]


def extract_sections(filename: str, file_bytes: bytes) -> list[Section]:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        return _extract_pdf_sections(file_bytes)
    elif ext == "docx":
        return _extract_docx_sections(file_bytes)
    elif ext == "md":
        return _extract_markdown_sections(file_bytes)
    elif ext == "txt":
        return [(None, file_bytes.decode("utf-8", errors="ignore"))]
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


def sections_to_plain_text(sections: list[Section]) -> str:
    """Flattens sections back into plain text — used only to check whether a
    document produced any usable content at all."""
    parts = []
    for heading, body in sections:
        if heading:
            parts.append(heading)
        if body:
            parts.append(body)
    return "\n\n".join(parts)


# --- PDF: font-size-based heading detection --------------------------------

_BOLD_FLAG = 1 << 4  # PyMuPDF span flag bit for bold text


def _extract_pdf_sections(file_bytes: bytes) -> list[Section]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    lines: list[tuple[str, float, bool]] = []  # (text, max_font_size, is_bold)
    for page in doc:
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                size = max((s.get("size", 0) for s in spans), default=0)
                bold = any((s.get("flags", 0) & _BOLD_FLAG) for s in spans)
                lines.append((text, size, bold))
    doc.close()

    if not lines:
        return [(None, "")]

    body_size = statistics.median(size for _, size, _ in lines)
    # A line counts as a heading if it's noticeably larger than the
    # document's own typical body text, OR bold — but only if it's also
    # short and doesn't end in sentence punctuation, since a bolded phrase
    # mid-sentence shouldn't hijack the whole rest of the paragraph.
    heading_size_threshold = body_size * 1.15

    sections: list[Section] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def flush():
        body_text = " ".join(current_body).strip()
        if body_text or current_heading:
            sections.append((current_heading, body_text))

    for text, size, bold in lines:
        looks_like_heading = (
            (size >= heading_size_threshold or bold)
            and len(text) <= 120
            and not text.endswith(".")
        )
        if looks_like_heading:
            flush()
            current_heading = text
            current_body = []
        else:
            current_body.append(text)
    flush()

    return sections if sections else [(None, " ".join(t for t, _, _ in lines))]


# --- DOCX: real Word heading styles -----------------------------------------

def _extract_docx_sections(file_bytes: bytes) -> list[Section]:
    doc = Document(io.BytesIO(file_bytes))

    sections: list[Section] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def flush():
        body_text = " ".join(current_body).strip()
        if body_text or current_heading:
            sections.append((current_heading, body_text))

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name or "") if para.style else ""
        is_heading = style_name.startswith("Heading") or style_name == "Title"
        if is_heading:
            flush()
            current_heading = text
            current_body = []
        else:
            current_body.append(text)
    flush()

    return sections if sections else [(None, "")]


# --- Markdown: '#' syntax ----------------------------------------------------

_MD_HEADING = re.compile(r"^#{1,6}\s+(.+)$")


def _extract_markdown_sections(file_bytes: bytes) -> list[Section]:
    text = file_bytes.decode("utf-8", errors="ignore")

    sections: list[Section] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def flush():
        body_text = " ".join(current_body).strip()
        if body_text or current_heading:
            sections.append((current_heading, body_text))

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = _MD_HEADING.match(line)
        if match:
            flush()
            current_heading = match.group(1).strip()
            current_body = []
        else:
            current_body.append(line)
    flush()

    return sections if sections else [(None, text)]
