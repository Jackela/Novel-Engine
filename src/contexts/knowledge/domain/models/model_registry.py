"""
Model Registry Domain Models

Manages LLM provider and model configurations with task-based routing.
Supports model aliases and capability-based selection.

Constitution Compliance:
- Article II (Hexagonal): Domain models independent of infrastructure
- Article I (DDD): Value objects for provider, model, and task configuration

Warzone 4: AI Brain - BRAIN-023
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass


class LLMProvider(str, Enum):
    """
    LLM Provider enumeration.

    Why str enum:
        String-compatible enum allows JSON serialization and direct comparison.

    Providers:
        OPENAI: OpenAI API (GPT-4, GPT-3.5, etc.)
        ANTHROPIC: Anthropic Claude API
        GEMINI: Google Gemini API
        OLLAMA: Local Ollama models
        MOCK: Mock provider for testing
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    MOCK = "mock"

    def __str__(self) -> str:
        """Return string value of the provider."""
        return self.value


class TaskType(str, Enum):
    """
    Task type enumeration for model routing.

    Why str enum:
        String-compatible enum allows JSON serialization.

    Task Types:
        CREATIVE: Creative writing, dialogue generation (needs higher temperature)
        LOGICAL: Logical reasoning, analysis, structured output (needs lower temperature)
        FAST: Quick operations, autocomplete (needs fast response)
        CHEAP: Cost-sensitive operations (needs low-cost model)
    """

    CREATIVE = "creative"
    LOGICAL = "logical"
    FAST = "fast"
    CHEAP = "cheap"

    def __str__(self) -> str:
        """Return string value of the task type."""
        return self.value


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    """
    Definition of an LLM model.

    Why frozen:
        Immutable model definitions prevent accidental modification.

    Why not a full entity:
        Model definitions are value objects with identity via provider:model_name.

    Attributes:
        provider: LLM provider hosting the model
        model_name: Model identifier (e.g., "gpt-4-turbo", "claude-3-opus-20240229")
        display_name: Human-readable name for UI display
        max_context_tokens: Maximum input context window
        max_output_tokens: Maximum output tokens (may be less than context)
        supports_functions: Whether model supports function calling
        supports_vision: Whether model supports vision/multimodal
        supports_streaming: Whether model supports streaming responses
        cost_per_1m_input_tokens: Cost per 1M input tokens in USD
        cost_per_1m_output_tokens: Cost per 1M output tokens in USD
        recommended_temperature: Recommended temperature for this model
        deprecated: Whether model is deprecated
        metadata: Additional model-specific metadata
    """

    provider: LLMProvider
    model_name: str
    display_name: str
    max_context_tokens: int
    max_output_tokens: int
    supports_functions: bool
    supports_vision: bool
    supports_streaming: bool
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float
    recommended_temperature: float = 0.7
    deprecated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Get the fully qualified model name (provider:model_name)."""
        return f"{self.provider.value}:{self.model_name}"

    @property
    def cost_factor(self) -> float:
        """
        Calculate cost factor for CHEAP task routing.

        Higher values = more expensive. Used for model selection.
        Combines input and output costs weighted toward output (typically more expensive).
        """
        return (
            self.cost_per_1m_input_tokens * 0.3
            + self.cost_per_1m_output_tokens * 0.7
        ) / 1_000_000


@dataclass(frozen=True, slots=True)
class TaskModelConfig:
    """
    Model configuration for a specific task type.

    Why frozen:
        Task configurations should be immutable once defined.

    Attributes:
        task_type: The task this config applies to
        provider: Preferred provider for this task
        model_name: Preferred model name
        temperature: Recommended temperature for this task
        max_tokens: Recommended max tokens for this task
        fallback_providers: Ordered list of fallback providers if primary unavailable
    """

    task_type: TaskType
    provider: LLMProvider
    model_name: str
    temperature: float
    max_tokens: int
    fallback_providers: tuple[LLMProvider, ...] = ()

    @property
    def qualified_model_name(self) -> str:
        """Get the fully qualified model name (provider:model_name)."""
        return f"{self.provider.value}:{self.model_name}"


@dataclass(frozen=True, slots=True)
class ModelAlias:
    """
    Model alias for shorthand references.

    Why frozen:
        Aliases should be immutable once defined.

    Aliases allow users to reference models with short names like:
    - "gpt4" -> "openai:gpt-4-turbo"
    - "claude" -> "anthropic:claude-3-opus-20240229"
    - "fast" -> "openai:gpt-3.5-turbo"

    Attributes:
        alias: The shorthand alias
        provider: Target provider
        model_name: Target model name
    """

    alias: str
    provider: LLMProvider
    model_name: str

    @property
    def target(self) -> str:
        """Get the target fully qualified model name."""
        return f"{self.provider.value}:{self.model_name}"

    @classmethod
    def from_string(cls, alias: str, target: str) -> "ModelAlias":
        """
        Create alias from target string.

        Args:
            alias: The alias name
            target: Target in "provider:model" format

        Returns:
            ModelAlias instance

        Raises:
            ValueError: If target format is invalid
        """
        if ":" not in target:
            raise ValueError(
                f"Invalid target format '{target}'. Expected 'provider:model'"
            )

        provider_str, model_name = target.split(":", 1)

        try:
            provider = LLMProvider(provider_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid provider '{provider_str}'. "
                f"Must be one of: {[p.value for p in LLMProvider]}"
            ) from e

        return cls(alias=alias, provider=provider, model_name=model_name)


__all__ = [
    "LLMProvider",
    "TaskType",
    "ModelDefinition",
    "TaskModelConfig",
    "ModelAlias",
]
