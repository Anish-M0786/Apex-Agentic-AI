"""Response validation and structured output parsing for the Apex AI Runtime."""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.runtime.models import GenerationResponse

log = logging.getLogger('apex.runtime.validation')
T = TypeVar('T', bound=BaseModel)

MAX_RESPONSE_CHARS = 200_000


def validate_response(
    response: GenerationResponse,
    max_chars: int = MAX_RESPONSE_CHARS,
) -> None:
    """Validate a raw generation response.

    Raises ValueError if the response is empty or exceeds the size limit.
    """
    if not response.content or not response.content.strip():
        raise ValueError('Provider returned an empty response')
    if len(response.content) > max_chars:
        raise ValueError('Provider response exceeds size limit')


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON."""
    return re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I)


def _extract_json_substring(text: str) -> str:
    """Extract the outermost JSON object or array from text.

    Raises ValueError if no JSON boundaries are found.
    """
    obj_start = text.find('{')
    obj_end = text.rfind('}')
    arr_start = text.find('[')
    arr_end = text.rfind(']')

    candidates: list[tuple[int, int]] = []
    if obj_start >= 0 and obj_end > obj_start:
        candidates.append((obj_start, obj_end))
    if arr_start >= 0 and arr_end > arr_start:
        candidates.append((arr_start, arr_end))

    if not candidates:
        raise ValueError('Malformed structured model output: no JSON found')

    # Pick the candidate that starts earliest
    start, end = min(candidates, key=lambda c: c[0])
    return text[start:end + 1]


def _attempt_repair(raw_json: str) -> str | None:
    """One bounded repair attempt for common JSON issues.

    Returns repaired JSON string or None if repair fails.
    """
    repaired = raw_json
    # Remove trailing commas before } or ]
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    # Remove single-line JS comments
    repaired = re.sub(r'//[^\n]*', '', repaired)
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return None


def parse_structured(content: str, schema: type[T]) -> T:
    """Parse model output into a validated Pydantic model.

    Process:
    1. Strip markdown fences.
    2. Extract JSON substring.
    3. Attempt json.loads.
    4. If malformed, perform one bounded repair attempt.
    5. Validate against the Pydantic schema.
    6. If still invalid, raise ValueError.
    """
    cleaned = _strip_markdown_fences(content)
    json_str = _extract_json_substring(cleaned)

    # First attempt: direct parse
    parsed = None
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        # One bounded repair attempt
        repaired = _attempt_repair(json_str)
        if repaired is not None:
            log.info('Structured output required JSON repair')
            parsed = json.loads(repaired)
        else:
            raise ValueError('Malformed structured model output: invalid JSON')

    try:
        return schema.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError(
            f'Structured output failed schema validation: {exc.errors()}'
        ) from exc
