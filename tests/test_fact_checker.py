"""Tests for backend/content/fact_checker.py"""
import pytest
from backend.content.fact_checker import (
    check_and_correct,
    check_document_sections,
    check_slides,
    VerificationStatus,
)


# ---------------------------------------------------------------------------
# Factuality: company/product relationships
# ---------------------------------------------------------------------------

def test_correct_chatgpt_attribution():
    result = check_and_correct("ChatGPT was developed by OpenAI and released in November 2022.")
    assert result.passed


def test_incorrect_chatgpt_alibaba():
    text = "chatGPT is an artificial intelligence language model developed by Alibaba Cloud."
    result = check_and_correct(text)
    assert result.violations, "Should flag Alibaba Cloud as wrong developer for ChatGPT"
    assert any(v.trusted_value == "OpenAI" for v in result.violations)
    assert result.corrected_text is not None
    assert "OpenAI" in result.corrected_text


def test_incorrect_chatgpt_google():
    result = check_and_correct("ChatGPT was created by Google.")
    assert result.violations


def test_correct_qwen_attribution():
    result = check_and_correct("Qwen is an AI model developed by Alibaba Cloud.")
    assert result.passed


def test_incorrect_pytorch_google():
    result = check_and_correct("PyTorch was created by Google.")
    assert result.violations


def test_incorrect_react_google():
    result = check_and_correct("React is a JavaScript library developed by Google.")
    assert result.violations
    assert any("Meta" in (v.trusted_value or "") for v in result.violations)


def test_incorrect_bert_openai():
    result = check_and_correct("BERT was developed by OpenAI researchers.")
    assert result.violations


def test_unknown_fact_no_false_positive():
    result = check_and_correct("The sky is blue. Water consists of hydrogen and oxygen.")
    assert result.passed


def test_unsupported_claim_passes():
    # A claim we don't have data on should not be flagged
    result = check_and_correct("WidgetLib was created by CorpX in 2021.")
    assert result.passed


def test_correction_replaces_wrong_value():
    text = "GPT-4 is a language model created by Microsoft."
    result = check_and_correct(text)
    assert result.violations
    assert result.corrected_text is not None
    assert "OpenAI" in result.corrected_text


# ---------------------------------------------------------------------------
# Document section checking
# ---------------------------------------------------------------------------

def test_check_document_sections_clean():
    sections = [
        {"heading": "Introduction", "paragraphs": ["OpenAI developed ChatGPT."], "bullet_points": []},
    ]
    result = check_document_sections(sections)
    assert result.passed


def test_check_document_sections_violation():
    sections = [
        {
            "heading": "Introduction",
            "paragraphs": ["ChatGPT was developed by Alibaba Cloud."],
            "bullet_points": [],
        }
    ]
    result = check_document_sections(sections)
    assert result.violations
    # Correction should be applied back to sections
    assert "OpenAI" in sections[0]["paragraphs"][0]


def test_check_document_sections_bullet_violation():
    sections = [
        {
            "heading": "Tools",
            "paragraphs": [],
            "bullet_points": ["React was developed by Google"],
        }
    ]
    result = check_document_sections(sections)
    assert result.violations


# ---------------------------------------------------------------------------
# Slide checking
# ---------------------------------------------------------------------------

def test_check_slides_clean():
    slides = [
        {"title": "AI Overview", "bullets": ["ChatGPT was created by OpenAI in 2022."]},
    ]
    result = check_slides(slides)
    assert result.passed


def test_check_slides_violation():
    slides = [
        {"title": "AI Tools", "bullets": ["ChatGPT was developed by Alibaba Cloud."]},
    ]
    result = check_slides(slides)
    assert result.violations
    assert "OpenAI" in slides[0]["bullets"][0]


# ---------------------------------------------------------------------------
# Contradictory claims
# ---------------------------------------------------------------------------

def test_contradictory_claims_in_same_text():
    # Two contradicting claims in the same block
    text = (
        "ChatGPT was developed by OpenAI. "
        "However, some reports say ChatGPT was created by Alibaba Cloud."
    )
    result = check_and_correct(text)
    # The second sentence should be flagged
    assert result.violations
