"""Code Intelligence base — generation, caching, and LLM integration.

All LLM calls go through the centralized LLMService / AIRuntime.
Do NOT create separate Ollama clients here.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TypeVar

from pydantic import BaseModel

from backend.config import get_settings
from backend.core.llm import LLMService
from backend.code.prompts import prompt
from backend.intelligence.base import cache_get, cache_put

T = TypeVar('T', bound=BaseModel)

# Module-level shared service — uses the centralized runtime
_service: LLMService | None = None


def _get_service() -> LLMService:
    """Return a shared LLMService instance."""
    global _service
    if _service is None:
        _service = LLMService()
    return _service


def _parse(raw: str) -> dict:
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    a, b = raw.find('{'), raw.rfind('}')
    if a < 0 or b < a:
        raise ValueError('Model did not return JSON')
    return json.loads(raw[a:b + 1])


def generate(
    operation: str,
    model: type[T],
    task: str,
    language: str = '',
    code: str = '',
    request: str = '',
    error: str = '',
) -> T:
    settings = get_settings()
    key = hashlib.sha256(
        json.dumps(
            {
                'namespace': 'code-v1',
                'operation': operation,
                'language': language,
                'code': code,
                'request': request,
                'error': error,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()

    if getattr(settings, 'code_cache_enabled', True):
        cached = cache_get(key)
        if cached:
            return model.model_validate(cached)

    raw = _get_service().chat(
        prompt(task, model.model_json_schema(), code, language, request, error)
    )
    result = model.model_validate(_parse(raw))

    if getattr(settings, 'code_cache_enabled', True):
        cache_put(key, result.model_dump())

    return result
