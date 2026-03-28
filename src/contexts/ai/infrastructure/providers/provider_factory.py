"""Provider factory for text generation adapters."""

from __future__ import annotations

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.openai_compatible_text_generation_provider import (
    OpenAICompatibleTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.unconfigured_text_generation_provider import (
    UnconfiguredTextGenerationProvider,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings


def create_text_generation_provider(
    settings: NovelEngineSettings,
    provider_name: TextGenerationProviderName | None = None,
    model_name: str | None = None,
) -> TextGenerationProvider:
    """Create a concrete text generation provider from runtime settings."""
    resolved_provider = (provider_name or settings.llm.provider).strip().lower()
    resolved_model = model_name or settings.llm.resolved_model(resolved_provider)

    if resolved_provider == "mock":
        return DeterministicTextGenerationProvider(
            provider_name="mock",
            model=resolved_model or "deterministic-story-v1",
        )

    if resolved_provider == "dashscope":
        api_key = settings.llm.resolved_api_key("dashscope")
        if not api_key:
            return UnconfiguredTextGenerationProvider(
                provider_name="dashscope",
                model=resolved_model or "qwen3.5-flash",
                message="DASHSCOPE_API_KEY is required when provider is dashscope",
            )
        return DashScopeTextGenerationProvider(
            api_key=api_key,
            model=resolved_model or "qwen3.5-flash",
            api_base=settings.llm.resolved_api_base("dashscope"),
            transport_mode=settings.llm.resolved_dashscope_transport_mode(),
            timeout=settings.llm.timeout,
            retry_attempts=settings.llm.retry_attempts,
            retry_delay=settings.llm.retry_delay,
        )

    if resolved_provider == "openai_compatible":
        api_key = settings.llm.resolved_api_key("openai_compatible")
        if not api_key:
            return UnconfiguredTextGenerationProvider(
                provider_name="openai_compatible",
                model=resolved_model or "gpt-4o-mini",
                message="LLM_API_KEY is required when provider is openai_compatible",
            )
        return OpenAICompatibleTextGenerationProvider(
            api_key=api_key,
            model=resolved_model or "gpt-4o-mini",
            api_base=settings.llm.resolved_api_base("openai_compatible"),
            timeout=settings.llm.timeout,
        )

    raise ValueError(f"Unsupported text generation provider: {resolved_provider}")
