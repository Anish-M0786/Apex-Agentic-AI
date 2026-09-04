"""Model manager for the Apex AI Runtime.

Manages configured model, queries available models,
verifies model availability, and supports fallback architecture.
"""

from __future__ import annotations

import logging

from backend.runtime.config import RuntimeConfig
from backend.runtime.models import ModelInfo
from backend.runtime.ollama_provider import OllamaProvider

log = logging.getLogger('apex.runtime.manager')


class ModelManager:
    """Centralized model management for the runtime."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        provider: OllamaProvider | None = None,
    ) -> None:
        self.config = config or RuntimeConfig()
        self.provider = provider or OllamaProvider(
            host=self.config.host,
            timeout=self.config.timeout,
            config=self.config,
        )

    # ---- model queries ---------------------------------------------------

    @property
    def configured_model(self) -> str:
        """Return the currently configured generation model."""
        return self.config.model

    @property
    def fallback_model(self) -> str:
        """Return the configured fallback model (empty if none)."""
        return self.config.fallback_model

    @property
    def has_fallback(self) -> bool:
        """Return True if a fallback model is configured."""
        return bool(self.config.fallback_model)

    def models(self) -> list[ModelInfo]:
        """Return all models available on the provider."""
        return self.provider.list_models()

    def configured_model_available(self) -> bool:
        """Check if the configured generation model is available."""
        return self.provider.model_available(self.config.model)

    def model_metadata(self) -> dict:
        """Return metadata about the configured model."""
        available = self.configured_model_available()
        all_models = self.models()
        size = None
        for m in all_models:
            base_configured = self.config.model.split(':')[0]
            if m.name == self.config.model or m.name.split(':')[0] == base_configured:
                size = m.size
                break
        return {
            'name': self.config.model,
            'available': available,
            'size': size,
            'fallback': self.config.fallback_model or None,
        }

    def select(self, model: str) -> str:
        """Validate and select a model.

        Raises ValueError if the model is not available.
        """
        if not self.provider.model_available(model):
            raise ValueError(f'Model {model!r} is not available on the provider')
        log.info('Model selected: %s', model)
        return model
