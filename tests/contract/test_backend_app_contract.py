"""Contracts for the canonical backend application."""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute


def _route_paths(app: Any) -> set[str]:
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def test_canonical_app_mounts_core_routes(canonical_app: Any) -> None:
    paths = _route_paths(canonical_app)

    assert "/health" in paths
    assert "/version" in paths

    api_v1_paths = {path for path in paths if path.startswith("/api/v1/")}
    assert api_v1_paths, "canonical app must expose versioned API routes"
    assert any(path.startswith("/api/v1/auth/") for path in api_v1_paths)
    assert any(path.startswith("/api/v1/knowledge") for path in api_v1_paths)
    assert any(path.startswith("/api/v1/story") for path in api_v1_paths)
    assert any(path.endswith("/story/{story_id}/workspace") for path in api_v1_paths)
    assert any(path.endswith("/story/{story_id}/runs") for path in api_v1_paths)
    assert any(path.endswith("/story/{story_id}/runs/{run_id}") for path in api_v1_paths)
    assert any(path.endswith("/story/{story_id}/artifacts") for path in api_v1_paths)
    assert "/api/v1/dashboard/status" not in api_v1_paths
    assert "/api/v1/world/rumors/propagate" not in api_v1_paths


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


def test_story_pipeline_contract_shape_when_mounted(
    canonical_app: Any,
    canonical_client: Any,
) -> None:
    paths = _route_paths(canonical_app)
    pipeline_path = next(path for path in paths if path.endswith("/story/pipeline"))

    openapi = canonical_client.get("/openapi.json")
    assert openapi.status_code == 200

    schema = openapi.json()["paths"]
    pipeline_operation = schema[pipeline_path]["post"]
    responses: dict[str, Any] = pipeline_operation["responses"]
    assert "200" in responses
    assert "content" in responses["200"]
    assert "application/json" in responses["200"]["content"]
    assert "schema" in responses["200"]["content"]["application/json"]

    canonical_client.post("/api/v1/guest/session")
    payload = {
        "title": "Contract Story",
        "genre": "fantasy",
        "premise": "A recovered relic forces three rivals into the same lost city.",
        "target_chapters": 3,
        "publish": True,
    }
    response = canonical_client.post(pipeline_path, json=payload)
    assert response.status_code == 200
    story_payload = response.json()
    assert story_payload["published"] is True
    assert story_payload["story"]["title"] == "Contract Story"
    assert story_payload["story"]["chapter_count"] == 3
    assert (
        story_payload["workspace"]["review"]["structural_review"]["metrics"][
            "continuity_score"
        ]
        >= 85
    )
    assert story_payload["workspace"]["review"]["semantic_review"]["metrics"][
        "reader_pull_score"
    ] >= 78
    assert story_payload["final_review"]["ready_for_publish"] is True
