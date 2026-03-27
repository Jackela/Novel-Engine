"""Provider factory for text generation adapters."""

from __future__ import annotations

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.openai_text_generation_provider import (
    OpenAITextGenerationProvider,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings


def create_text_generation_provider(
    settings: NovelEngineSettings,
    provider_name: str | None = None,
    model_name: str | None = None,
) -> TextGenerationProvider:
    """Create a concrete text generation provider from runtime settings."""
    if provider_name is None and (settings.is_testing or settings.is_development):
        resolved_provider = "mock"
    else:
        resolved_provider = (provider_name or settings.llm.provider).strip().lower()
    resolved_model = model_name or settings.llm.model

    if resolved_provider == "mock":
        return DeterministicTextGenerationProvider(
            provider_name="mock",
            model=resolved_model or "deterministic-story-v1",
        )

    if resolved_provider == "openai":
        if not settings.llm.api_key:
            raise ValueError("LLM_API_KEY is required when provider is openai")
        return OpenAITextGenerationProvider(
            api_key=settings.llm.api_key,
            model=resolved_model or "gpt-4o-mini",
            api_base=settings.llm.api_base,
            timeout=settings.llm.timeout,
        )

    raise ValueError(f"Unsupported text generation provider: {resolved_provider}")
