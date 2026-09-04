"""Apex AI Runtime — centralized generation engine.

All application layers (Chat API, Agent, Intelligence, Code) use this
single runtime for LLM generation, structured output, and streaming.
"""

from __future__ import annotations

import logging
import time
from typing import Iterator
from uuid import uuid4

from pydantic import BaseModel

from backend.runtime.manager import ModelManager
from backend.runtime.metrics import metrics
from backend.runtime.models import GenerationRequest, GenerationResponse
from backend.runtime.validation import parse_structured, validate_response

log = logging.getLogger('apex.runtime')


class AIRuntime:
    """Centralized AI runtime providing generation, structured output,
    streaming, retry, fallback, and metrics.

    This is the ONE entry point that all Apex services must use
    for LLM generation. Do not create separate Ollama clients.
    """

    def __init__(self, manager: ModelManager | None = None) -> None:
        self.manager = manager or ModelManager()

    # ---- health ----------------------------------------------------------

    def health(self) -> bool:
        """Return True if the underlying provider is reachable."""
        return self.manager.provider.health()

    # ---- generation ------------------------------------------------------

    def generate(
        self,
        request: GenerationRequest,
        request_id: str | None = None,
    ) -> GenerationResponse:
        """Generate a completion with retry and fallback support.

        Retry policy:
        - Only retries transient failures (connection, timeout).
        - Never retries: ValueError, schema errors, security errors.
        - Bounded by config.max_retries.

        Fallback policy:
        - If a fallback model is configured and the primary fails
          with a transient error, one attempt with the fallback model
          is made for non-structured requests.
        - The response always reports which model was used.
        """
        request_id = request_id or uuid4().hex
        request.model = request.model or self.manager.config.model

        # Validate model availability
        if not self.manager.provider.model_available(request.model):
            raise ValueError(f'Configured model {request.model!r} is unavailable')

        # Apply config defaults
        if request.temperature is None:
            request.temperature = self.manager.config.temperature
        if request.max_tokens is None:
            request.max_tokens = self.manager.config.max_tokens

        started = time.perf_counter()
        last_exception: Exception | None = None

        # Primary model attempts
        for attempt in range(self.manager.config.max_retries + 1):
            try:
                response = self.manager.provider.generate(request, request_id)
                validate_response(response)
                metrics.record(True, response.duration_ms, response.model)
                log.info(
                    'runtime provider=ollama model=%s request_id=%s '
                    'success=true retry=%d',
                    response.model, request_id, attempt,
                )
                return response
            except ValueError:
                # Never retry validation / schema / security errors
                raise
            except Exception as exc:
                last_exception = exc
                log.warning(
                    'runtime request_id=%s retry=%d failed: %s',
                    request_id, attempt, exc,
                )

        # Fallback model attempt (only for non-structured, transient failures)
        if self.manager.has_fallback:
            fallback = self.manager.fallback_model
            if self.manager.provider.model_available(fallback):
                try:
                    log.info(
                        'runtime fallback model=%s request_id=%s',
                        fallback, request_id,
                    )
                    request.model = fallback
                    response = self.manager.provider.generate(request, request_id)
                    validate_response(response)
                    metrics.record(True, response.duration_ms, response.model)
                    return response
                except Exception as exc:
                    last_exception = exc
                    log.warning(
                        'runtime fallback failed request_id=%s: %s',
                        request_id, exc,
                    )

        # All attempts exhausted
        latency = int((time.perf_counter() - started) * 1000)
        metrics.record(False, latency, request.model or '')
        raise RuntimeError('Generation provider failure') from last_exception

    # ---- structured generation -------------------------------------------

    def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[BaseModel],
        request_id: str | None = None,
    ) -> BaseModel:
        """Generate and validate structured JSON output.

        Process:
        1. Send request with JSON format hint.
        2. Parse and validate against the Pydantic schema.
        3. If malformed, attempt one bounded repair.
        4. Never silently switch models for structured operations.
        """
        request_id = request_id or uuid4().hex
        request.model = request.model or self.manager.config.model

        if not self.manager.provider.model_available(request.model):
            raise ValueError(f'Configured model {request.model!r} is unavailable')

        if request.temperature is None:
            request.temperature = self.manager.config.temperature
        if request.max_tokens is None:
            request.max_tokens = self.manager.config.max_tokens

        started = time.perf_counter()
        last_exception: Exception | None = None

        for attempt in range(self.manager.config.max_retries + 1):
            try:
                response = self.manager.provider.generate_structured(
                    request, request_id, schema,
                )
                validate_response(response)
                result = parse_structured(response.content, schema)
                metrics.record(True, response.duration_ms, response.model)
                log.info(
                    'runtime structured provider=ollama model=%s '
                    'request_id=%s success=true retry=%d',
                    response.model, request_id, attempt,
                )
                return result
            except ValueError:
                raise
            except Exception as exc:
                last_exception = exc
                log.warning(
                    'runtime structured request_id=%s retry=%d failed: %s',
                    request_id, attempt, exc,
                )

        latency = int((time.perf_counter() - started) * 1000)
        metrics.record(False, latency, request.model or '')
        raise RuntimeError('Structured generation provider failure') from last_exception

    # ---- streaming -------------------------------------------------------

    def stream(
        self,
        request: GenerationRequest,
        request_id: str | None = None,
    ) -> Iterator[str]:
        """Stream completion tokens from the provider.

        Returns a generator yielding text chunks.
        Compatible with non-streaming callers (just collect all chunks).
        """
        request_id = request_id or uuid4().hex
        request.model = request.model or self.manager.config.model

        if request.temperature is None:
            request.temperature = self.manager.config.temperature
        if request.max_tokens is None:
            request.max_tokens = self.manager.config.max_tokens

        return self.manager.provider.stream(request, request_id)
