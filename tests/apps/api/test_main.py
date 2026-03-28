"""Tests for the canonical FastAPI application."""

from __future__ import annotations

from typing import Any


def test_root_endpoint_exposes_canonical_metadata(
    canonical_client: Any,
) -> None:
    response = canonical_client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_base"] == "/api/v1"
    assert payload["story"] == "/api/v1/story"
    assert payload["story_pipeline"] == "/api/v1/story/pipeline"


def test_docs_and_openapi_are_available(canonical_client: Any) -> None:
    docs_response = canonical_client.get("/docs")
    openapi_response = canonical_client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "Novel Engine API"


def test_versioning_endpoint_and_headers_are_present(
    canonical_client: Any,
) -> None:
    response = canonical_client.get("/api/versions")
    assert response.status_code == 200
    assert response.headers["x-api-version"] == "1.0"
    assert response.headers["x-supported-versions"] == "1.0"
    assert response.json()["current_version"] == "1.0"
    assert response.json()["supported_versions"] == ["1.0"]


def test_health_and_version_endpoints_are_available(
    canonical_client: Any,
) -> None:
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


def test_guest_story_pipeline_flow(canonical_client: Any) -> None:
    guest_response = canonical_client.post("/api/v1/guest/session")
    assert guest_response.status_code == 200
    workspace_id = guest_response.json()["workspace_id"]
    assert isinstance(workspace_id, str)
    assert workspace_id

    create_response = canonical_client.post(
        "/api/v1/story",
        json={
            "title": "Guest Story",
            "genre": "fantasy",
            "premise": "A courier finds a map that rewrites the kingdom's borders.",
            "target_chapters": 3,
        },
    )
    assert create_response.status_code == 200
    story = create_response.json()["story"]
    assert story["author_id"] == workspace_id

    blueprint_response = canonical_client.post(f"/api/v1/story/{story['id']}/blueprint")
    assert blueprint_response.status_code == 200

    outline_response = canonical_client.post(f"/api/v1/story/{story['id']}/outline")
    assert outline_response.status_code == 200

    draft_response = canonical_client.post(
        f"/api/v1/story/{story['id']}/draft",
        json={"target_chapters": 3},
    )
    assert draft_response.status_code == 200
    drafted_story = draft_response.json()["story"]
    assert drafted_story["chapter_count"] == 3

    review_response = canonical_client.post(f"/api/v1/story/{story['id']}/review")
    assert review_response.status_code == 200
    review_report = review_response.json()["report"]
    assert review_report["ready_for_publish"] is True

    revise_response = canonical_client.post(f"/api/v1/story/{story['id']}/revise")
    assert revise_response.status_code == 200
    assert revise_response.json()["revision_notes"]

    export_response = canonical_client.post(f"/api/v1/story/{story['id']}/export")
    assert export_response.status_code == 200
    assert export_response.json()["export"]["story"]["id"] == story["id"]

    publish_response = canonical_client.post(f"/api/v1/story/{story['id']}/publish")
    assert publish_response.status_code == 200
    published_story = publish_response.json()["story"]
    assert published_story["status"] == "active"


def test_auth_routes_work_with_canonical_in_memory_dependencies(
    canonical_client: Any,
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

    create_response = canonical_client.post(
        "/api/v1/story",
        json={
            "title": "Auth Story",
            "genre": "mystery",
            "premise": "A locked room case turns into a conspiracy across the harbor.",
            "target_chapters": 3,
            "author_id": tokens["workspace_id"],
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["story"]["author_id"] == tokens["workspace_id"]

    refresh_response = canonical_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["token_type"] == "bearer"

    logout_response = canonical_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Successfully logged out"
