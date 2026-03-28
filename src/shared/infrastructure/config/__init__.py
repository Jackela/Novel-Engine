"""Infrastructure configuration package.

This package provides configuration management for the Novel Engine,
supporting YAML files and environment-backed settings.

Example:
    >>> from src.shared.infrastructure.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.environment)
"""

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
    "get_settings",
    "load_yaml_config",
    "merge_configs",
    "reload_settings",
    "reset_settings",
    # Exceptions
    "ConfigLoadError",
]
