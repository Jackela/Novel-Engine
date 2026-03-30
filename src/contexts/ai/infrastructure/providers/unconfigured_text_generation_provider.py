"""Explicit provider used when runtime configuration is incomplete."""

from __future__ import annotations

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)


class UnconfiguredTextGenerationProvider:
    """Fail explicitly when generation is attempted without provider credentials."""

    def __init__(self, *, provider_name: str, model: str, message: str) -> None:
        self._provider_name = provider_name
        self._model = model
        self._message = message

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        raise TextGenerationProviderError(self._message)


__all__ = ["UnconfiguredTextGenerationProvider"]
