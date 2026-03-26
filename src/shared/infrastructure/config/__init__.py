"""Infrastructure configuration package.

This package provides configuration management for the Novel Engine,
supporting multiple sources: YAML files, environment variables, and
programmatic overrides.

Example:
    >>> from src.shared.infrastructure.config import ConfigManager, get_settings
    >>> config = ConfigManager()
    >>> db_url = config.get("database.url")
    >>> settings = get_settings()
    >>> print(settings.environment)
"""

from .config_manager import (
    ConfigManager,
    ConfigManagerError,
    get_config,
    get_config_value,
)
from .loader import ConfigLoader, ConfigLoadError, load_yaml_config, merge_configs
from .settings import (
    APISettings,
    DatabaseSettings,
    Environment,
    LLMSettings,
    LoggingSettings,
    LogLevel,
    MonitoringSettings,
    NovelEngineSettings,
    RedisSettings,
    SecuritySettings,
    get_settings,
    reload_settings,
    reset_settings,
)

__all__ = [
    # Main classes
    "ConfigManager",
    "ConfigLoader",
    "NovelEngineSettings",
    # Settings classes
    "APISettings",
    "DatabaseSettings",
    "Environment",
    "LLMSettings",
    "LogLevel",
    "LoggingSettings",
    "MonitoringSettings",
    "RedisSettings",
    "SecuritySettings",
    # Functions
    "get_config",
    "get_config_value",
    "get_settings",
    "load_yaml_config",
    "merge_configs",
    "reload_settings",
    "reset_settings",
    # Exceptions
    "ConfigLoadError",
    "ConfigManagerError",
]
