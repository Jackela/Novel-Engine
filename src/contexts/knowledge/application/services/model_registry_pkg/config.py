"""
Model Registry Service

Manages LLM model configurations with task-based routing.
Supports model aliases and capability-based selection.

Constitution Compliance:
- Article II (Hexagonal): Application service with no infrastructure dependencies
- Article V (SOLID): SRP - model registration and lookup only

Warzone 4: AI Brain - BRAIN-023
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import structlog
from pydantic import BaseModel, Field

from src.core.result import (
    Err,
    Error,
    NotFoundError,
    Ok,
    Result,
    ValidationError,
)

from ....domain.models.model_registry import (
    LLMProvider,
    ModelAlias,
    ModelDefinition,
    PromptModelFamily,
    TaskModelConfig,
    TaskType,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Default model definitions for each provider
DEFAULT_MODELS: dict[LLMProvider, list[ModelDefinition]] = {
    LLMProvider.OPENAI: [
        ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            display_name="GPT-4o",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=2.50,
            cost_per_1m_output_tokens=10.00,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o-mini",
            display_name="GPT-4o Mini",
            max_context_tokens=128000,
            max_output_tokens=16384,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.15,
            cost_per_1m_output_tokens=0.60,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=10.00,
            cost_per_1m_output_tokens=30.00,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            max_context_tokens=16385,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.50,
            cost_per_1m_output_tokens=1.50,
            recommended_temperature=0.7,
            deprecated=True,
        ),
    ],
    LLMProvider.ANTHROPIC: [
        ModelDefinition(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            display_name="Claude 3.5 Sonnet",
            max_context_tokens=200000,
            max_output_tokens=8192,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=3.00,
            cost_per_1m_output_tokens=15.00,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-5-haiku-20241022",
            display_name="Claude 3.5 Haiku",
            max_context_tokens=200000,
            max_output_tokens=8192,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.80,
            cost_per_1m_output_tokens=4.00,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            display_name="Claude 3 Opus",
            max_context_tokens=200000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=15.00,
            cost_per_1m_output_tokens=75.00,
            recommended_temperature=0.7,
        ),
    ],
    LLMProvider.GEMINI: [
        ModelDefinition(
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.0-flash",
            display_name="Gemini 2.0 Flash",
            max_context_tokens=1000000,
            max_output_tokens=8192,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.075,
            cost_per_1m_output_tokens=0.30,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.5-pro",
            display_name="Gemini 2.5 Pro",
            max_context_tokens=1000000,
            max_output_tokens=8192,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=1.25,
            cost_per_1m_output_tokens=5.00,
            recommended_temperature=0.7,
        ),
        ModelDefinition(
            provider=LLMProvider.GEMINI,
            model_name="gemini-1.5-flash",
            display_name="Gemini 1.5 Flash",
            max_context_tokens=1000000,
            max_output_tokens=8192,
            supports_functions=True,
            supports_vision=True,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.075,
            cost_per_1m_output_tokens=0.30,
            recommended_temperature=0.7,
        ),
    ],
    LLMProvider.OLLAMA: [
        # Llama models
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="llama3.2",
            display_name="Llama 3.2",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.LLAMA,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="llama3.1",
            display_name="Llama 3.1",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.LLAMA,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="llama3",
            display_name="Llama 3",
            max_context_tokens=8192,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.LLAMA,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="llama2:13b",
            display_name="Llama 2 13B",
            max_context_tokens=4096,
            max_output_tokens=2048,
            supports_functions=False,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.LLAMA,
        ),
        # DeepSeek models
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-r1:32b",
            display_name="DeepSeek R1 32B",
            max_context_tokens=64000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.6,
            model_family=PromptModelFamily.DEEPSEEK,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-r1:14b",
            display_name="DeepSeek R1 14B",
            max_context_tokens=64000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.6,
            model_family=PromptModelFamily.DEEPSEEK,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-r1:8b",
            display_name="DeepSeek R1 8B",
            max_context_tokens=64000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.6,
            model_family=PromptModelFamily.DEEPSEEK,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-coder-v2:16b",
            display_name="DeepSeek Coder V2 16B",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.5,
            model_family=PromptModelFamily.DEEPSEEK_CODER,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-coder-v2:6.7b",
            display_name="DeepSeek Coder V2 6.7B",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.5,
            model_family=PromptModelFamily.DEEPSEEK_CODER,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-coder:33b",
            display_name="DeepSeek Coder 33B",
            max_context_tokens=16000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.5,
            model_family=PromptModelFamily.DEEPSEEK_CODER,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="deepseek-coder:6.7b",
            display_name="DeepSeek Coder 6.7B",
            max_context_tokens=16000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.5,
            model_family=PromptModelFamily.DEEPSEEK_CODER,
        ),
        # Mistral models
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="mistral",
            display_name="Mistral 7B",
            max_context_tokens=32768,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.MISTRAL,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="codestral",
            display_name="Codestral",
            max_context_tokens=32000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.5,
            model_family=PromptModelFamily.CODESTRAL,
        ),
        # Phi models
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="phi3",
            display_name="Phi-3",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.PHI,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="phi3:14b",
            display_name="Phi-3 14B",
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.PHI,
        ),
        # Qwen models
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="qwen2.5:7b",
            display_name="Qwen 2.5 7B",
            max_context_tokens=32768,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.QWEN,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="qwen2.5:14b",
            display_name="Qwen 2.5 14B",
            max_context_tokens=32768,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.QWEN,
        ),
        ModelDefinition(
            provider=LLMProvider.OLLAMA,
            model_name="qwen2.5:32b",
            display_name="Qwen 2.5 32B",
            max_context_tokens=32768,
            max_output_tokens=4096,
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
            model_family=PromptModelFamily.QWEN,
        ),
    ],
    LLMProvider.MOCK: [
        ModelDefinition(
            provider=LLMProvider.MOCK,
            model_name="mock-model",
            display_name="Mock Model",
            max_context_tokens=10000,
            max_output_tokens=1000,
            supports_functions=False,
            supports_vision=False,
            supports_streaming=False,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            recommended_temperature=0.7,
        ),
    ],
}

# Default task-based model configurations
DEFAULT_TASK_CONFIGS: list[TaskModelConfig] = [
    TaskModelConfig(
        task_type=TaskType.CREATIVE,
        provider=LLMProvider.GEMINI,
        model_name="gemini-2.0-flash",
        temperature=0.9,
        max_tokens=2000,
        fallback_providers=(LLMProvider.ANTHROPIC, LLMProvider.OPENAI),
    ),
    TaskModelConfig(
        task_type=TaskType.LOGICAL,
        provider=LLMProvider.OPENAI,
        model_name="gpt-4o",
        temperature=0.2,
        max_tokens=4000,
        fallback_providers=(LLMProvider.ANTHROPIC, LLMProvider.GEMINI),
    ),
    TaskModelConfig(
        task_type=TaskType.FAST,
        provider=LLMProvider.GEMINI,
        model_name="gemini-2.0-flash",
        temperature=0.5,
        max_tokens=1000,
        fallback_providers=(LLMProvider.OPENAI, LLMProvider.OLLAMA),
    ),
    TaskModelConfig(
        task_type=TaskType.CHEAP,
        provider=LLMProvider.GEMINI,
        model_name="gemini-2.0-flash",
        temperature=0.7,
        max_tokens=1000,
        fallback_providers=(LLMProvider.OPENAI, LLMProvider.OLLAMA),
    ),
]

# Default model aliases
DEFAULT_ALIASES: list[ModelAlias] = [
    # OpenAI aliases
    ModelAlias("gpt4", LLMProvider.OPENAI, "gpt-4o"),
    ModelAlias("gpt4-turbo", LLMProvider.OPENAI, "gpt-4-turbo"),
    ModelAlias("gpt35", LLMProvider.OPENAI, "gpt-3.5-turbo"),
    ModelAlias("gpt4o", LLMProvider.OPENAI, "gpt-4o"),
    ModelAlias("gpt4o-mini", LLMProvider.OPENAI, "gpt-4o-mini"),
    # Anthropic aliases
    ModelAlias("claude", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022"),
    ModelAlias("claude-sonnet", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022"),
    ModelAlias("claude-haiku", LLMProvider.ANTHROPIC, "claude-3-5-haiku-20241022"),
    ModelAlias("claude-opus", LLMProvider.ANTHROPIC, "claude-3-opus-20240229"),
    # Gemini aliases
    ModelAlias("gemini", LLMProvider.GEMINI, "gemini-2.0-flash"),
    ModelAlias("gemini-flash", LLMProvider.GEMINI, "gemini-2.0-flash"),
    ModelAlias("gemini-pro", LLMProvider.GEMINI, "gemini-2.5-pro"),
    # Llama aliases
    ModelAlias("llama", LLMProvider.OLLAMA, "llama3.2"),
    ModelAlias("llama2", LLMProvider.OLLAMA, "llama2:13b"),
    ModelAlias("llama3", LLMProvider.OLLAMA, "llama3"),
    ModelAlias("llama3.1", LLMProvider.OLLAMA, "llama3.1"),
    ModelAlias("llama3.2", LLMProvider.OLLAMA, "llama3.2"),
    # DeepSeek aliases
    ModelAlias("deepseek", LLMProvider.OLLAMA, "deepseek-r1:14b"),
    ModelAlias("deepseek-r1", LLMProvider.OLLAMA, "deepseek-r1:14b"),
    ModelAlias("deepseek-r1-32b", LLMProvider.OLLAMA, "deepseek-r1:32b"),
    ModelAlias("deepseek-r1-8b", LLMProvider.OLLAMA, "deepseek-r1:8b"),
    ModelAlias("deepseek-coder", LLMProvider.OLLAMA, "deepseek-coder-v2:16b"),
    ModelAlias("deepseek-coder-v2", LLMProvider.OLLAMA, "deepseek-coder-v2:16b"),
    ModelAlias("coder", LLMProvider.OLLAMA, "deepseek-coder-v2:16b"),
    # Mistral aliases
    ModelAlias("mistral", LLMProvider.OLLAMA, "mistral"),
    ModelAlias("codestral", LLMProvider.OLLAMA, "codestral"),
    # Phi aliases
    ModelAlias("phi", LLMProvider.OLLAMA, "phi3"),
    ModelAlias("phi3", LLMProvider.OLLAMA, "phi3"),
    ModelAlias("phi3-14b", LLMProvider.OLLAMA, "phi3:14b"),
    # Qwen aliases
    ModelAlias("qwen", LLMProvider.OLLAMA, "qwen2.5:7b"),
    ModelAlias("qwen2.5", LLMProvider.OLLAMA, "qwen2.5:7b"),
    ModelAlias("qwen-7b", LLMProvider.OLLAMA, "qwen2.5:7b"),
    ModelAlias("qwen-14b", LLMProvider.OLLAMA, "qwen2.5:14b"),
    ModelAlias("qwen-32b", LLMProvider.OLLAMA, "qwen2.5:32b"),
    # Functional aliases
    ModelAlias("fast", LLMProvider.GEMINI, "gemini-2.0-flash"),
    ModelAlias("cheap", LLMProvider.GEMINI, "gemini-2.0-flash"),
    ModelAlias("creative", LLMProvider.GEMINI, "gemini-2.0-flash"),
    ModelAlias("logical", LLMProvider.OPENAI, "gpt-4o"),
    ModelAlias("local", LLMProvider.OLLAMA, "llama3.2"),
    ModelAlias("code", LLMProvider.OLLAMA, "deepseek-coder-v2:16b"),
]


@dataclass
class ModelRegistryConfig:
    """
    Configuration for ModelRegistry.

    Attributes:
        custom_models: Additional model definitions
        custom_aliases: Custom model aliases
        custom_task_configs: Custom task-based configurations
        alias_config_path: Path to alias configuration file
    """

    custom_models: dict[LLMProvider, list[ModelDefinition]] = field(
        default_factory=dict
    )
    custom_aliases: list[ModelAlias] = field(default_factory=list)
    custom_task_configs: list[TaskModelConfig] = field(default_factory=list)
    alias_config_path: Optional[Path] = None


class ModelRegistryConfigFile(BaseModel):
    """
    Pydantic model for alias configuration file.

    Attributes:
        aliases: Dictionary of alias -> target mappings
    """

    aliases: dict[str, str] = Field(default_factory=dict)


@dataclass
class ModelLookupResult:
    """
    Result of a model lookup operation.

    Attributes:
        provider: The resolved provider
        model_name: The resolved model name
        model_definition: The full model definition (if found)
        alias_used: The alias that was used (if any)
        qualified_name: Fully qualified name (provider:model_name)
    """

    provider: LLMProvider
    model_name: str
    model_definition: Optional[ModelDefinition]
    alias_used: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        """Get the fully qualified model name."""
        return f"{self.provider.value}:{self.model_name}"


