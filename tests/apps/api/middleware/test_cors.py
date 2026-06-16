from __future__ import annotations

import pytest

from src.apps.api.middleware.cors import (
    get_cors_config,
    get_cors_origins,
    is_origin_allowed,
)
from src.shared.infrastructure.config.settings import reset_settings


def test_default_cors_config_includes_local_development_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    reset_settings()

    config = get_cors_config()

    assert "http://localhost:5173" in config["allow_origins"]
    assert config["allow_credentials"] is True
    assert "Authorization" in config["allow_headers"]
    assert "X-CSRF-Token" in config["allow_headers"]
    assert "X-Request-ID" in config["expose_headers"]


def test_cors_config_rejects_wildcards_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com, *, http://localhost:*",
    )
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_SECRET_KEY", "production-secret-key-32-characters")
    monkeypatch.setenv("DB_URL", "sqlite:///./data/novel-engine.sqlite3")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "false")
    monkeypatch.setenv("API_DOCS_URL", "/internal/docs")
    monkeypatch.setenv("API_REDOC_URL", "/internal/redoc")
    monkeypatch.setenv("API_OPENAPI_URL", "/internal/openapi.json")
    reset_settings()

    with pytest.raises(ValueError, match="Production CORS origins"):
        get_cors_config()


def test_origin_allowance_supports_exact_wildcard_and_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com,http://localhost:*",
    )
    monkeypatch.setenv("APP_ENVIRONMENT", "development")
    reset_settings()

    assert get_cors_origins() == [
        "https://app.example.com",
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8000",
    ]
    assert is_origin_allowed("https://app.example.com") is True
    assert is_origin_allowed("http://localhost:5173") is True
    assert is_origin_allowed("http://localhost:4173") is True
    assert is_origin_allowed("https://evil.example.com") is False


def test_wildcard_origin_allows_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("APP_ENVIRONMENT", "development")
    reset_settings()

    assert is_origin_allowed("https://anywhere.example.com") is True
