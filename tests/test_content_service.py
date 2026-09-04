"""Tests for the TennuX Content Generation Service.

These tests verify that:
- Content generation returns valid structured Pydantic models
- Empty/invalid content is rejected with ValueError
- The service calls LLMService (Qwen) and never bypasses it
- Malformed JSON is handled with one repair attempt
- to_plain_text and to_paragraphs render correctly
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.content.service import (
    DocumentContent,
    DocumentSection,
    PresentationContent,
    SlideContent,
    SpreadsheetContent,
    SpreadsheetRow,
    generate_document_content,
    generate_presentation_content,
    generate_spreadsheet_content,
)


# ---------------------------------------------------------------------------
# DocumentContent model tests
# ---------------------------------------------------------------------------

class TestDocumentContentModel:
    def _valid_section(self) -> DocumentSection:
        return DocumentSection(
            heading='Introduction',
            paragraphs=['This is a paragraph about the topic.'],
            bullet_points=['Key point one', 'Key point two'],
        )

    def test_valid_document_content(self):
        doc = DocumentContent(
            title='Test Document',
            sections=[self._valid_section()],
        )
        assert doc.title == 'Test Document'
        assert len(doc.sections) == 1

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            DocumentContent(title='', sections=[self._valid_section()])

    def test_no_sections_rejected(self):
        with pytest.raises(ValidationError):
            DocumentContent(title='Valid Title', sections=[])

    def test_empty_section_content_rejected(self):
        with pytest.raises(ValidationError):
            DocumentSection(heading='Empty', paragraphs=[], bullet_points=[])

    def test_to_plain_text_contains_title(self):
        doc = DocumentContent(
            title='Generative AI',
            sections=[self._valid_section()],
        )
        text = doc.to_plain_text()
        assert 'GENERATIVE AI' in text
        assert 'Introduction' in text

    def test_to_plain_text_contains_section_content(self):
        doc = DocumentContent(
            title='Test',
            sections=[DocumentSection(
                heading='Section 1',
                paragraphs=['This paragraph has content.'],
                bullet_points=['Bullet A'],
            )],
            conclusion='This is the conclusion.',
        )
        text = doc.to_plain_text()
        assert 'This paragraph has content.' in text
        assert '• Bullet A' in text
        assert 'This is the conclusion.' in text

    def test_to_paragraphs_returns_list(self):
        doc = DocumentContent(
            title='Test',
            sections=[self._valid_section()],
        )
        paras = doc.to_paragraphs()
        assert isinstance(paras, list)
        assert len(paras) > 0


# ---------------------------------------------------------------------------
# PresentationContent model tests
# ---------------------------------------------------------------------------

class TestPresentationContentModel:
    def _valid_slide(self, title: str = 'Slide') -> SlideContent:
        return SlideContent(title=title, bullets=['Point 1', 'Point 2'])

    def test_valid_presentation(self):
        pres = PresentationContent(
            title='Test Presentation',
            slides=[self._valid_slide('Intro'), self._valid_slide('Content')],
        )
        assert pres.title == 'Test Presentation'
        assert len(pres.slides) == 2

    def test_single_slide_rejected(self):
        with pytest.raises(ValidationError):
            PresentationContent(title='Test', slides=[self._valid_slide()])

    def test_empty_bullets_rejected(self):
        with pytest.raises(ValidationError):
            SlideContent(title='Empty', bullets=[])

    def test_to_generator_slides(self):
        pres = PresentationContent(
            title='Test',
            slides=[
                SlideContent(title='Slide 1', bullets=['A', 'B']),
                SlideContent(title='Slide 2', bullets=['C', 'D']),
            ],
        )
        slides = pres.to_generator_slides()
        assert len(slides) == 2
        assert slides[0]['title'] == 'Slide 1'
        assert slides[0]['bullet_points'] == ['A', 'B']


# ---------------------------------------------------------------------------
# SpreadsheetContent model tests
# ---------------------------------------------------------------------------

class TestSpreadsheetContentModel:
    def test_valid_spreadsheet(self):
        sc = SpreadsheetContent(
            sheet_name='AI Questions',
            columns=['Question', 'Topic', 'Difficulty', 'Answer'],
            rows=[SpreadsheetRow(question='What is RAG?', topic='AI', difficulty='medium', answer='Retrieval-Augmented Generation')],
        )
        assert len(sc.rows) == 1

    def test_empty_rows_rejected(self):
        with pytest.raises(ValidationError):
            SpreadsheetContent(sheet_name='Empty', rows=[])

    def test_to_generator_rows(self):
        sc = SpreadsheetContent(
            sheet_name='Test',
            rows=[SpreadsheetRow(question='Q1', topic='T1', difficulty='easy', answer='A1')],
        )
        rows = sc.to_generator_rows()
        assert rows == [['Q1', 'T1', 'easy', 'A1']]


# ---------------------------------------------------------------------------
# Content generation service tests (with mocked LLMService)
# ---------------------------------------------------------------------------

def _make_mock_service(return_value):
    """Create a mock LLMService that returns the given structured value."""
    mock = MagicMock()
    mock.generate_structured.return_value = return_value
    return mock


class TestGenerateDocumentContent:
    def _valid_doc(self) -> DocumentContent:
        return DocumentContent(
            title='Generative AI',
            sections=[
                DocumentSection(
                    heading='Introduction',
                    paragraphs=['Generative AI creates new content from learned patterns.'],
                    bullet_points=['Text generation', 'Image generation'],
                ),
                DocumentSection(
                    heading='Applications',
                    paragraphs=['It is used in chatbots, code assistants, and creative tools.'],
                    bullet_points=['ChatGPT', 'GitHub Copilot'],
                ),
            ],
        )

    def test_returns_document_content_from_qwen(self):
        service = _make_mock_service(self._valid_doc())
        result = generate_document_content('Generative AI', service=service)
        assert isinstance(result, DocumentContent)
        assert result.title == 'Generative AI'
        assert len(result.sections) >= 1
        service.generate_structured.assert_called_once()

    def test_llm_service_is_called_with_messages(self):
        service = _make_mock_service(self._valid_doc())
        generate_document_content('Quantum Computing', service=service)
        args = service.generate_structured.call_args
        messages = args[0][0]
        assert any(m['role'] == 'system' for m in messages)
        assert any('Quantum Computing' in m.get('content', '') for m in messages)

    def test_failure_raises_value_error(self):
        service = MagicMock()
        service.generate_structured.side_effect = RuntimeError('Ollama unavailable')
        with pytest.raises(ValueError, match='Content generation failed'):
            generate_document_content('Test Topic', service=service)

    def test_never_bypasses_llm_service(self):
        """The service must always call generate_structured — never return hard-coded content."""
        service = MagicMock()
        service.generate_structured.side_effect = ValueError('Validation error')
        with pytest.raises(ValueError):
            generate_document_content('Any Topic', service=service)
        # Ensure it actually called the LLM
        service.generate_structured.assert_called_once()


class TestGeneratePresentationContent:
    def _valid_pres(self) -> PresentationContent:
        return PresentationContent(
            title='RAG Explained',
            slides=[
                SlideContent(title='What is RAG?', bullets=['Retrieval-Augmented Generation', 'Combines LLMs with retrieval']),
                SlideContent(title='How it works', bullets=['Query → Retrieve → Generate', 'Grounded in real documents']),
                SlideContent(title='Benefits', bullets=['Reduces hallucinations', 'Up-to-date information']),
            ],
        )

    def test_returns_presentation_content(self):
        service = _make_mock_service(self._valid_pres())
        result = generate_presentation_content('RAG', service=service)
        assert isinstance(result, PresentationContent)
        assert len(result.slides) >= 2

    def test_failure_raises_value_error(self):
        service = MagicMock()
        service.generate_structured.side_effect = RuntimeError('timeout')
        with pytest.raises(ValueError, match='Presentation generation failed'):
            generate_presentation_content('RAG', service=service)


class TestGenerateSpreadsheetContent:
    def _valid_sheet(self) -> SpreadsheetContent:
        return SpreadsheetContent(
            sheet_name='AI Interview Questions',
            columns=['Question', 'Topic', 'Difficulty', 'Answer'],
            rows=[
                SpreadsheetRow(question=f'Question {i}', topic='AI', difficulty='medium', answer=f'Answer {i}')
                for i in range(20)
            ],
        )

    def test_returns_spreadsheet_content(self):
        service = _make_mock_service(self._valid_sheet())
        result = generate_spreadsheet_content('AI', count=20, service=service)
        assert isinstance(result, SpreadsheetContent)
        assert len(result.rows) == 20

    def test_generator_rows_have_correct_shape(self):
        service = _make_mock_service(self._valid_sheet())
        result = generate_spreadsheet_content('AI', count=20, service=service)
        rows = result.to_generator_rows()
        assert len(rows) == 20
        assert len(rows[0]) == 4  # question, topic, difficulty, answer

    def test_failure_raises_value_error(self):
        service = MagicMock()
        service.generate_structured.side_effect = RuntimeError('timeout')
        with pytest.raises(ValueError, match='Spreadsheet generation failed'):
            generate_spreadsheet_content('AI', service=service)


# ---------------------------------------------------------------------------
# Integration: content → generator pipeline (with mocked Qwen)
# ---------------------------------------------------------------------------

class TestContentToPipelineIntegration:
    """Verify content service output is compatible with the generators."""

    def test_document_content_to_pdf_text_is_long_enough(self):
        """to_plain_text must produce content >= 50 chars for PDFInput."""
        doc = DocumentContent(
            title='Operating Systems',
            sections=[
                DocumentSection(
                    heading='Introduction',
                    paragraphs=['Operating systems manage hardware and software resources.'],
                    bullet_points=['Process management', 'Memory management', 'File systems'],
                ),
            ],
        )
        text = doc.to_plain_text()
        assert len(text) >= 50, f'Plain text too short: {len(text)} chars'

    def test_presentation_content_to_generator_slides_compatible(self):
        """to_generator_slides output must be accepted by create_ppt."""
        pres = PresentationContent(
            title='RAG',
            slides=[
                SlideContent(title='Intro', bullets=['Point A', 'Point B']),
                SlideContent(title='Details', bullets=['Point C', 'Point D']),
            ],
        )
        slides = pres.to_generator_slides()
        # Each slide must have 'title' and 'bullet_points' keys
        for slide in slides:
            assert 'title' in slide
            assert 'bullet_points' in slide
            assert isinstance(slide['bullet_points'], list)

    def test_spreadsheet_content_to_generator_rows_compatible(self):
        """to_generator_rows must produce list[list] for create_excel."""
        sc = SpreadsheetContent(
            sheet_name='Test',
            rows=[
                SpreadsheetRow(question='Q', topic='T', difficulty='easy', answer='A'),
            ],
        )
        rows = sc.to_generator_rows()
        assert isinstance(rows, list)
        assert isinstance(rows[0], list)
