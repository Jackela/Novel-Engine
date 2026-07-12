from __future__ import annotations

import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_live_ready_and_version(
    canonical_app: FastAPI,
    canonical_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setenv("BUILD_SHA", "build-health-test")

    # When
    live = canonical_client.get("/health/live")
    ready = canonical_client.get("/health/ready")
    health = canonical_client.get("/health")
    version = canonical_client.get("/version")

    # Then
    assert live.status_code == 200
    assert live.json() == {"status": "alive", "reason": None}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert health.status_code == 200
    assert health.json()["overall_status"] == "healthy"
    assert health.json()["components"]["database"]["message"] == "SQLite ready"
    assert version.status_code == 200
    assert version.json() == {
        "version": canonical_app.state.settings.project_version,
        "name": canonical_app.state.settings.project_name,
        "python_version": sys.version.split()[0],
        "environment": "testing",
        "build": "build-health-test",
    }


def test_readiness_reports_failed_database_health_check(
    canonical_app: FastAPI,
    canonical_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def unhealthy() -> bool:
        return False

    monkeypatch.setattr(
        canonical_app.state.studio_store.repository,
        "health_check",
        unhealthy,
    )

    # When
    response = canonical_client.get("/health/ready")

    # Then
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "database health check failed",
    }


def test_health_reports_database_runtime_error(
    canonical_app: FastAPI,
    canonical_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def raise_runtime_error() -> bool:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        canonical_app.state.studio_store.repository,
        "health_check",
        raise_runtime_error,
    )

    # When
    response = canonical_client.get("/health")

    # Then
    assert response.status_code == 200
    assert response.json()["overall_status"] == "unhealthy"
    assert response.json()["components"]["database"]["error"] == "database unavailable"
