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
from typing import TYPE_CHECKING, Any

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


class PromptFormat(str, Enum):
    """
    Prompt format enumeration for different LLM families.

    Why str enum:
        String-compatible enum allows JSON serialization and direct comparison.

    Formats:
        CHAT_MESSAGES: Chat format with role-based messages (OpenAI, Gemini, Anthropic)
        COMPLETION: Single prompt completion format (Llama-style via Ollama)
        INSTRUCTION: Instruction-based format with explicit sections (Alpaca/DeepSeek style)
        CODE_INSTRUCTION: Code-focused instruction format (DeepSeek-Coder)
    """

    CHAT_MESSAGES = "chat_messages"
    COMPLETION = "completion"
    INSTRUCTION = "instruction"
    CODE_INSTRUCTION = "code_instruction"

    def __str__(self) -> str:
        """Return string value of the format."""
        return self.value


class PromptModelFamily(str, Enum):
    """
    Model family enumeration for prompt format selection.

    Why str enum:
        String-compatible enum allows JSON serialization and direct comparison.

    Why "Prompt" prefix:
        Distinguishes from token_counter.PromptModelFamily which is for tokenizer selection.
        This enum is specifically for prompt format selection.

    Families:
        GPT: OpenAI GPT models
        CLAUDE: Anthropic Claude models
        GEMINI: Google Gemini models
        LLAMA: Meta Llama models
        MISTRAL: Mistral AI models
        DEEPSEEK: DeepSeek models
        DEEPSEEK_CODER: DeepSeek-Coder models
        PHI: Microsoft Phi models
        QWEN: Alibaba Qwen models
        CODESTRAL: Code-focused Mistral models
        UNKNOWN: Unknown model family
    """

    GPT = "gpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    LLAMA = "llama"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    DEEPSEEK_CODER = "deepseek_coder"
    PHI = "phi"
    QWEN = "qwen"
    CODESTRAL = "codestral"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return string value of the family."""
        return self.value

    @classmethod
    def from_model_name(cls, model_name: str) -> "PromptModelFamily":
        """
        Detect model family from model name.

        Args:
            model_name: Model identifier string

        Returns:
            PromptModelFamily enum value
        """
        name_lower = model_name.lower()

        # DeepSeek models
        if "deepseek-coder" in name_lower or "deepseek_coder" in name_lower:
            return cls.DEEPSEEK_CODER
        if "deepseek" in name_lower:
            return cls.DEEPSEEK

        # Llama models
        if "llama" in name_lower or "llama-" in name_lower:
            return cls.LLAMA

        # Mistral models
        if "codestral" in name_lower:
            return cls.CODESTRAL
        if "mistral" in name_lower:
            return cls.MISTRAL

        # Phi models
        if "phi" in name_lower:
            return cls.PHI

        # Qwen models
        if "qwen" in name_lower:
            return cls.QWEN

        # GPT models
        if "gpt" in name_lower:
            return cls.GPT

        # Claude models
        if "claude" in name_lower:
            return cls.CLAUDE

        # Gemini models
        if "gemini" in name_lower:
            return cls.GEMINI

        return cls.UNKNOWN

    @property
    def default_prompt_format(self) -> PromptFormat:
        """
        Get the default prompt format for this model family.

        Returns:
            PromptFormat to use for this family
        """
        match self:
            case PromptModelFamily.DEEPSEEK_CODER:
                return PromptFormat.CODE_INSTRUCTION
            case PromptModelFamily.DEEPSEEK:
                return PromptFormat.INSTRUCTION
            case PromptModelFamily.LLAMA | PromptModelFamily.MISTRAL | PromptModelFamily.CODESTRAL:
                return PromptFormat.INSTRUCTION
            case PromptModelFamily.PHI | PromptModelFamily.QWEN:
                return PromptFormat.INSTRUCTION
            case _:
                return PromptFormat.CHAT_MESSAGES


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
        model_family: Model family for prompt format selection (auto-detected if UNKNOWN)
        prompt_format: Prompt format to use (auto-detected from family if CHAT_MESSAGES)
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
    model_family: PromptModelFamily = PromptModelFamily.UNKNOWN
    prompt_format: PromptFormat = PromptFormat.CHAT_MESSAGES

    def __post_init__(self) -> None:
        """Auto-detect model family and prompt format if not explicitly set."""
        # Auto-detect model family if UNKNOWN
        if self.model_family == PromptModelFamily.UNKNOWN:
            detected_family = PromptModelFamily.from_model_name(self.model_name)
            if detected_family != PromptModelFamily.UNKNOWN:
                object.__setattr__(self, "model_family", detected_family)

        # Auto-detect prompt format if CHAT_MESSAGES and family suggests otherwise
        if (
            self.prompt_format == PromptFormat.CHAT_MESSAGES
            and self.model_family != PromptModelFamily.UNKNOWN
            and self.model_family not in (PromptModelFamily.GPT, PromptModelFamily.CLAUDE, PromptModelFamily.GEMINI)
        ):
            detected_format = self.model_family.default_prompt_format
            if detected_format != PromptFormat.CHAT_MESSAGES:
                object.__setattr__(self, "prompt_format", detected_format)

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
    "PromptFormat",
    "PromptModelFamily",
    "ModelDefinition",
    "TaskModelConfig",
    "ModelAlias",
]
