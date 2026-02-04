"""
LLM Client Port

Protocol for Large Language Model clients used in knowledge context services.
Provides a unified interface for different LLM providers (OpenAI, Anthropic, Gemini, etc.).

Constitution Compliance:
- Article II (Hexagonal): Application port defining LLM interaction contract
- Article V (SOLID): Dependency Inversion - services depend on this abstraction

Warzone 4: AI Brain - BRAIN-009A
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """
    Request to an LLM provider.

    Why frozen:
        Immutable snapshot ensures request doesn't change during processing.

    Attributes:
        system_prompt: System instructions for the LLM
        user_prompt: User query or task
        temperature: Sampling temperature (0.0-2.0, lower = more deterministic)
        max_tokens: Maximum tokens to generate
    """

    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """
    Response from an LLM provider.

    Attributes:
        text: Generated text content
        model: Model identifier used for generation
        tokens_used: Total tokens used (input + output), if available
    """

    text: str
    model: str
    tokens_used: int | None = None


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class ILLMClient(Protocol):
    """
    Protocol for LLM client implementations.

    Defines the interface for calling Large Language Models.
    Implementations can wrap OpenAI, Anthropic, Gemini, or other providers.

    Example:
        >>> client = GeminiLLMClient(api_key="...")
        >>> request = LLMRequest(
        ...     system_prompt="You are a helpful assistant.",
        ...     user_prompt="What is the capital of France?"
        ... )
        >>> response = await client.generate(request)
        >>> print(response.text)
    """

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using the LLM.

        Args:
            request: LLMRequest with system/user prompts and parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMError: If generation fails
        """
        raise NotImplementedError("ILLMClient implementations must define `generate`.")
