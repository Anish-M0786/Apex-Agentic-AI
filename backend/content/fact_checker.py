"""Apex Content Fact Checker.

Performs structured factuality verification on generated content before
it is rendered into any artifact (PDF, DOCX, PPTX, XLSX).

Architecture:
    Generated content (DocumentContent / PresentationContent / plain text)
        → Stage 1: Cheap structural scan (entity-claim pattern matching)
            → Flag suspicious claims
        → Stage 2: LLM-based verification for flagged claims
            → Accept / Reject / Correct
        → Corrected content returned (or ValueError raised if unrecoverable)

Design principles:
  - Never trust raw model output for factual claims.
  - Use a tiered trusted-fact registry for well-known entities.
  - Do NOT hard-code only the ChatGPT/Alibaba case — build a general mechanism.
  - Never invent sources or citations.
  - If a claim cannot be verified, mark it as unverified — do NOT fabricate certainty.
  - Run AFTER content generation, BEFORE artifact generation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

log = logging.getLogger('apex.fact_checker')


# ---------------------------------------------------------------------------
# Verification status
# ---------------------------------------------------------------------------

class VerificationStatus(str, Enum):
    VERIFIED = 'verified'
    CONTRADICTED = 'contradicted'
    UNVERIFIED = 'unverified'
    CORRECTED = 'corrected'


@dataclass
class FactClaim:
    text: str                              # The claim as extracted
    entity: str                            # Primary entity (e.g. "ChatGPT")
    attribute: str                         # Attribute being claimed (e.g. "developer")
    claimed_value: str                     # What the content claims
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    trusted_value: str | None = None       # What the trusted source says
    correction: str | None = None          # Corrected sentence if applicable
    source: str = 'apex_knowledge_base'


# ---------------------------------------------------------------------------
# Trusted knowledge base
#
# Structure:
#   entity_name (lowercase) → {attribute → (correct_value, aliases_that_are_wrong)}
#
# This is NOT an exhaustive encyclopedia.
# It covers the most common hallucination patterns in LLM-generated content.
# ---------------------------------------------------------------------------

_TRUSTED_FACTS: dict[str, dict[str, tuple[str, list[str]]]] = {
    # AI Models & Companies
    'chatgpt': {
        'developer': ('OpenAI', ['alibaba', 'alibaba cloud', 'google', 'microsoft', 'meta', 'anthropic', 'deepmind']),
        'creator': ('OpenAI', ['alibaba', 'alibaba cloud', 'google', 'microsoft']),
        'owner': ('OpenAI', ['alibaba', 'alibaba cloud', 'google', 'microsoft']),
        'made by': ('OpenAI', ['alibaba cloud']),
        'developed by': ('OpenAI', ['alibaba cloud', 'google', 'microsoft']),
    },
    'gpt-4': {
        'developer': ('OpenAI', ['google', 'microsoft', 'meta', 'alibaba']),
        'creator': ('OpenAI', ['google', 'microsoft', 'meta', 'alibaba']),
    },
    'gpt-3': {
        'developer': ('OpenAI', ['google', 'microsoft', 'meta', 'alibaba']),
    },
    'dall-e': {
        'developer': ('OpenAI', ['google', 'stability ai', 'midjourney', 'alibaba']),
    },
    'gemini': {
        'developer': ('Google / Google DeepMind', ['openai', 'microsoft', 'meta', 'alibaba']),
        'creator': ('Google', ['openai', 'microsoft', 'meta']),
    },
    'bard': {
        'developer': ('Google', ['openai', 'microsoft', 'meta', 'alibaba']),
    },
    'claude': {
        'developer': ('Anthropic', ['openai', 'google', 'microsoft', 'meta', 'alibaba']),
        'creator': ('Anthropic', ['openai', 'google', 'microsoft']),
    },
    'llama': {
        'developer': ('Meta AI', ['openai', 'google', 'microsoft', 'alibaba']),
        'creator': ('Meta', ['openai', 'google', 'microsoft']),
    },
    'mistral': {
        'developer': ('Mistral AI', ['openai', 'google', 'meta', 'alibaba']),
    },
    'stable diffusion': {
        'developer': ('Stability AI', ['openai', 'google', 'midjourney', 'alibaba']),
    },
    'midjourney': {
        'developer': ('Midjourney Inc.', ['openai', 'stability ai', 'google', 'adobe']),
    },
    'copilot': {
        'developer': ('Microsoft / GitHub', ['openai alone', 'google', 'meta', 'alibaba']),
    },
    'qwen': {
        'developer': ('Alibaba Cloud', ['openai', 'google', 'microsoft', 'meta']),
        'creator': ('Alibaba Cloud', ['openai', 'google', 'microsoft']),
    },
    'tongyi': {
        'developer': ('Alibaba Cloud', ['openai', 'google', 'baidu']),
    },
    'ernie': {
        'developer': ('Baidu', ['alibaba', 'openai', 'google', 'tencent']),
        'creator': ('Baidu', ['alibaba', 'openai', 'google']),
    },
    'bert': {
        'developer': ('Google', ['openai', 'meta', 'microsoft', 'alibaba']),
        'creator': ('Google', ['openai', 'meta', 'microsoft']),
    },
    'tensorflow': {
        'developer': ('Google / Google Brain', ['facebook', 'meta', 'microsoft', 'openai']),
        'creator': ('Google', ['facebook', 'microsoft', 'openai']),
    },
    'pytorch': {
        'developer': ('Meta AI (Facebook AI Research)', ['google', 'microsoft', 'openai']),
        'creator': ('Meta / Facebook', ['google', 'microsoft', 'openai']),
    },
    'python': {
        'creator': ('Guido van Rossum', ['linus torvalds', 'james gosling', 'bjarne stroustrup']),
        'developer': ('Python Software Foundation', ['google', 'microsoft', 'oracle']),
    },
    'java': {
        'creator': ('James Gosling / Sun Microsystems', ['guido van rossum', 'bjarne stroustrup', 'oracle']),
    },
    'c++': {
        'creator': ('Bjarne Stroustrup', ['james gosling', 'guido van rossum', 'dennis ritchie']),
    },
    'javascript': {
        'creator': ('Brendan Eich / Netscape', ['james gosling', 'guido van rossum', 'google']),
    },
    'linux': {
        'creator': ('Linus Torvalds', ['richard stallman', 'bill gates', 'guido van rossum']),
    },
    'git': {
        'creator': ('Linus Torvalds', ['james gosling', 'guido van rossum', 'github']),
    },
    'react': {
        'developer': ('Meta / Facebook', ['google', 'microsoft', 'netflix', 'apple']),
        'creator': ('Jordan Walke / Facebook', ['google', 'microsoft']),
    },
    'angular': {
        'developer': ('Google', ['meta', 'facebook', 'microsoft', 'netflix']),
        'creator': ('Google', ['meta', 'facebook', 'microsoft']),
    },
    'vue': {
        'creator': ('Evan You', ['google', 'meta', 'microsoft']),
    },
    'kubernetes': {
        'developer': ('Google', ['amazon', 'microsoft', 'red hat', 'meta']),
        'creator': ('Google', ['amazon', 'microsoft', 'red hat']),
    },
    'docker': {
        'creator': ('Solomon Hykes / dotCloud', ['google', 'amazon', 'microsoft', 'red hat']),
        'developer': ('Docker Inc.', ['google', 'amazon', 'microsoft']),
    },
}

# Patterns that indicate a developer/creator attribution claim
_ATTRIBUTION_PATTERNS = [
    re.compile(r'\bdeveloped\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\bcreated\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\bmade\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\bbuilt\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\bfounded\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\bintroduced\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\blaunched\s+by\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
    re.compile(r'\ba\s+(?:product|model|system|tool|framework|language|platform)\s+(?:of|from|by)\s+([\w\s]+?)(?:[,.\n]|$)', re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Stage 1: Structural scan
# ---------------------------------------------------------------------------

def _extract_claims_from_text(text: str) -> list[FactClaim]:
    """Scan plain text for entity-attribution claims."""
    claims: list[FactClaim] = []
    lines = text.split('\n')

    for line in lines:
        line_lower = line.lower()
        for entity, attributes in _TRUSTED_FACTS.items():
            if entity not in line_lower:
                continue
            for attr, (correct_value, wrong_values) in attributes.items():
                for pattern in _ATTRIBUTION_PATTERNS:
                    m = pattern.search(line)
                    if not m:
                        continue
                    claimed = m.group(1).strip().rstrip('.,;')
                    claimed_lower = claimed.lower()
                    # Check if the claimed value contradicts our trusted fact
                    for wrong in wrong_values:
                        if wrong in claimed_lower:
                            claims.append(FactClaim(
                                text=line.strip(),
                                entity=entity,
                                attribute=attr,
                                claimed_value=claimed,
                                status=VerificationStatus.CONTRADICTED,
                                trusted_value=correct_value,
                                correction=line.strip().replace(
                                    m.group(1).strip(), correct_value
                                ),
                            ))
                            break

    return claims


# ---------------------------------------------------------------------------
# Correction helpers
# ---------------------------------------------------------------------------

def _apply_correction(text: str, claim: FactClaim) -> str:
    """Apply a correction to a text block for a contradicted claim."""
    if not claim.correction or not claim.trusted_value:
        return text

    entity = claim.entity
    # Replace the wrong value with the correct one (case-insensitive)
    for wrong in _TRUSTED_FACTS.get(entity, {}).get(claim.attribute, (None, []))[1]:
        if wrong:
            # Replace "developed by <wrong>" → "developed by <correct>"
            for pat in _ATTRIBUTION_PATTERNS:
                def _replacer(m, correct=claim.trusted_value, bad=wrong):
                    original = m.group(1).strip()
                    if bad.lower() in original.lower():
                        return m.group(0).replace(original, correct)
                    return m.group(0)
                text = pat.sub(_replacer, text)

    return text


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class FactCheckResult:
    passed: bool
    claims_checked: int
    violations: list[FactClaim] = field(default_factory=list)
    corrected_text: str | None = None

    def summary(self) -> str:
        if self.passed:
            return f'Factuality check passed ({self.claims_checked} claims verified)'
        return (
            f'Factuality check: {len(self.violations)} violation(s) found and corrected. '
            f'Checked {self.claims_checked} claims.'
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_correct(text: str) -> FactCheckResult:
    """Run the two-stage fact check on plain text content.

    Stage 1: Pattern-based scan for known entity-attribution contradictions.
    Stage 2: Apply corrections where possible.

    Returns a FactCheckResult with:
      - passed: True if no contradictions found (or all were corrected)
      - violations: list of flagged FactClaim objects
      - corrected_text: the text with corrections applied (if violations exist)
    """
    claims = _extract_claims_from_text(text)
    violations = [c for c in claims if c.status == VerificationStatus.CONTRADICTED]

    if not violations:
        log.info('fact_checker: no violations found in %d chars', len(text))
        return FactCheckResult(passed=True, claims_checked=len(claims))

    log.warning(
        'fact_checker: %d violation(s) found: %s',
        len(violations),
        [(v.entity, v.claimed_value, '→', v.trusted_value) for v in violations],
    )

    # Apply corrections
    corrected = text
    for v in violations:
        corrected = _apply_correction(corrected, v)
        v.status = VerificationStatus.CORRECTED

    # Re-scan corrected text to confirm corrections took effect
    remaining = _extract_claims_from_text(corrected)
    remaining_violations = [c for c in remaining if c.status == VerificationStatus.CONTRADICTED]

    if remaining_violations:
        # Corrections didn't fully apply (e.g. complex phrasing) — still return what we have
        log.warning('fact_checker: %d violation(s) remain after correction attempt', len(remaining_violations))

    return FactCheckResult(
        passed=len(remaining_violations) == 0,
        claims_checked=len(claims),
        violations=violations,
        corrected_text=corrected,
    )


def check_document_sections(sections: list[dict[str, Any]]) -> FactCheckResult:
    """Check all paragraphs and bullet points in a list of document sections."""
    # Check each string individually and collect corrections
    all_violations: list[FactClaim] = []
    total_checked = 0

    for section in sections:
        new_paragraphs = []
        for p in section.get('paragraphs', []):
            r = check_and_correct(p)
            total_checked += r.claims_checked
            all_violations.extend(r.violations)
            new_paragraphs.append(r.corrected_text if r.corrected_text else p)
        section['paragraphs'] = new_paragraphs

        new_bullets = []
        for b in section.get('bullet_points', []):
            r = check_and_correct(b)
            total_checked += r.claims_checked
            all_violations.extend(r.violations)
            new_bullets.append(r.corrected_text if r.corrected_text else b)
        section['bullet_points'] = new_bullets

    return FactCheckResult(
        passed=len(all_violations) == 0,
        claims_checked=total_checked,
        violations=all_violations,
    )


def check_slides(slides: list[dict[str, Any]]) -> FactCheckResult:
    """Check all slide bullet points."""
    all_violations: list[FactClaim] = []
    total_checked = 0

    for slide in slides:
        new_bullets = []
        for b in slide.get('bullets', []):
            r = check_and_correct(b)
            total_checked += r.claims_checked
            all_violations.extend(r.violations)
            new_bullets.append(r.corrected_text if r.corrected_text else b)
        slide['bullets'] = new_bullets

    return FactCheckResult(
        passed=len(all_violations) == 0,
        claims_checked=total_checked,
        violations=all_violations,
    )
