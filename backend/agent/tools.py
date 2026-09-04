"""Agent tool registration.

Registers both document-intelligence tools (need a document_id) and
content-generation tools (generate content from scratch using Qwen).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.core.tools import Tool, register_tool
from backend.intelligence.summarizer import summarize_document
from backend.intelligence.notes import generate_notes
from backend.intelligence.quiz import generate_quiz
from backend.intelligence.flashcards import generate_flashcards
from backend.exporters.study_export import export_study_result
from backend.intelligence.models import Summary, Notes, Quiz, Flashcards
from backend.content.service import (
    generate_document_content,
    generate_presentation_content,
    generate_spreadsheet_content,
    DocumentContent,
    PresentationContent,
    SpreadsheetContent,
)


# ---------------------------------------------------------------------------
# Document intelligence tool schemas (require document_id)
# ---------------------------------------------------------------------------

class DocInput(BaseModel):
    document_id: str


class NotesInput(DocInput):
    style: str = 'exam'


class QuizInput(DocInput):
    count: int = 10
    difficulty: str = 'mixed'


class FlashInput(DocInput):
    count: int = 20


class ExportInput(BaseModel):
    result: dict
    format: str
    filename: str


# ---------------------------------------------------------------------------
# Content generation tool schemas (topic-based, no document_id)
# ---------------------------------------------------------------------------

class DocumentGenInput(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    purpose: str = 'educational reference'
    audience: str = 'general readers'
    requirements: list[str] = Field(default_factory=list)
    filename: str = 'document'
    # Full original user request — passed to ContentPlanner for depth/scope detection
    request: str = ''


class PresentationGenInput(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    purpose: str = 'educational presentation'
    audience: str = 'general audience'
    filename: str = 'presentation'
    # Full original user request — passed to ContentPlanner for depth/scope detection
    request: str = ''


class SpreadsheetGenInput(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    count: int = Field(default=20, ge=5, le=100)
    item_type: str = 'interview questions'
    filename: str = 'spreadsheet'


# ---------------------------------------------------------------------------
# Tool wrappers
# ---------------------------------------------------------------------------

def _dump(fn):
    return lambda **kwargs: fn(**kwargs).model_dump()


def _export(result: dict, format: str, filename: str) -> dict:
    if 'questions' in result:
        model = Quiz.model_validate(result)
    elif 'cards' in result:
        model = Flashcards.model_validate(result)
    elif 'sections' in result:
        model = Notes.model_validate(result)
    else:
        model = Summary.model_validate(result)
    return export_study_result(model, format, filename)


def _generate_document(
    topic: str,
    purpose: str,
    audience: str,
    requirements: list[str],
    filename: str,
    request: str = '',
) -> dict:
    """Generate document content from Qwen and return serializable dict."""
    content: DocumentContent = generate_document_content(
        topic=topic,
        purpose=purpose,
        audience=audience,
        requirements=requirements,
        request=request,
    )
    data = content.model_dump()
    # Add convenience fields for the executor / downstream steps
    data['plain_text'] = content.to_plain_text()
    data['paragraphs'] = content.to_paragraphs()
    data['title'] = content.title
    data['filename_base'] = filename
    return data


def _generate_presentation(
    topic: str,
    purpose: str,
    audience: str,
    filename: str,
    request: str = '',
) -> dict:
    """Generate presentation content from Qwen and return serializable dict."""
    content: PresentationContent = generate_presentation_content(
        topic=topic,
        purpose=purpose,
        audience=audience,
        request=request,
    )
    data = content.model_dump()
    data['slides_for_generator'] = content.to_generator_slides()
    data['title'] = content.title
    data['filename_base'] = filename
    return data


def _generate_spreadsheet(
    topic: str,
    count: int,
    item_type: str,
    filename: str,
) -> dict:
    """Generate spreadsheet rows from Qwen and return serializable dict."""
    content: SpreadsheetContent = generate_spreadsheet_content(
        topic=topic,
        count=count,
        item_type=item_type,
    )
    data = content.model_dump()
    data['columns'] = content.columns or ['Question', 'Topic', 'Difficulty', 'Answer']
    data['generator_rows'] = content.to_generator_rows()
    data['sheet_name'] = content.sheet_name
    data['filename_base'] = filename
    return data


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_agent_tools() -> None:
    """Register all agent tools with the tool registry."""

    # --- Document intelligence tools (require an uploaded document) ---
    intelligence_tools = [
        ('summarize_document', 'Summarize an indexed document', DocInput, summarize_document),
        ('generate_notes', 'Generate document notes', NotesInput, generate_notes),
        ('generate_quiz', 'Generate document MCQs', QuizInput, generate_quiz),
        ('generate_flashcards', 'Generate document flashcards', FlashInput, generate_flashcards),
    ]
    for name, description, schema, fn in intelligence_tools:
        register_tool(Tool(name, description, schema, _dump(fn)))

    register_tool(Tool('export_study_result', 'Export a study result using existing generators', ExportInput, _export))

    # --- Content generation tools (topic-based, call Qwen from scratch) ---
    register_tool(Tool(
        'generate_document_content',
        'Generate a structured document about any topic using Qwen',
        DocumentGenInput,
        _generate_document,
    ))
    register_tool(Tool(
        'generate_presentation_content',
        'Generate a structured presentation about any topic using Qwen',
        PresentationGenInput,
        _generate_presentation,
    ))
    register_tool(Tool(
        'generate_spreadsheet_content',
        'Generate structured spreadsheet rows about any topic using Qwen',
        SpreadsheetGenInput,
        _generate_spreadsheet,
    ))
