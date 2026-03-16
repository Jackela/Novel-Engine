"""Configuration manager module.

This module provides the main ConfigManager class that orchestrates
settings from multiple sources: YAML configs, environment variables,
and programmatic overrides.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .loader import ConfigLoader, ConfigLoadError, load_yaml_config
from .settings import (
    Environment,
    NovelEngineSettings,
    get_settings,
    reload_settings,
    reset_settings,
)


class ConfigManagerError(Exception):
    """Exception raised by ConfigManager operations."""

    pass


class ConfigManager:
    """Central configuration manager for Novel Engine.

    This class provides a unified interface for accessing configuration
    from multiple sources with proper precedence:
    1. Default values (lowest priority)
    2. YAML configuration files
    3. Environment variables
    4. Programmatic overrides (highest priority)

    Attributes:
        settings: The pydantic-settings instance with all configuration.
        loader: The YAML config loader instance.
        environment: The current environment type.

    Example:
        >>> from src.shared.infrastructure.config import ConfigManager
        >>> config = ConfigManager()
        >>> db_url = config.get("database.url")
        >>> # Or use typed settings
        >>> api_port = config.settings.api.port
    """

    _instance: ConfigManager | None = None
    _overrides: dict[str, Any]
    _environment: Environment
    _loader: ConfigLoader
    _settings: NovelEngineSettings

    def __new__(cls, *args: Any, **kwargs: Any) -> ConfigManager:
        """Implement singleton pattern for ConfigManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        config_dir: str | Path | None = None,
        environment: Environment | str | None = None,
    ) -> None:
        """Initialize the configuration manager.

        Args:
            config_dir: Directory containing YAML config files.
            environment: Environment type to use. If None, uses APP_ENVIRONMENT
                        env var or defaults to development.
        """
        # Skip initialization if already done (singleton pattern)
        if getattr(self, "_initialized", False):
            return

        self._overrides = {}

        # Determine environment
        if environment is None:
            env_str = os.environ.get("APP_ENVIRONMENT", "development")
            self._environment = Environment(env_str)
        elif isinstance(environment, str):
            self._environment = Environment(environment)
        else:
            self._environment = environment  # type: ignore[unreachable]

        # Set environment variable for pydantic-settings
        os.environ["APP_ENVIRONMENT"] = self._environment.value

        # Initialize loader
        self._loader = ConfigLoader(config_dir)

        # Initialize settings
        self._settings = NovelEngineSettings()

        # Load and apply YAML overrides
        self._load_yaml_overrides()

        self._initialized = True

    def _load_yaml_overrides(self) -> None:
        """Load YAML configuration and apply as overrides to settings."""
        assert self._loader is not None
        try:
            yaml_config = self._loader.load_for_environment(self._environment)
            if yaml_config:
                self._apply_yaml_to_settings(yaml_config)
        except ConfigLoadError:
            # YAML config is optional
            pass

    def _apply_yaml_to_settings(self, config: dict[str, Any]) -> None:
        """Apply YAML configuration to settings.

        This maps YAML structure to pydantic settings fields.
        """
        # Map YAML sections to settings fields
        section_mapping = {
            "database": "database",
            "redis": "redis",
            "api": "api",
            "security": "security",
            "llm": "llm",
            "logging": "logging",
            "monitoring": "monitoring",
        }

        for yaml_section, settings_field in section_mapping.items():
            if yaml_section in config:
                section_config = config[yaml_section]
                if hasattr(self._settings, settings_field):
                    settings_section = getattr(self._settings, settings_field)
                    self._update_section(settings_section, section_config)

        # Apply root-level settings
        root_settings = [
            "project_name",
            "project_version",
            "project_description",
            "debug",
        ]
        for key in root_settings:
            if key in config:
                setattr(self._settings, key, config[key])

    def _update_section(self, section: Any, config: dict[str, Any]) -> None:
        """Update a settings section with YAML config values."""
        for key, value in config.items():
            if hasattr(section, key):
                # Convert path strings to Path objects
                if key.endswith("_dir") or key.endswith("_path") or key == "file_path":
                    if isinstance(value, str):
                        value = Path(value)
                # Convert lists from comma-separated strings if needed
                if isinstance(value, str) and key in [
                    "cors_origins",
                    "cors_allow_methods",
                    "cors_allow_headers",
                ]:
                    value = [item.strip() for item in value.split(",")]
                setattr(section, key, value)

    @property
    def settings(self) -> NovelEngineSettings:
        """Get the current settings instance.

        Returns:
            NovelEngineSettings: The current settings.
        """
        return self._settings

    @property
    def environment(self) -> Environment:
        """Get the current environment.

        Returns:
            Environment: The current environment type.
        """
        return self._environment

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Supports dot notation for nested values (e.g., 'database.url').

        Args:
            key: Configuration key in dot notation.
            default: Default value if key is not found.

        Returns:
            Configuration value or default.

        Example:
            >>> config.get("database.url")
            "sqlite:///./novel_engine.db"
            >>> config.get("api.port")
            8000
        """
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Navigate nested attributes
        keys = key.split(".")
        value: Any = self._settings

        for k in keys:
            if value is None:
                return default
            if isinstance(value, dict):
                value = value.get(k, default)
            elif hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

        return value

    def get_section(self, section: str) -> Any:
        """Get a configuration section.

        Args:
            section: Section name (e.g., 'database', 'api', 'security').

        Returns:
            The configuration section object.

        Raises:
            ConfigManagerError: If section does not exist.
        """
        if not hasattr(self._settings, section):
            raise ConfigManagerError(f"Configuration section '{section}' not found")
        return getattr(self._settings, section)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value override.

        This creates a runtime override that takes precedence over
        all other configuration sources.

        Args:
            key: Configuration key in dot notation.
            value: Value to set.

        Example:
            >>> config.set("api.port", 9000)
        """
        self._overrides[key] = value

    def remove_override(self, key: str) -> None:
        """Remove a configuration override.

        Args:
            key: Configuration key to remove.
        """
        self._overrides.pop(key, None)

    def clear_overrides(self) -> None:
        """Clear all configuration overrides."""
        self._overrides.clear()

    def reload(self) -> None:
        """Reload all configuration from sources.

        This re-reads environment variables and YAML configs,
        then rebuilds the settings object.
        """
        reset_settings()
        self._settings = reload_settings()
        self._overrides.clear()
        self._load_yaml_overrides()

    def to_dict(self, safe: bool = False) -> dict[str, Any]:
        """Export configuration as a dictionary.

        Args:
            safe: If True, mask sensitive fields like API keys.

        Returns:
            Dictionary representation of configuration.
        """
        if safe:
            return self._settings.model_dump_safe()
        return self._settings.model_dump()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        This is primarily useful for testing to ensure a fresh instance.
        """
        cls._instance = None
        reset_settings()

    @classmethod
    def get_instance(cls) -> ConfigManager:
        """Get the singleton ConfigManager instance.

        Returns:
            ConfigManager: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ConfigManager(environment={self._environment.value})"


# Convenience functions for module-level access


def get_config(
    config_dir: str | Path | None = None,
    environment: Environment | str | None = None,
) -> ConfigManager:
    """Get or create the global ConfigManager instance.

    Args:
        config_dir: Configuration directory path.
        environment: Environment type.

    Returns:
        ConfigManager: The global configuration manager.
    """
    if ConfigManager._instance is None:
        return ConfigManager(config_dir, environment)
    return ConfigManager._instance


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value using the global ConfigManager.

    Args:
        key: Configuration key.
        default: Default value.

    Returns:
        Configuration value.
    """
    return get_config().get(key, default)
