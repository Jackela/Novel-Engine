"""Infrastructure wiring for AI text generation in Studio."""

from __future__ import annotations

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)
from src.contexts.ai.infrastructure.providers.provider_factory import (
    create_text_generation_provider,
)
from src.shared.infrastructure.config.settings import get_settings


def create_studio_text_generation_provider(
    provider_name: TextGenerationProviderName,
    model_name: str,
) -> TextGenerationProvider:
    """Create a text generation provider using the runtime settings."""
    return create_text_generation_provider(get_settings(), provider_name, model_name)
