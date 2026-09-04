"""RAG-grounded chat for uploaded documents.

Reads uploaded PDFs from data/uploads/{document_id}.pdf, chunks the text,
retrieves the most relevant chunks for the user's question, and returns
a context-augmented response via the centralized LLMService.

Design principles:
- Never exposes filesystem paths or chunk IDs to callers.
- Degrades gracefully: if retrieval fails, raises ValueError with a safe message.
- Uses keyword-overlap scoring for specific questions; falls back to the first
  N chunks for vague/overview queries — suitable for CPU-only operation with
  Qwen 2.5 3B, no vector store required.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.config import get_settings
from backend.core.llm import LLMService

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = (ROOT / "data" / "uploads").resolve()

_CHUNK_CHARS = 2000   # characters per chunk
_CHUNK_OVERLAP = 200  # overlap between adjacent chunks
_MAX_RETRIEVE = 3     # chunks sent to the model

# Words that signal "give me an overview" rather than a specific lookup.
# When a query is dominated by these words its keyword score will be ~0
# against normal document text, so we fall back to the first N chunks.
_OVERVIEW_SIGNALS = frozenset({
    "explain", "describe", "overview", "summary", "summarize", "about",
    "tell", "what", "give", "cover", "brief", "discuss", "elaborate",
    "review", "outline", "content", "document", "pdf", "file", "this",
    "me", "the", "a", "an", "is", "are", "it",
})

# Score below which we consider the query too vague for keyword retrieval
_VAGUE_THRESHOLD = 0.05


def _read_uploaded_pdf(document_id: str) -> str:
    """Extract text from an uploaded PDF by its document_id (32-char hex)."""
    if not re.fullmatch(r"[A-Za-z0-9]{32}", document_id):
        raise ValueError("Invalid document ID")
    path = (UPLOAD_DIR / f"{document_id}.pdf").resolve()
    if path.parent != UPLOAD_DIR or not path.is_file():
        raise ValueError("Document not found")
    try:
        from pypdf import PdfReader  # type: ignore[import]
        text = "\n".join(
            page.extract_text() or "" for page in PdfReader(str(path)).pages
        )
    except ImportError as exc:
        raise RuntimeError("PDF reading requires pypdf") from exc
    if not text.strip():
        raise ValueError("Document has no extractable text")
    return text.strip()


def _chunk(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    size = _CHUNK_CHARS
    step = max(size - _CHUNK_OVERLAP, 500)
    return [text[i: i + size] for i in range(0, len(text), step)]


def _score(chunk: str, tokens: frozenset[str]) -> float:
    """Keyword-overlap score between a chunk and the query tokens."""
    if not tokens:
        return 0.0
    chunk_lower = chunk.lower()
    return sum(1 for t in tokens if t in chunk_lower) / len(tokens)


def _is_vague_query(query: str) -> bool:
    """Return True when the query is a generic overview / 'explain this' request."""
    words = set(re.findall(r"\b\w{3,}\b", query.lower()))
    meaningful = words - _OVERVIEW_SIGNALS
    # Fewer than 2 domain-specific words → treat as vague
    return len(meaningful) < 2


def _retrieve(all_chunks: list[str], query: str) -> list[str]:
    """
    Return the most relevant chunks for the query.

    For vague queries (overview, summarise, explain this pdf…) return the
    first _MAX_RETRIEVE chunks — that gives a good document overview.
    For specific questions use keyword-overlap ranking.
    """
    if not all_chunks:
        return []

    if _is_vague_query(query):
        # Overview query: return the opening chunks for a general summary
        return all_chunks[:_MAX_RETRIEVE]

    tokens = frozenset(re.findall(r"\b\w{3,}\b", query.lower())) - _OVERVIEW_SIGNALS
    scored = sorted(
        range(len(all_chunks)),
        key=lambda i: _score(all_chunks[i], tokens),
        reverse=True,
    )
    top = [all_chunks[i] for i in scored[:_MAX_RETRIEVE]]

    # If every chunk scored near-zero, fall back to the first chunks
    best_score = _score(all_chunks[scored[0]], tokens) if scored else 0.0
    if best_score < _VAGUE_THRESHOLD:
        return all_chunks[:_MAX_RETRIEVE]

    return top


def rag_chat(message: str, document_ids: list[str], history: list[dict[str, str]] | None = None) -> str:
    """
    Perform retrieval-augmented generation over uploaded documents.

    Args:
        message: The user's question or instruction.
        document_ids: List of uploaded document IDs (hex strings from /api/documents/upload).

    Returns:
        The LLM's answer grounded in the retrieved document content.

    Raises:
        ValueError: If any document_id is invalid or the document has no text.
        RuntimeError: If PDF reading dependencies are missing.
    """
    settings = get_settings()
    service = LLMService(settings)

    all_chunks: list[str] = []
    for doc_id in document_ids:
        text = _read_uploaded_pdf(doc_id)
        all_chunks.extend(_chunk(text))

    if not all_chunks:
        raise ValueError("No content could be retrieved from the provided documents")

    relevant = _retrieve(all_chunks, message)
    # Keep the prompt compact so CPU-only local models do not spend minutes processing a whole PDF for a short overview question.
    context = "\n\n---\n\n".join(relevant)[:7000]

    # The system prompt must be explicit that:
    # (a) the excerpts ARE the uploaded PDF the user is referring to, and
    # (b) Qwen should answer as if it has read the whole document.
    system_prompt = (
        "You are Apex, a warm and emotionally intelligent AI assistant. Recognize emotional intent, validate briefly, match the user's tone, and remain helpful without claiming human feelings or encouraging dependency. "
        "The user has uploaded a PDF document. "
        "The excerpts below are taken directly from that uploaded PDF. "
        "Use these excerpts to answer the user's question thoroughly and helpfully. "
        "If the excerpts do not contain enough information for a complete answer, "
        "summarise what they do cover and note that the document may contain more detail. "
        "Never say you don't know which PDF the user is referring to — "
        "the excerpts provided ARE the document they uploaded. "
        "Do not invent information that is not in the excerpts. Copy experiment titles exactly as written in the excerpts; never replace them with common textbook examples. If a requested experiment title is not present, say that it was not found instead of guessing. Format the answer with clear Markdown headings, bold key terms, short paragraphs separated by blank lines, and bullet lists where useful. Put any code in fenced code blocks."
    )

    prior_context = ""
    if history:
        prior_context = "\n--- Recent conversation ---\n" + "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in history[-6:] if item.get('content')
        ) + "\n--- End recent conversation ---\n"

    user_prompt = (
        f"{prior_context}--- Excerpts from the uploaded PDF ---\n\n"
        f"{context}\n\n"
        f"--- End of excerpts ---\n\n"
        f"User question: {message}"
    )

    return service.chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
