"""Contracts for the canonical backend application."""

from __future__ import annotations

import time
from typing import Any, cast

from fastapi.routing import APIRoute


def _route_paths(app: Any) -> set[str]:
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def _wait_for_job(canonical_client: Any, workspace_id: str, job_id: str) -> dict[str, Any]:
    for _ in range(100):
        response = canonical_client.get(
            f"/api/workspaces/{workspace_id}/jobs/{job_id}"
        )
        assert response.status_code == 200
        payload = cast(dict[str, Any], response.json())
        if payload["status"] in {"completed", "failed", "interrupted"}:
            return payload
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not finish")


def test_canonical_app_mounts_core_routes(canonical_app: Any) -> None:
    paths = _route_paths(canonical_app)

    assert "/health" in paths
    assert "/version" in paths

    api_paths = {path for path in paths if path.startswith("/api/")}
    assert api_paths, "canonical app must expose API routes"
    assert any(path.startswith("/api/auth/") for path in api_paths)
    assert any(path.startswith("/api/knowledge") for path in api_paths)
    assert "/api/providers" in api_paths
    assert "/api/workspaces" in api_paths
    assert "/api/workspaces/{workspace_id}/jobs" in api_paths
    assert "/api/dashboard/status" not in api_paths
    assert "/api/world/rumors/propagate" not in api_paths
    assert not any(path.startswith("/api/" + "v") for path in api_paths)
    assert not any(path.startswith("/api/") and "/story" in path for path in api_paths)


def test_guest_session_contract(
    canonical_app: Any,
    canonical_client: Any,
) -> None:
    paths = _route_paths(canonical_app)
    guest_path = next(path for path in paths if path.endswith("/guest/session"))

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


def test_workspace_contract_shape_when_mounted(
    canonical_app: Any,
    canonical_client: Any,
) -> None:
    paths = _route_paths(canonical_app)
    workspace_path = next(path for path in paths if path.endswith("/workspaces"))
    job_path = next(path for path in paths if path.endswith("/workspaces/{workspace_id}/jobs"))

    openapi = canonical_client.get("/openapi.json")
    assert openapi.status_code == 200

    schema = openapi.json()["paths"]
    create_operation = schema[workspace_path]["post"]
    job_operation = schema[job_path]["post"]
    responses: dict[str, Any] = create_operation["responses"]
    assert "201" in responses
    assert "application/json" in responses["201"]["content"]

    responses = job_operation["responses"]
    assert "202" in responses
    assert "application/json" in responses["202"]["content"]

    canonical_client.post("/api/guest/session")
    create_response = canonical_client.post(
        workspace_path,
        json={
            "workspace_id": "contract-story",
            "title": "Contract Story",
            "genre": "fantasy",
            "premise": "A recovered relic forces three rivals into the same lost city.",
            "target_chapters": 3,
        },
    )
    assert create_response.status_code == 201
    workspace_payload = create_response.json()
    assert workspace_payload["story"]["title"] == "Contract Story"
    assert workspace_payload["chapters"] == []

    response = canonical_client.post(
        "/api/workspaces/contract-story/jobs",
        json={"operation": "run", "target_chapters": 3, "provider": "mock"},
    )
    assert response.status_code == 202
    job_payload = _wait_for_job(
        canonical_client,
        "contract-story",
        str(response.json()["job_id"]),
    )
    assert job_payload["status"] == "completed"
    assert job_payload["result"]["result_type"] == "run"
    assert job_payload["result"]["review"]["export_blocked"] is False

    status_response = canonical_client.get("/api/workspaces/contract-story")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert len(status_payload["chapters"]) == 3
    assert status_payload["latest_review"]["export_blocked"] is False
