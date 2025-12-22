from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class APISettings:
    cors_allow_origins: List[str]

    cookie_name: str
    refresh_cookie_name: str
    csrf_cookie_name: str
    guest_session_cookie_name: str

    cookie_secure: bool
    cookie_httponly: bool
    cookie_samesite: str
    cookie_max_age_seconds: int
    refresh_cookie_max_age_seconds: int
    csrf_cookie_max_age_seconds: int

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int

    guest_workspace_ttl_days: int

    @staticmethod
    def from_env() -> "APISettings":
        cookie_secure = os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
        jwt_secret_key = os.getenv(
            "JWT_SECRET_KEY", os.getenv("SECRET_KEY", "development-secret-key-change-in-production")
        )

        ttl_days_raw = os.getenv("GUEST_WORKSPACE_TTL_DAYS", "30").strip()
        try:
            ttl_days = int(ttl_days_raw)
            if ttl_days <= 0:
                raise ValueError
        except ValueError:
            ttl_days = 30

        return APISettings(
            cors_allow_origins=[
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
            cookie_name="access_token",
            refresh_cookie_name="refresh_token",
            csrf_cookie_name="csrf_token",
            guest_session_cookie_name="guest_session",
            cookie_secure=cookie_secure,
            cookie_httponly=True,
            cookie_samesite="lax",
            cookie_max_age_seconds=3600 * 24,
            refresh_cookie_max_age_seconds=3600 * 24 * 30,
            csrf_cookie_max_age_seconds=3600 * 24,
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm="HS256",
            jwt_access_token_expire_minutes=15,
            guest_workspace_ttl_days=ttl_days,
        )

