"""Runtime configuration bridge.

Reads validated settings from the application config and exposes
them as a simple object for the runtime layer.
"""

from __future__ import annotations

from backend.config import get_settings


class RuntimeConfig:
    """Provides runtime-specific configuration values."""

    def __init__(self) -> None:
        s = get_settings()

        # Provider
        self.host: str = s.ollama_host
        self.model: str = s.ollama_model
        self.embed_model: str = getattr(s, 'ollama_embed_model', '')
        self.fallback_model: str = s.ollama_fallback_model

        # Generation parameters
        self.temperature: float = s.llm_temperature
        self.top_p: float = s.llm_top_p
        self.top_k: int = s.llm_top_k
        self.num_ctx: int = s.llm_num_ctx
        self.max_tokens: int = s.llm_max_tokens

        # Reliability
        self.timeout: int = s.llm_timeout_seconds
        self.max_retries: int = s.llm_max_retries
