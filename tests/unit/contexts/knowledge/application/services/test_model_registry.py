"""
Tests for ModelRegistry Service

Unit tests for model registration, lookup, alias resolution, and task-based selection.

Warzone 4: AI Brain - BRAIN-023
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.contexts.knowledge.application.services.model_registry import (
    DEFAULT_ALIASES,
    DEFAULT_MODELS,
    DEFAULT_TASK_CONFIGS,
    ModelLookupResult,
    ModelRegistry,
    ModelRegistryConfig,
    ModelRegistryConfigFile,
    create_model_registry,
)
from src.contexts.knowledge.domain.models.model_registry import (
    LLMProvider,
    ModelAlias,
    ModelDefinition,
    TaskModelConfig,
    TaskType,
)

pytestmark = pytest.mark.unit


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self) -> None:
        """Test provider enum values are correct strings."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.OLLAMA.value == "ollama"
        assert LLMProvider.MOCK.value == "mock"

    def test_provider_string_conversion(self) -> None:
        """Test provider enum converts to string correctly."""
        assert str(LLMProvider.OPENAI) == "openai"
        assert str(LLMProvider.ANTHROPIC) == "anthropic"


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self) -> None:
        """Test task type enum values are correct strings."""
        assert TaskType.CREATIVE.value == "creative"
        assert TaskType.LOGICAL.value == "logical"
        assert TaskType.FAST.value == "fast"
        assert TaskType.CHEAP.value == "cheap"


class TestModelDefinition:
    """Tests for ModelDefinition value object."""

    def test_model_definition_properties(self) -> None:
        """Test model definition properties."""
        model = ModelDefinition(
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
        )

        assert model.provider == LLMProvider.OPENAI
        assert model.model_name == "gpt-4o"
        assert model.qualified_name == "openai:gpt-4o"
        assert model.cost_factor > 0

    def test_model_definition_frozen(self) -> None:
        """Test model definition is frozen."""
        model = ModelDefinition(
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
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            model.model_name = "gpt-3.5-turbo"


class TestModelAlias:
    """Tests for ModelAlias value object."""

    def test_alias_properties(self) -> None:
        """Test alias properties."""
        alias = ModelAlias(
            alias="gpt4",
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )

        assert alias.alias == "gpt4"
        assert alias.provider == LLMProvider.OPENAI
        assert alias.target == "openai:gpt-4o"

    def test_alias_from_string(self) -> None:
        """Test creating alias from target string."""
        alias = ModelAlias.from_string("gpt4", "openai:gpt-4o")

        assert alias.alias == "gpt4"
        assert alias.provider == LLMProvider.OPENAI
        assert alias.model_name == "gpt-4o"

    def test_alias_from_string_invalid_target(self) -> None:
        """Test alias from string with invalid target format."""
        with pytest.raises(ValueError, match="Invalid target format"):
            ModelAlias.from_string("gpt4", "invalid-format")

    def test_alias_from_string_invalid_provider(self) -> None:
        """Test alias from string with invalid provider."""
        with pytest.raises(ValueError, match="Invalid provider"):
            ModelAlias.from_string("gpt4", "invalid-provider:gpt-4o")


class TestModelRegistry:
    """Tests for ModelRegistry service."""

    def test_registry_initialization(self) -> None:
        """Test registry initializes with default models."""
        registry = ModelRegistry()

        stats = registry.get_stats()
        assert stats["total_models"] > 0
        assert stats["total_aliases"] > 0
        assert stats["total_task_configs"] == 4  # CREATIVE, LOGICAL, FAST, CHEAP

    def test_register_model(self) -> None:
        """Test registering a custom model."""
        registry = ModelRegistry()
        custom_model = ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="custom-model",
            display_name="Custom Model",
            max_context_tokens=1000,
            max_output_tokens=500,
            supports_functions=False,
            supports_vision=False,
            supports_streaming=False,
            cost_per_1m_input_tokens=1.0,
            cost_per_1m_output_tokens=1.0,
        )

        result = registry.register_model(custom_model)
        assert result.is_ok

        model_result = registry.get_model(LLMProvider.OPENAI, "custom-model")
        assert model_result.is_ok
        assert model_result.unwrap().model_name == "custom-model"

    def test_register_task_config(self) -> None:
        """Test registering a custom task config."""
        registry = ModelRegistry()
        custom_config = TaskModelConfig(
            task_type=TaskType.LOGICAL,
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.0-flash",
            temperature=0.1,
            max_tokens=2000,
        )

        result = registry.register_task_config(custom_config)
        assert result.is_ok

        result = registry.get_model_for_task(TaskType.LOGICAL)
        assert result.is_ok
        config = result.unwrap()
        assert config.provider == LLMProvider.GEMINI
        assert config.model_name == "gemini-2.0-flash"

    def test_register_alias(self) -> None:
        """Test registering a custom alias."""
        registry = ModelRegistry()
        custom_alias = ModelAlias(
            alias="myalias",
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )

        result = registry.register_alias(custom_alias)
        assert result.is_ok

        result = registry.resolve_model("myalias")
        assert result.is_ok
        lookup = result.unwrap()
        assert lookup.provider == LLMProvider.OPENAI
        assert lookup.model_name == "gpt-4o"
        assert lookup.alias_used == "myalias"

    def test_get_model(self) -> None:
        """Test getting a model by provider and name."""
        registry = ModelRegistry()

        result = registry.get_model(LLMProvider.OPENAI, "gpt-4o")
        assert result.is_ok
        model = result.unwrap()
        assert model.model_name == "gpt-4o"
        assert model.provider == LLMProvider.OPENAI

    def test_get_model_not_found(self) -> None:
        """Test getting a non-existent model returns NotFoundError."""
        registry = ModelRegistry()

        result = registry.get_model(LLMProvider.OPENAI, "non-existent")
        assert result.is_error
        assert result.error.code == "NOT_FOUND"

    def test_list_models(self) -> None:
        """Test listing all models."""
        registry = ModelRegistry()

        result = registry.list_models()
        assert result.is_ok
        models = result.unwrap()
        assert len(models) > 0

        # Check non-deprecated only
        deprecated_models = [m for m in models if m.deprecated]
        assert len(deprecated_models) == 0

    def test_list_models_with_provider_filter(self) -> None:
        """Test listing models filtered by provider."""
        registry = ModelRegistry()

        result = registry.list_models(provider=LLMProvider.OPENAI)
        assert result.is_ok
        openai_models = result.unwrap()
        assert all(m.provider == LLMProvider.OPENAI for m in openai_models)

    def test_list_models_include_deprecated(self) -> None:
        """Test listing models includes deprecated when requested."""
        registry = ModelRegistry()

        result_all = registry.list_models(include_deprecated=True)
        result_non_deprecated = registry.list_models(include_deprecated=False)

        assert result_all.is_ok
        assert result_non_deprecated.is_ok
        assert len(result_all.unwrap()) >= len(result_non_deprecated.unwrap())

    def test_get_model_for_task(self) -> None:
        """Test getting model config for a task type."""
        registry = ModelRegistry()

        result = registry.get_model_for_task(TaskType.CREATIVE)
        assert result.is_ok
        config = result.unwrap()
        assert config.task_type == TaskType.CREATIVE
        assert config.temperature > 0.7  # CREATIVE uses higher temp

        result = registry.get_model_for_task(TaskType.LOGICAL)
        assert result.is_ok
        config = result.unwrap()
        assert config.task_type == TaskType.LOGICAL
        assert config.temperature < 0.5  # LOGICAL uses lower temp

    def test_get_model_for_task_invalid(self) -> None:
        """Test getting model for invalid task type returns error."""
        registry = ModelRegistry()

        # Create a mock registry with empty configs
        registry._task_configs = {}
        result = registry.get_model_for_task(TaskType.CREATIVE)
        assert result.is_error
        assert result.error.code == "NOT_FOUND"

    def test_resolve_model_alias(self) -> None:
        """Test resolving model reference via alias."""
        registry = ModelRegistry()

        result = registry.resolve_model("gpt4")
        assert result.is_ok
        lookup = result.unwrap()
        assert lookup.provider == LLMProvider.OPENAI
        assert lookup.model_name == "gpt-4o"
        assert lookup.alias_used == "gpt4"

    def test_resolve_model_qualified_name(self) -> None:
        """Test resolving model reference with qualified name."""
        registry = ModelRegistry()

        result = registry.resolve_model("openai:gpt-4o")
        assert result.is_ok
        lookup = result.unwrap()
        assert lookup.provider == LLMProvider.OPENAI
        assert lookup.model_name == "gpt-4o"
        assert lookup.alias_used is None

    def test_resolve_model_name_only(self) -> None:
        """Test resolving model reference with just model name."""
        registry = ModelRegistry()

        result = registry.resolve_model("gpt-4o", default_provider=LLMProvider.OPENAI)
        assert result.is_ok
        lookup = result.unwrap()
        assert lookup.provider == LLMProvider.OPENAI
        assert lookup.model_name == "gpt-4o"

    def test_resolve_model_invalid_provider(self) -> None:
        """Test resolving model with invalid provider returns validation error."""
        registry = ModelRegistry()

        result = registry.resolve_model("invalid-provider:model")
        assert result.is_error
        assert result.error.code == "VALIDATION_ERROR"

    def test_resolve_model_empty_ref(self) -> None:
        """Test resolving model with empty reference returns error."""
        registry = ModelRegistry()

        result = registry.resolve_model("")
        assert result.is_error

    def test_list_aliases(self) -> None:
        """Test listing all aliases."""
        registry = ModelRegistry()

        result = registry.list_aliases()
        assert result.is_ok
        aliases = result.unwrap()
        assert len(aliases) > 0

        # Check for expected aliases
        alias_names = [a.alias for a in aliases]
        assert "gpt4" in alias_names
        assert "claude" in alias_names
        assert "gemini" in alias_names

    def test_list_task_types(self) -> None:
        """Test listing all task types."""
        registry = ModelRegistry()

        result = registry.list_task_types()
        assert result.is_ok
        task_types = result.unwrap()
        assert TaskType.CREATIVE in task_types
        assert TaskType.LOGICAL in task_types
        assert TaskType.FAST in task_types
        assert TaskType.CHEAP in task_types

    def test_get_recommended_model_by_task(self) -> None:
        """Test getting recommended model based on task."""
        registry = ModelRegistry()

        result = registry.get_recommended_model(task_type=TaskType.CREATIVE)
        assert result.is_ok
        model = result.unwrap()
        assert model is not None

    def test_get_recommended_model_with_filters(self) -> None:
        """Test getting recommended model with capability filters."""
        registry = ModelRegistry()

        # Require function support
        result = registry.get_recommended_model(requires_functions=True)
        assert result.is_ok
        model = result.unwrap()
        assert model is not None
        assert model.supports_functions is True

        # Require vision support
        result = registry.get_recommended_model(requires_vision=True)
        assert result.is_ok
        model = result.unwrap()
        assert model is not None
        assert model.supports_vision is True

    def test_get_recommended_model_with_cost_limit(self) -> None:
        """Test getting recommended model with cost limit."""
        registry = ModelRegistry()

        # Low cost limit should return cheapest models
        result = registry.get_recommended_model(max_cost=1.0)
        assert result.is_ok
        model = result.unwrap()
        assert model is not None
        assert model.cost_per_1m_output_tokens <= 1.0

    def test_get_recommended_model_with_provider_filter(self) -> None:
        """Test getting recommended model with provider filter."""
        registry = ModelRegistry()

        result = registry.get_recommended_model(provider_filter=[LLMProvider.OPENAI])
        assert result.is_ok
        model = result.unwrap()
        assert model is not None
        assert model.provider == LLMProvider.OPENAI

    def test_get_recommended_model_no_match(self) -> None:
        """Test getting recommended model when no match exists."""
        registry = ModelRegistry()

        # Require vision with provider that has no vision models
        result = registry.get_recommended_model(
            provider_filter=[LLMProvider.OLLAMA],
            requires_vision=True,  # Ollama models don't support vision
        )
        assert result.is_ok
        model = result.unwrap()
        # Should return None when no match
        assert model is None

    def test_get_provider_for_model(self) -> None:
        """Test getting provider for a model reference."""
        registry = ModelRegistry()

        result = registry.get_provider_for_model("gpt4")
        assert result.is_ok
        assert result.unwrap() == LLMProvider.OPENAI

        result = registry.get_provider_for_model("anthropic:claude-3-opus-20240229")
        assert result.is_ok
        assert result.unwrap() == LLMProvider.ANTHROPIC

    def test_get_provider_for_model_invalid(self) -> None:
        """Test getting provider for invalid model reference."""
        registry = ModelRegistry()

        result = registry.get_provider_for_model("invalid-provider:model")
        assert result.is_error

    def test_is_model_available(self) -> None:
        """Test checking if model is available."""
        registry = ModelRegistry()

        assert registry.is_model_available(LLMProvider.OPENAI, "gpt-4o") is True
        assert registry.is_model_available(LLMProvider.OPENAI, "non-existent") is False

    def test_is_model_available_deprecated(self) -> None:
        """Test that deprecated models are not available."""
        registry = ModelRegistry()

        # gpt-3.5-turbo is marked as deprecated
        assert registry.is_model_available(LLMProvider.OPENAI, "gpt-3.5-turbo") is False

    def test_get_stats(self) -> None:
        """Test getting registry statistics."""
        registry = ModelRegistry()

        stats = registry.get_stats()
        assert "total_models" in stats
        assert "total_aliases" in stats
        assert "total_task_configs" in stats
        assert "models_by_provider" in stats
        assert "deprecated_models" in stats

    def test_stats_models_by_provider(self) -> None:
        """Test stats show models grouped by provider."""
        registry = ModelRegistry()

        stats = registry.get_stats()
        by_provider = stats["models_by_provider"]

        assert "openai" in by_provider
        assert "anthropic" in by_provider
        assert "gemini" in by_provider
        assert "ollama" in by_provider

    def test_frozen_model_definition_immutability(self) -> None:
        """Test that model definitions are immutable."""
        model = ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="test-model",
            display_name="Test",
            max_context_tokens=1000,
            max_output_tokens=500,
            supports_functions=False,
            supports_vision=False,
            supports_streaming=False,
            cost_per_1m_input_tokens=1.0,
            cost_per_1m_output_tokens=1.0,
        )

        original_name = model.model_name
        with pytest.raises(Exception):
            model.model_name = "changed"

        assert model.model_name == original_name


class TestModelRegistryConfigFile:
    """Tests for ModelRegistryConfigFile."""

    def test_empty_config(self) -> None:
        """Test empty configuration file."""
        config = ModelRegistryConfigFile()
        assert config.aliases == {}

    def test_config_with_aliases(self) -> None:
        """Test configuration with aliases."""
        data = {
            "aliases": {
                "gpt4": "openai:gpt-4o",
                "claude": "anthropic:claude-3-opus-20240229",
            }
        }
        config = ModelRegistryConfigFile(**data)

        assert len(config.aliases) == 2
        assert config.aliases["gpt4"] == "openai:gpt-4o"


class TestModelRegistryFileLoading:
    """Tests for loading aliases from files."""

    def test_load_aliases_from_valid_file(self, tmp_path: Path) -> None:
        """Test loading aliases from a valid JSON file."""
        config_file = tmp_path / "aliases.json"
        config_data = {
            "aliases": {
                "custom-gpt4": "openai:gpt-4o",
                "custom-claude": "anthropic:claude-3-5-sonnet-20241022",
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = ModelRegistryConfig(alias_config_path=config_file)
        registry = ModelRegistry(config)

        # Check custom aliases are registered
        result = registry.resolve_model("custom-gpt4")
        assert result.is_ok
        lookup = result.unwrap()
        assert lookup.provider == LLMProvider.OPENAI
        assert lookup.model_name == "gpt-4o"

    def test_load_aliases_from_missing_file(self, tmp_path: Path) -> None:
        """Test loading from non-existent file doesn't crash."""
        config_file = tmp_path / "non-existent.json"

        config = ModelRegistryConfig(alias_config_path=config_file)
        registry = ModelRegistry(config)

        # Registry should still work with default aliases
        result = registry.resolve_model("gpt4")
        assert result.is_ok
        assert result.unwrap().provider == LLMProvider.OPENAI

    def test_load_aliases_from_invalid_json(self, tmp_path: Path) -> None:
        """Test loading from invalid JSON file logs warning."""
        config_file = tmp_path / "invalid.json"

        with open(config_file, "w") as f:
            f.write("not valid json {]")

        config = ModelRegistryConfig(alias_config_path=config_file)
        registry = ModelRegistry(config)

        # Registry should still work
        stats = registry.get_stats()
        assert stats["total_aliases"] > 0

    def test_load_aliases_with_invalid_target(self, tmp_path: Path) -> None:
        """Test loading aliases with invalid target formats."""
        config_file = tmp_path / "aliases.json"
        config_data = {
            "aliases": {
                "valid": "openai:gpt-4o",
                "invalid-format": "missing-colon",
                "invalid-provider": "unknown-provider:model",
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = ModelRegistryConfig(alias_config_path=config_file)
        registry = ModelRegistry(config)

        # Valid alias should work
        result = registry.resolve_model("valid")
        assert result.is_ok
        assert result.unwrap().provider == LLMProvider.OPENAI

        # Invalid aliases should be skipped
        # (registry should still have default aliases)
        stats = registry.get_stats()
        assert stats["total_aliases"] > 0


class TestModelRegistryEnvLoading:
    """Tests for loading aliases from environment variables."""

    @patch.dict(
        "os.environ",
        {"MODEL_ALIASES": "gpt4=openai:gpt-4o;claude=anthropic:claude-3-opus-20240229"},
    )
    def test_load_aliases_from_env(self) -> None:
        """Test loading aliases from MODEL_ALIASES env var."""
        registry = ModelRegistry()

        # Check env aliases are registered
        result = registry.resolve_model("gpt4")
        assert result.is_ok
        assert result.unwrap().provider == LLMProvider.OPENAI

    @patch.dict("os.environ", {"MODEL_ALIASES": "invalid-format"})
    def test_load_aliases_from_env_invalid_format(self) -> None:
        """Test loading invalid alias format from env doesn't crash."""
        registry = ModelRegistry()

        # Registry should still work with defaults
        stats = registry.get_stats()
        assert stats["total_aliases"] > 0

    @patch.dict("os.environ", {"MODEL_ALIASES": ""})
    def test_load_aliases_from_empty_env(self) -> None:
        """Test loading from empty env var doesn't crash."""
        registry = ModelRegistry()

        stats = registry.get_stats()
        assert stats["total_aliases"] > 0


class TestModelRegistryFactory:
    """Tests for the create_model_registry factory function."""

    def test_factory_creates_registry(self) -> None:
        """Test factory creates a properly configured registry."""
        registry = create_model_registry()

        assert isinstance(registry, ModelRegistry)
        stats = registry.get_stats()
        assert stats["total_models"] > 0

    def test_factory_with_config(self) -> None:
        """Test factory respects provided config."""
        custom_model = ModelDefinition(
            provider=LLMProvider.OPENAI,
            model_name="factory-test",
            display_name="Factory Test",
            max_context_tokens=1000,
            max_output_tokens=500,
            supports_functions=False,
            supports_vision=False,
            supports_streaming=False,
            cost_per_1m_input_tokens=1.0,
            cost_per_1m_output_tokens=1.0,
        )

        config = ModelRegistryConfig(custom_models={LLMProvider.OPENAI: [custom_model]})
        registry = create_model_registry(config)

        result = registry.get_model(LLMProvider.OPENAI, "factory-test")
        assert result.is_ok
        assert result.unwrap().model_name == "factory-test"


class TestModelLookupResult:
    """Tests for ModelLookupResult."""

    def test_qualified_name_property(self) -> None:
        """Test qualified_name property formats correctly."""
        result = ModelLookupResult(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            model_definition=None,
            alias_used="gpt4",
        )

        assert result.qualified_name == "openai:gpt-4o"

    def test_result_without_alias(self) -> None:
        """Test result created without alias."""
        result = ModelLookupResult(
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.0-flash",
            model_definition=None,
        )

        assert result.alias_used is None
        assert result.qualified_name == "gemini:gemini-2.0-flash"


class TestTaskModelConfig:
    """Tests for TaskModelConfig."""

    def test_qualified_model_name_property(self) -> None:
        """Test qualified_model_name formats correctly."""
        config = TaskModelConfig(
            task_type=TaskType.CREATIVE,
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            temperature=0.9,
            max_tokens=2000,
        )

        assert config.qualified_model_name == "openai:gpt-4o"

    def test_config_with_fallbacks(self) -> None:
        """Test config with fallback providers."""
        config = TaskModelConfig(
            task_type=TaskType.LOGICAL,
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            temperature=0.2,
            max_tokens=4000,
            fallback_providers=(
                LLMProvider.ANTHROPIC,
                LLMProvider.GEMINI,
            ),
        )

        # fallback_providers contains 2 providers (not including primary)
        assert len(config.fallback_providers) == 2
        assert config.fallback_providers[0] == LLMProvider.ANTHROPIC


class TestDefaultConstants:
    """Tests for default constants."""

    def test_default_models_structure(self) -> None:
        """Test DEFAULT_MODELS has correct structure."""
        assert LLMProvider.OPENAI in DEFAULT_MODELS
        assert LLMProvider.ANTHROPIC in DEFAULT_MODELS
        assert LLMProvider.GEMINI in DEFAULT_MODELS
        assert LLMProvider.OLLAMA in DEFAULT_MODELS
        assert LLMProvider.MOCK in DEFAULT_MODELS

    def test_default_task_configs_complete(self) -> None:
        """Test DEFAULT_TASK_CONFIGS has all task types."""
        task_types = {config.task_type for config in DEFAULT_TASK_CONFIGS}
        assert TaskType.CREATIVE in task_types
        assert TaskType.LOGICAL in task_types
        assert TaskType.FAST in task_types
        assert TaskType.CHEAP in task_types

    def test_default_aliases_complete(self) -> None:
        """Test DEFAULT_ALIASES has expected aliases."""
        alias_names = {alias.alias for alias in DEFAULT_ALIASES}
        assert "gpt4" in alias_names
        assert "claude" in alias_names
        assert "gemini" in alias_names
        assert "fast" in alias_names
        assert "cheap" in alias_names


class TestResultPattern:
    """Test Result pattern implementation in ModelRegistry."""

    def test_get_model_returns_result_like_object(self) -> None:
        """Test that get_model returns a Result-like object."""
        registry = ModelRegistry()
        result = registry.get_model(LLMProvider.OPENAI, "gpt-4o")
        # Result is a Union type, check for expected attributes
        assert hasattr(result, "is_ok")
        assert hasattr(result, "is_error")
        assert hasattr(result, "unwrap")
        # Check properties work correctly
        assert result.is_ok is True
        assert result.is_error is False

    def test_resolve_model_returns_result_like_object(self) -> None:
        """Test that resolve_model returns a Result-like object."""
        registry = ModelRegistry()
        result = registry.resolve_model("gpt4")
        # Result is a Union type, check for expected attributes
        assert hasattr(result, "is_ok")
        assert hasattr(result, "is_error")
        assert hasattr(result, "unwrap")
        # Check properties work correctly
        assert result.is_ok is True
        assert result.is_error is False

    def test_ok_result_can_be_unwrapped(self) -> None:
        """Test unwrapping Ok result."""
        registry = ModelRegistry()
        result = registry.get_model(LLMProvider.OPENAI, "gpt-4o")
        assert result.is_ok
        model = result.unwrap()
        assert model.model_name == "gpt-4o"

    def test_error_result_has_code(self) -> None:
        """Test error result has error code."""
        registry = ModelRegistry()
        result = registry.get_model(LLMProvider.OPENAI, "nonexistent")
        assert result.is_error
        assert result.error.code == "NOT_FOUND"

    def test_result_and_then_chaining(self) -> None:
        """Test Result and_then chaining."""
        from src.core.result import Ok
        registry = ModelRegistry()
        result = registry.get_model(LLMProvider.OPENAI, "gpt-4o")
        chained = result.and_then(lambda m: Ok(m.model_name))
        assert chained.is_ok
        assert chained.unwrap() == "gpt-4o"
