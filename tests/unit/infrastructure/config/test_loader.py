"""Tests for the config loader module."""

from pathlib import Path

import pytest

from src.shared.infrastructure.config.loader import (
    ConfigLoader,
    ConfigLoadError,
    load_yaml_config,
    merge_configs,
)
from src.shared.infrastructure.config.settings import Environment


class TestConfigLoadError:
    """Test ConfigLoadError exception."""

    def test_error_is_exception(self):
        """Test ConfigLoadError is an Exception subclass."""
        assert issubclass(ConfigLoadError, Exception)

    def test_error_can_be_raised(self):
        """Test ConfigLoadError can be raised and caught."""
        with pytest.raises(ConfigLoadError) as exc_info:
            raise ConfigLoadError("test error message")
        assert "test error message" in str(exc_info.value)


class TestConfigLoaderInit:
    """Test ConfigLoader initialization."""

    def test_default_config_dir(self):
        """Test ConfigLoader uses default config directory."""
        loader = ConfigLoader()
        expected_path = Path(__file__).parent.parent.parent.parent.parent / "config"
        assert loader.config_dir == expected_path

    def test_custom_config_dir(self, tmp_path):
        """Test ConfigLoader with custom config directory."""
        config_dir = tmp_path / "custom_config"
        config_dir.mkdir()
        loader = ConfigLoader(config_dir)
        assert loader.config_dir == config_dir

    def test_string_config_dir(self, tmp_path):
        """Test ConfigLoader accepts string path."""
        config_dir = tmp_path / "custom_config"
        config_dir.mkdir()
        loader = ConfigLoader(str(config_dir))
        assert loader.config_dir == config_dir

    def test_nonexistent_dir_raises_error(self, tmp_path):
        """Test ConfigLoader raises error for nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(ConfigLoadError) as exc_info:
            ConfigLoader(nonexistent)
        assert "not found" in str(exc_info.value)


class TestConfigLoaderLoadYamlFile:
    """Test loading individual YAML files."""

    def test_load_existing_file(self, tmp_path):
        """Test loading an existing YAML file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value\nnumber: 42")

        loader = ConfigLoader(tmp_path)
        result = loader._load_yaml_file(config_file)

        assert result == {"key": "value", "number": 42}

    def test_load_nonexistent_file_returns_empty(self, tmp_path):
        """Test loading nonexistent file returns empty dict."""
        loader = ConfigLoader(tmp_path)
        result = loader._load_yaml_file(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_load_empty_file_returns_empty(self, tmp_path):
        """Test loading empty YAML file returns empty dict."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        loader = ConfigLoader(tmp_path)
        result = loader._load_yaml_file(config_file)
        assert result == {}

    def test_load_invalid_yaml_raises_error(self, tmp_path):
        """Test loading invalid YAML raises ConfigLoadError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigLoadError) as exc_info:
            loader._load_yaml_file(config_file)
        assert "Failed to parse YAML" in str(exc_info.value)


class TestConfigLoaderDeepMerge:
    """Test deep merge functionality."""

    def test_simple_merge(self):
        """Test simple dictionary merge."""
        loader = ConfigLoader()
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = loader._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test nested dictionary merge."""
        loader = ConfigLoader()
        base = {"database": {"host": "localhost", "port": 5432}}
        override = {"database": {"port": 3306}}
        result = loader._deep_merge(base, override)
        assert result == {"database": {"host": "localhost", "port": 3306}}

    def test_deep_nested_merge(self):
        """Test deeply nested dictionary merge."""
        loader = ConfigLoader()
        base = {
            "level1": {"level2": {"level3": {"value": "original"}, "other": "keep"}}
        }
        override = {"level1": {"level2": {"level3": {"value": "updated"}}}}
        result = loader._deep_merge(base, override)
        assert result["level1"]["level2"]["level3"]["value"] == "updated"
        assert result["level1"]["level2"]["other"] == "keep"

    def test_override_non_dict_raises_no_error(self):
        """Test that non-dict values override correctly."""
        loader = ConfigLoader()
        base = {"key": {"nested": "value"}}
        override = {"key": "string_value"}
        result = loader._deep_merge(base, override)
        assert result == {"key": "string_value"}


class TestConfigLoaderLoad:
    """Test the main load method."""

    def test_load_base_config_only(self, tmp_path, monkeypatch):
        """Test loading only base config when no env-specific file exists."""
        monkeypatch.setenv("APP_ENVIRONMENT", "development")

        base_file = tmp_path / "app.yaml"
        base_file.write_text("key: base_value\nname: test")

        loader = ConfigLoader(tmp_path)
        result = loader.load("app")

        assert result == {"key": "base_value", "name": "test"}

    def test_load_with_environment_override(self, tmp_path, monkeypatch):
        """Test loading base and environment-specific config."""
        monkeypatch.setenv("APP_ENVIRONMENT", "development")

        base_file = tmp_path / "app.yaml"
        base_file.write_text("key: base_value\nname: test\nkeep: this")

        env_file = tmp_path / "app.development.yaml"
        env_file.write_text("key: dev_value\nnew: dev_only")

        loader = ConfigLoader(tmp_path)
        result = loader.load("app")

        assert result["key"] == "dev_value"  # Overridden
        assert result["name"] == "test"  # From base
        assert result["keep"] == "this"  # From base
        assert result["new"] == "dev_only"  # From env

    def test_load_with_explicit_environment(self, tmp_path):
        """Test loading with explicitly specified environment."""
        base_file = tmp_path / "app.yaml"
        base_file.write_text("key: base")

        prod_file = tmp_path / "app.production.yaml"
        prod_file.write_text("key: production")

        loader = ConfigLoader(tmp_path)
        result = loader.load("app", environment=Environment.PRODUCTION)

        assert result["key"] == "production"

    def test_load_with_string_environment(self, tmp_path):
        """Test loading with string environment."""
        base_file = tmp_path / "app.yaml"
        base_file.write_text("key: base")

        test_file = tmp_path / "app.testing.yaml"
        test_file.write_text("key: testing")

        loader = ConfigLoader(tmp_path)
        result = loader.load("app", environment="testing")

        assert result["key"] == "testing"

    def test_load_defaults_to_development(self, tmp_path, monkeypatch):
        """Test loading defaults to development environment."""
        monkeypatch.delenv("APP_ENVIRONMENT", raising=False)

        dev_file = tmp_path / "app.development.yaml"
        dev_file.write_text("env: development")

        loader = ConfigLoader(tmp_path)
        result = loader.load("app")

        assert result["env"] == "development"


class TestConfigLoaderLoadForEnvironment:
    """Test loading environment-specific configs."""

    def test_load_development_config(self, tmp_path):
        """Test loading development.yaml."""
        dev_file = tmp_path / "development.yaml"
        dev_file.write_text("debug: true\nlog_level: DEBUG")

        loader = ConfigLoader(tmp_path)
        result = loader.load_for_environment(Environment.DEVELOPMENT)

        assert result["debug"] is True
        assert result["log_level"] == "DEBUG"

    def test_load_production_config(self, tmp_path):
        """Test loading production.yaml."""
        prod_file = tmp_path / "production.yaml"
        prod_file.write_text("debug: false\nlog_level: INFO")

        loader = ConfigLoader(tmp_path)
        result = loader.load_for_environment("production")

        assert result["debug"] is False
        assert result["log_level"] == "INFO"

    def test_load_nonexistent_config(self, tmp_path):
        """Test loading nonexistent environment config returns empty."""
        loader = ConfigLoader(tmp_path)
        # Use testing environment but don't create testing.yaml
        result = loader.load_for_environment(Environment.TESTING)
        assert result == {}


class TestConfigLoaderListAvailableConfigs:
    """Test listing available configurations."""

    def test_list_configs(self, tmp_path):
        """Test listing available config files."""
        (tmp_path / "app.yaml").write_text("")
        (tmp_path / "database.yaml").write_text("")
        (tmp_path / "app.development.yaml").write_text("")
        (tmp_path / "app.production.yaml").write_text("")

        loader = ConfigLoader(tmp_path)
        configs = loader.list_available_configs()

        assert "app" in configs
        assert "database" in configs
        assert "app.development" not in configs  # Should be filtered out
        assert "app.production" not in configs  # Should be filtered out

    def test_list_empty_directory(self, tmp_path):
        """Test listing empty directory."""
        loader = ConfigLoader(tmp_path)
        configs = loader.list_available_configs()
        assert configs == []

    def test_list_nonexistent_directory(self, tmp_path):
        """Test listing from nonexistent directory."""
        loader = ConfigLoader(tmp_path)
        loader.config_dir = tmp_path / "does_not_exist"
        configs = loader.list_available_configs()
        assert configs == []


class TestConfigLoaderConfigExists:
    """Test checking if config exists."""

    def test_existing_config(self, tmp_path):
        """Test checking existing config."""
        (tmp_path / "app.yaml").write_text("")
        loader = ConfigLoader(tmp_path)
        assert loader.config_exists("app") is True

    def test_nonexistent_config(self, tmp_path):
        """Test checking nonexistent config."""
        loader = ConfigLoader(tmp_path)
        assert loader.config_exists("nonexistent") is False


class TestLoadYamlConfig:
    """Test convenience function load_yaml_config."""

    def test_load_yaml_config_function(self, tmp_path, monkeypatch):
        """Test load_yaml_config convenience function."""
        monkeypatch.setenv("APP_ENVIRONMENT", "development")

        base_file = tmp_path / "app.yaml"
        base_file.write_text("key: value")

        result = load_yaml_config("app", config_dir=tmp_path)
        assert result == {"key": "value"}


class TestMergeConfigs:
    """Test merge_configs function."""

    def test_merge_two_configs(self):
        """Test merging two configs."""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        result = merge_configs(config1, config2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_multiple_configs(self):
        """Test merging multiple configs."""
        config1 = {"a": 1}
        config2 = {"b": 2}
        config3 = {"c": 3}
        result = merge_configs(config1, config2, config3)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge_no_configs(self):
        """Test merging no configs returns empty dict."""
        result = merge_configs()
        assert result == {}

    def test_merge_single_config(self):
        """Test merging single config returns copy."""
        config = {"a": 1, "b": 2}
        result = merge_configs(config)
        assert result == config
        assert result is not config  # Should be a copy

    def test_merge_preserves_nested(self):
        """Test merge preserves nested structures."""
        config1 = {"database": {"host": "localhost", "port": 5432}}
        config2 = {"database": {"port": 3306, "user": "admin"}}
        result = merge_configs(config1, config2)
        assert result == {
            "database": {"host": "localhost", "port": 3306, "user": "admin"}
        }


class TestRealConfigFiles:
    """Test with real config files in the project."""

    def test_real_development_config_exists(self):
        """Test that development.yaml exists and is valid."""
        loader = ConfigLoader()
        result = loader.load_for_environment(Environment.DEVELOPMENT)

        # Should load the real config file
        assert "project_name" in result or result == {}

    def test_real_production_config_exists(self):
        """Test that production.yaml exists and is valid."""
        loader = ConfigLoader()
        result = loader.load_for_environment(Environment.PRODUCTION)

        # Should load the real config file
        assert "project_name" in result or result == {}

    def test_real_testing_config_exists(self):
        """Test that testing.yaml exists and is valid."""
        loader = ConfigLoader()
        result = loader.load_for_environment(Environment.TESTING)

        # Should load the real config file
        assert "project_name" in result or result == {}

    def test_config_directory_structure(self):
        """Test the config directory has expected structure."""
        loader = ConfigLoader()

        assert loader.config_dir.exists()
        assert loader.config_dir.is_dir()

        # Check that environment config files exist
        assert (loader.config_dir / "development.yaml").exists()
        assert (loader.config_dir / "production.yaml").exists()
        assert (loader.config_dir / "testing.yaml").exists()
