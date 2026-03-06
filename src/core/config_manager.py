#!/usr/bin/env python3
"""
Unified Configuration Management System

Consolidates all configuration loading patterns found across the codebase
into a single, consistent, and maintainable configuration manager.

Result Pattern Migration:
    - get() -> Result[Any, ConfigError]
    - get_section() -> Result[Dict[str, Any], ConfigError]
    - reload() -> Result[bool, ConfigError]
    - save_to_file() -> Result[bool, ConfigError]
"""

import json
import structlog
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .result import Error, Err, Ok, Result

logger = structlog.get_logger(__name__)


class ConfigError(Error):
    """Error raised when configuration operations fail."""

    def __init__(
        self,
        message: str,
        operation: str,
        key_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        full_details["operation"] = operation
        if key_path:
            full_details["key_path"] = key_path
        super().__init__(
            code="CONFIG_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class ConfigFormat(Enum):
    """Supported configuration file formats."""

    YAML = "yaml"
    JSON = "json"
    ENV = "env"


@dataclass
class ConfigurationPaths:
    """Standard configuration file paths."""

    main_config: str = "config/environments/development.yaml"
    security_config: str = "config/security/security.yaml"
    settings: str = "config/environments/settings.yaml"
    staging_settings: str = "staging/settings_staging.yaml"

    @classmethod
    def get_all_paths(cls) -> List[str]:
        """Get all standard configuration paths."""
        instance = cls()
        return [
            instance.main_config,
            instance.security_config,
            instance.settings,
            instance.staging_settings,
        ]


@dataclass
class ConfigDefaults:
    """Default configuration values."""

    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    environment: str = "development"

    # Database Configuration
    database_url: str = "sqlite:///data/novel_engine.db"
    database_pool_size: int = 10
    database_timeout: int = 30

    # API Configuration
    api_version: str = "v1"
    max_request_size: int = 10485760  # 10MB
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # Security Configuration
    cors_origins: List[str] = field(default_factory=list)
    enable_docs: bool = True
    enable_metrics: bool = True

    # Performance Configuration
    max_concurrent_agents: int = 20
    cache_ttl_seconds: int = 300
    background_task_interval: int = 60

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = (
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert defaults to dictionary."""
        return {
            "server": {
                "host": self.host,
                "port": self.port,
                "debug": self.debug,
                "environment": self.environment,
            },
            "database": {
                "url": self.database_url,
                "pool_size": self.database_pool_size,
                "timeout": self.database_timeout,
            },
            "api": {
                "version": self.api_version,
                "max_request_size": self.max_request_size,
                "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
                "rate_limit_burst": self.rate_limit_burst,
            },
            "security": {
                "cors_origins": self.cors_origins,
                "enable_docs": self.enable_docs,
                "enable_metrics": self.enable_metrics,
            },
            "performance": {
                "max_concurrent_agents": self.max_concurrent_agents,
                "cache_ttl_seconds": self.cache_ttl_seconds,
                "background_task_interval": self.background_task_interval,
            },
            "logging": {"level": self.log_level, "format": self.log_format},
        }


class ConfigurationManager:
    """
    Unified configuration manager that consolidates all configuration loading patterns.

    Features:
    - Multiple configuration file format support (YAML, JSON)
    - Environment variable override support
    - Configuration validation and defaults
    - Hot configuration reloading
    - Configuration merging and inheritance
    """

    def __init__(self, base_path: Optional[str] = None) -> None:
        """
        Initialize configuration manager.

        Args:
            base_path: Base directory for configuration files
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_data: Dict[str, Any] = {}
        self.defaults = ConfigDefaults()
        self.paths = ConfigurationPaths()

        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load all configuration files in priority order."""
        # Start with defaults
        self.config_data = self.defaults.to_dict()

        # Load configuration files in priority order (later files override earlier ones)
        config_files = [
            self.paths.main_config,
            self.paths.security_config,
            self.paths.settings,
            self.paths.staging_settings,
        ]

        for config_file in config_files:
            config_path = self.base_path / config_file
            if config_path.exists():
                try:
                    file_config = self._load_config_file(config_path)
                    if file_config:
                        self._merge_configurations(self.config_data, file_config)
                        logger.info(f"Loaded configuration from {config_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to load configuration from {config_path}: {e}"
                    )

        # Apply environment variable overrides
        self._apply_environment_overrides()

        # Validate final configuration
        self._validate_configuration()

    def _load_config_file(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from a single file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == ".json":
                    return json.load(f) or {}
                else:
                    logger.warning(
                        f"Unsupported configuration file format: {config_path}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error loading configuration file {config_path}: {e}")
            return None

    def _merge_configurations(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configurations(base[key], value)
            else:
                base[key] = value

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            # Server configuration
            "API_HOST": ("server", "host"),
            "API_PORT": ("server", "port"),
            "DEBUG": ("server", "debug"),
            "ENVIRONMENT": ("server", "environment"),
            # Database configuration
            "DATABASE_URL": ("database", "url"),
            "DATABASE_POOL_SIZE": ("database", "pool_size"),
            "DATABASE_TIMEOUT": ("database", "timeout"),
            # Security configuration
            "CORS_ORIGINS": ("security", "cors_origins"),
            "ENABLE_DOCS": ("security", "enable_docs"),
            "ENABLE_METRICS": ("security", "enable_metrics"),
            # Performance configuration
            "MAX_CONCURRENT_AGENTS": ("performance", "max_concurrent_agents"),
            "CACHE_TTL_SECONDS": ("performance", "cache_ttl_seconds"),
            # Logging configuration
            "LOG_LEVEL": ("logging", "level"),
        }

        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert environment variable value to appropriate type
                converted_value = self._convert_env_value(env_value, section, key)

                # Set the value in configuration
                if section not in self.config_data:
                    self.config_data[section] = {}
                self.config_data[section][key] = converted_value

                logger.debug(
                    f"Applied environment override: {env_var} -> {section}.{key}"
                )

    def _convert_env_value(self, value: str, section: str, key: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversions
        if key in ["debug", "enable_docs", "enable_metrics"]:
            return value.lower() in ["true", "1", "yes", "on"]

        # Integer conversions
        if key in [
            "port",
            "pool_size",
            "timeout",
            "max_concurrent_agents",
            "cache_ttl_seconds",
        ]:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {section}.{key}: {value}")
                return value

        # List conversions (comma-separated)
        if key == "cors_origins":
            return [origin.strip() for origin in value.split(",") if origin.strip()]

        # Default to string
        return value

    def _validate_configuration(self) -> None:
        """Validate the final configuration."""
        errors: list[Any] = []
        # Validate required sections
        required_sections = ["server", "database", "security"]
        for section in required_sections:
            if section not in self.config_data:
                errors.append(f"Missing required configuration section: {section}")

        # Validate specific values
        if "server" in self.config_data:
            port = self.config_data["server"].get("port")
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Invalid port number: {port}")

        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path. (Legacy - use get_result)"""
        result = self.get_result(key_path)
        if result.is_ok:
            return result.value
        return default

    def get_result(self, key_path: str) -> Result[Any, ConfigError]:
        """
        Get configuration value by dot-separated key path using Result pattern.

        Args:
            key_path: Dot-separated path (e.g., "server.host")

        Returns:
            Result containing configuration value or error
        """
        keys = key_path.split(".")
        current = self.config_data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return Err(
                    ConfigError(
                        message=f"Configuration key not found: {key_path}",
                        operation="get",
                        key_path=key_path,
                    )
                )

        return Ok(current)

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by dot-separated key path.

        Args:
            key_path: Dot-separated path (e.g., "server.host")
            value: Value to set
        """
        keys = key_path.split(".")
        current = self.config_data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section. (Legacy - use get_section_result)"""
        result = self.get_section_result(section)
        if result.is_ok:
            return result.value
        return {}

    def get_section_result(self, section: str) -> Result[Dict[str, Any], ConfigError]:
        """
        Get entire configuration section using Result pattern.

        Args:
            section: Name of the configuration section

        Returns:
            Result containing configuration section or error
        """
        if section in self.config_data:
            return Ok(self.config_data[section])
        return Err(
            ConfigError(
                message=f"Configuration section not found: {section}",
                operation="get_section",
                key_path=section,
            )
        )

    def reload(self) -> None:
        """Reload configuration from files. (Legacy - use reload_result)"""
        result = self.reload_result()
        if result.is_error and result.error:
            logger.error(
                "configuration_reload_failed", error=result.error.message
            )

    def reload_result(self) -> Result[bool, ConfigError]:
        """
        Reload configuration from files using Result pattern.

        Returns:
            Result containing True on success or error
        """
        try:
            logger.info("Reloading configuration")
            self._load_configurations()
            return Ok(True)
        except Exception as e:
            return Err(
                ConfigError(
                    message=f"Failed to reload configuration: {e}",
                    operation="reload",
                    key_path=None,
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        return self.config_data.copy()

    def save_to_file(
        self, file_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML
    ) -> None:
        """Save current configuration to file. (Legacy - use save_to_file_result)"""
        result = self.save_to_file_result(file_path, format)
        if result.is_error:
            raise ValueError(f"Failed to save configuration: {result.error.message}")

    def save_to_file_result(
        self, file_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML
    ) -> Result[bool, ConfigError]:
        """
        Save current configuration to file using Result pattern.

        Args:
            file_path: Path to save configuration
            format: File format to use

        Returns:
            Result containing True on success or error
        """
        file_path = Path(file_path)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
                elif format == ConfigFormat.JSON:
                    json.dump(self.config_data, f, indent=2)
                else:
                    return Err(
                        ConfigError(
                            message=f"Unsupported format: {format}",
                            operation="save_to_file",
                            details={"file_path": str(file_path), "format": format.value},
                        )
                    )

            logger.info(f"Configuration saved to {file_path}")
            return Ok(True)

        except Exception as e:
            return Err(
                ConfigError(
                    message=f"Failed to save configuration: {e}",
                    operation="save_to_file",
                    details={"file_path": str(file_path)},
                )
            )


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(base_path: Optional[str] = None) -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigurationManager(base_path)

    return _config_manager


def get_config(key_path: Optional[str] = None, default: Any = None) -> Any:
    """
    Get configuration value using global manager.

    Args:
        key_path: Dot-separated path (e.g., "server.host")
        default: Default value if key not found

    Returns:
        Configuration value, full config dict if key_path is None
    """
    manager = get_config_manager()

    if key_path is None:
        return manager.to_dict()
    else:
        return manager.get(key_path, default)


def reload_config() -> None:
    """Reload global configuration."""
    if _config_manager is not None:
        _config_manager.reload()


# Backwards compatibility functions for existing code
def get_campaign_log_filename() -> str:
    """Get campaign log filename from configuration."""
    result: str = get_config("logging.campaign_log_path", "campaign_log.md")
    return result


__all__ = [
    "ConfigurationManager",
    "ConfigDefaults",
    "ConfigurationPaths",
    "ConfigFormat",
    "get_config_manager",
    "get_config",
    "reload_config",
    "get_campaign_log_filename",
]
