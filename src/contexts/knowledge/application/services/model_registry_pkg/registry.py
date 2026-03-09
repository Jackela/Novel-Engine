"""Model Registry Implementation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import structlog

from src.contexts.knowledge.application.services.model_registry_pkg.config import (
    DEFAULT_ALIASES,
    DEFAULT_MODELS,
    DEFAULT_TASK_CONFIGS,
    ModelLookupResult,
    ModelRegistryConfig,
    ModelRegistryConfigFile,
)
from src.contexts.knowledge.domain.models.model_registry import (
    LLMProvider,
    ModelAlias,
    ModelDefinition,
    TaskModelConfig,
    TaskType,
)
from src.core.result import Err, Error, NotFoundError, Ok, Result, ValidationError

logger = structlog.get_logger(__name__)

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
        >>> result = registry.get_model_for_task(TaskType.CREATIVE)
        >>> match result:
        ...     case Ok(config):
        ...         print(config.model_name)  # "gemini-2.0-flash"
        ...     case Err(error):
        ...         print(f"Error: {error}")
        >>>
        >>> # Resolve alias
        >>> result = registry.resolve_model("gpt4")
        >>> match result:
        ...     case Ok(lookup):
        ...         print(lookup.qualified_name)  # "openai:gpt-4o"
        ...     case Err(error):
        ...         print(f"Error: {error}")
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

    def register_model(self, model: ModelDefinition) -> Result[None, Error]:
        """
        Register a model definition.

        Args:
            model: Model definition to register

        Returns:
            Result containing None on success, Error on failure
        """
        try:
            key = (model.provider, model.model_name)
            self._models[key] = model
            logger.debug(
                "model_registered",
                provider=model.provider.value,
                model_name=model.model_name,
            )
            return Ok(None)
        except Exception as e:
            logger.error("model_registration_failed", error=str(e))
            return Err(
                Error(
                    code="MODEL_REGISTRATION_ERROR",
                    message=f"Failed to register model: {e}",
                    recoverable=True,
                )
            )

    def register_task_config(self, config: TaskModelConfig) -> Result[None, Error]:
        """
        Register a task-based model configuration.

        Args:
            config: Task configuration to register

        Returns:
            Result containing None on success, Error on failure
        """
        try:
            self._task_configs[config.task_type] = config
            logger.debug(
                "task_config_registered",
                task_type=config.task_type.value,
                provider=config.provider.value,
                model_name=config.model_name,
            )
            return Ok(None)
        except Exception as e:
            logger.error("task_config_registration_failed", error=str(e))
            return Err(
                Error(
                    code="TASK_CONFIG_REGISTRATION_ERROR",
                    message=f"Failed to register task config: {e}",
                    recoverable=True,
                )
            )

    def register_alias(self, alias: ModelAlias) -> Result[None, Error]:
        """
        Register a model alias.

        Args:
            alias: Alias to register

        Returns:
            Result containing None on success, Error on failure
        """
        try:
            self._aliases[alias.alias] = alias
            logger.debug(
                "alias_registered",
                alias=alias.alias,
                target=alias.target,
            )
            return Ok(None)
        except Exception as e:
            logger.error("alias_registration_failed", error=str(e))
            return Err(
                Error(
                    code="ALIAS_REGISTRATION_ERROR",
                    message=f"Failed to register alias: {e}",
                    recoverable=True,
                )
            )

    def get_model(
        self, provider: LLMProvider, model_name: str
    ) -> Result[ModelDefinition, Error]:
        """
        Get a model definition.

        Args:
            provider: LLM provider
            model_name: Model name

        Returns:
            Result containing ModelDefinition on success, NotFoundError on failure
        """
        key = (provider, model_name)
        model = self._models.get(key)
        if model is None:
            return Err(
                NotFoundError(
                    message=f"Model not found: {provider.value}:{model_name}",
                    details={"provider": provider.value, "model_name": model_name},
                )
            )
        return Ok(model)

    def list_models(
        self,
        provider: Optional[LLMProvider] = None,
        include_deprecated: bool = False,
    ) -> Result[list[ModelDefinition], Error]:
        """
        List all registered models.

        Args:
            provider: Optional provider filter
            include_deprecated: Whether to include deprecated models

        Returns:
            Result containing list of model definitions
        """
        try:
            models = list(self._models.values())

            if provider:
                models = [m for m in models if m.provider == provider]

            if not include_deprecated:
                models = [m for m in models if not m.deprecated]

            return Ok(models)
        except Exception as e:
            logger.error("list_models_failed", error=str(e))
            return Err(
                Error(
                    code="LIST_MODELS_ERROR",
                    message=f"Failed to list models: {e}",
                    recoverable=True,
                )
            )

    def get_model_for_task(self, task_type: TaskType) -> Result[TaskModelConfig, Error]:
        """
        Get the model configuration for a task type.

        Args:
            task_type: The task type

        Returns:
            Result containing TaskModelConfig on success, NotFoundError on failure
        """
        config = self._task_configs.get(task_type)
        if config is None:
            return Err(
                NotFoundError(
                    message=f"No model configuration for task type: {task_type.value}",
                    details={"task_type": task_type.value},
                )
            )
        return Ok(config)

    def resolve_model(
        self, model_ref: str, default_provider: LLMProvider = LLMProvider.GEMINI
    ) -> Result[ModelLookupResult, Error]:
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
            Result containing ModelLookupResult on success, Error on failure

        Example:
            >>> result = registry.resolve_model("gpt4")
            >>> match result:
            ...     case Ok(lookup):
            ...         print(lookup.qualified_name)  # "openai:gpt-4o"
            ...     case Err(error):
            ...         print(f"Error: {error}")
        """
        if not model_ref or not isinstance(model_ref, str):
            return Err(
                ValidationError(
                    message="model_ref must be a non-empty string",
                    field="model_ref",
                )
            )

        # Check if it's an alias
        if alias := self._aliases.get(model_ref):
            model_result = self.get_model(alias.provider, alias.model_name)
            return Ok(
                ModelLookupResult(
                    provider=alias.provider,
                    model_name=alias.model_name,
                    model_definition=model_result.unwrap() if model_result.is_ok else None,
                    alias_used=alias.alias,
                )
            )

        # Check if it's in "provider:model" format
        if ":" in model_ref:
            parts = model_ref.split(":", 1)
            provider_str = parts[0]
            model_name = parts[1]

            try:
                provider = LLMProvider(provider_str)
            except ValueError:
                # Unknown provider, try to find it as an alias
                if alias := self._aliases.get(provider_str):
                    model_result = self.get_model(alias.provider, model_name)
                    return Ok(
                        ModelLookupResult(
                            provider=alias.provider,
                            model_name=model_name,
                            model_definition=model_result.unwrap() if model_result.is_ok else None,
                            alias_used=f"{provider_str}:{model_name}",
                        )
                    )
                return Err(
                    ValidationError(
                        message=f"Invalid provider '{provider_str}'",
                        field="provider",
                        details={
                            "valid_providers": [p.value for p in LLMProvider],
                        },
                    )
                )

            model_result = self.get_model(provider, model_name)
            return Ok(
                ModelLookupResult(
                    provider=provider,
                    model_name=model_name,
                    model_definition=model_result.unwrap() if model_result.is_ok else None,
                )
            )

        # Treat as model name with default provider
        model_result = self.get_model(default_provider, model_ref)
        return Ok(
            ModelLookupResult(
                provider=default_provider,
                model_name=model_ref,
                model_definition=model_result.unwrap() if model_result.is_ok else None,
            )
        )

    def list_aliases(self) -> Result[list[ModelAlias], Error]:
        """
        List all registered aliases.

        Returns:
            Result containing list of model aliases
        """
        try:
            return Ok(list(self._aliases.values()))
        except Exception as e:
            logger.error("list_aliases_failed", error=str(e))
            return Err(
                Error(
                    code="LIST_ALIASES_ERROR",
                    message=f"Failed to list aliases: {e}",
                    recoverable=True,
                )
            )

    def list_task_types(self) -> Result[list[TaskType], Error]:
        """
        List all available task types.

        Returns:
            Result containing list of task types
        """
        try:
            return Ok(list(TaskType))
        except Exception as e:
            logger.error("list_task_types_failed", error=str(e))
            return Err(
                Error(
                    code="LIST_TASK_TYPES_ERROR",
                    message=f"Failed to list task types: {e}",
                    recoverable=True,
                )
            )

    def get_recommended_model(
        self,
        task_type: Optional[TaskType] = None,
        requires_functions: bool = False,
        requires_vision: bool = False,
        max_cost: Optional[float] = None,
        provider_filter: Optional[list[LLMProvider]] = None,
    ) -> Result[Optional[ModelDefinition], Error]:
        """
        Get a recommended model based on requirements.

        Args:
            task_type: Optional task type for task-based selection
            requires_functions: Whether model must support function calling
            requires_vision: Whether model must support vision
            max_cost: Maximum cost per 1M tokens (output)
            provider_filter: Optional list of allowed providers

        Returns:
            Result containing best matching ModelDefinition, or None if no match
        """
        try:
            candidates: list[ModelDefinition] = []

            if task_type:
                # Start with task-based recommendation
                task_config_result = self.get_model_for_task(task_type)
                if task_config_result.is_ok:
                    task_config = task_config_result.unwrap()
                    if task_config is not None:
                        model_result = self.get_model(task_config.provider, task_config.model_name)
                        if model_result.is_ok:
                            model_def = model_result.unwrap()
                            if model_def is not None:
                                candidates.append(model_def)

                        # Check fallback providers (null-safe iteration)
                        for provider in task_config.fallback_providers or []:
                            fallback_result = self.get_model(provider, task_config.model_name)
                            if fallback_result.is_ok:
                                fallback_model = fallback_result.unwrap()
                                if fallback_model is not None:
                                    candidates.append(fallback_model)

            # If no task-based candidates, search all models
            if not candidates:
                all_models_result = self.list_models(include_deprecated=False)
                if all_models_result.is_error:
                    return all_models_result  # type: ignore[return-value]
                all_models = all_models_result.unwrap()
                if all_models is None:
                    return Ok(None)
                candidates = all_models

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
                return Ok(None)

            best_model = min(
                candidates,
                key=lambda m: (m.cost_factor, -m.max_context_tokens),
            )
            return Ok(best_model)
        except Exception as e:
            logger.error("get_recommended_model_failed", error=str(e))
            return Err(
                Error(
                    code="RECOMMENDATION_ERROR",
                    message=f"Failed to get recommended model: {e}",
                    recoverable=True,
                )
            )

    def get_provider_for_model(self, model_ref: str) -> Result[LLMProvider, Error]:
        """
        Get the provider for a model reference.

        Args:
            model_ref: Model reference (alias, provider:model, or model name)

        Returns:
            Result containing LLMProvider on success, Error on failure
        """
        result = self.resolve_model(model_ref)
        if result.is_error:
            return result  # type: ignore[return-value]
        lookup_result = result.unwrap()
        if lookup_result is None:
            return Err(
                Error(
                    code="MODEL_RESOLUTION_ERROR",
                    message=f"Could not resolve model: {model_ref}",
                    recoverable=True,
                )
            )
        return Ok(lookup_result.provider)

    def is_model_available(self, provider: LLMProvider, model_name: str) -> bool:
        """
        Check if a model is available in the registry.

        Args:
            provider: LLM provider
            model_name: Model name

        Returns:
            True if model is registered and not deprecated
        """
        model_result = self.get_model(provider, model_name)
        if model_result.is_error:
            return False
        model = model_result.unwrap()
        if model is None:
            return False
        return not model.deprecated

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


