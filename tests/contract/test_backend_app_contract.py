"""Contracts for the canonical backend application."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.routing import APIRoute


def _route_paths(app) -> set[str]:
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def _find_route(paths: set[str], suffix: str) -> str | None:
    for path in sorted(paths):
        if path.endswith(suffix):
            return path
    return None


def _find_orchestration_status_path(paths: set[str]) -> str | None:
    return _find_route(paths, "/orchestration/status") or _find_route(
        paths, "/dashboard/orchestration"
    )


def test_canonical_app_mounts_core_routes(canonical_app) -> None:
    paths = _route_paths(canonical_app)

    assert "/health" in paths
    assert "/version" in paths

    api_v1_paths = {path for path in paths if path.startswith("/api/v1/")}
    assert api_v1_paths, "canonical app must expose versioned API routes"
    assert any(path.startswith("/api/v1/auth/") for path in api_v1_paths)
    assert any(path.startswith("/api/v1/knowledge") for path in api_v1_paths)
    assert any(path.startswith("/api/v1/world/") for path in api_v1_paths)


def test_guest_session_contract(canonical_app, canonical_client) -> None:
    paths = _route_paths(canonical_app)
    guest_path = _find_route(paths, "/guest/session")

    assert guest_path is not None, "guest session endpoint must be mounted"

    first_response = canonical_client.post(guest_path)
    assert first_response.status_code == 200
    assert "set-cookie" in first_response.headers

    first_payload = first_response.json()
    assert set(first_payload) >= {"workspace_id", "created"}
    assert isinstance(first_payload["workspace_id"], str)
    assert first_payload["workspace_id"]
    assert first_payload["created"] is True

    second_response = canonical_client.post(guest_path)
    assert second_response.status_code == 200

    second_payload = second_response.json()
    assert second_payload["workspace_id"] == first_payload["workspace_id"]
    assert second_payload["created"] is False


def test_orchestration_contract_shape_when_mounted(
    canonical_app,
    canonical_client,
) -> None:
    paths = _route_paths(canonical_app)

    start_path = _find_route(paths, "/orchestration/start")
    status_path = _find_orchestration_status_path(paths)
    stop_path = _find_route(paths, "/orchestration/stop")

    if not any((start_path, status_path, stop_path)):
        pytest.skip("canonical app does not expose orchestration routes yet")

    assert start_path is not None
    assert status_path is not None
    assert stop_path is not None

    openapi = canonical_client.get("/openapi.json")
    assert openapi.status_code == 200

    schema = openapi.json()["paths"]

    start_operation = schema[start_path]["post"]
    status_operation = schema[status_path]["get"]
    stop_operation = schema[stop_path]["post"]

    for operation in (start_operation, status_operation, stop_operation):
        responses: dict[str, Any] = operation["responses"]
        assert "200" in responses
        assert "content" in responses["200"]
        assert "application/json" in responses["200"]["content"]
        assert "schema" in responses["200"]["content"]["application/json"]
