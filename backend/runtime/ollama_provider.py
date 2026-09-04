"""Ollama provider implementation for the Apex AI Runtime."""

from __future__ import annotations

import json as _json
import logging
import time
from typing import Any, Iterator

import ollama
from pydantic import BaseModel

from backend.runtime.config import RuntimeConfig
from backend.runtime.models import (
    GenerationRequest,
    GenerationResponse,
    ModelInfo,
    Usage,
)

log = logging.getLogger('apex.runtime.ollama')


class OllamaProvider:
    """Concrete AI provider backed by a local Ollama instance."""

    def __init__(
        self,
        host: str,
        timeout: int = 120,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.client = ollama.Client(host=host, timeout=timeout)
        self._config = config
        self._host = host

    # ---- health ----------------------------------------------------------

    def health(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    # ---- model discovery -------------------------------------------------

    def list_models(self) -> list[ModelInfo]:
        """Return all models available on this Ollama instance."""
        try:
            data = self.client.list()
        except Exception as exc:
            log.warning('Failed to list Ollama models: %s', exc)
            return []

        items: list[Any] = (
            data.get('models', []) if isinstance(data, dict)
            else getattr(data, 'models', [])
        )
        models: list[ModelInfo] = []
        for item in items:
            if isinstance(item, dict):
                name = item.get('name') or item.get('model') or ''
                size = item.get('size')
            else:
                name = getattr(item, 'model', '') or getattr(item, 'name', '')
                size = getattr(item, 'size', None)
            if name:
                models.append(ModelInfo(name=name, size=size))
        return models

    def model_available(self, model: str) -> bool:
        """Check if a specific model is available on Ollama."""
        base = model.split(':')[0]
        for m in self.list_models():
            if m.name == model or m.name.split(':')[0] == base:
                return True
        return False

    # ---- generation options ----------------------------------------------

    def _build_options(self, request: GenerationRequest) -> dict[str, Any]:
        """Build the Ollama options dict from request + config defaults."""
        opts: dict[str, Any] = {}

        # Request-level overrides take priority
        if request.temperature is not None:
            opts['temperature'] = request.temperature
        if request.max_tokens is not None:
            opts['num_predict'] = request.max_tokens

        # Merge config-level defaults for anything not set
        if self._config:
            opts.setdefault('temperature', self._config.temperature)
            opts.setdefault('num_predict', self._config.max_tokens)
            opts.setdefault('top_p', self._config.top_p)
            opts.setdefault('top_k', self._config.top_k)
            opts.setdefault('num_ctx', self._config.num_ctx)

        return opts

    # ---- response extraction ---------------------------------------------

    @staticmethod
    def _extract_content(result: Any) -> str:
        """Extract the text content from an Ollama chat response."""
        msg = (
            result.get('message', {}) if isinstance(result, dict)
            else getattr(result, 'message', {})
        )
        content = (
            msg.get('content', '') if isinstance(msg, dict)
            else getattr(msg, 'content', '')
        )
        return str(content).strip()

    @staticmethod
    def _extract_usage(result: Any) -> Usage:
        """Extract real token counts from Ollama — never fabricate."""
        if isinstance(result, dict):
            prompt = result.get('prompt_eval_count')
            completion = result.get('eval_count')
        else:
            prompt = getattr(result, 'prompt_eval_count', None)
            completion = getattr(result, 'eval_count', None)

        total = None
        if prompt is not None and completion is not None:
            total = prompt + completion

        return Usage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    # ---- generate --------------------------------------------------------

    def generate(
        self,
        request: GenerationRequest,
        request_id: str,
    ) -> GenerationResponse:
        """Generate a chat completion via Ollama."""
        start = time.perf_counter()
        messages = [m.model_dump() for m in request.messages]
        options = self._build_options(request)

        result: Any = self.client.chat(
            model=request.model,
            messages=messages,
            options=options,
        )

        content = self._extract_content(result)
        usage = self._extract_usage(result)
        duration_ms = int((time.perf_counter() - start) * 1000)

        log.info(
            'generate provider=ollama model=%s request_id=%s duration_ms=%d',
            request.model, request_id, duration_ms,
        )

        return GenerationResponse(
            success=True,
            model=request.model or '',
            content=content,
            usage=usage,
            duration_ms=duration_ms,
            request_id=request_id,
        )

    # ---- structured generation -------------------------------------------

    def generate_structured(
        self,
        request: GenerationRequest,
        request_id: str,
        schema: type[BaseModel] | None = None,
    ) -> GenerationResponse:
        """Generate a completion constrained to JSON output.

        Uses Ollama's format='json' to encourage valid JSON.
        The schema instruction is prepended to help the model.
        """
        start = time.perf_counter()
        messages = [m.model_dump() for m in request.messages]
        options = self._build_options(request)

        # Add schema hint to system message if schema provided
        if schema is not None:
            schema_json = _json.dumps(schema.model_json_schema(), indent=2)
            schema_instruction = (
                'You MUST respond with valid JSON matching this schema:\n'
                f'{schema_json}\n'
                'Return ONLY the JSON object, no other text.'
            )
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += '\n\n' + schema_instruction
            else:
                messages.insert(0, {'role': 'system', 'content': schema_instruction})

        result: Any = self.client.chat(
            model=request.model,
            messages=messages,
            options=options,
            format='json',
        )

        content = self._extract_content(result)
        usage = self._extract_usage(result)
        duration_ms = int((time.perf_counter() - start) * 1000)

        log.info(
            'generate_structured provider=ollama model=%s request_id=%s duration_ms=%d',
            request.model, request_id, duration_ms,
        )

        return GenerationResponse(
            success=True,
            model=request.model or '',
            content=content,
            usage=usage,
            duration_ms=duration_ms,
            request_id=request_id,
        )

    # ---- streaming -------------------------------------------------------

    def stream(
        self,
        request: GenerationRequest,
        request_id: str,
    ) -> Iterator[str]:
        """Stream completion tokens from Ollama."""
        messages = [m.model_dump() for m in request.messages]
        options = self._build_options(request)

        log.info(
            'stream_start provider=ollama model=%s request_id=%s',
            request.model, request_id,
        )

        for part in self.client.chat(
            model=request.model,
            messages=messages,
            options=options,
            stream=True,
        ):
            msg = (
                part.get('message', {}) if isinstance(part, dict)
                else getattr(part, 'message', {})
            )
            chunk = (
                msg.get('content', '') if isinstance(msg, dict)
                else getattr(msg, 'content', '')
            )
            if chunk:
                yield chunk
