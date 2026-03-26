"""
CORS Configuration

Cross-Origin Resource Sharing configuration for FastAPI.
"""

import os
from typing import List


def get_cors_config() -> dict:
    """
    Get CORS configuration from environment variables.

    Returns:
        Dictionary with CORS configuration options.
    """
    # Get allowed origins from environment or use defaults
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")

    if origins_env:
        allow_origins: list[str] = [
            origin.strip() for origin in origins_env.split(",") if origin.strip()
        ]
    else:
        # Default origins for development
        allow_origins = [
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # React development
            "http://localhost:8000",  # FastAPI development
            "http://localhost:8080",  # Vue.js development
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8080",
        ]

    # In production, restrict origins
    if os.getenv("APP_ENVIRONMENT", os.getenv("ENVIRONMENT", "")).lower() == "production":
        # Remove wildcard origins in production
        allow_origins = [
            origin
            for origin in allow_origins
            if origin not in ("*", "http://localhost:*")
        ]

    return {
        "allow_origins": allow_origins,
        "allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower()
        == "true",
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-Total-Count",
        ],
        "max_age": 600,  # 10 minutes
    }


def get_cors_origins() -> List[str]:
    """Get list of allowed CORS origins."""
    return list(get_cors_config()["allow_origins"])


def is_origin_allowed(origin: str) -> bool:
    """
    Check if an origin is allowed.

    Args:
        origin: The origin to check.

    Returns:
        True if origin is allowed, False otherwise.
    """
    allowed_origins = get_cors_origins()

    # Allow all origins
    if "*" in allowed_origins:
        return True

    # Check exact match
    if origin in allowed_origins:
        return True

    # Check wildcard origins (e.g., http://localhost:*)
    for allowed in allowed_origins:
        if allowed.endswith(":*"):
            prefix = allowed[:-1]  # Remove the *
            if origin.startswith(prefix):
                return True

    return False
