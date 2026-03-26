"""Tests for the config manager module."""

import os

import pytest
import yaml

from src.shared.infrastructure.config.config_manager import (
    ConfigManager,
    ConfigManagerError,
    get_config,
    get_config_value,
)
from src.shared.infrastructure.config.settings import (
    Environment,
    NovelEngineSettings,
)


class TestConfigManagerError:
    """Test ConfigManagerError exception."""

    def test_error_is_exception(self):
        """Test ConfigManagerError is an Exception subclass."""
        assert issubclass(ConfigManagerError, Exception)

    def test_error_message(self):
        """Test ConfigManagerError message."""
        with pytest.raises(ConfigManagerError) as exc_info:
            raise ConfigManagerError("test error")
        assert "test error" in str(exc_info.value)


class TestConfigManagerSingleton:
    """Test ConfigManager singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_singleton_same_instance(self):
        """Test that ConfigManager is a singleton."""
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2

    def test_singleton_attributes_preserved(self):
        """Test that singleton preserves attributes."""
        config1 = ConfigManager()
        config1.set("custom.key", "value")

        config2 = ConfigManager()
        assert config2.get("custom.key") == "value"

    def test_reset_instance_creates_new_instance(self):
        """Test reset_instance creates new singleton."""
        config1 = ConfigManager()
        ConfigManager.reset_instance()
        config2 = ConfigManager()
        assert config1 is not config2

    def test_get_instance_creates_instance(self):
        """Test get_instance creates instance if none exists."""
        ConfigManager.reset_instance()
        config = ConfigManager.get_instance()
        assert isinstance(config, ConfigManager)

    def test_get_instance_returns_same_instance(self):
        """Test get_instance returns same instance."""
        ConfigManager.reset_instance()
        config1 = ConfigManager.get_instance()
        config2 = ConfigManager.get_instance()
        assert config1 is config2


class TestConfigManagerInit:
    """Test ConfigManager initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton and environment after each test."""
        ConfigManager.reset_instance()
        os.environ.pop("APP_ENVIRONMENT", None)

    def test_default_environment(self):
        """Test ConfigManager defaults to development."""
        config = ConfigManager()
        assert config.environment == Environment.DEVELOPMENT

    def test_environment_from_env_var(self, monkeypatch):
        """Test ConfigManager reads environment from env var."""
        monkeypatch.setenv("APP_ENVIRONMENT", "production")
        config = ConfigManager()
        assert config.environment == Environment.PRODUCTION

    def test_explicit_environment(self):
        """Test ConfigManager with explicit environment."""
        config = ConfigManager(environment=Environment.TESTING)
        assert config.environment == Environment.TESTING

    def test_explicit_string_environment(self):
        """Test ConfigManager with explicit string environment."""
        config = ConfigManager(environment="staging")
        assert config.environment == Environment.STAGING

    def test_custom_config_dir(self, tmp_path):
        """Test ConfigManager with custom config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config = ConfigManager(config_dir=config_dir)
        assert config._loader.config_dir == config_dir


class TestConfigManagerProperties:
    """Test ConfigManager properties."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_settings_property(self):
        """Test settings property returns NovelEngineSettings."""
        config = ConfigManager()
        assert isinstance(config.settings, NovelEngineSettings)

    def test_environment_property(self):
        """Test environment property."""
        config = ConfigManager(environment=Environment.PRODUCTION)
        assert config.environment == Environment.PRODUCTION


class TestConfigManagerGet:
    """Test ConfigManager get method."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_get_simple_value(self):
        """Test getting simple value."""
        config = ConfigManager()
        result = config.get("project_name")
        assert result == "Novel Engine (Development)"

    def test_get_nested_value(self, tmp_path):
        """Test getting nested value with dot notation."""
        # Use temp config dir to avoid YAML overrides
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config = ConfigManager(config_dir=config_dir)
        result = config.get("database.pool_size")
        assert result == 5

    def test_get_default_value(self):
        """Test getting default when key not found."""
        config = ConfigManager()
        result = config.get("nonexistent.key", "default")
        assert result == "default"

    def test_get_none_default(self):
        """Test getting None default when key not found."""
        config = ConfigManager()
        result = config.get("nonexistent.key")
        assert result is None

    def test_get_override_value(self):
        """Test that overrides take precedence."""
        config = ConfigManager()
        config.set("database.pool_size", 100)
        result = config.get("database.pool_size")
        assert result == 100

    def test_get_section(self, tmp_path):
        """Test getting section object."""
        # Use temp config dir to avoid YAML overrides
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config = ConfigManager(config_dir=config_dir)
        section = config.get_section("database")
        assert section.url == "sqlite:///./novel_engine.db"

    def test_get_nonexistent_section(self):
        """Test getting nonexistent section raises error."""
        config = ConfigManager()
        with pytest.raises(ConfigManagerError) as exc_info:
            config.get_section("nonexistent")
        assert "not found" in str(exc_info.value)


class TestConfigManagerOverrides:
    """Test ConfigManager override functionality."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_set_override(self):
        """Test setting an override."""
        config = ConfigManager()
        config.set("test.key", "value")
        assert config.get("test.key") == "value"

    def test_override_precedence(self):
        """Test that overrides override settings."""
        config = ConfigManager()
        original = config.get("api.port")
        config.set("api.port", 9999)
        assert config.get("api.port") == 9999
        assert config.get("api.port") != original

    def test_remove_override(self):
        """Test removing an override."""
        config = ConfigManager()
        config.set("test.key", "value")
        assert config.get("test.key") == "value"

        config.remove_override("test.key")
        assert config.get("test.key") is None

    def test_clear_overrides(self):
        """Test clearing all overrides."""
        config = ConfigManager()
        config.set("key1", "value1")
        config.set("key2", "value2")

        config.clear_overrides()

        assert config.get("key1") is None
        assert config.get("key2") is None


class TestConfigManagerReload:
    """Test ConfigManager reload functionality."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()
        os.environ.pop("APP_TEST_VAR", None)

    def test_reload_clears_overrides(self):
        """Test that reload clears overrides."""
        config = ConfigManager()
        config.set("test.key", "value")

        config.reload()

        assert config.get("test.key") is None

    def test_reload_reads_new_env_vars(self, monkeypatch, tmp_path):
        """Test that reload reads new environment variables."""
        # Use temp config dir to avoid YAML overrides
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config = ConfigManager(config_dir=config_dir)
        original_port = config.get("api.port")
        assert original_port == 8000  # Default value

        monkeypatch.setenv("API_PORT", "9999")
        config.reload()

        assert config.get("api.port") == 9999
        assert config.get("api.port") != original_port


class TestConfigManagerExport:
    """Test ConfigManager export functionality."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_to_dict(self):
        """Test exporting to dictionary."""
        config = ConfigManager()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert "project_name" in data
        assert "database" in data
        assert "api" in data

    def test_to_dict_safe(self):
        """Test safe export masks sensitive data."""
        config = ConfigManager()
        data = config.to_dict(safe=True)

        # Check that sensitive fields are masked
        if data.get("security", {}).get("secret_key"):
            assert data["security"]["secret_key"] == "***REDACTED***"


class TestConfigManagerYamlLoading:
    """Test ConfigManager YAML configuration loading."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_loads_yaml_config(self, tmp_path):
        """Test that ConfigManager loads YAML config."""
        # Create a test config file
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        dev_file = config_dir / "development.yaml"
        dev_file.write_text(yaml.dump({"project_name": "Test From YAML"}))

        config = ConfigManager(
            config_dir=config_dir, environment=Environment.DEVELOPMENT
        )

        # YAML should be loaded (though may be overridden by defaults)
        assert config.settings.project_name == "Test From YAML"

    def test_yaml_section_override(self, tmp_path):
        """Test YAML section override."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        dev_file = config_dir / "development.yaml"
        dev_file.write_text(yaml.dump({"database": {"pool_size": 25}}))

        config = ConfigManager(
            config_dir=config_dir, environment=Environment.DEVELOPMENT
        )

        assert config.settings.database.pool_size == 25


class TestGetConfig:
    """Test get_config convenience function."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_get_config_returns_manager(self):
        """Test get_config returns ConfigManager."""
        config = get_config()
        assert isinstance(config, ConfigManager)

    def test_get_config_singleton(self):
        """Test get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_get_config_with_environment(self):
        """Test get_config with environment."""
        config = get_config(environment=Environment.TESTING)
        assert config.environment == Environment.TESTING


class TestGetConfigValue:
    """Test get_config_value convenience function."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_get_config_value(self):
        """Test get_config_value returns value."""
        # Use the default repository config path
        get_config()
        result = get_config_value("project_name")
        assert result == "Novel Engine (Development)"

    def test_get_config_value_with_default(self):
        """Test get_config_value with default."""
        result = get_config_value("nonexistent", "default")
        assert result == "default"


class TestConfigManagerRepr:
    """Test ConfigManager string representation."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        ConfigManager.reset_instance()

    def test_repr(self):
        """Test __repr__ method."""
        config = ConfigManager(environment=Environment.PRODUCTION)
        repr_str = repr(config)

        assert "ConfigManager" in repr_str
        assert "production" in repr_str


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigManager.reset_instance()

    def teardown_method(self):
        """Reset singleton and clean up environment after each test."""
        ConfigManager.reset_instance()
        for key in ["APP_ENVIRONMENT", "API_PORT", "DB_URL"]:
            os.environ.pop(key, None)

    def test_full_workflow(self):
        """Test full configuration workflow."""
        # Create config manager
        config = ConfigManager()

        # Check default values
        assert config.get("api.port") == 8000
        assert config.get("database.echo") is True

        # Set overrides
        config.set("api.port", 9000)
        assert config.get("api.port") == 9000

        # Export config
        data = config.to_dict()
        assert "project_name" in data

        # Clear overrides and reload
        config.clear_overrides()
        assert config.get("api.port") == 8000

    def test_environment_specific_behavior(self):
        """Test environment-specific configuration behavior."""
        # Development environment
        dev_config = ConfigManager(environment=Environment.DEVELOPMENT)
        assert dev_config.environment == Environment.DEVELOPMENT
        assert dev_config.settings.is_development is True

        ConfigManager.reset_instance()

        # Production environment
        prod_config = ConfigManager(environment=Environment.PRODUCTION)
        assert prod_config.environment == Environment.PRODUCTION
        assert prod_config.settings.is_production is True

        ConfigManager.reset_instance()

        # Testing environment
        test_config = ConfigManager(environment=Environment.TESTING)
        assert test_config.environment == Environment.TESTING
        assert test_config.settings.is_testing is True

    def test_nested_access_patterns(self):
        """Test various nested access patterns."""
        config = ConfigManager()

        # Single level
        assert config.get("project_name") is not None

        # Two levels
        assert config.get("api.port") is not None

        # Deep nesting
        assert config.get("logging.level") is not None

        # Non-existent paths
        assert config.get("api.nonexistent.nested") is None
        assert config.get("completely.missing.path", "default") == "default"
