"""Apex chat router — intent classification.

Determines how a user message should be handled:
  - 'rag_chat'     — document-grounded question (requires document_ids)
  - 'workflow'     — multi-step agent workflow
  - 'single_tool'  — single registered tool call
  - 'simple_chat'  — plain LLM conversation

RAG intent is only returned when document_ids are present AND the message
contains clear document-reference language. Apex does not activate RAG
for general knowledge questions just because a PDF happens to be attached.
"""

from __future__ import annotations

from pydantic import BaseModel

# Phrases that strongly signal the user is asking about an attached document.
_DOCUMENT_SIGNALS = frozenset({
    # Direct references to the file
    "this document", "the document", "this pdf", "the pdf",
    "this file", "the file", "uploaded", "attachment",
    "this text", "the text", "this content",
    # Overview/explain requests
    "explain", "describe", "explain about", "tell me about",
    "about this", "explain the", "describe the", "explain this",
    "overview", "summarize", "summary", "summarise",
    "what is in", "what does", "what is it", "what does it",
    "give me", "give an", "brief",
    # Structural references
    "in this", "from this", "unit", "chapter", "section", "page", "topic",
    "module", "lecture", "part", "appendix",
    # Attribution
    "according to", "based on the", "based on this",
    "from the pdf", "from the document",
    "what does it say", "what does the",
})


_WORKFLOW_KEYWORDS = frozenset({
    "notes", "study guide", "mcq", "quiz", "flashcard",
    "questions", "exam notes", "semester notes",
})

# Keywords that trigger the full agent workflow for direct artifact creation
_CREATION_VERBS = frozenset({"create", "make", "generate", "write", "build", "produce", "draft"})
_CREATION_TARGETS = frozenset({
    "pdf", "excel", "xlsx", "spreadsheet", "powerpoint", "ppt", "presentation",
    "docx", "word document", "word file", "notes", "study guide", "report",
})

_MULTI_STEP_PAIRS = (
    (" and ", ("excel", "pdf", "ppt", "notes", "quiz", "docx")),
    ("export", ("excel", "xlsx", "ppt", "pdf")),
)


class ToolDecision(BaseModel):
    intent: str = "simple_chat"
    tool: str | None = None
    arguments: dict = {}


def _has_document_intent(text: str) -> bool:
    """Return True if the message is clearly about an attached document.

    Uses two signal tiers:
    - STRONG: unambiguous file references — any match is sufficient.
    - WEAK: generic words like 'explain' or 'describe' that only indicate
      document intent when paired with a strong anchor.
    """
    # Strong signals: unambiguous references to the attached document
    _STRONG = frozenset({
        "this document", "the document", "this pdf", "the pdf",
        "this file", "the file", "uploaded", "attachment",
        "this text", "the text", "this content",
        "in this", "from this",
        "from the pdf", "from the document",
        "according to", "based on the", "based on this",
        "what does it say", "what does the",
        "unit", "chapter", "section", "page", "topic",
        "module", "lecture", "appendix", "part",
        "summarize", "summarise", "summary",
    })
    # Weak signals: only meaningful when paired with a strong anchor
    _WEAK = frozenset({
        "explain", "describe", "overview", "brief", "outline",
        "tell me about", "give me", "about this",
        "explain about", "explain the", "describe the",
    })
    if any(signal in text for signal in _STRONG):
        return True
    # Weak + any strong anchor word present → document intent
    if any(signal in text for signal in _WEAK):
        anchors = {"pdf", "document", "file", "text", "uploaded", "attachment"}
        return any(a in text for a in anchors)
    return False


def _is_workflow(text: str) -> bool:
    """Return True for requests that need the agent engine (multi-step or content creation)."""
    # Multi-step creation: contains "and" / "export" plus a format keyword
    for connector, targets in _MULTI_STEP_PAIRS:
        if connector in text and any(t in text for t in targets):
            return True
    # Document intelligence workflows
    if any(kw in text for kw in _WORKFLOW_KEYWORDS):
        if any(fmt in text for fmt in ("excel", "xlsx", "ppt", "pdf", "docx", "export")):
            return True
    # Direct artifact creation — always uses agent workflow so Qwen generates real content
    if any(verb in text for verb in _CREATION_VERBS):
        if any(target in text for target in _CREATION_TARGETS):
            return True
    return False


def decide(message: str, document_ids: list[str] | None = None) -> ToolDecision:
    """Classify a chat message into an intent.

    Args:
        message: The raw user message.
        document_ids: IDs of documents the user has attached, if any.

    Returns:
        A ToolDecision with intent, optional tool name, and arguments.
    """
    text = message.lower()
    has_docs = bool(document_ids)

    # ---- RAG takes priority for questions about an attached document -----
    # A request such as "summarize this PDF" must use the uploaded PDF,
    # not the generic workflow engine.
    if has_docs and _has_document_intent(text):
        return ToolDecision(intent="rag_chat")

    # ---- Workflow: agent engine handles multi-step creation ----------------
    workflow_words = sum(
        keyword in text
        for keyword in (
            " then ", " and ", "export", "excel", "ppt", "notes",
            "mcq", "quiz", "flashcard", "summarize", "summary",
        )
    )
    if (
        workflow_words >= 2
        and any(
            keyword in text
            for keyword in ("document", "pdf", "notes", "quiz", "mcq", "flashcard", "summary")
        )
    ) or _is_workflow(text):
        return ToolDecision(intent="workflow")

    # ---- RAG: document-grounded question with attached documents -----------
    if has_docs and _has_document_intent(text):
        return ToolDecision(intent="rag_chat")

    # ---- Code intelligence: single-tool dispatch ---------------------------
    language = next(
        (
            lang for lang in (
                "python", "java", "javascript", "typescript",
                "c++", "cpp", "c", "sql", "html", "css", "bash",
            )
            if lang in text
        ),
        "python",
    )

    code_intents = [
        ("debug", "debug_code"),
        ("refactor", "refactor_code"),
        ("review", "review_code"),
        ("explain", "explain_code"),
        ("complexity", "analyze_complexity"),
        ("test", "generate_tests"),
        ("documentation", "generate_documentation"),
    ]
    for key, tool in code_intents:
        if key in text and any(
            kw in text for kw in ("code", "program", "function", "query", "script")
        ):
            return ToolDecision(
                intent="single_tool",
                tool=tool,
                arguments={"code": message, "language": language},
            )

    if any(kw in text for kw in ("write a ", "write an ", "generate code", "program for", "implement ")):
        return ToolDecision(
            intent="single_tool",
            tool="generate_code",
            arguments={"language": language, "task": message},
        )

    # ---- Default: plain LLM chat ------------------------------------------
    return ToolDecision()
