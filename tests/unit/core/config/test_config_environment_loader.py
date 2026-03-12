#!/usr/bin/env python3
"""
Unit tests for config_environment_loader module.

Tests cover:
- Environment enum
- ConfigPaths dataclass
- EnvironmentConfigLoader class
- Environment detection
- Configuration loading and merging
- Environment variable overrides
- Validation
"""

import os
from unittest.mock import mock_open, patch

import pytest

from src.core.config.config_environment_loader import (
    ConfigPaths,
    Environment,
    EnvironmentConfigLoader,
    get_config_value,
    get_environment_config_loader,
    load_config,
)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test all environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"
        assert Environment.KUBERNETES.value == "kubernetes"

    def test_environment_from_string_valid(self):
        """Test creating Environment from valid string."""
        assert Environment("development") == Environment.DEVELOPMENT
        assert Environment("staging") == Environment.STAGING
        assert Environment("production") == Environment.PRODUCTION
        assert Environment("testing") == Environment.TESTING
        assert Environment("kubernetes") == Environment.KUBERNETES

    def test_environment_from_string_invalid(self):
        """Test creating Environment from invalid string raises ValueError."""
        with pytest.raises(ValueError):
            Environment("invalid_env")

    def test_environment_values_are_lowercase(self):
        """Test environment enum values are lowercase strings."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"


class TestConfigPaths:
    """Tests for ConfigPaths dataclass."""

    def test_default_values(self):
        """Test default configuration paths."""
        paths = ConfigPaths()
        assert paths.environments_config == "config/environments/environments.yaml"
        assert paths.development_config == "config/environments/development.yaml"
        assert paths.settings_config == "config/environments/settings.yaml"
        assert paths.security_config == "config/security/security.yaml"
        assert paths.nginx_config == "config/nginx/nginx.conf"
        assert paths.prometheus_config == "config/prometheus/prometheus.yml"
        assert paths.prometheus_rules == "config/prometheus/rules/novel-engine.yml"

    def test_custom_values(self):
        """Test custom configuration paths."""
        paths = ConfigPaths(
            environments_config="custom/env.yaml",
            development_config="custom/dev.yaml",
        )
        assert paths.environments_config == "custom/env.yaml"
        assert paths.development_config == "custom/dev.yaml"


class TestEnvironmentConfigLoaderInit:
    """Tests for EnvironmentConfigLoader initialization."""

    def test_default_initialization(self):
        """Test initialization with default environment."""
        loader = EnvironmentConfigLoader()
        assert isinstance(loader.environment, Environment)
        assert isinstance(loader.config_paths, ConfigPaths)
        assert loader.config_cache == {}

    def test_explicit_environment(self):
        """Test initialization with explicit environment."""
        loader = EnvironmentConfigLoader("production")
        assert loader.environment == Environment.PRODUCTION

    def test_explicit_environment_case_insensitive(self):
        """Test environment string is case-insensitive."""
        loader = EnvironmentConfigLoader("PRODUCTION")
        assert loader.environment == Environment.PRODUCTION


class TestEnvironmentDetection:
    """Tests for environment detection logic."""

    def test_detect_environment_override_valid(self):
        """Test valid environment override."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment("staging")
        assert env == Environment.STAGING

    def test_detect_environment_override_invalid(self):
        """Test invalid environment override falls back to development."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment("invalid_env")
        assert env == Environment.DEVELOPMENT

    @patch.dict(os.environ, {"NOVEL_ENGINE_ENV": "production"})
    def test_detect_from_novel_engine_env(self):
        """Test detection from NOVEL_ENGINE_ENV variable."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {"ENVIRONMENT": "staging"})
    def test_detect_from_environment_var(self):
        """Test detection from ENVIRONMENT variable."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.STAGING

    @patch.dict(os.environ, {"ENV": "testing"})
    def test_detect_from_env_var(self):
        """Test detection from ENV variable."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.TESTING

    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_detect_from_flask_env(self):
        """Test detection from FLASK_ENV variable."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {"NODE_ENV": "staging"})
    def test_detect_from_node_env(self):
        """Test detection from NODE_ENV variable."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.STAGING

    @patch.dict(os.environ, {"NOVEL_ENGINE_ENV": "invalid"})
    def test_detect_from_env_invalid_value(self):
        """Test detection with invalid env var value continues to next."""
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        # Should fall through to development indicators or default
        assert isinstance(env, Environment)

    @patch("os.path.exists")
    def test_detect_kubernetes_environment(self, mock_exists):
        """Test detection of Kubernetes environment."""
        def exists_side_effect(path):
            return path == "/var/run/secrets/kubernetes.io"

        mock_exists.side_effect = exists_side_effect
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.KUBERNETES

    @patch("os.path.exists")
    def test_detect_development_from_git(self, mock_exists):
        """Test detection of development environment from .git folder."""
        def exists_side_effect(path):
            # Only return True for .git, not for kubernetes
            return path == ".git"
        mock_exists.side_effect = exists_side_effect
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.DEVELOPMENT

    @patch("os.path.exists")
    def test_detect_development_from_venv(self, mock_exists):
        """Test detection of development environment from venv folder."""
        def exists_side_effect(path):
            return path == "venv"

        mock_exists.side_effect = exists_side_effect
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.DEVELOPMENT

    @patch("os.path.exists")
    def test_default_development(self, mock_exists):
        """Test default fallback to development."""
        mock_exists.return_value = False
        loader = EnvironmentConfigLoader()
        env = loader._detect_environment()
        assert env == Environment.DEVELOPMENT


class TestDeepMerge:
    """Tests for _deep_merge method."""

    def test_merge_empty_dicts(self):
        """Test merging two empty dictionaries."""
        loader = EnvironmentConfigLoader()
        result = loader._deep_merge({}, {})
        assert result == {}

    def test_merge_base_empty(self):
        """Test merging with empty base."""
        loader = EnvironmentConfigLoader()
        result = loader._deep_merge({}, {"key": "value"})
        assert result == {"key": "value"}

    def test_merge_override_empty(self):
        """Test merging with empty override."""
        loader = EnvironmentConfigLoader()
        result = loader._deep_merge({"key": "value"}, {})
        assert result == {"key": "value"}

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        loader = EnvironmentConfigLoader()
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = loader._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test deep merging of nested dictionaries."""
        loader = EnvironmentConfigLoader()
        base = {"outer": {"inner1": "value1", "inner2": "value2"}}
        override = {"outer": {"inner2": "new_value", "inner3": "value3"}}
        result = loader._deep_merge(base, override)
        expected = {"outer": {"inner1": "value1", "inner2": "new_value", "inner3": "value3"}}
        assert result == expected

    def test_merge_deeply_nested(self):
        """Test merging deeply nested dictionaries."""
        loader = EnvironmentConfigLoader()
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 3, "e": 4}}}
        result = loader._deep_merge(base, override)
        expected = {"a": {"b": {"c": 1, "d": 3, "e": 4}}}
        assert result == expected

    def test_merge_non_dict_override(self):
        """Test that non-dict override replaces dict base."""
        loader = EnvironmentConfigLoader()
        base = {"key": {"nested": "value"}}
        override = {"key": "simple_value"}
        result = loader._deep_merge(base, override)
        assert result == {"key": "simple_value"}

    def test_merge_preserves_base(self):
        """Test that original base dict is not modified."""
        loader = EnvironmentConfigLoader()
        base = {"key": "value"}
        override = {"new_key": "new_value"}
        result = loader._deep_merge(base, override)
        assert base == {"key": "value"}  # Unchanged
        assert result == {"key": "value", "new_key": "new_value"}


class TestLoadYAMLFile:
    """Tests for _load_yaml_file method."""

    def test_load_yaml_file_success(self):
        """Test successful YAML file loading."""
        loader = EnvironmentConfigLoader()
        yaml_content = "key: value\nlist:\n  - item1\n  - item2"

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("os.path.exists", return_value=True):
                result = loader._load_yaml_file("test.yaml")

        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_file_not_found(self):
        """Test handling of missing YAML file."""
        loader = EnvironmentConfigLoader()

        with patch("os.path.exists", return_value=False):
            result = loader._load_yaml_file("nonexistent.yaml")

        assert result == {}

    def test_load_yaml_file_parse_error(self):
        """Test handling of YAML parse error."""
        loader = EnvironmentConfigLoader()
        invalid_yaml = "invalid: yaml: {broken"

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("os.path.exists", return_value=True):
                result = loader._load_yaml_file("test.yaml")

        assert result == {}

    def test_load_yaml_file_io_error(self):
        """Test handling of IO error."""
        loader = EnvironmentConfigLoader()

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                result = loader._load_yaml_file("test.yaml")

        assert result == {}


class TestLoadConfiguration:
    """Tests for load_configuration method."""

    def test_load_default_configuration(self):
        """Test loading returns configuration dictionary."""
        loader = EnvironmentConfigLoader()
        config = loader.load_configuration()

        assert isinstance(config, dict)
        # Config may be empty or populated depending on actual files
        assert "api" in config

    def test_load_with_base_config(self):
        """Test loading with base configuration."""
        loader = EnvironmentConfigLoader()
        env_config = {
            "base": {"base_key": "base_value"},
            "development": {"dev_key": "dev_value"},
        }

        with patch.object(loader, "_load_environments_config", return_value=env_config):
            with patch.object(loader, "_load_development_config", return_value={}):
                with patch.object(loader, "_load_settings_config", return_value={}):
                    with patch.object(loader, "_load_security_config", return_value={}):
                        config = loader.load_configuration()

        assert config.get("base_key") == "base_value"
        assert config.get("dev_key") == "dev_value"

    def test_load_caches_configuration(self):
        """Test that configuration is cached."""
        loader = EnvironmentConfigLoader()
        
        # Load configuration twice
        config1 = loader.load_configuration()
        config2 = loader.load_configuration()
        
        # Both should have the same content
        assert config1 == config2
        # The cache should be populated
        assert loader.config_cache == config1


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_apply_no_overrides(self):
        """Test with no environment variables set."""
        loader = EnvironmentConfigLoader()
        config = {"api": {"host": "127.0.0.1", "port": 8000}}
        result = loader._apply_environment_overrides(config)
        assert result == config

    @patch.dict(os.environ, {"NOVEL_ENGINE_HOST": "0.0.0.0"})
    def test_apply_host_override(self):
        """Test applying NOVEL_ENGINE_HOST override."""
        loader = EnvironmentConfigLoader()
        config = {"api": {"host": "127.0.0.1"}}
        result = loader._apply_environment_overrides(config)
        assert result["api"]["host"] == "0.0.0.0"

    @patch.dict(os.environ, {"NOVEL_ENGINE_PORT": "9000"})
    def test_apply_port_override(self):
        """Test applying NOVEL_ENGINE_PORT override."""
        loader = EnvironmentConfigLoader()
        config = {"api": {"port": 8000}}
        result = loader._apply_environment_overrides(config)
        assert result["api"]["port"] == 9000

    @patch.dict(os.environ, {"DATABASE_URL": "postgres://localhost/db"})
    def test_apply_database_url_override(self):
        """Test applying DATABASE_URL override."""
        loader = EnvironmentConfigLoader()
        config = {"storage": {}}
        result = loader._apply_environment_overrides(config)
        assert result["storage"]["postgres_url"] == "postgres://localhost/db"

    @patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"})
    def test_apply_redis_url_override(self):
        """Test applying REDIS_URL override."""
        loader = EnvironmentConfigLoader()
        config = {"storage": {}}
        result = loader._apply_environment_overrides(config)
        assert result["storage"]["redis_url"] == "redis://localhost:6379"

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_apply_log_level_override(self):
        """Test applying LOG_LEVEL override."""
        loader = EnvironmentConfigLoader()
        config = {"logging": {"level": "INFO"}}
        result = loader._apply_environment_overrides(config)
        assert result["logging"]["level"] == "DEBUG"

    @patch.dict(os.environ, {"DEBUG_MODE": "true"})
    def test_apply_debug_mode_true(self):
        """Test applying DEBUG_MODE=true override."""
        loader = EnvironmentConfigLoader()
        config = {"system": {}}
        result = loader._apply_environment_overrides(config)
        assert result["system"]["debug_mode"] is True

    @patch.dict(os.environ, {"DEBUG_MODE": "false"})
    def test_apply_debug_mode_false(self):
        """Test applying DEBUG_MODE=false override."""
        loader = EnvironmentConfigLoader()
        config = {"system": {"debug_mode": True}}
        result = loader._apply_environment_overrides(config)
        assert result["system"]["debug_mode"] is False

    @patch.dict(os.environ, {"MAX_AGENTS": "50"})
    def test_apply_max_agents_override(self):
        """Test applying MAX_AGENTS override."""
        loader = EnvironmentConfigLoader()
        config = {"simulation": {"max_agents": 10}}
        result = loader._apply_environment_overrides(config)
        assert result["simulation"]["max_agents"] == 50

    @patch.dict(os.environ, {"API_TIMEOUT": "120"})
    def test_apply_api_timeout_override(self):
        """Test applying API_TIMEOUT override."""
        loader = EnvironmentConfigLoader()
        config = {"simulation": {"api_timeout": 30}}
        result = loader._apply_environment_overrides(config)
        assert result["simulation"]["api_timeout"] == 120

    def test_creates_nested_structure(self):
        """Test that overrides create nested structure if needed."""
        loader = EnvironmentConfigLoader()
        config = {}

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            result = loader._apply_environment_overrides(config)

        assert "logging" in result
        assert result["logging"]["level"] == "DEBUG"


class TestGetConfigValue:
    """Tests for get_config_value method."""

    def test_get_existing_value(self):
        """Test getting an existing config value."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {"api": {"host": "127.0.0.1", "port": 8000}}
        value = loader.get_config_value("api.host")
        assert value == "127.0.0.1"

    def test_get_nested_value(self):
        """Test getting deeply nested config value."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {"level1": {"level2": {"level3": "value"}}}
        value = loader.get_config_value("level1.level2.level3")
        assert value == "value"

    def test_get_nonexistent_value(self):
        """Test getting nonexistent value returns default."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {"api": {"host": "127.0.0.1"}}
        value = loader.get_config_value("nonexistent.key")
        assert value is None

    def test_get_nonexistent_with_default(self):
        """Test getting nonexistent value with custom default."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {"api": {"host": "127.0.0.1"}}
        value = loader.get_config_value("nonexistent.key", default="default_value")
        assert value == "default_value"

    def test_get_value_loads_config(self):
        """Test that get_config_value loads config if not cached."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {}

        with patch.object(loader, "load_configuration") as mock_load:
            mock_load.return_value = {"api": {"host": "127.0.0.1"}}
            loader.get_config_value("api.host")

        mock_load.assert_called_once()


class TestValidateConfiguration:
    """Tests for validate_configuration method."""

    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {"name": "Test"},
            "api": {"host": "127.0.0.1", "port": 8000},
            "logging": {"level": "INFO"},
            "simulation": {"max_agents": 10},
        }
        errors = loader.validate_configuration()
        assert errors == []

    def test_missing_required_section(self):
        """Test validation with missing required section."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "api": {"host": "127.0.0.1", "port": 8000},
        }
        errors = loader.validate_configuration()
        assert any("system" in error for error in errors)

    def test_missing_api_host(self):
        """Test validation with missing API host."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {},
            "api": {"port": 8000},
            "logging": {},
            "simulation": {},
        }
        errors = loader.validate_configuration()
        assert any("host" in error.lower() for error in errors)

    def test_missing_api_port(self):
        """Test validation with missing API port."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {},
            "api": {"host": "127.0.0.1"},
            "logging": {},
            "simulation": {},
        }
        errors = loader.validate_configuration()
        assert any("port" in error.lower() for error in errors)

    def test_invalid_api_port_type(self):
        """Test validation with invalid API port type."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {},
            "api": {"host": "127.0.0.1", "port": "invalid"},
            "logging": {},
            "simulation": {},
        }
        errors = loader.validate_configuration()
        assert any("port" in error.lower() for error in errors)

    def test_invalid_api_port_zero(self):
        """Test validation with API port = 0."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {},
            "api": {"host": "127.0.0.1", "port": 0},
            "logging": {},
            "simulation": {},
        }
        errors = loader.validate_configuration()
        assert any("positive" in error.lower() for error in errors)

    def test_invalid_max_agents(self):
        """Test validation with invalid max_agents."""
        loader = EnvironmentConfigLoader()
        loader.config_cache = {
            "system": {},
            "api": {"host": "127.0.0.1", "port": 8000},
            "logging": {},
            "simulation": {"max_agents": 0},
        }
        errors = loader.validate_configuration()
        assert any("max_agents" in error.lower() for error in errors)


class TestDefaultConfiguration:
    """Tests for _get_default_configuration method."""

    def test_default_configuration_structure(self):
        """Test structure of default configuration."""
        loader = EnvironmentConfigLoader()
        config = loader._get_default_configuration()

        required_sections = ["system", "api", "logging", "simulation", "storage"]
        for section in required_sections:
            assert section in config

    def test_default_configuration_values(self):
        """Test specific values in default configuration."""
        loader = EnvironmentConfigLoader()
        config = loader._get_default_configuration()

        assert config["system"]["name"] == "Novel Engine"
        assert config["api"]["host"] == "127.0.0.1"
        assert config["api"]["port"] == 8000
        assert config["logging"]["level"] == "INFO"

    def test_default_debug_mode_in_development(self):
        """Test debug mode is True in development."""
        loader = EnvironmentConfigLoader("development")
        config = loader._get_default_configuration()
        assert config["system"]["debug_mode"] is True

    def test_default_debug_mode_in_production(self):
        """Test debug mode is False in production."""
        loader = EnvironmentConfigLoader("production")
        config = loader._get_default_configuration()
        assert config["system"]["debug_mode"] is False


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_environment_config_loader_singleton(self):
        """Test that get_environment_config_loader returns singleton."""
        loader1 = get_environment_config_loader()
        loader2 = get_environment_config_loader()
        assert loader1 is loader2

    def test_load_config_returns_dict(self):
        """Test that load_config returns a dictionary."""
        config = load_config()
        assert isinstance(config, dict)

    def test_load_config_with_environment(self):
        """Test load_config with explicit environment."""
        config = load_config("production")
        assert isinstance(config, dict)
        # The config should have an environment value set
        assert "environment" in config.get("system", {})

    def test_get_config_value_existing(self):
        """Test getting existing config value."""
        value = get_config_value("system.name")
        assert value == "Novel Engine"

    def test_get_config_value_nonexistent(self):
        """Test getting nonexistent config value returns default."""
        value = get_config_value("nonexistent.key", default="default")
        assert value == "default"


class TestErrorHandling:
    """Tests for error handling in configuration loading."""

    def test_load_configuration_exception_handling(self):
        """Test that exceptions during loading return default config."""
        loader = EnvironmentConfigLoader()

        with patch.object(loader, "_load_environments_config", side_effect=Exception("Test error")):
            config = loader.load_configuration()

        # Should return default configuration
        assert "system" in config
        assert config["system"]["name"] == "Novel Engine"

    def test_additional_config_loader_exception(self):
        """Test that exceptions in additional config loaders are handled gracefully."""
        loader = EnvironmentConfigLoader()

        with patch.object(loader, "_load_environments_config", return_value={}):
            with patch.object(loader, "_load_development_config", side_effect=Exception("Dev config error")):
                with patch.object(loader, "_load_settings_config", return_value={}):
                    with patch.object(loader, "_load_security_config", return_value={}):
                        # Should not raise an exception
                        config = loader.load_configuration()

        # Should return a configuration dict (may be empty or have defaults)
        assert isinstance(config, dict)
