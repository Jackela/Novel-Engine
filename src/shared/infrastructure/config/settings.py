"""Type-safe, environment-aware configuration for Novel Studio."""

# mypy: disable-error-code=misc

from __future__ import annotations

import secrets
import tomllib
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, Literal, Self, cast

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Development placeholder. Production and staging reject this value; local and
# testing runs replace it with a generated/test secret at settings validation.
DEFAULT_SECRET_KEY = "change-me-in-production-32-char-long"  # noqa: S105  # nosec B105
LOCAL_DOTENV_FILE = ".env.local"


def _package_version() -> str:
    pyproject = Path(__file__).parents[4] / "pyproject.toml"
    if pyproject.is_file():
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(project["project"]["version"])
    try:
        return version("novel-engine")
    except PackageNotFoundError:
        return "0.3.0"


def _settings_config(
    *,
    env_prefix: str,
    env_nested_delimiter: str | None = None,
    validate_default: bool | None = None,
    populate_by_name: bool | None = None,
) -> SettingsConfigDict:
    """Build a consistent settings config that loads local-only dotenv files."""
    config: dict[str, Any] = {
        "env_file": LOCAL_DOTENV_FILE,
        "env_file_encoding": "utf-8",
        "env_prefix": env_prefix,
        "extra": "ignore",
        "case_sensitive": False,
    }
    if env_nested_delimiter is not None:
        config["env_nested_delimiter"] = env_nested_delimiter
    if validate_default is not None:
        config["validate_default"] = validate_default
    if populate_by_name is not None:
        config["populate_by_name"] = populate_by_name
    return cast(SettingsConfigDict, config)


class Environment(str, Enum):  # noqa: UP042
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):  # noqa: UP042
    """Logging level types."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = _settings_config(env_prefix="DB_")

    url: str = Field(
        default="sqlite:///./data/novel-engine.sqlite3",
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
        if not v.startswith("sqlite:///"):
            raise ValueError("DB_URL must use the self-hosted SQLite store")
        return v


# Default bind for containers; override with API_HOST.
_DEFAULT_API_HOST = "0.0.0.0"  # noqa: S104  # nosec B104


class APISettings(BaseSettings):
    """API server configuration settings."""

    model_config = _settings_config(env_prefix="API_")

    host: str = Field(default=_DEFAULT_API_HOST, description="API server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="API server port")
    workers: int = Field(
        default=1, ge=1, le=32, description="Number of worker processes"
    )
    reload: bool = Field(default=False, description="Enable auto-reload")
    title: str = Field(default="Novel Studio API", description="API title")
    version: str = Field(default_factory=_package_version, description="API version")
    docs_url: str | None = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str | None = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str | None = Field(
        default="/openapi.json", description="OpenAPI schema URL"
    )


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = _settings_config(
        env_prefix="SECURITY_",
        populate_by_name=True,
    )

    secret_key: str = Field(
        default=DEFAULT_SECRET_KEY,
        min_length=16,
        description="Local session security secret",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:4173",
            "http://localhost:8000",
        ],
        description=(
            "Allowed CORS origins. "
            "Production deployments must explicitly set SECURITY_CORS_ORIGINS."
        ),
        validation_alias=AliasChoices(
            "SECURITY_CORS_ORIGINS",
            "CORS_ALLOWED_ORIGINS",
            "CORS_ORIGINS",
        ),
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow CORS credentials",
        validation_alias=AliasChoices(
            "SECURITY_CORS_ALLOW_CREDENTIALS",
            "CORS_ALLOW_CREDENTIALS",
        ),
    )
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "Accept",
            "Origin",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
        description="Allowed CORS headers",
    )
    rate_limit: str = Field(default="5/minute", description="Rate limit string")
    rate_limit_burst: int = Field(
        default=5, ge=1, le=100, description="Rate limit burst"
    )
    trusted_proxies: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description=(
            "Trusted proxy IP addresses or CIDR networks. "
            "When set, X-Forwarded-For is parsed for requests coming from these proxies."
        ),
        validation_alias=AliasChoices(
            "SECURITY_TRUSTED_PROXIES",
            "TRUSTED_PROXIES",
        ),
    )

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit(cls, v: str) -> str:
        """Validate that the rate limit string is parseable."""
        from src.shared.infrastructure.rate_limit import parse_rate_limit

        parse_rate_limit(v)
        return v

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

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v: Any) -> list[str]:
        """Parse trusted proxies from string or list."""
        if isinstance(v, str):
            return [proxy.strip() for proxy in v.split(",") if proxy.strip()]
        return v if isinstance(v, list) else []


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""

    model_config = _settings_config(env_prefix="LLM_")

    provider: Literal["mock", "dashscope", "openai_compatible"] = Field(
        default="mock",
        description="LLM provider name",
    )
    model: str = Field(default="studio-copilot-v1", description="LLM model name")
    api_key: str | None = Field(
        default=None,
        description="API key for OpenAI-compatible providers",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL",
        validation_alias=AliasChoices("LLM_API_BASE", "OPENAI_API_BASE"),
    )
    dashscope_api_key: str | None = Field(
        default=None,
        description="DashScope API key",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY"),
    )
    dashscope_api_base: str | None = Field(
        default=None,
        description="DashScope API base URL",
        validation_alias=AliasChoices("DASHSCOPE_API_BASE"),
    )
    dashscope_model: str | None = Field(
        default=None,
        description="DashScope model override",
        validation_alias=AliasChoices("DASHSCOPE_MODEL"),
    )
    dashscope_transport_mode: Literal[
        "text_generation", "multimodal_generation", "responses"
    ] = Field(
        default="multimodal_generation",
        description="DashScope native transport mode",
        validation_alias=AliasChoices("DASHSCOPE_TRANSPORT_MODE"),
    )
    dashscope_review_model: str | None = Field(
        default=None,
        description="DashScope review model override",
        validation_alias=AliasChoices("DASHSCOPE_REVIEW_MODEL"),
    )
    openai_compatible_model: str | None = Field(
        default=None,
        description="OpenAI-compatible model override",
        validation_alias=AliasChoices("OPENAI_COMPATIBLE_MODEL"),
    )
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
    def resolved_api_key(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str | None:
        if provider_name == "dashscope":
            return self.dashscope_api_key
        if provider_name == "openai_compatible":
            return self.api_key
        return None

    def resolved_api_base(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str | None:
        if provider_name == "dashscope":
            return self.dashscope_api_base or "https://dashscope.aliyuncs.com/api/v1"
        if provider_name == "openai_compatible":
            return self.api_base or "https://api.openai.com/v1"
        return None

    def resolved_model(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str:
        if provider_name == "dashscope":
            return self.dashscope_model or self.model or "qwen3.5-flash"
        if provider_name == "openai_compatible":
            return self.openai_compatible_model or self.model or "gpt-4o-mini"
        return self.model or "deterministic-story-v1"

    def resolved_review_model(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str:
        if provider_name == "dashscope":
            return self.dashscope_review_model or self.resolved_model("dashscope")
        return self.resolved_model(provider_name)

    def resolved_dashscope_transport_mode(
        self,
    ) -> Literal["text_generation", "multimodal_generation", "responses"]:
        return self.dashscope_transport_mode


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
    metrics_enabled: bool = Field(default=False, description="Enable Prometheus metrics")
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
        if not self.security.secret_key or self.security.secret_key == DEFAULT_SECRET_KEY:
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
