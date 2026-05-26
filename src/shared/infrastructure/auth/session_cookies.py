"""Browser session cookie names and defaults."""

from __future__ import annotations

ACCESS_TOKEN_COOKIE = "novel_engine_access"
REFRESH_TOKEN_COOKIE = "novel_engine_refresh"
REFRESH_TOKEN_PATH = "/api/auth"

__all__ = [
    "ACCESS_TOKEN_COOKIE",
    "REFRESH_TOKEN_COOKIE",
    "REFRESH_TOKEN_PATH",
]
