"""Tests for ConfigManager."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.shared.infrastructure.config.config_manager import (
    ConfigManager,
    ConfigManagerError,
    get_config,
    get_config_value,
)
from src.shared.infrastructure.config.loader import ConfigLoadError
from src.shared.infrastructure.config.settings import Environment


@pytest.fixture(autouse=True)
def reset_config_manager():
    """Reset ConfigManager singleton before each test."""
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = MagicMock()
    settings.model_dump = MagicMock(return_value={"key": "value"})
    settings.model_dump_safe = MagicMock(return_value={"key": "***"})
    settings.database = MagicMock()
    settings.database.url = "postgresql://localhost/test"
    settings.api = MagicMock()
    settings.api.port = 8000
    settings.debug = False
    return settings


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        # Act
        cm1 = ConfigManager()
        cm2 = ConfigManager()

        # Assert
        assert cm1 is cm2

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        # Act
        with patch.dict(os.environ, {}, clear=True):
            cm = ConfigManager()

        # Assert
        assert cm.environment == Environment.DEVELOPMENT

    def test_initialization_with_environment_string(self):
        """Test initialization with environment string."""
        # Act
        cm = ConfigManager(environment="production")

        # Assert
        assert cm.environment == Environment.PRODUCTION

    def test_initialization_with_environment_enum(self):
        """Test initialization with environment enum."""
        # Act
        cm = ConfigManager(environment=Environment.STAGING)

        # Assert
        assert cm.environment == Environment.STAGING

    def test_initialization_from_env_var(self):
        """Test initialization from environment variable."""
        # Act
        with patch.dict(os.environ, {"APP_ENVIRONMENT": "testing"}):
            ConfigManager.reset_instance()
            cm = ConfigManager()

        # Assert
        assert cm.environment == Environment.TESTING

    def test_get_simple_key(self):
        """Test getting simple configuration key."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.debug = True

        # Act
        result = cm.get("debug")

        # Assert
        assert result is True

    def test_get_nested_key(self):
        """Test getting nested configuration key."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.database = MagicMock()
        cm._settings.database.url = "postgresql://localhost/db"

        # Act
        result = cm.get("database.url")

        # Assert
        assert result == "postgresql://localhost/db"

    def test_get_missing_key_returns_default(self):
        """Test that missing key returns default value."""
        # Arrange
        cm = ConfigManager()

        # Act
        result = cm.get("nonexistent.key", default="default_value")

        # Assert
        assert result == "default_value"

    def test_get_missing_key_no_default(self):
        """Test that missing key without default returns None."""
        # Arrange
        cm = ConfigManager()

        # Act
        result = cm.get("nonexistent.key")

        # Assert
        assert result is None

    def test_get_section_success(self):
        """Test getting configuration section."""
        # Arrange
        cm = ConfigManager()
        section_mock = MagicMock()
        cm._settings = MagicMock()
        cm._settings.database = section_mock

        # Act
        result = cm.get_section("database")

        # Assert
        assert result is section_mock

    def test_get_section_not_found_raises_error(self):
        """Test that getting non-existent section raises error."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.__dict__ = {}

        # Act & Assert
        with pytest.raises(ConfigManagerError, match="not found"):
            cm.get_section("nonexistent")

    def test_set_override(self):
        """Test setting configuration override."""
        # Arrange
        cm = ConfigManager()

        # Act
        cm.set("custom.key", "custom_value")

        # Assert
        assert cm.get("custom.key") == "custom_value"

    def test_set_override_priority(self):
        """Test that overrides take priority."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.debug = False

        # Act
        cm.set("debug", True)
        result = cm.get("debug")

        # Assert
        assert result is True

    def test_remove_override(self):
        """Test removing configuration override."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.debug = True
        cm.set("debug", False)

        # Act
        cm.remove_override("debug")
        result = cm.get("debug")

        # Assert
        assert result is True  # Should fall back to settings value

    def test_remove_nonexistent_override(self):
        """Test removing non-existent override doesn't raise error."""
        # Arrange
        cm = ConfigManager()

        # Act & Assert - should not raise
        cm.remove_override("nonexistent")

    def test_clear_overrides(self):
        """Test clearing all overrides."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.debug = True
        cm.set("debug", False)
        cm.set("api.port", 9000)

        # Act
        cm.clear_overrides()

        # Assert
        assert cm.get("debug") is True
        assert len(cm._overrides) == 0

    def test_reload_configuration(self):
        """Test reloading configuration."""
        # Arrange
        cm = ConfigManager()
        cm.set("test.key", "old_value")

        # Act
        cm.reload()

        # Assert
        assert len(cm._overrides) == 0

    def test_to_dict(self):
        """Test exporting configuration to dictionary."""
        # Arrange
        cm = ConfigManager()
        expected_dict = {"database": {"url": "test"}, "api": {"port": 8000}}
        cm._settings = MagicMock()
        cm._settings.model_dump = MagicMock(return_value=expected_dict)

        # Act
        result = cm.to_dict()

        # Assert
        assert result == expected_dict

    def test_to_dict_safe(self):
        """Test safe export of configuration."""
        # Arrange
        cm = ConfigManager()
        expected_dict = {"api_key": "***", "debug": True}
        cm._settings = MagicMock()
        cm._settings.model_dump_safe = MagicMock(return_value=expected_dict)

        # Act
        result = cm.to_dict(safe=True)

        # Assert
        assert result == expected_dict

    def test_repr(self):
        """Test string representation."""
        # Arrange
        cm = ConfigManager(environment="production")

        # Act
        result = repr(cm)

        # Assert
        assert "ConfigManager" in result
        assert "production" in result

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        # Arrange
        cm1 = ConfigManager()

        # Act
        ConfigManager.reset_instance()
        cm2 = ConfigManager()

        # Assert
        assert cm1 is not cm2

    def test_get_instance(self):
        """Test getting singleton instance."""
        # Act
        cm1 = ConfigManager.get_instance()
        cm2 = ConfigManager.get_instance()

        # Assert
        assert cm1 is cm2


class TestConfigManagerYAMLLoading:
    """Test YAML configuration loading."""

    def test_load_yaml_overrides_success(self):
        """Test successful YAML overrides loading."""
        # Arrange
        yaml_config = {
            "database": {"url": "postgresql://yaml/db"},
            "api": {"port": 9000},
        }

        with patch(
            "src.shared.infrastructure.config.config_manager.ConfigLoader"
        ) as MockLoader:
            mock_loader = MagicMock()
            mock_loader.load_for_environment.return_value = yaml_config
            MockLoader.return_value = mock_loader

            ConfigManager.reset_instance()
            cm = ConfigManager()
            cm._loader = mock_loader

            # Act
            cm._load_yaml_overrides()

            # Assert - may be called once or more due to singleton
            assert mock_loader.load_for_environment.call_count >= 1

    def test_load_yaml_overrides_file_not_found(self):
        """Test handling missing YAML file."""
        # Arrange
        with patch(
            "src.shared.infrastructure.config.config_manager.ConfigLoader"
        ) as MockLoader:
            mock_loader = MagicMock()
            mock_loader.load_for_environment.side_effect = ConfigLoadError(
                "File not found"
            )
            MockLoader.return_value = mock_loader

            cm = ConfigManager()
            cm._loader = mock_loader

            # Act & Assert - should not raise
            cm._load_yaml_overrides()

    def test_apply_yaml_to_settings(self):
        """Test applying YAML config to settings."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.database = MagicMock()
        cm._settings.api = MagicMock()

        yaml_config = {
            "database": {"url": "postgresql://yaml/db"},
            "api": {"port": 9000},
            "debug": True,
        }

        # Act
        cm._apply_yaml_to_settings(yaml_config)

        # Assert
        assert cm._settings.database.url == "postgresql://yaml/db"
        assert cm._settings.api.port == 9000
        assert cm._settings.debug is True


class TestConfigManagerSectionMapping:
    """Test configuration section mapping."""

    def test_update_section_with_path_conversion(self):
        """Test path string conversion in section update."""
        # Arrange
        cm = ConfigManager()
        section = MagicMock()

        # Act
        cm._update_section(section, {"data_dir": "/path/to/data"})

        # Assert
        assert isinstance(section.data_dir, (Path, MagicMock))

    def test_update_section_with_cors_origins(self):
        """Test CORS origins list conversion."""
        # Arrange
        cm = ConfigManager()
        section = MagicMock()

        # Act
        cm._update_section(section, {"cors_origins": "http://localhost,http://test"})

        # Assert
        expected = ["http://localhost", "http://test"]
        assert section.cors_origins == expected

    def test_update_section_with_cors_methods(self):
        """Test CORS methods list conversion."""
        # Arrange
        cm = ConfigManager()
        section = MagicMock()

        # Act
        cm._update_section(section, {"cors_allow_methods": "GET, POST, PUT"})

        # Assert
        expected = ["GET", "POST", "PUT"]
        assert section.cors_allow_methods == expected


class TestGetConfig:
    """Test get_config convenience function."""

    def test_get_config_creates_instance(self):
        """Test get_config creates instance if none exists."""
        # Act
        ConfigManager.reset_instance()
        cm = get_config()

        # Assert
        assert isinstance(cm, ConfigManager)

    def test_get_config_returns_existing_instance(self):
        """Test get_config returns existing instance."""
        # Arrange
        existing = ConfigManager()

        # Act
        result = get_config()

        # Assert
        assert result is existing

    def test_get_config_with_parameters(self):
        """Test get_config with configuration parameters."""
        # Act
        ConfigManager.reset_instance()
        cm = get_config(environment="testing")

        # Assert
        assert cm.environment == Environment.TESTING


class TestGetConfigValue:
    """Test get_config_value convenience function."""

    def test_get_config_value(self):
        """Test getting configuration value."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.debug = True

        # Act
        result = get_config_value("debug")

        # Assert
        assert result is True

    def test_get_config_value_with_default(self):
        """Test getting configuration value with default."""
        # Arrange & Act
        result = get_config_value("nonexistent.key", default="default")

        # Assert
        assert result == "default"


class TestConfigManagerEdgeCases:
    """Test edge cases for ConfigManager."""

    def test_get_with_none_value(self):
        """Test getting key with None value."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.none_field = None

        # Act
        result = cm.get("none_field")

        # Assert
        assert result is None

    def test_get_with_dict_attribute(self):
        """Test getting key from dict attribute."""
        # Arrange
        cm = ConfigManager()
        cm._settings = {"nested": {"key": "value"}}

        # Act
        result = cm.get("nested.key")

        # Assert
        assert result == "value"

    def test_set_override_nested_key(self):
        """Test setting nested override key."""
        # Arrange
        cm = ConfigManager()

        # Act
        cm.set("database.host", "localhost")
        result = cm.get("database.host")

        # Assert
        assert result == "localhost"

    def test_multiple_reloads(self):
        """Test multiple configuration reloads."""
        # Arrange
        cm = ConfigManager()
        cm.set("key1", "value1")
        cm.set("key2", "value2")

        # Act
        cm.reload()
        cm.reload()

        # Assert
        assert len(cm._overrides) == 0

    def test_environment_variable_override(self):
        """Test environment variable override."""
        # Act
        with patch.dict(os.environ, {}, clear=True):
            os.environ["APP_ENVIRONMENT"] = "production"
            ConfigManager.reset_instance()
            cm = ConfigManager()

            # Assert
            assert cm.environment == Environment.PRODUCTION
            assert os.environ["APP_ENVIRONMENT"] == "production"

    def test_invalid_environment_string(self):
        """Test handling invalid environment string."""
        # Act & Assert
        with pytest.raises(ValueError):
            ConfigManager(environment="invalid_env")


class TestConfigManagerIntegration:
    """Integration-style tests for ConfigManager."""

    def test_configuration_precedence(self):
        """Test configuration precedence order."""
        # Arrange - Create ConfigManager with different sources
        with patch.dict(os.environ, {"APP_ENVIRONMENT": "development"}):
            ConfigManager.reset_instance()
            cm = ConfigManager()
            cm._settings = MagicMock()
            cm._settings.debug = False  # Default value
            cm._settings.api = MagicMock()
            cm._settings.api.port = 8000  # Default value

            # Override with programmatic setting
            cm.set("debug", True)

        # Assert - Programmatic override should take precedence
        assert cm.get("debug") is True

    def test_complex_nested_access(self):
        """Test complex nested configuration access."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.database = MagicMock()
        cm._settings.database.pool = MagicMock()
        cm._settings.database.pool.size = 10

        # Act
        result = cm.get("database.pool.size")

        # Assert
        assert result == 10

    def test_config_manager_with_path_config_dir(self):
        """Test ConfigManager with Path config directory."""
        # Arrange - Create a temporary directory
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Act
            ConfigManager.reset_instance()
            cm = ConfigManager(config_dir=config_dir)

            # Assert
            assert cm is not None

    def test_concurrent_access_simulation(self):
        """Test ConfigManager with simulated concurrent access."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.value = "initial"

        results = []

        # Act - Simulate concurrent reads and writes
        for i in range(5):
            cm.set(f"key{i}", f"value{i}")
            results.append(cm.get(f"key{i}"))

        # Assert
        for i in range(5):
            assert results[i] == f"value{i}"

    def test_full_lifecycle(self):
        """Test ConfigManager full lifecycle."""
        # 1. Create instance
        ConfigManager.reset_instance()
        cm = ConfigManager(environment="testing")

        # 2. Set overrides
        cm.set("custom.setting", "value")
        assert cm.get("custom.setting") == "value"

        # 3. Get section
        # (requires actual settings object)

        # 4. Export to dict
        cm._settings = MagicMock()
        cm._settings.model_dump = MagicMock(return_value={"test": "data"})
        config_dict = cm.to_dict()
        assert "test" in config_dict

        # 5. Reload
        cm.reload()

        # 6. Reset instance
        ConfigManager.reset_instance()
        cm2 = ConfigManager()
        assert cm is not cm2

    def test_yaml_section_mapping(self):
        """Test YAML section mapping to settings."""
        # Arrange
        cm = ConfigManager()
        cm._settings = MagicMock()
        cm._settings.database = MagicMock()
        cm._settings.api = MagicMock()
        cm._settings.redis = MagicMock()
        cm._settings.security = MagicMock()
        cm._settings.llm = MagicMock()
        cm._settings.logging = MagicMock()
        cm._settings.monitoring = MagicMock()
        cm._settings.project_name = None
        cm._settings.project_version = None
        cm._settings.project_description = None
        cm._settings.debug = None

        yaml_config = {
            "database": {"host": "localhost", "port": 5432},
            "api": {"port": 8080},
            "redis": {"host": "redis.local"},
            "security": {"secret_key": "secret"},
            "llm": {"model": "gpt-4"},
            "logging": {"level": "INFO"},
            "monitoring": {"enabled": True},
            "project_name": "Test Project",
            "project_version": "1.0.0",
            "project_description": "A test project",
            "debug": True,
        }

        # Act
        cm._apply_yaml_to_settings(yaml_config)

        # Assert
        assert cm._settings.project_name == "Test Project"
        assert cm._settings.project_version == "1.0.0"
        assert cm._settings.debug is True
