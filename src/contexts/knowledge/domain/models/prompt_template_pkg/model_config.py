"""Prompt Template Model Configuration.

Model configuration for prompt templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """
    Configuration for LLM model parameters.

    Why frozen:
        Prevents accidental modification of model behavior.

    Attributes:
        provider: LLM provider (e.g., 'gemini', 'openai', 'anthropic')
        model: Model name/identifier
        temperature: Sampling temperature (0.0 - 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        presence_penalty: Presence penalty for token generation
        frequency_penalty: Frequency penalty for token generation
        stop_sequences: Sequences that stop generation
    """

    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    model_name: str = "gemini-2.0-flash"  # Alias for model, for backward compatibility
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop_sequences: Optional[tuple[str, ...]] = None
    supports_functions: bool = False  # Whether the model supports function calling
    extra: dict[str, Any] = field(default_factory=dict)  # Extra model-specific parameters

    def __post_init__(self) -> None:
        """Validate model configuration."""
        # Validate provider
        if not self.provider or not self.provider.strip():
            raise ValueError("provider cannot be empty")

        # Validate model/model_name
        if not self.model_name or not self.model_name.strip():
            raise ValueError("model_name cannot be empty")

        # Validate temperature
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"temperature must be between 0.0 and 2.0, got {self.temperature}"
            )

        # Validate max_tokens
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if self.max_tokens > 8192:
            raise ValueError(
                f"max_tokens cannot exceed 8192, got {self.max_tokens}"
            )

        # Validate optional parameters
        if self.top_p is not None and not 0.0 <= self.top_p <= 1.0:
            raise ValueError(f"top_p must be between 0.0 and 1.0, got {self.top_p}")

        if self.top_k is not None and self.top_k < 1:
            raise ValueError(f"top_k must be positive, got {self.top_k}")

        # Validate frequency_penalty (-2.0 to 2.0 is standard range)
        if self.frequency_penalty is not None and not -2.0 <= self.frequency_penalty <= 2.0:
            raise ValueError(
                f"frequency_penalty must be between -2.0 and 2.0, got {self.frequency_penalty}"
            )

        # Validate presence_penalty (-2.0 to 2.0 is standard range)
        if self.presence_penalty is not None and not -2.0 <= self.presence_penalty <= 2.0:
            raise ValueError(
                f"presence_penalty must be between -2.0 and 2.0, got {self.presence_penalty}"
            )

        # Convert stop_sequences to tuple if provided
        if self.stop_sequences is not None and not isinstance(
            self.stop_sequences, tuple
        ):
            object.__setattr__(  # type: ignore[unreachable]
                self, "stop_sequences", tuple(self.stop_sequences)
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "supports_functions": self.supports_functions,
            "extra": self.extra,
        }
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.top_k is not None:
            result["top_k"] = self.top_k
        if self.presence_penalty is not None:
            result["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            result["frequency_penalty"] = self.frequency_penalty
        if self.stop_sequences:
            result["stop_sequences"] = list(self.stop_sequences)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        """Create from dictionary."""
        stop_seq = data.get("stop_sequences")
        return cls(
            provider=data.get("provider", "gemini"),
            model=data.get("model", "gemini-2.0-flash"),
            model_name=data.get("model_name", data.get("model", "gemini-2.0-flash")),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2048),
            top_p=data.get("top_p"),
            top_k=data.get("top_k"),
            presence_penalty=data.get("presence_penalty"),
            frequency_penalty=data.get("frequency_penalty"),
            stop_sequences=tuple(stop_seq) if stop_seq else None,
            supports_functions=data.get("supports_functions", False),
            extra=data.get("extra", {}),
        )

    def with_temperature(self, temperature: float) -> ModelConfig:
        """Create a new config with different temperature."""
        return ModelConfig(
            provider=self.provider,
            model=self.model,
            model_name=self.model_name,
            temperature=temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            top_k=self.top_k,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stop_sequences=self.stop_sequences,
            supports_functions=self.supports_functions,
            extra=self.extra.copy(),
        )
