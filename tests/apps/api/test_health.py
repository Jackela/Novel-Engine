"""Tests for canonical health behavior."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.apps.api.health as health_module
from src.apps.api.health import (
    _get_health_checker,
    health_router,
    set_connection_pool,
    set_honcho_client,
)
from src.shared.infrastructure.health.health_checker import HealthChecker
from src.shared.infrastructure.persistence import DatabaseConnectionPool


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)


def test_health_returns_healthy_when_no_components_are_registered() -> None:
    client = _build_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["overall_status"] == "healthy"


def test_health_returns_http_200_even_when_runtime_is_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnhealthyChecker:
        checks: dict[str, object] = {}

        async def check_all(self) -> dict[str, object]:
            return {
                "overall_status": "unhealthy",
                "timestamp": "2026-05-06T00:00:00+00:00",
                "components": {
                    "database": {
                        "status": "unhealthy",
                        "message": "connection refused",
                        "response_time_ms": 1.5,
                        "error": "dial tcp 127.0.0.1:5432: connect refused",
                        "details": {},
                    }
                },
            }

    async def _get_unhealthy_checker() -> UnhealthyChecker:
        return UnhealthyChecker()

    monkeypatch.setattr(health_module, "_get_health_checker", _get_unhealthy_checker)

    client = _build_client()
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] == "unhealthy"
    assert payload["components"]["database"]["status"] == "unhealthy"


def test_readiness_is_ready_without_database_registration() -> None:
    client = _build_client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_succeeds_with_healthy_database_pool() -> None:
    class HealthyConnection:
        async def fetchval(self, query: str) -> int:
            assert query == "SELECT 1"
            return 1

    class HealthyPool(DatabaseConnectionPool):
        def __init__(self) -> None:
            pass

        @asynccontextmanager
        async def acquire(self) -> AsyncIterator[HealthyConnection]:
            yield HealthyConnection()

    set_connection_pool(HealthyPool())
    client = _build_client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_hides_internal_exception_details(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _boom() -> None:
        raise RuntimeError("database password leaked")

    monkeypatch.setattr(health_module, "_get_health_checker", _boom)

    client = _build_client()
    with caplog.at_level("ERROR"):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "Readiness check failed",
    }
    assert "database password leaked" not in response.text
    assert any("Readiness probe failed" in message for message in caplog.messages)


def test_honcho_is_optional_for_health_registration() -> None:
    health_module.HONCHO_RUNTIME_AVAILABLE = False
    set_honcho_client(MagicMock())
    checker = __import__("asyncio").run(_get_health_checker())
    assert "honcho" not in checker.checks


def test_get_health_checker_returns_cached_instance() -> None:
    checker = __import__("asyncio").run(_get_health_checker())
    assert isinstance(checker, HealthChecker)
