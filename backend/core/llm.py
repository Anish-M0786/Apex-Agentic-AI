"""LLM service — thin facade over the Apex AI Runtime.

All application code should use this service or the runtime directly.
Do not create separate Ollama clients in feature packages.
"""

from __future__ import annotations

from typing import Iterator

from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.runtime import AIRuntime, GenerationRequest, RuntimeMessage


# Module-level runtime singleton
_runtime: AIRuntime | None = None


def _get_runtime() -> AIRuntime:
    """Return a shared AIRuntime instance."""
    global _runtime
    if _runtime is None:
        _runtime = AIRuntime()
    return _runtime


class LLMService:
    """High-level LLM service used by the application layer.

    Delegates all generation to the centralized AIRuntime.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.runtime = _get_runtime()

    def health_check(self) -> bool:
        """Return True if the LLM provider is reachable."""
        return self.runtime.health()

    def model_available(self) -> bool:
        """Return True if the configured model is available."""
        return self.runtime.manager.configured_model_available()

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send messages and return the generated text content."""
        return self.runtime.generate(
            GenerationRequest(
                messages=[RuntimeMessage(**m) for m in messages],
            ),
        ).content

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> BaseModel:
        """Generate and validate structured JSON output."""
        return self.runtime.generate_structured(
            GenerationRequest(
                messages=[RuntimeMessage(**m) for m in messages],
            ),
            schema=schema,
        )

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Stream completion tokens."""
        return self.runtime.stream(
            GenerationRequest(
                messages=[RuntimeMessage(**m) for m in messages],
            ),
        )
