"""
Core Configuration Package.
This package contains configuration management components including
YAML configuration loading, validation, and environment variable handling.
"""

from .config_environment_loader import (  # noqa: F401
    ConfigPaths,
    Environment,
    EnvironmentConfigLoader,
    get_config_value,
    get_environment_config_loader,
    load_config,
)

__all__ = [
    "ConfigPaths",
    "Environment",
    "EnvironmentConfigLoader",
    "get_config_value",
    "get_environment_config_loader",
    "load_config",
]

__version__ = "1.1.0"
