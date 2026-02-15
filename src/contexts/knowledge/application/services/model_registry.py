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

from ...domain.models.model_registry import (
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


class ModelRegistry:
    """
    Registry for LLM model configurations.

    Why:
        - Centralizes model definitions and capabilities
        - Provides task-based model selection
        - Supports model aliases for shorthand references
        - Enables dynamic model switching

    The registry maintains:
    1. Model definitions with capabilities and costs
    2. Task-based default configurations
    3. Model aliases for shorthand references

    Example:
        >>> registry = ModelRegistry()
        >>> # Get model for task
        >>> config = registry.get_model_for_task(TaskType.CREATIVE)
        >>> print(config.model_name)  # "gemini-2.0-flash"
        >>>
        >>> # Resolve alias
        >>> result = registry.resolve_model("gpt4")
        >>> print(result.qualified_name)  # "openai:gpt-4o"
    """

    def __init__(self, config: Optional[ModelRegistryConfig] = None) -> None:
        """
        Initialize the model registry.

        Args:
            config: Optional registry configuration
        """
        self._config = config or ModelRegistryConfig()
        self._models: dict[tuple[LLMProvider, str], ModelDefinition] = {}
        self._task_configs: dict[TaskType, TaskModelConfig] = {}
        self._aliases: dict[str, ModelAlias] = {}

        # Register default models
        self._register_default_models()

        # Register default task configs
        self._register_default_task_configs()

        # Register default aliases
        self._register_default_aliases()

        # Register custom models
        for provider, models in self._config.custom_models.items():
            for model in models:
                self.register_model(model)

        # Register custom task configs
        for task_config in self._config.custom_task_configs:
            self.register_task_config(task_config)

        # Register custom aliases
        for alias in self._config.custom_aliases:
            self.register_alias(alias)

        # Load aliases from config file if specified
        if self._config.alias_config_path:
            self._load_aliases_from_file(self._config.alias_config_path)

        # Load aliases from environment variable
        self._load_aliases_from_env()

        log = logger.bind(
            models_count=len(self._models),
            task_configs_count=len(self._task_configs),
            aliases_count=len(self._aliases),
        )
        log.info("model_registry_initialized")

    def _register_default_models(self) -> None:
        """Register default model definitions."""
        for provider, models in DEFAULT_MODELS.items():
            for model in models:
                self._models[(provider, model.model_name)] = model

    def _register_default_task_configs(self) -> None:
        """Register default task-based configurations."""
        for config in DEFAULT_TASK_CONFIGS:
            self._task_configs[config.task_type] = config

    def _register_default_aliases(self) -> None:
        """Register default model aliases."""
        for alias in DEFAULT_ALIASES:
            self._aliases[alias.alias] = alias

    def _load_aliases_from_file(self, path: Path) -> None:
        """
        Load aliases from a configuration file.

        Args:
            path: Path to the alias configuration file (JSON or TOML)
        """
        if not path.exists():
            logger.debug("alias_config_file_not_found", path=str(path))
            return

        import json

        try:
            with open(path, "r") as f:
                data = json.load(f)
                config = ModelRegistryConfigFile(**data)

            for alias_name, target in config.aliases.items():
                try:
                    alias = ModelAlias.from_string(alias_name, target)
                    self._aliases[alias_name] = alias
                except ValueError as e:
                    logger.warning(
                        "invalid_alias_in_config",
                        alias=alias_name,
                        target=target,
                        error=str(e),
                    )

            logger.info(
                "aliases_loaded_from_file",
                path=str(path),
                count=len(config.aliases),
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "failed_to_load_alias_config",
                path=str(path),
                error=str(e),
            )

    def _load_aliases_from_env(self) -> None:
        """Load aliases from MODEL_ALIASES environment variable.

        Format: alias1=provider:model1;alias2=provider:model2
        Example: gpt4=openai:gpt-4-turbo;claude=anthropic:claude-3-opus-20240229
        """
        env_aliases = os.getenv("MODEL_ALIASES", "")
        if not env_aliases:
            return

        for alias_def in env_aliases.split(";"):
            if not alias_def.strip():
                continue

            if "=" not in alias_def:
                logger.warning("invalid_alias_env_format", alias=alias_def)
                continue

            alias_name, target = alias_def.split("=", 1)
            alias_name = alias_name.strip()
            target = target.strip()

            try:
                alias = ModelAlias.from_string(alias_name, target)
                self._aliases[alias_name] = alias
            except ValueError as e:
                logger.warning(
                    "invalid_alias_in_env",
                    alias=alias_name,
                    target=target,
                    error=str(e),
                )

        logger.info(
            "aliases_loaded_from_env",
            count=len([a for a in env_aliases.split(";") if a.strip()]),
        )

    def register_model(self, model: ModelDefinition) -> None:
        """
        Register a model definition.

        Args:
            model: Model definition to register
        """
        key = (model.provider, model.model_name)
        self._models[key] = model
        logger.debug(
            "model_registered",
            provider=model.provider.value,
            model_name=model.model_name,
        )

    def register_task_config(self, config: TaskModelConfig) -> None:
        """
        Register a task-based model configuration.

        Args:
            config: Task configuration to register
        """
        self._task_configs[config.task_type] = config
        logger.debug(
            "task_config_registered",
            task_type=config.task_type.value,
            provider=config.provider.value,
            model_name=config.model_name,
        )

    def register_alias(self, alias: ModelAlias) -> None:
        """
        Register a model alias.

        Args:
            alias: Alias to register
        """
        self._aliases[alias.alias] = alias
        logger.debug(
            "alias_registered",
            alias=alias.alias,
            target=alias.target,
        )

    def get_model(
        self, provider: LLMProvider, model_name: str
    ) -> Optional[ModelDefinition]:
        """
        Get a model definition.

        Args:
            provider: LLM provider
            model_name: Model name

        Returns:
            ModelDefinition if found, None otherwise
        """
        return self._models.get((provider, model_name))

    def list_models(
        self,
        provider: Optional[LLMProvider] = None,
        include_deprecated: bool = False,
    ) -> list[ModelDefinition]:
        """
        List all registered models.

        Args:
            provider: Optional provider filter
            include_deprecated: Whether to include deprecated models

        Returns:
            List of model definitions
        """
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if not include_deprecated:
            models = [m for m in models if not m.deprecated]

        return models

    def get_model_for_task(self, task_type: TaskType) -> TaskModelConfig:
        """
        Get the model configuration for a task type.

        Args:
            task_type: The task type

        Returns:
            TaskModelConfig for the task

        Raises:
            ValueError: If task type has no configuration
        """
        config = self._task_configs.get(task_type)
        if config is None:
            raise ValueError(f"No model configuration for task type: {task_type}")
        return config

    def resolve_model(
        self, model_ref: str, default_provider: LLMProvider = LLMProvider.GEMINI
    ) -> ModelLookupResult:
        """
        Resolve a model reference to provider and model name.

        Supports formats:
        - "alias" -> looks up in aliases
        - "provider:model" -> parses directly
        - "model" -> uses default_provider

        Args:
            model_ref: Model reference string
            default_provider: Provider to use if not specified

        Returns:
            ModelLookupResult with resolved provider and model name

        Example:
            >>> registry.resolve_model("gpt4")
            ModelLookupResult(provider=LLMProvider.OPENAI, model_name="gpt-4o", ...)
            >>> registry.resolve_model("anthropic:claude-3-opus-20240229")
            ModelLookupResult(provider=LLMProvider.ANTHROPIC, model_name="claude-3-opus-20240229", ...)
        """
        # Check if it's an alias
        if alias := self._aliases.get(model_ref):
            return ModelLookupResult(
                provider=alias.provider,
                model_name=alias.model_name,
                model_definition=self.get_model(alias.provider, alias.model_name),
                alias_used=alias.alias,
            )

        # Check if it's in "provider:model" format
        if ":" in model_ref:
            provider_str, model_name = model_ref.split(":", 1)

            try:
                provider = LLMProvider(provider_str)
            except ValueError:
                # Unknown provider, try to find it as an alias
                if alias := self._aliases.get(provider_str):
                    return ModelLookupResult(
                        provider=alias.provider,
                        model_name=model_name,
                        model_definition=self.get_model(alias.provider, model_name),
                        alias_used=f"{provider_str}:{model_name}",
                    )
                raise ValueError(
                    f"Invalid provider '{provider_str}'. "
                    f"Must be one of: {[p.value for p in LLMProvider]}"
                )

            return ModelLookupResult(
                provider=provider,
                model_name=model_name,
                model_definition=self.get_model(provider, model_name),
            )

        # Treat as model name with default provider
        return ModelLookupResult(
            provider=default_provider,
            model_name=model_ref,
            model_definition=self.get_model(default_provider, model_ref),
        )

    def list_aliases(self) -> list[ModelAlias]:
        """
        List all registered aliases.

        Returns:
            List of model aliases
        """
        return list(self._aliases.values())

    def list_task_types(self) -> list[TaskType]:
        """
        List all available task types.

        Returns:
            List of task types
        """
        return list(TaskType)

    def get_recommended_model(
        self,
        task_type: Optional[TaskType] = None,
        requires_functions: bool = False,
        requires_vision: bool = False,
        max_cost: Optional[float] = None,
        provider_filter: Optional[list[LLMProvider]] = None,
    ) -> Optional[ModelDefinition]:
        """
        Get a recommended model based on requirements.

        Args:
            task_type: Optional task type for task-based selection
            requires_functions: Whether model must support function calling
            requires_vision: Whether model must support vision
            max_cost: Maximum cost per 1M tokens (output)
            provider_filter: Optional list of allowed providers

        Returns:
            Best matching ModelDefinition, or None if no match
        """
        candidates: list[ModelDefinition] = []

        if task_type:
            # Start with task-based recommendation
            task_config = self._task_configs.get(task_type)
            if task_config:
                model = self.get_model(task_config.provider, task_config.model_name)
                if model:
                    candidates.append(model)

                # Check fallback providers (null-safe iteration)
                for provider in task_config.fallback_providers or []:
                    if model := self.get_model(provider, task_config.model_name):
                        candidates.append(model)

        # If no task-based candidates, search all models
        if not candidates:
            candidates = self.list_models(include_deprecated=False)

        # Apply filters
        if requires_functions:
            candidates = [m for m in candidates if m.supports_functions]

        if requires_vision:
            candidates = [m for m in candidates if m.supports_vision]

        if provider_filter:
            candidates = [m for m in candidates if m.provider in provider_filter]

        if max_cost is not None:
            candidates = [
                m for m in candidates if m.cost_per_1m_output_tokens <= max_cost
            ]

        # Return best candidate (prefer lower cost, then higher context)
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda m: (m.cost_factor, -m.max_context_tokens),
        )

    def get_provider_for_model(self, model_ref: str) -> LLMProvider:
        """
        Get the provider for a model reference.

        Args:
            model_ref: Model reference (alias, provider:model, or model name)

        Returns:
            LLMProvider for the model

        Raises:
            ValueError: If model reference is invalid
        """
        result = self.resolve_model(model_ref)
        return result.provider

    def is_model_available(self, provider: LLMProvider, model_name: str) -> bool:
        """
        Check if a model is available in the registry.

        Args:
            provider: LLM provider
            model_name: Model name

        Returns:
            True if model is registered and not deprecated
        """
        model = self.get_model(provider, model_name)
        return model is not None and not model.deprecated

    def get_stats(self) -> dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        models_by_provider: dict[str, int] = {}
        for provider in list(LLMProvider):
            models_by_provider[provider.value] = len(
                [m for m in self._models.keys() if m[0] == provider]
            )

        return {
            "total_models": len(self._models),
            "total_aliases": len(self._aliases),
            "total_task_configs": len(self._task_configs),
            "models_by_provider": models_by_provider,
            "deprecated_models": len(
                [m for m in self._models.values() if m.deprecated]
            ),
        }


def create_model_registry(
    config: Optional[ModelRegistryConfig] = None,
) -> ModelRegistry:
    """
    Factory function to create a ModelRegistry.

    Why factory:
        - Provides convenient instantiation
        - Allows for future dependency injection
        - Consistent with other service factories

    Args:
        config: Optional registry configuration

    Returns:
        Configured ModelRegistry instance
    """
    return ModelRegistry(config)


__all__ = [
    "ModelRegistry",
    "ModelRegistryConfig",
    "ModelLookupResult",
    "ModelRegistryConfigFile",
    "create_model_registry",
    "DEFAULT_MODELS",
    "DEFAULT_TASK_CONFIGS",
    "DEFAULT_ALIASES",
]
