"""TennuX Content Generation Service.

All content is generated dynamically by Qwen 2.5 3B via the centralized
AIRuntime / LLMService.  This service does NOT hard-code any topic content.

Architecture:
    User request
        → ContentPlanner.plan()          (scope + depth + section outline)
            → ContentService             (builds detailed prompts from the plan)
                → LLMService             (→ AIRuntime → OllamaProvider → Qwen)
                    → Structured Pydantic output
                        → Validation
                            → Generator  (PDF / Excel / PPT / DOCX)

Rules:
  - Never hard-code topic content.
  - Never bypass the AI Runtime.
  - Validate every output; raise ValueError on failure — do not return empty.
  - One bounded repair attempt via runtime/validation.parse_structured.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from backend.content.fact_checker import (
    check_and_correct,
    check_document_sections,
    check_slides,
)
from backend.content.planner import (
    ContentPlan,
    plan as make_plan,
    DEPTH_QUICK,
    DEPTH_COMPREHENSIVE,
    TASK_PROGRAMMING,
    TASK_STUDY_NOTES,
)
from backend.core.llm import LLMService

log = logging.getLogger('apex.content')


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class DocumentSection(BaseModel):
    heading: str = Field(min_length=1)
    paragraphs: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def has_content(self) -> 'DocumentSection':
        total = sum(len(p.strip()) for p in self.paragraphs) + sum(len(b.strip()) for b in self.bullet_points)
        if total < 10:
            raise ValueError(f'Section "{self.heading}" has no meaningful content')
        return self


class DocumentContent(BaseModel):
    title: str = Field(min_length=1)
    subtitle: str | None = None
    sections: list[DocumentSection] = Field(min_length=1)
    conclusion: str | None = None

    @model_validator(mode='after')
    def validate_content(self) -> 'DocumentContent':
        if not self.title.strip():
            raise ValueError('Document title is empty')
        if not self.sections:
            raise ValueError('Document has no sections')
        return self

    def to_plain_text(self) -> str:
        """Render to a plain-text string suitable for the PDF generator."""
        lines: list[str] = [self.title.upper()]
        if self.subtitle:
            lines.append(self.subtitle)
        lines.append('')
        for section in self.sections:
            lines.append(section.heading)
            for para in section.paragraphs:
                if para.strip():
                    lines.append(para.strip())
            for bullet in section.bullet_points:
                if bullet.strip():
                    lines.append(f'• {bullet.strip()}')
            lines.append('')
        if self.conclusion:
            lines.append('Conclusion')
            lines.append(self.conclusion.strip())
        return '\n'.join(lines)

    def to_paragraphs(self) -> list[str]:
        """Render to a list of paragraphs for DOCX generator."""
        parts: list[str] = []
        if self.subtitle:
            parts.append(self.subtitle)
        for section in self.sections:
            parts.append(section.heading)
            parts.extend(p.strip() for p in section.paragraphs if p.strip())
            parts.extend(f'• {b.strip()}' for b in section.bullet_points if b.strip())
        if self.conclusion:
            parts.append('Conclusion')
            parts.append(self.conclusion.strip())
        return parts


class SlideContent(BaseModel):
    title: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode='after')
    def has_bullets(self) -> 'SlideContent':
        if not self.bullets:
            raise ValueError(f'Slide "{self.title}" has no bullet points')
        return self


class PresentationContent(BaseModel):
    title: str = Field(min_length=1)
    slides: list[SlideContent] = Field(min_length=2)

    @model_validator(mode='after')
    def validate_deck(self) -> 'PresentationContent':
        if not self.title.strip():
            raise ValueError('Presentation title is empty')
        if len(self.slides) < 2:
            raise ValueError('Presentation must have at least 2 slides')
        return self

    def to_generator_slides(self) -> list[dict[str, Any]]:
        """Convert to the format expected by create_ppt."""
        return [
            {'title': slide.title, 'bullet_points': slide.bullets}
            for slide in self.slides
        ]


class SpreadsheetRow(BaseModel):
    question: str = Field(min_length=1)
    topic: str = ''
    difficulty: str = 'medium'
    answer: str = ''


class SpreadsheetContent(BaseModel):
    sheet_name: str = 'Sheet1'
    columns: list[str] = Field(default_factory=list)
    rows: list[SpreadsheetRow] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_rows(self) -> 'SpreadsheetContent':
        if not self.rows:
            raise ValueError('Spreadsheet has no rows')
        return self

    def to_generator_rows(self) -> list[list[object]]:
        return [
            [r.question, r.topic, r.difficulty, r.answer]
            for r in self.rows
        ]


# ---------------------------------------------------------------------------
# Prompt builders — driven by ContentPlan, no content is hard-coded here
# ---------------------------------------------------------------------------

def _document_prompt(topic: str, purpose: str, audience: str, requirements: list[str], content_plan: ContentPlan | None = None) -> str:
    reqs = '\n'.join(f'- {r}' for r in requirements) if requirements else '- Cover the topic thoroughly'

    if content_plan is not None:
        cp = content_plan
        depth_instruction = cp.depth_instruction()
        structure_instruction = cp.structure_instruction()
        min_sections = cp.min_sections
        code_instruction = (
            '\n- Include actual working code examples with comments in the appropriate sections.'
            if cp.include_code else ''
        )
        examples_instruction = (
            '\n- Include at least one concrete real-world example per major section.'
            if cp.include_examples else ''
        )
        exam_instruction = (
            '\n- Add exam/interview-relevant points and common pitfalls where appropriate.'
            if cp.include_exam_notes else ''
        )
        section_instruction = (
            f'\n- Generate at least {min_sections} sections. '
            f'For broad topics, generate as many sections as needed to cover all major aspects.'
        )
        quality_instruction = (
            '\n- Every section must have substantive paragraphs with real explanations — '
            'not just headings with a single bullet point.'
            '\n- Do NOT pad with filler. Every sentence must add value.'
        )
    else:
        depth_instruction = 'Provide thorough coverage of the topic.'
        structure_instruction = 'Structure logically with introduction, core concepts, detailed sections, examples, and conclusion.'
        code_instruction = ''
        examples_instruction = ''
        exam_instruction = ''
        section_instruction = '\n- Include at least 5 sections.'
        quality_instruction = ''

    return (
        f'You are a technical writer. Generate a well-structured document about the following topic.\n\n'
        f'Topic: {topic}\n'
        f'Purpose: {purpose}\n'
        f'Audience: {audience}\n'
        f'Requirements:\n{reqs}\n\n'
        f'Content depth: {depth_instruction}\n'
        f'Content structure: {structure_instruction}\n\n'
        f'Important rules:{section_instruction}{code_instruction}{examples_instruction}{exam_instruction}{quality_instruction}\n\n'
        f'Return ONLY a JSON object with this exact structure:\n'
        f'{{\n'
        f'  "title": "document title",\n'
        f'  "subtitle": "optional subtitle or null",\n'
        f'  "sections": [\n'
        f'    {{\n'
        f'      "heading": "section heading",\n'
        f'      "paragraphs": ["paragraph 1 with full explanation", "paragraph 2"],\n'
        f'      "bullet_points": ["key point 1", "key point 2"]\n'
        f'    }}\n'
        f'  ],\n'
        f'  "conclusion": "comprehensive conclusion paragraph or null"\n'
        f'}}\n\n'
        f'Each section must use paragraphs for explanations and bullet_points for key facts. '
        f'Never return a section with only a heading and no content.'
    )


def _presentation_prompt(topic: str, purpose: str, audience: str, content_plan: ContentPlan | None = None) -> str:
    if content_plan is not None:
        slide_count = content_plan.slide_count
        depth_instruction = content_plan.depth_instruction()
        bullets_per_slide = 5 if content_plan.depth == DEPTH_COMPREHENSIVE else 4 if content_plan.depth != DEPTH_QUICK else 3
    else:
        slide_count = 8
        depth_instruction = 'Provide good coverage of the topic.'
        bullets_per_slide = 4

    return (
        f'You are a presentation designer. Generate a structured presentation about the following topic.\n\n'
        f'Topic: {topic}\n'
        f'Purpose: {purpose}\n'
        f'Audience: {audience}\n\n'
        f'Content depth: {depth_instruction}\n\n'
        f'Rules:\n'
        f'- Generate exactly {slide_count} slides (title/intro + content slides + conclusion).\n'
        f'- Each content slide must have at least {bullets_per_slide} informative bullet points.\n'
        f'- Bullet points must be substantive — at least one full sentence each, not single words.\n'
        f'- Cover all major aspects of the topic across the slides.\n'
        f'- Do NOT repeat the same points across slides.\n\n'
        f'Return ONLY a JSON object with this exact structure:\n'
        f'{{\n'
        f'  "title": "presentation title",\n'
        f'  "slides": [\n'
        f'    {{\n'
        f'      "title": "slide title",\n'
        f'      "bullets": ["full sentence bullet 1", "full sentence bullet 2", "full sentence bullet 3"],\n'
        f'      "notes": "optional speaker notes or null"\n'
        f'    }}\n'
        f'  ]\n'
        f'}}\n\n'
        f'Slides must follow: Introduction → Core Concepts → Detailed Sections → Examples/Applications → Conclusion.'
    )


def _spreadsheet_prompt(topic: str, count: int, item_type: str) -> str:
    return (
        f'You are a content expert. Generate {count} {item_type} about "{topic}".\n\n'
        f'Rules:\n'
        f'- Generate exactly {count} rows.\n'
        f'- Each row must have a complete, non-trivial question and a thorough answer.\n'
        f'- Cover diverse sub-topics within "{topic}" — do not repeat similar questions.\n'
        f'- Vary difficulty: roughly 30% easy, 50% medium, 20% hard.\n\n'
        f'Return ONLY a JSON object with this exact structure:\n'
        f'{{\n'
        f'  "sheet_name": "descriptive sheet name",\n'
        f'  "columns": ["Question", "Topic", "Difficulty", "Answer"],\n'
        f'  "rows": [\n'
        f'    {{\n'
        f'      "question": "the question text",\n'
        f'      "topic": "specific sub-topic",\n'
        f'      "difficulty": "easy|medium|hard",\n'
        f'      "answer": "complete answer"\n'
        f'    }}\n'
        f'  ]\n'
        f'}}\n'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_document_content(
    topic: str,
    purpose: str = 'educational reference',
    audience: str = 'general readers',
    requirements: list[str] | None = None,
    request: str = '',
    *,
    service: LLMService | None = None,
    request_id: str | None = None,
) -> DocumentContent:
    """Generate structured document content about a topic using Qwen.

    Uses ContentPlanner to determine scope, depth, and section requirements
    before building the prompt.  Validates output and raises ValueError on failure.
    Never returns empty or placeholder content.
    """
    service = service or LLMService()
    content_plan = make_plan(topic, request or purpose, purpose=purpose, audience=audience)
    prompt = _document_prompt(topic, purpose, audience, requirements or [], content_plan)
    messages = [
        {
            'role': 'system',
            'content': (
                'You generate structured JSON documents. Return only valid JSON. '
                'Never truncate. Never summarize — generate full content for every section.'
            ),
        },
        {'role': 'user', 'content': prompt},
    ]
    log.info(
        'content.generate_document topic=%r depth=%s task=%s sections_min=%d request_id=%s',
        topic, content_plan.depth, content_plan.task_type, content_plan.min_sections, request_id,
    )

    try:
        result = service.generate_structured(messages, DocumentContent)
        if not isinstance(result, DocumentContent):
            raise ValueError('Unexpected result type from structured generation')

        # --- Stage: Factuality check + correction ----------------------------
        sections_data = [s.model_dump() for s in result.sections]
        fc = check_document_sections(sections_data)
        if fc.violations:
            log.info(
                'content.generate_document fact_check corrected=%d topic=%r request_id=%s',
                len(fc.violations), topic, request_id,
            )
            # Re-validate corrected sections
            corrected_sections = []
            for s in sections_data:
                corrected_sections.append(DocumentSection(**s))
            result = DocumentContent(
                title=result.title,
                subtitle=result.subtitle,
                sections=corrected_sections,
                conclusion=result.conclusion,
            )
        # ---------------------------------------------------------------------

        log.info(
            'content.generate_document success sections=%d request_id=%s',
            len(result.sections), request_id,
        )
        return result
    except Exception as exc:
        log.warning('content.generate_document failed request_id=%s error=%s', request_id, exc)
        raise ValueError(f'Content generation failed for topic "{topic}": {exc}') from exc


def generate_presentation_content(
    topic: str,
    purpose: str = 'educational presentation',
    audience: str = 'general audience',
    request: str = '',
    *,
    service: LLMService | None = None,
    request_id: str | None = None,
) -> PresentationContent:
    """Generate structured presentation content about a topic using Qwen."""
    service = service or LLMService()
    content_plan = make_plan(topic, request or purpose, purpose=purpose, audience=audience)
    prompt = _presentation_prompt(topic, purpose, audience, content_plan)
    messages = [
        {
            'role': 'system',
            'content': (
                'You generate structured JSON presentations. Return only valid JSON. '
                'Never truncate. Each slide must have full informative bullet points.'
            ),
        },
        {'role': 'user', 'content': prompt},
    ]
    log.info(
        'content.generate_presentation topic=%r depth=%s slides=%d request_id=%s',
        topic, content_plan.depth, content_plan.slide_count, request_id,
    )

    try:
        result = service.generate_structured(messages, PresentationContent)
        if not isinstance(result, PresentationContent):
            raise ValueError('Unexpected result type from structured generation')

        # --- Stage: Factuality check + correction ----------------------------
        slides_data = [s.model_dump() for s in result.slides]
        fc = check_slides(slides_data)
        if fc.violations:
            log.info(
                'content.generate_presentation fact_check corrected=%d topic=%r request_id=%s',
                len(fc.violations), topic, request_id,
            )
            corrected_slides = [SlideContent(**s) for s in slides_data]
            result = PresentationContent(title=result.title, slides=corrected_slides)
        # ---------------------------------------------------------------------

        log.info(
            'content.generate_presentation success slides=%d request_id=%s',
            len(result.slides), request_id,
        )
        return result
    except Exception as exc:
        log.warning('content.generate_presentation failed request_id=%s error=%s', request_id, exc)
        raise ValueError(f'Presentation generation failed for topic "{topic}": {exc}') from exc


def generate_spreadsheet_content(
    topic: str,
    count: int = 20,
    item_type: str = 'interview questions',
    *,
    service: LLMService | None = None,
    request_id: str | None = None,
) -> SpreadsheetContent:
    """Generate structured spreadsheet rows about a topic using Qwen."""
    service = service or LLMService()
    prompt = _spreadsheet_prompt(topic, count, item_type)
    messages = [
        {
            'role': 'system',
            'content': 'You generate structured JSON spreadsheet data. Return only valid JSON.',
        },
        {'role': 'user', 'content': prompt},
    ]
    log.info('content.generate_spreadsheet topic=%r count=%d request_id=%s', topic, count, request_id)

    try:
        result = service.generate_structured(messages, SpreadsheetContent)
        if not isinstance(result, SpreadsheetContent):
            raise ValueError('Unexpected result type from structured generation')
        log.info(
            'content.generate_spreadsheet success rows=%d request_id=%s',
            len(result.rows), request_id,
        )
        return result
    except Exception as exc:
        log.warning('content.generate_spreadsheet failed request_id=%s error=%s', request_id, exc)
        raise ValueError(f'Spreadsheet generation failed for topic "{topic}": {exc}') from exc
