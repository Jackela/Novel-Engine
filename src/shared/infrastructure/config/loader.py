"""YAML configuration loader module.

This module provides utilities for loading and merging YAML configuration files
with environment-specific overrides.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .settings import Environment


class ConfigLoadError(Exception):
    """Exception raised when configuration loading fails."""

    pass


class ConfigLoader:
    """Configuration loader for YAML files with environment-specific overrides.

    This loader supports a hierarchical configuration system where:
    1. Base config is loaded from {name}.yaml
    2. Environment-specific config is loaded from {name}.{environment}.yaml
    3. Environment variables override YAML values (handled by pydantic-settings)

    Example:
        loader = ConfigLoader("config")
        config = loader.load("app")  # Loads app.yaml + app.development.yaml
    """

    def __init__(self, config_dir: str | Path | None = None) -> None:
        """Initialize the config loader.

        Args:
            config_dir: Directory containing YAML config files.
                       Defaults to project root /config.
        """
        if config_dir is None:
            # Default to project_root/config
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.config_dir = project_root / "config"
        else:
            self.config_dir = Path(config_dir)

        if not self.config_dir.exists():
            raise ConfigLoadError(
                f"Configuration directory not found: {self.config_dir}"
            )

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load a YAML file and return its contents as a dictionary.

        Args:
            file_path: Path to the YAML file.

        Returns:
            Dictionary containing the YAML data.

        Raises:
            ConfigLoadError: If the file cannot be loaded.
        """
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content if content is not None else {}
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML file {file_path}: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Failed to load config file {file_path}: {e}")

    def _deep_merge(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries.

        Values in override take precedence. Nested dictionaries are merged recursively.

        Args:
            base: Base dictionary.
            override: Dictionary with override values.

        Returns:
            Merged dictionary.
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def load(
        self,
        name: str,
        environment: Environment | str | None = None,
    ) -> dict[str, Any]:
        """Load configuration for a specific name and environment.

        Args:
            name: Configuration name (e.g., 'app', 'database').
            environment: Environment type. If None, uses APP_ENVIRONMENT or defaults
                        to development.

        Returns:
            Merged configuration dictionary.

        Raises:
            ConfigLoadError: If configuration cannot be loaded.
        """
        if environment is None:
            env_str = os.environ.get("APP_ENVIRONMENT", "development")
            environment = Environment(env_str)
        elif isinstance(environment, str):
            environment = Environment(environment)

        # Load base config
        base_file = self.config_dir / f"{name}.yaml"
        config = self._load_yaml_file(base_file)

        # Load environment-specific config and merge
        env_file = self.config_dir / f"{name}.{environment.value}.yaml"
        env_config = self._load_yaml_file(env_file)

        if env_config:
            config = self._deep_merge(config, env_config)

        return config

    def load_for_environment(
        self,
        environment: Environment | str | None = None,
    ) -> dict[str, Any]:
        """Load all configuration files for a specific environment.

        This loads the main {environment}.yaml file if it exists.

        Args:
            environment: Environment type. If None, uses APP_ENVIRONMENT or defaults
                        to development.

        Returns:
            Configuration dictionary.
        """
        if environment is None:
            env_str = os.environ.get("APP_ENVIRONMENT", "development")
            environment = Environment(env_str)
        elif isinstance(environment, str):
            environment = Environment(environment)

        # Load environment-specific config directly
        env_file = self.config_dir / f"{environment.value}.yaml"
        return self._load_yaml_file(env_file)

    def list_available_configs(self) -> list[str]:
        """List available configuration files in the config directory.

        Returns:
            List of configuration file names (without extensions).
        """
        if not self.config_dir.exists():
            return []

        configs = []
        for file_path in self.config_dir.glob("*.yaml"):
            # Skip environment-specific files
            name = file_path.stem
            if not any(name.endswith(f".{env.value}") for env in Environment):
                configs.append(name)

        return sorted(configs)

    def config_exists(self, name: str) -> bool:
        """Check if a configuration file exists.

        Args:
            name: Configuration name.

        Returns:
            True if the config file exists.
        """
        base_file = self.config_dir / f"{name}.yaml"
        return base_file.exists()


def load_yaml_config(
    name: str,
    environment: Environment | str | None = None,
    config_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Convenience function to load YAML configuration.

    Args:
        name: Configuration name.
        environment: Environment type.
        config_dir: Configuration directory path.

    Returns:
        Configuration dictionary.
    """
    loader = ConfigLoader(config_dir)
    return loader.load(name, environment)


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple configuration dictionaries.

    Later configurations override earlier ones.

    Args:
        *configs: Configuration dictionaries to merge.

    Returns:
        Merged configuration dictionary.
    """
    if not configs:
        return {}

    result = configs[0].copy()
    loader = ConfigLoader()

    for config in configs[1:]:
        result = loader._deep_merge(result, config)

    return result
