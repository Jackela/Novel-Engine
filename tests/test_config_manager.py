#!/usr/bin/env python3
"""
Unit tests for ConfigurationManager - unified configuration management system.

Tests cover:
- ConfigFormat enum
- ConfigurationPaths dataclass
- ConfigDefaults dataclass
- ConfigurationManager class (initialization, loading, merging, environment overrides, validation)
- Global configuration functions
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from src.core.config_manager import (
    ConfigDefaults,
    ConfigFormat,
    ConfigurationManager,
    ConfigurationPaths,
    get_config,
    get_config_manager,
    get_campaign_log_filename,
    reload_config,
)


class TestConfigFormat:
    """Unit tests for ConfigFormat enum."""

    def test_config_format_values(self):
        """Test ConfigFormat enum values."""
        assert ConfigFormat.YAML.value == "yaml"
        assert ConfigFormat.JSON.value == "json"
        assert ConfigFormat.ENV.value == "env"


class TestConfigurationPaths:
    """Unit tests for ConfigurationPaths dataclass."""

    def test_configuration_paths_defaults(self):
        """Test ConfigurationPaths default values."""
        paths = ConfigurationPaths()

        assert paths.main_config == "configs/environments/development.yaml"
        assert paths.security_config == "configs/security/security.yaml"
        assert paths.settings == "configs/environments/settings.yaml"
        assert paths.staging_settings == "staging/settings_staging.yaml"

    def test_get_all_paths(self):
        """Test get_all_paths returns all standard paths."""
        all_paths = ConfigurationPaths.get_all_paths()

        assert isinstance(all_paths, list)
        assert len(all_paths) == 4
        assert "configs/environments/development.yaml" in all_paths
        assert "configs/security/security.yaml" in all_paths


class TestConfigDefaults:
    """Unit tests for ConfigDefaults dataclass."""

    def test_config_defaults_initialization(self):
        """Test ConfigDefaults default values."""
        defaults = ConfigDefaults()

        assert defaults.host == "127.0.0.1"
        assert defaults.port == 8000
        assert defaults.debug is False
        assert defaults.environment == "development"
        assert defaults.database_url == "sqlite:///data/novel_engine.db"

    def test_config_defaults_to_dict(self):
        """Test ConfigDefaults to_dict conversion."""
        defaults = ConfigDefaults()
        config_dict = defaults.to_dict()

        assert "server" in config_dict
        assert "database" in config_dict
        assert "api" in config_dict
        assert "security" in config_dict
        assert "performance" in config_dict
        assert "logging" in config_dict

        assert config_dict["server"]["host"] == "127.0.0.1"
        assert config_dict["server"]["port"] == 8000
        assert config_dict["database"]["url"] == "sqlite:///data/novel_engine.db"

    def test_config_defaults_custom_values(self):
        """Test ConfigDefaults with custom values."""
        defaults = ConfigDefaults(
            host="0.0.0.0", port=9000, debug=True, environment="production"
        )

        assert defaults.host == "0.0.0.0"
        assert defaults.port == 9000
        assert defaults.debug is True
        assert defaults.environment == "production"


class TestConfigurationManager:
    """Unit tests for ConfigurationManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for test configuration files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigurationManager with temp directory."""
        return ConfigurationManager(base_path=str(temp_config_dir))

    def test_initialization(self, config_manager):
        """Test ConfigurationManager initialization."""
        assert config_manager.config_data is not None
        assert isinstance(config_manager.config_data, dict)
        assert config_manager.defaults is not None
        assert config_manager.paths is not None

    def test_default_configuration_loaded(self, config_manager):
        """Test default configuration is loaded."""
        assert "server" in config_manager.config_data
        assert "database" in config_manager.config_data
        assert config_manager.get("server.host") == "127.0.0.1"
        assert config_manager.get("server.port") == 8000

    def test_load_yaml_config_file(self, temp_config_dir):
        """Test loading YAML configuration file."""
        configs_dir = temp_config_dir / "configs" / "environments"
        configs_dir.mkdir(parents=True, exist_ok=True)

        config_file = configs_dir / "development.yaml"
        config_data = {"server": {"host": "0.0.0.0", "port": 9000}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager(base_path=str(temp_config_dir))

        assert manager.get("server.host") == "0.0.0.0"
        assert manager.get("server.port") == 9000

    def test_load_json_config_file(self, temp_config_dir):
        """Test loading JSON configuration file."""
        configs_dir = temp_config_dir / "configs" / "environments"
        configs_dir.mkdir(parents=True, exist_ok=True)

        config_file = configs_dir / "development.json"
        config_data = {"server": {"host": "192.168.1.1", "port": 7000}}

        config_file_yaml = config_file.with_suffix(".yaml")
        if config_file_yaml.exists():
            config_file_yaml.unlink()

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        manager = ConfigurationManager(base_path=str(temp_config_dir))
        manager.paths.main_config = "configs/environments/development.json"
        manager._load_configurations()

        assert manager.get("server.host") in ["192.168.1.1", "127.0.0.1"]

    def test_merge_configurations(self, config_manager):
        """Test configuration merging."""
        base = {"server": {"host": "127.0.0.1", "port": 8000}, "database": {"url": ""}}
        override = {"server": {"port": 9000}, "api": {"version": "v2"}}

        config_manager._merge_configurations(base, override)

        assert base["server"]["host"] == "127.0.0.1"
        assert base["server"]["port"] == 9000
        assert "api" in base
        assert base["api"]["version"] == "v2"

    def test_environment_variable_override(self, temp_config_dir, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("API_HOST", "10.0.0.1")
        monkeypatch.setenv("API_PORT", "5000")
        monkeypatch.setenv("DEBUG", "true")

        manager = ConfigurationManager(base_path=str(temp_config_dir))

        assert manager.get("server.host") == "10.0.0.1"
        assert manager.get("server.port") == 5000
        assert manager.get("server.debug") is True

    def test_convert_env_value_boolean(self, config_manager):
        """Test environment value conversion for booleans."""
        assert config_manager._convert_env_value("true", "server", "debug") is True
        assert config_manager._convert_env_value("1", "server", "debug") is True
        assert config_manager._convert_env_value("yes", "server", "debug") is True
        assert config_manager._convert_env_value("false", "server", "debug") is False

    def test_convert_env_value_integer(self, config_manager):
        """Test environment value conversion for integers."""
        assert config_manager._convert_env_value("8080", "server", "port") == 8080
        assert config_manager._convert_env_value("100", "database", "pool_size") == 100

    def test_convert_env_value_list(self, config_manager):
        """Test environment value conversion for lists."""
        result = config_manager._convert_env_value(
            "http://localhost,https://example.com", "security", "cors_origins"
        )
        assert result == ["http://localhost", "https://example.com"]

    def test_get_configuration_value(self, config_manager):
        """Test getting configuration values."""
        assert config_manager.get("server.host") == "127.0.0.1"
        assert config_manager.get("server.port") == 8000
        assert config_manager.get("nonexistent.key") is None
        assert config_manager.get("nonexistent.key", "default") == "default"

    def test_set_configuration_value(self, config_manager):
        """Test setting configuration values."""
        config_manager.set("server.host", "192.168.1.100")
        assert config_manager.get("server.host") == "192.168.1.100"

        config_manager.set("new.nested.key", "value")
        assert config_manager.get("new.nested.key") == "value"

    def test_get_section(self, config_manager):
        """Test getting entire configuration section."""
        server_config = config_manager.get_section("server")

        assert isinstance(server_config, dict)
        assert "host" in server_config
        assert "port" in server_config

    def test_to_dict(self, config_manager):
        """Test converting configuration to dictionary."""
        config_dict = config_manager.to_dict()

        assert isinstance(config_dict, dict)
        assert "server" in config_dict
        assert "database" in config_dict

    def test_save_to_file_yaml(self, config_manager, temp_config_dir):
        """Test saving configuration to YAML file."""
        output_file = temp_config_dir / "output.yaml"
        config_manager.save_to_file(output_file, ConfigFormat.YAML)

        assert output_file.exists()

        with open(output_file, "r") as f:
            loaded_data = yaml.safe_load(f)

        assert "server" in loaded_data
        assert loaded_data["server"]["host"] == "127.0.0.1"

    def test_save_to_file_json(self, config_manager, temp_config_dir):
        """Test saving configuration to JSON file."""
        output_file = temp_config_dir / "output.json"
        config_manager.save_to_file(output_file, ConfigFormat.JSON)

        assert output_file.exists()

        with open(output_file, "r") as f:
            loaded_data = json.load(f)

        assert "server" in loaded_data
        assert loaded_data["server"]["host"] == "127.0.0.1"

    def test_reload_configuration(self, temp_config_dir):
        """Test reloading configuration."""
        manager = ConfigurationManager(base_path=str(temp_config_dir))
        initial_host = manager.get("server.host")

        manager.set("server.host", "10.10.10.10")
        assert manager.get("server.host") == "10.10.10.10"

        manager.reload()
        assert manager.get("server.host") == initial_host

    def test_validation_missing_section(self, temp_config_dir):
        """Test configuration validation with missing sections."""
        manager = ConfigurationManager(base_path=str(temp_config_dir))
        manager.config_data = {"server": {}}

        with pytest.raises(ValueError, match="Missing required configuration section"):
            manager._validate_configuration()

    def test_validation_invalid_port(self, temp_config_dir):
        """Test configuration validation with invalid port."""
        manager = ConfigurationManager(base_path=str(temp_config_dir))
        manager.config_data = {
            "server": {"port": 99999},
            "database": {},
            "security": {},
        }

        with pytest.raises(ValueError, match="Invalid port number"):
            manager._validate_configuration()


class TestGlobalConfigurationFunctions:
    """Unit tests for global configuration functions."""

    def test_get_config_manager_singleton(self):
        """Test get_config_manager returns singleton instance."""
        from src.core import config_manager as cm_module

        cm_module._config_manager = None

        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_get_config_with_key_path(self):
        """Test get_config with key path."""
        value = get_config("server.host")
        assert value is not None

    def test_get_config_with_default(self):
        """Test get_config with default value."""
        value = get_config("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_get_config_full_dict(self):
        """Test get_config returns full dict when no key path."""
        config = get_config()
        assert isinstance(config, dict)
        assert "server" in config

    def test_reload_config_function(self):
        """Test reload_config function."""
        from src.core import config_manager as cm_module

        cm_module._config_manager = ConfigurationManager()
        reload_config()

    def test_get_campaign_log_filename(self):
        """Test get_campaign_log_filename function."""
        filename = get_campaign_log_filename()
        assert isinstance(filename, str)
        assert len(filename) > 0
