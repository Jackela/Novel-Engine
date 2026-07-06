from __future__ import annotations

import tomllib
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from ipaddress import IPv4Address
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_SECRET_KEY_PARTS = ("change-me", "in-production", "32-char-long")
DEFAULT_SECRET_KEY = "-".join(_DEFAULT_SECRET_KEY_PARTS)
LOCAL_DOTENV_FILE = ".env.local"


def _package_version() -> str:
    pyproject = Path(__file__).parents[4] / "pyproject.toml"
    if pyproject.is_file():
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(project["project"]["version"])
    try:
        return version("novel-engine")
    except PackageNotFoundError:
        return "0.3.1"


def _settings_config(
    *,
    env_prefix: str,
    env_nested_delimiter: str | None = None,
    validate_default: bool | None = None,
    populate_by_name: bool | None = None,
) -> SettingsConfigDict:
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


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
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
        if not v:
            raise ValueError("Database URL cannot be empty")
        if not v.startswith("sqlite:///"):
            raise ValueError("DB_URL must use the self-hosted SQLite store")
        return v


_DEFAULT_API_HOST = IPv4Address(0).compressed


class APISettings(BaseSettings):
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
        from src.shared.infrastructure.rate_limit import parse_rate_limit

        parse_rate_limit(v)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if isinstance(v, list) else []

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [method.strip() for method in v.split(",") if method.strip()]
        return v if isinstance(v, list) else []

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v if isinstance(v, list) else []

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [proxy.strip() for proxy in v.split(",") if proxy.strip()]
        return v if isinstance(v, list) else []


class LLMSettings(BaseSettings):
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
