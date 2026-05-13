"""CORS configuration derived from application settings."""

from __future__ import annotations

from typing import TypedDict

from src.shared.infrastructure.config.settings import (
    NovelEngineSettings,
    get_settings,
)


class CorsConfig(TypedDict):
    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]
    expose_headers: list[str]
    max_age: int


def get_cors_config(settings: NovelEngineSettings | None = None) -> CorsConfig:
    """Return FastAPI CORS middleware configuration."""
    resolved_settings = settings or get_settings()
    return {
        "allow_origins": list(resolved_settings.security.cors_origins),
        "allow_credentials": resolved_settings.security.cors_allow_credentials,
        "allow_methods": list(resolved_settings.security.cors_allow_methods),
        "allow_headers": list(resolved_settings.security.cors_allow_headers),
        "expose_headers": [
            "X-Request-ID",
            "X-Total-Count",
        ],
        "max_age": 600,
    }


def get_cors_origins(settings: NovelEngineSettings | None = None) -> list[str]:
    """Get list of allowed CORS origins."""
    return list(get_cors_config(settings)["allow_origins"])


def is_origin_allowed(
    origin: str,
    settings: NovelEngineSettings | None = None,
) -> bool:
    """Check if an origin is allowed by the configured CORS policy."""
    allowed_origins = get_cors_origins(settings)
    if "*" in allowed_origins:
        return True

    if origin in allowed_origins:
        return True

    for allowed in allowed_origins:
        if allowed.endswith(":*") and origin.startswith(allowed[:-1]):
            return True

    return False
