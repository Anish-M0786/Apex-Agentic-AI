"""Streaming support for the Apex AI Runtime.

Provides helper utilities for consuming streamed generation output.
The actual streaming implementation lives in the provider and AIRuntime.
"""

from __future__ import annotations

from typing import Iterator

from backend.runtime.generation import AIRuntime
from backend.runtime.models import GenerationRequest


def stream_tokens(
    runtime: AIRuntime,
    request: GenerationRequest,
    request_id: str | None = None,
) -> Iterator[str]:
    """Stream tokens from the runtime.

    This is a convenience wrapper around AIRuntime.stream() for use
    by API endpoints and internal services.

    Args:
        runtime: The AIRuntime instance.
        request: The generation request.
        request_id: Optional request ID to propagate.

    Yields:
        Text chunks as they are generated.
    """
    return runtime.stream(request, request_id)


def collect_stream(token_iterator: Iterator[str]) -> str:
    """Collect all streamed tokens into a single string.

    Useful for callers that want the complete response but also
    need to go through the streaming path.
    """
    return ''.join(token_iterator)
