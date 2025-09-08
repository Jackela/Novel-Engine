"""
Environment Configuration Module

Manages environment-specific configurations for development, staging, and production.
Provides utilities for loading and validating environment variables and settings.

Features:
- Environment detection and validation
- Configuration loading and merging
- Environment-specific overrides
- Secrets management integration

Example:
    from configs.environments import get_env_config, validate_environment

    config = get_env_config('production')
    if validate_environment(config):
        # Use validated configuration
        pass
"""

import os
from typing import Any, Dict, Optional

__version__ = "1.0.0"

# Environment configuration utilities
__all__ = [
    "get_current_environment",
    "load_environment_config",
    "validate_environment_config",
    "merge_configs",
]


def get_current_environment() -> str:
    """
    Detect the current environment from environment variables.

    Returns:
        str: Environment name (dev, staging, production)
    """
    return os.getenv("NOVEL_ENV", "dev").lower()


def load_environment_config(env: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for the specified environment.

    Args:
        env: Environment name. If None, uses current environment.

    Returns:
        Dict containing environment configuration
    """
    if env is None:
        env = get_current_environment()

    # Placeholder for actual configuration loading
    # Will be implemented during migration
    return {"environment": env, "debug": env == "dev", "config_loaded": True}


def validate_environment_config(config: Dict[str, Any]) -> bool:
    """
    Validate environment configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        bool: True if configuration is valid
    """
    required_keys = ["environment"]
    return all(key in config for key in required_keys)


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple configuration dictionaries.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Dict: Merged configuration
    """
    result = {}
    for config in configs:
        result.update(config)
    return result
