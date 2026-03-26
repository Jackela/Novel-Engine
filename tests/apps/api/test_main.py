"""Tests for the canonical FastAPI application."""

from __future__ import annotations


def test_root_endpoint_exposes_canonical_metadata(canonical_client) -> None:
    response = canonical_client.get("/")
    assert response.status_code == 200
    assert response.json()["api_base"] == "/api/v1"


def test_docs_and_openapi_are_available(canonical_client) -> None:
    docs_response = canonical_client.get("/docs")
    openapi_response = canonical_client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "Novel Engine API"


def test_versioning_endpoint_and_headers_are_present(canonical_client) -> None:
    response = canonical_client.get("/api/versions")
    assert response.status_code == 200
    assert response.headers["x-api-version"] == "1.0"
    assert response.headers["x-supported-versions"] == "1.0"
    assert response.json()["current_version"] == "1.0"
    assert response.json()["supported_versions"] == ["1.0"]


def test_health_and_version_endpoints_are_available(canonical_client) -> None:
    health_response = canonical_client.get("/health")
    assert health_response.status_code in {200, 503}
    assert "overall_status" in health_response.json()

    assert canonical_client.get("/health/live").json()["status"] == "alive"
    readiness_response = canonical_client.get("/health/ready")
    assert readiness_response.status_code in {200, 503}
    assert "status" in readiness_response.json()

    version_response = canonical_client.get("/version")
    assert version_response.status_code == 200
    assert "version" in version_response.json()


def test_guest_dashboard_and_orchestration_flow(canonical_client) -> None:
    guest_response = canonical_client.post("/api/v1/guest/session")
    assert guest_response.status_code == 200
    workspace_id = guest_response.json()["workspace_id"]
    assert isinstance(workspace_id, str)
    assert workspace_id

    dashboard_response = canonical_client.get("/api/v1/dashboard/status")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    dashboard_data = dashboard_payload.get("data", dashboard_payload)
    available_characters = dashboard_data["runtime"]["available_characters"]
    assert isinstance(available_characters, list)
    assert available_characters

    start_response = canonical_client.post(
        "/api/v1/dashboard/orchestration/start",
        json={"character_names": available_characters[:1], "total_turns": 2},
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    start_data = start_payload.get("data", start_payload)
    assert start_data["status"] == "running"

    status_response = canonical_client.get("/api/v1/dashboard/orchestration")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    status_data = status_payload.get("data", status_payload)
    assert status_data["status"] in {"running", "paused", "stopped", "idle"}

    pause_response = canonical_client.post("/api/v1/dashboard/orchestration/pause")
    assert pause_response.status_code == 200
    pause_payload = pause_response.json()
    pause_data = pause_payload.get("data", pause_payload)
    assert pause_data["status"] == "paused"

    stop_response = canonical_client.post("/api/v1/dashboard/orchestration/stop")
    assert stop_response.status_code == 200
    stop_payload = stop_response.json()
    stop_data = stop_payload.get("data", stop_payload)
    assert stop_data["status"] in {"stopped", "idle"}


def test_invalid_orchestration_rejects_unknown_character(canonical_client) -> None:
    canonical_client.post("/api/v1/guest/session")
    response = canonical_client.post(
        "/api/v1/dashboard/orchestration/start",
        json={"character_names": ["does-not-exist"], "total_turns": 1},
    )
    assert response.status_code == 400


def test_auth_routes_work_with_canonical_in_memory_dependencies(
    canonical_client,
) -> None:
    register_response = canonical_client.post(
        "/api/v1/auth/register",
        json={
            "email": "writer@example.com",
            "username": "writer",
            "password": "supersecret",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["username"] == "writer"

    login_response = canonical_client.post(
        "/api/v1/auth/login",
        json={"username": "writer", "password": "supersecret"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_response = canonical_client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "writer"

    refresh_response = canonical_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["token_type"] == "bearer"

    logout_response = canonical_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Successfully logged out"
