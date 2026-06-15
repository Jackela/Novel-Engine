"""Application-layer port for AI text generation in Studio."""

from __future__ import annotations

from typing import Protocol

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)


class TextGenerationProviderFactory(Protocol):
    """Factory that resolves runtime AI provider configuration.

    Implementations live in the infrastructure layer so that application
    services remain decoupled from provider-specific construction logic.
    """

    def __call__(
        self,
        provider_name: TextGenerationProviderName,
        model_name: str,
    ) -> TextGenerationProvider:
        """Create a configured text generation provider."""
        ...
