"""AI provider protocol for the Apex runtime.

All concrete providers (Ollama, future cloud providers) must
implement this interface.
"""

from __future__ import annotations

from typing import Iterator, Protocol, TypeVar

from pydantic import BaseModel

from backend.runtime.models import GenerationRequest, GenerationResponse, ModelInfo

T = TypeVar('T', bound=BaseModel)


class AIProvider(Protocol):
    """Protocol that all AI providers must satisfy."""

    def health(self) -> bool:
        """Return True if the provider is reachable."""
        ...

    def list_models(self) -> list[ModelInfo]:
        """Return available models from the provider."""
        ...

    def model_available(self, model: str) -> bool:
        """Check whether a specific model is available."""
        ...

    def generate(
        self,
        request: GenerationRequest,
        request_id: str,
    ) -> GenerationResponse:
        """Generate a completion."""
        ...

    def generate_structured(
        self,
        request: GenerationRequest,
        request_id: str,
        schema: type[T],
    ) -> GenerationResponse:
        """Generate a completion constrained to produce valid JSON."""
        ...

    def stream(
        self,
        request: GenerationRequest,
        request_id: str,
    ) -> Iterator[str]:
        """Stream completion tokens/chunks."""
        ...
