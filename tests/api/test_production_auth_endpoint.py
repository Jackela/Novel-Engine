#!/usr/bin/env python3
"""
Production auth endpoint validation for query/body credential handling.
"""

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _load_production_app(monkeypatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-bytes-minimum-0001")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-32-bytes-minimum-0001")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")

    if "production_api_server" in sys.modules:
        module = importlib.reload(sys.modules["production_api_server"])
    else:
        module = importlib.import_module("production_api_server")

    return TestClient(module.app)


@pytest.fixture
def client(monkeypatch):
    return _load_production_app(monkeypatch)


def test_auth_rejects_query_credentials(client):
    response = client.post(
        "/auth/token?username=admin&password=admin-password",
        json={"username": "admin", "password": "admin-password"},
    )
    assert response.status_code == 400
    assert "Credentials must be sent" in response.json()["detail"]


def test_auth_accepts_body_credentials(client):
    response = client.post(
        "/auth/token",
        json={"username": "admin", "password": "admin-password"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
