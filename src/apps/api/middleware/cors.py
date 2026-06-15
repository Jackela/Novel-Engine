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


# Ports that are expanded from a localhost wildcard such as ``http://localhost:*``.
# Starlette's CORSMiddleware does not understand ``:*``, so we materialise them.
_LOCALHOST_WILDCARD_PORTS = (5173, 4173, 8000)


def _expand_wildcard_origin(origin: str) -> list[str]:
    """Expand localhost/127.0.0.1 ``:*`` placeholders into concrete ports."""
    if not origin.endswith(":*"):
        return [origin]
    prefix = origin[:-2]
    if "localhost" not in prefix and "127.0.0.1" not in prefix:
        return [origin]
    return [f"{prefix}:{port}" for port in _LOCALHOST_WILDCARD_PORTS]


def get_cors_config(settings: NovelEngineSettings | None = None) -> CorsConfig:
    """Return FastAPI CORS middleware configuration."""
    resolved_settings = settings or get_settings()
    allow_origins: list[str] = []
    for origin in resolved_settings.security.cors_origins:
        allow_origins.extend(_expand_wildcard_origin(origin))
    return {
        "allow_origins": allow_origins,
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
