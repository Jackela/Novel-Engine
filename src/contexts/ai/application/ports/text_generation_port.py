"""Text generation contract used by narrative workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

TextGenerationProviderName = Literal["mock", "dashscope", "openai_compatible"]


class TextGenerationProviderError(RuntimeError):
    """Raised when a text generation provider cannot complete a request."""


@dataclass(frozen=True)
class TextGenerationTask:
    """Structured generation task for provider adapters."""

    step: str
    system_prompt: str
    user_prompt: str
    response_schema: dict[str, Any]
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TextGenerationResult:
    """Structured response produced by a generation provider."""

    step: str
    provider: TextGenerationProviderName
    model: str
    raw_text: str
    content: dict[str, Any]


class TextGenerationProvider(Protocol):
    """Provider interface for structured text generation."""

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        """Generate structured JSON-like output for a task."""
        ...
