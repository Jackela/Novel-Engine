"""Configuration settings module using pydantic-settings v2.

This module provides type-safe, environment-aware configuration management
for the Novel Engine application.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging level types."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
        case_sensitive=False,
    )

    url: str = Field(
        default="sqlite:///./novel_engine.db",
        description="Database connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=10, ge=0, le=100, description="Max overflow connections"
    )
    pool_timeout: int = Field(
        default=30, ge=1, le=300, description="Pool timeout in seconds"
    )
    echo: bool = Field(default=False, description="Echo SQL statements")

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        valid_prefixes = ("sqlite:///", "postgresql://", "postgresql+asyncpg://")
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Database URL must start with one of: {', '.join(valid_prefixes)}"
            )
        return v


class RedisSettings(BaseSettings):
    """Redis cache configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="Redis server host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")
    ssl: bool = Field(default=False, description="Use SSL connection")
    socket_timeout: int = Field(
        default=5, ge=1, le=60, description="Socket timeout in seconds"
    )
    socket_connect_timeout: int = Field(
        default=5, ge=1, le=60, description="Socket connect timeout in seconds"
    )
    health_check_interval: int = Field(
        default=30, ge=10, le=300, description="Health check interval in seconds"
    )


class APISettings(BaseSettings):
    """API server configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="API server port")
    workers: int = Field(
        default=1, ge=1, le=32, description="Number of worker processes"
    )
    reload: bool = Field(default=False, description="Enable auto-reload")
    title: str = Field(default="Novel Engine API", description="API title")
    version: str = Field(default="0.1.0", description="API version")
    docs_url: str | None = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str | None = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str | None = Field(
        default="/openapi.json", description="OpenAPI schema URL"
    )


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        extra="ignore",
        case_sensitive=False,
    )

    secret_key: str = Field(
        default="change-me-in-production",
        min_length=16,
        description="Secret key for JWT signing",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=5, le=1440, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, ge=1, le=30, description="Refresh token expiration in days"
    )
    encryption_key: str | None = Field(
        default=None, description="Fernet encryption key for sensitive data"
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow CORS credentials"
    )
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS headers",
    )
    rate_limit: str = Field(default="100/minute", description="Rate limit string")
    rate_limit_burst: int = Field(
        default=10, ge=1, le=100, description="Rate limit burst"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if isinstance(v, list) else []

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v: Any) -> list[str]:
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",") if method.strip()]
        return v if isinstance(v, list) else []

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v: Any) -> list[str]:
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v if isinstance(v, list) else []


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",
        case_sensitive=False,
    )

    provider: Literal["gemini", "openai", "anthropic", "mock"] = Field(
        default="gemini",
        description="LLM provider name",
    )
    model: str = Field(default="gemini-pro", description="LLM model name")
    api_key: str | None = Field(default=None, description="LLM API key")
    api_base: str | None = Field(default=None, description="Custom API base URL")
    timeout: int = Field(
        default=30, ge=5, le=300, description="Request timeout in seconds"
    )
    max_tokens: int = Field(
        default=4096, ge=1, le=8192, description="Max tokens per request"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=40, ge=1, le=100, description="Top-k sampling")
    retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Retry delay in seconds"
    )
    max_monthly_cost: float = Field(
        default=10.0, ge=0.0, le=1000.0, description="Monthly cost limit in USD"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
        case_sensitive=False,
    )

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

    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable monitoring")
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
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
    service_name: str = Field(
        default="novel-engine", description="Service name for tracing"
    )
    service_version: str = Field(default="0.1.0", description="Service version")


class NovelEngineSettings(BaseSettings):
    """Main application settings using pydantic-settings v2.

    This is the root configuration class that aggregates all sub-settings.
    It supports environment-specific overrides via .env files and YAML configs.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
        populate_by_name=True,
    )

    # Core settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    project_name: str = Field(default="Novel Engine", description="Project name")
    project_version: str = Field(default="0.1.0", description="Project version")
    project_description: str = Field(
        default="AI-Enhanced Interactive Novel Engine",
        description="Project description",
    )

    # Path settings
    base_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent.parent,
        description="Project base directory",
    )
    config_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent.parent
        / "config",
        description="Configuration directory",
    )
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent.parent
        / "data",
        description="Data directory",
    )
    logs_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent.parent
        / "logs",
        description="Logs directory",
    )

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

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

        # Set the environment and create settings
        import os

        original_env = os.environ.get("APP_ENVIRONMENT")
        os.environ["APP_ENVIRONMENT"] = env.value

        try:
            return cls()
        finally:
            if original_env is None:
                os.environ.pop("APP_ENVIRONMENT", None)
            else:
                os.environ["APP_ENVIRONMENT"] = original_env


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
