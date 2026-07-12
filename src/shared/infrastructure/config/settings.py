"""Type-safe, environment-aware configuration for Novel Studio."""

# mypy: disable-error-code=misc

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from src.shared.infrastructure.config.settings_sections import (
    DEFAULT_SECRET_KEY,
    APISettings,
    DatabaseSettings,
    Environment,
    LLMSettings,
    LogLevel,
    SecuritySettings,
    _package_version,
    _settings_config,
)
from src.shared.infrastructure.config.settings_sections import (
    LOCAL_DOTENV_FILE as LOCAL_DOTENV_FILE,
)


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = _settings_config(env_prefix="LOG_")

    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    json_format: bool = Field(default=False, description="Use JSON log format")
    file_path: Path | None = Field(default=None, description="Log file path")
    max_bytes: int = Field(
        default=10_485_760, ge=1024, description="Max log file size in bytes"
    )
    backup_count: int = Field(
        default=5, ge=0, le=100, description="Number of backup files"
    )
    console_output: bool = Field(default=True, description="Output logs to console")
    structured: bool = Field(default=True, description="Use structured logging")


class MonitoringSettings(BaseSettings):
    """Monitoring and telemetry configuration settings."""

    model_config = _settings_config(env_prefix="MONITORING_")

    enabled: bool = Field(default=True, description="Enable monitoring")
    metrics_enabled: bool = Field(
        default=False, description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=9090, ge=1024, le=65535, description="Metrics server port"
    )
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")
    tracing_enabled: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    jaeger_endpoint: str | None = Field(
        default=None, description="Jaeger collector endpoint"
    )
    service_name: str = Field(default="novel-studio", description="Service name")
    service_version: str = Field(
        default_factory=_package_version,
        description="Service version derived from the installed package",
    )


class HealthCheckSettings(BaseSettings):
    """Health check configuration settings."""

    model_config = _settings_config(env_prefix="HEALTH_")

    timeout_seconds: int = Field(
        default=5, ge=1, le=60, description="Health check timeout in seconds"
    )
    cache_check_enabled: bool = Field(
        default=True, description="Enable cache health check"
    )
    external_services_check_enabled: bool = Field(
        default=True, description="Enable external services health check"
    )


class NovelEngineSettings(BaseSettings):
    """Main application settings using pydantic-settings v2.

    This is the root configuration class that aggregates all sub-settings.
    It supports environment-specific overrides via .env files and YAML configs.
    """

    model_config = _settings_config(
        env_prefix="APP_",
        env_nested_delimiter="__",
        validate_default=True,
        populate_by_name=True,
    )

    # Core settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    project_name: str = Field(default="Novel Studio", description="Project name")
    project_version: str = Field(
        default_factory=_package_version,
        description="Project version",
    )
    project_description: str = Field(
        default="Self-hosted single-author novel writing studio",
        description="Project description",
    )

    # Path settings
    base_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent.parent,
        description="Project base directory",
    )
    config_dir: Path = Field(
        default_factory=lambda: (
            Path(__file__).parent.parent.parent.parent.parent / "config"
        ),
        description="Configuration directory",
    )
    data_dir: Path = Field(
        default_factory=lambda: (
            Path(__file__).parent.parent.parent.parent.parent / "data"
        ),
        description="Data directory",
    )
    logs_dir: Path = Field(
        default_factory=lambda: (
            Path(__file__).parent.parent.parent.parent.parent / "logs"
        ),
        description="Logs directory",
    )

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    health: HealthCheckSettings = Field(default_factory=HealthCheckSettings)

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @model_validator(mode="after")
    def apply_runtime_security_defaults(self) -> Self:
        """Apply safe runtime defaults for local and testing environments."""
        if self.is_production or self.is_staging:
            environment_name = "production" if self.is_production else "staging"
            if (
                not self.security.secret_key
                or self.security.secret_key == DEFAULT_SECRET_KEY
            ):
                raise ValueError(
                    f"SECURITY_SECRET_KEY must be set to a non-default value in {environment_name}"
                )
            if self.is_production:
                if not self.database.url.startswith("sqlite:///"):
                    raise ValueError("DB_URL must use the self-hosted SQLite store")
                if "*" in self.security.cors_origins:
                    raise ValueError(
                        "Production CORS origins cannot include a wildcard"
                    )
                for origin in self.security.cors_origins:
                    if "localhost" in origin or "127.0.0.1" in origin:
                        raise ValueError(
                            "Production CORS origins cannot include localhost or 127.0.0.1"
                        )
        if (
            not self.security.secret_key
            or self.security.secret_key == DEFAULT_SECRET_KEY
        ):
            if self.is_testing:
                self.security.secret_key = (
                    self.security.secret_key
                    or "test-secret-key-for-novel-engine-32-chars"
                )
            else:
                self.security.secret_key = secrets.token_urlsafe(32)
        return self

    def model_dump_safe(self) -> dict[str, Any]:
        """Dump settings with sensitive fields masked."""
        import typing

        data = self.model_dump()

        # Mask sensitive fields
        sensitive_keys = ["api_key", "secret_key", "encryption_key", "password"]

        def mask_sensitive(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: "***REDACTED***"
                    if any(sk in k.lower() for sk in sensitive_keys)
                    else mask_sensitive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [mask_sensitive(item) for item in obj]
            elif isinstance(obj, str) and any(
                sk in repr(obj).lower() for sk in sensitive_keys
            ):
                return "***REDACTED***"
            return obj

        return typing.cast(dict[str, Any], mask_sensitive(data))

    @classmethod
    def from_environment(cls, env: Environment | str | None = None) -> Self:
        """Create settings for a specific environment.

        Args:
            env: Environment type. If None, uses APP_ENVIRONMENT or defaults to DEVELOPMENT.

        Returns:
            NovelEngineSettings instance configured for the specified environment.
        """
        if env is None:
            # Will be resolved from environment variable
            return cls()

        if isinstance(env, str):
            env = Environment(env.lower())

        return cls(environment=env)


# Global settings instance (lazy-loaded)
_settings: NovelEngineSettings | None = None


def get_settings() -> NovelEngineSettings:
    """Get the global settings instance.

    This function returns a cached settings instance.
    The first call will initialize the settings from environment variables.

    Returns:
        NovelEngineSettings: The global settings instance.
    """
    global _settings
    if _settings is None:
        _settings = NovelEngineSettings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance.

    This is useful for testing to ensure fresh settings.
    """
    global _settings
    _settings = None


def reload_settings() -> NovelEngineSettings:
    """Reload settings from environment.

    This forces a fresh load of all settings from environment variables
    and .env files.

    Returns:
        NovelEngineSettings: The reloaded settings instance.
    """
    reset_settings()
    return get_settings()
