"""Document Intelligence base — extraction, chunking, generation, and caching.

All LLM calls go through the centralized LLMService / AIRuntime.
Do NOT create separate Ollama clients here.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from backend.config import get_settings
from backend.core.llm import LLMService
from backend.intelligence.prompts import structured_prompt

ROOT = Path(__file__).resolve().parents[2]
DOCS = (ROOT / 'data' / 'documents').resolve()
CACHE = (ROOT / 'data' / 'intelligence_cache.sqlite').resolve()
T = TypeVar('T', bound=BaseModel)

# Module-level shared service — uses the centralized runtime
_service: LLMService | None = None


def _get_service() -> LLMService:
    """Return a shared LLMService instance."""
    global _service
    if _service is None:
        _service = LLMService()
    return _service


def _db() -> sqlite3.Connection:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE)
    con.execute(
        'CREATE TABLE IF NOT EXISTS intelligence_cache '
        '(cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL)'
    )
    return con


def cache_get(key: str) -> dict | None:
    with _db() as con:
        row = con.execute(
            'SELECT payload FROM intelligence_cache WHERE cache_key=?', (key,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def cache_put(key: str, value: dict) -> None:
    with _db() as con:
        con.execute(
            'INSERT OR REPLACE INTO intelligence_cache(cache_key, payload) VALUES (?, ?)',
            (key, json.dumps(value)),
        )


def document_text(document_id: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', document_id):
        raise ValueError('Invalid document ID')
    if not DOCS.exists():
        raise FileNotFoundError('Document not found')
    matches = [p.resolve() for p in DOCS.glob(document_id + '.*') if p.is_file()]
    if not matches:
        raise FileNotFoundError('Document not found')
    path = matches[0]
    if path.parent != DOCS:
        raise ValueError('Invalid document ID')
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
            text = '\n'.join(
                page.extract_text() or '' for page in PdfReader(str(path)).pages
            )
        except ImportError as exc:
            raise RuntimeError('PDF reading requires pypdf') from exc
    else:
        text = path.read_text(encoding='utf-8', errors='replace')
    if not text.strip():
        raise ValueError('Document has no extractable text')
    return text.strip()


def chunks(text: str) -> list[str]:
    settings = get_settings()
    size = getattr(settings, 'intelligence_chunk_chars', 5000)
    maximum = getattr(settings, 'intelligence_max_chunks', 40)
    return [text[i:i + size] for i in range(0, len(text), size)][:maximum]


def _parse(raw: str) -> dict:
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    a, b = raw.find('{'), raw.rfind('}')
    if a < 0 or b < a:
        raise ValueError('Model did not return JSON')
    return json.loads(raw[a:b + 1])


def generate(
    document_id: str,
    operation: str,
    model: type[T],
    task: str,
    request: str = '',
    count: int | None = None,
) -> T:
    text = document_text(document_id)
    digest = hashlib.sha256(text.encode()).hexdigest()
    key = hashlib.sha256(
        json.dumps(
            {
                'id': document_id,
                'op': operation,
                'request': request,
                'count': count,
                'text': digest,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()

    cached = cache_get(key)
    if cached:
        return model.model_validate(cached)

    service = _get_service()
    parts = chunks(text)

    if len(parts) > 1:
        extracts: list[str] = []
        fact_schema = {
            'type': 'object',
            'properties': {
                'facts': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['facts'],
        }
        for part in parts:
            extracts.append(
                service.chat(
                    structured_prompt(
                        'Extract source facts, terminology, headings and '
                        'relationships as JSON.',
                        fact_schema,
                        part,
                    )
                )
            )
        text = '\n'.join(extracts)

    result = model.model_validate(
        _parse(
            service.chat(
                structured_prompt(task, model.model_json_schema(), text, request)
            )
        )
    )
    cache_put(key, result.model_dump())
    return result
