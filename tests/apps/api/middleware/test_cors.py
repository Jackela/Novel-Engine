from __future__ import annotations

import pytest

from src.apps.api.middleware.cors import (
    get_cors_config,
    get_cors_origins,
    is_origin_allowed,
)


def test_default_cors_config_includes_local_development_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    config = get_cors_config()

    assert "http://localhost:5173" in config["allow_origins"]
    assert config["allow_credentials"] is True
    assert "Authorization" in config["allow_headers"]
    assert "X-Request-ID" in config["expose_headers"]


def test_cors_config_reads_env_and_filters_production_wildcards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com, *, http://localhost:*",
    )
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "false")

    config = get_cors_config()

    assert config["allow_origins"] == ["https://app.example.com"]
    assert config["allow_credentials"] is False


def test_origin_allowance_supports_exact_wildcard_and_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com,http://localhost:*",
    )
    monkeypatch.setenv("APP_ENVIRONMENT", "development")

    assert get_cors_origins() == [
        "https://app.example.com",
        "http://localhost:*",
    ]
    assert is_origin_allowed("https://app.example.com") is True
    assert is_origin_allowed("http://localhost:5173") is True
    assert is_origin_allowed("https://evil.example.com") is False


def test_wildcard_origin_allows_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("APP_ENVIRONMENT", "development")

    assert is_origin_allowed("https://anywhere.example.com") is True
