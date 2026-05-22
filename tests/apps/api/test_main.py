"""Tests for the canonical FastAPI application."""

from __future__ import annotations

import time
from typing import Any, cast


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


def test_root_endpoint_exposes_canonical_metadata(
    canonical_client: Any,
) -> None:
    response = canonical_client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_base"] == "/api"
    assert "story" not in payload
    assert "version" + "ing" not in payload
    assert payload["workspaces"] == "/api/workspaces"


def test_docs_and_openapi_are_available(canonical_client: Any) -> None:
    docs_response = canonical_client.get("/docs")
    openapi_response = canonical_client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "Novel Engine API"


def test_api_version_endpoint_and_headers_are_removed(
    canonical_client: Any,
) -> None:
    response = canonical_client.get("/api/" + "versions")
    assert response.status_code == 404
    assert "x-api-" + "version" not in response.headers
    assert "x-supported-" + "versions" not in response.headers


def test_health_and_version_endpoints_are_available(
    canonical_client: Any,
) -> None:
    health_response = canonical_client.get("/health")
    assert health_response.status_code == 200
    assert "overall_status" in health_response.json()

    assert canonical_client.get("/health/live").json()["status"] == "alive"
    readiness_response = canonical_client.get("/health/ready")
    assert readiness_response.status_code in {200, 503}
    assert "status" in readiness_response.json()

    version_response = canonical_client.get("/version")
    assert version_response.status_code == 200
    assert "version" in version_response.json()


def test_guest_workspace_flow(canonical_client: Any) -> None:
    guest_response = canonical_client.post("/api/guest/session")
    assert guest_response.status_code == 200
    workspace_id = guest_response.json()["workspace_id"]
    assert isinstance(workspace_id, str)
    assert workspace_id

    create_response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "guest-story",
            "title": "Guest Story",
            "genre": "fantasy",
            "premise": "A courier finds a map that rewrites the kingdom's borders.",
            "target_chapters": 3,
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["workspace_id"] == "guest-story"

    run_response = canonical_client.post(
        "/api/workspaces/guest-story/jobs",
        json={"operation": "run", "target_chapters": 3, "provider": "mock"},
    )
    assert run_response.status_code == 202
    run_job = _wait_for_job(
        canonical_client,
        "guest-story",
        str(run_response.json()["job_id"]),
    )
    assert run_job["status"] == "completed"

    review_response = canonical_client.post(
        "/api/workspaces/guest-story/jobs",
        json={"operation": "review"},
    )
    assert review_response.status_code == 202
    review_job = _wait_for_job(
        canonical_client,
        "guest-story",
        str(review_response.json()["job_id"]),
    )
    assert review_job["result"]["result_type"] == "review"
    assert review_job["result"]["review"]["export_blocked"] is False

    export_response = canonical_client.post(
        "/api/workspaces/guest-story/jobs",
        json={"operation": "export"},
    )
    assert export_response.status_code == 202
    export_job = _wait_for_job(
        canonical_client,
        "guest-story",
        str(export_response.json()["job_id"]),
    )
    assert export_job["result"]["result_type"] == "export"
    assert export_job["result"]["export"]["filename"] == "manuscript.md"


def test_auth_routes_work_with_canonical_in_memory_dependencies(
    canonical_client: Any,
) -> None:
    register_response = canonical_client.post(
        "/api/auth/register",
        json={
            "email": "writer@example.com",
            "username": "writer",
            "password": "supersecret",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["username"] == "writer"

    login_response = canonical_client.post(
        "/api/auth/login",
        json={"username": "writer", "password": "supersecret"},
    )
    assert login_response.status_code == 200
    session = login_response.json()
    assert "access_token" not in session
    assert "refresh_token" not in session
    assert "novel_engine_access=" in login_response.headers["set-cookie"]

    me_response = canonical_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "writer"

    refresh_response = canonical_client.post("/api/auth/refresh", json={})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["workspace_id"] == session["workspace_id"]
    assert "novel_engine_refresh=" in refresh_response.headers["set-cookie"]

    logout_response = canonical_client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Successfully logged out"

    refresh_after_logout = canonical_client.post("/api/auth/refresh", json={})
    assert refresh_after_logout.status_code == 401
