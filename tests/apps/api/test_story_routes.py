"""Tests for the canonical story workflow routes."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _start_guest(canonical_client: Any) -> str:
    response = canonical_client.post("/api/v1/guest/session")
    assert response.status_code == 200
    return str(response.json()["workspace_id"])


def test_story_route_lifecycle(canonical_client: Any) -> None:
    workspace_id = _start_guest(canonical_client)
    create_response = canonical_client.post(
        "/api/v1/story",
        json={
            "title": "Route Story",
            "genre": "adventure",
            "premise": "A guild of mapmakers uncovers a path through a living storm.",
            "target_chapters": 3,
        },
    )
    assert create_response.status_code == 200
    story = create_response.json()["story"]
    story_id = story["id"]

    assert story["author_id"] == workspace_id

    list_response = canonical_client.get("/api/v1/story")
    assert list_response.status_code == 200
    assert list_response.json()["count"] >= 1

    get_response = canonical_client.get(f"/api/v1/story/{story_id}")
    assert get_response.status_code == 200
    assert get_response.json()["story"]["id"] == story_id
    assert get_response.json()["workspace"]["story"]["id"] == story_id

    workspace_response = canonical_client.get(f"/api/v1/story/{story_id}/workspace")
    assert workspace_response.status_code == 200
    assert workspace_response.json()["workspace"]["story"]["id"] == story_id
    assert workspace_response.json()["workspace"]["run_history"] == []
    assert workspace_response.json()["workspace"]["artifact_history"] == []
    assert (
        workspace_response.json()["workspace"]["workspace_context"]["workspace_kind"]
        == "guest"
    )
    assert (
        workspace_response.json()["workspace"]["recommended_next_action"]["action"]
        == "generate_blueprint"
    )
    assert workspace_response.json()["workspace"]["evidence_summary"]["zero_warning"] is True

    blueprint_response = canonical_client.post(f"/api/v1/story/{story_id}/blueprint")
    assert blueprint_response.status_code == 200
    assert blueprint_response.json()["blueprint"]["world_bible"]
    assert blueprint_response.json()["workspace"]["blueprint"]["provider"] == "mock"

    outline_response = canonical_client.post(f"/api/v1/story/{story_id}/outline")
    assert outline_response.status_code == 200
    assert outline_response.json()["outline"]["chapters"]

    draft_response = canonical_client.post(
        f"/api/v1/story/{story_id}/draft",
        json={"target_chapters": 3},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["drafted_chapters"] == 3

    review_response = canonical_client.post(f"/api/v1/story/{story_id}/review")
    assert review_response.status_code == 200
    assert review_response.json()["report"]["ready_for_publish"] is True
    assert (
        review_response.json()["workspace"]["review"]["structural_review"]["metrics"][
            "pacing_score"
        ]
        >= 70
    )

    revise_response = canonical_client.post(f"/api/v1/story/{story_id}/revise")
    assert revise_response.status_code == 200
    assert isinstance(revise_response.json()["revision_notes"], list)
    assert revise_response.json()["report"]["publish_gate_passed"] is True

    export_response = canonical_client.post(f"/api/v1/story/{story_id}/export")
    assert export_response.status_code == 200
    assert export_response.json()["export"]["story"]["id"] == story_id
    assert export_response.json()["workspace"]["export"]["exported_at"]

    publish_response = canonical_client.post(f"/api/v1/story/{story_id}/publish")
    assert publish_response.status_code == 200
    assert publish_response.json()["story"]["status"] == "active"
    assert publish_response.json()["workspace"]["run"]["stages"]
    assert publish_response.json()["workspace"]["run_history"]
    assert publish_response.json()["workspace"]["run_events"]
    assert publish_response.json()["workspace"]["artifact_history"]

    runs_response = canonical_client.get(f"/api/v1/story/{story_id}/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["current_run"]["status"] == "completed"
    assert runs_response.json()["runs"]

    artifacts_response = canonical_client.get(f"/api/v1/story/{story_id}/artifacts")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["current"]["review"]["version"] >= 1
    assert any(
        entry["kind"] == "blueprint"
        for entry in artifacts_response.json()["history"]
    )


def test_story_pipeline_route_builds_complete_story(
    canonical_client: Any,
) -> None:
    _start_guest(canonical_client)
    response = canonical_client.post(
        "/api/v1/story/pipeline",
        json={
            "title": "Pipeline Story",
            "genre": "fantasy",
            "premise": "A trapped city must bargain with a sentient archive to survive.",
            "target_chapters": 3,
            "publish": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["published"] is True
    assert payload["story"]["chapter_count"] == 3
    assert payload["workspace"]["run"]["mode"] == "pipeline"
    assert payload["workspace"]["run_history"]
    assert payload["workspace"]["run_events"]
    assert payload["workspace"]["artifact_history"]
    assert payload["initial_review"]["ready_for_publish"] is True
    assert payload["final_review"]["ready_for_publish"] is True


def test_story_run_resource_executes_pipeline_for_existing_story(
    canonical_client: Any,
) -> None:
    _start_guest(canonical_client)
    create_response = canonical_client.post(
        "/api/v1/story",
        json={
            "title": "Resource Story",
            "genre": "fantasy",
            "premise": "A sealed atlas rewrites each district the moment someone reads it.",
            "target_chapters": 3,
        },
    )
    assert create_response.status_code == 200
    story_id = create_response.json()["story"]["id"]

    run_response = canonical_client.post(
        f"/api/v1/story/{story_id}/runs",
        json={
            "operation": "pipeline",
            "target_chapters": 3,
            "publish": False,
        },
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["operation"] == "pipeline"
    assert payload["run"]["mode"] == "pipeline"
    assert payload["run"]["status"] == "completed"
    assert payload["artifacts"]
    assert payload["latest_snapshot"] is not None
    assert payload["latest_snapshot"]["workspace"]["review"]["ready_for_publish"] is True

    run_id = payload["run"]["run_id"]
    get_run_response = canonical_client.get(f"/api/v1/story/{story_id}/runs/{run_id}")
    assert get_run_response.status_code == 200
    run_payload = get_run_response.json()
    assert run_payload["run"]["run_id"] == run_id
    assert run_payload["events"]
    assert run_payload["latest_snapshot"] is not None
    assert run_payload["stage_snapshots"]
    assert any(artifact["kind"] == "review" for artifact in run_payload["artifacts"])
    assert run_payload["provenance"]["run_id"] == run_id
    assert run_payload["publish_verdict"]["warning_count"] == 0
    assert run_payload["evidence_status"]["zero_warning"] is True


def test_story_routes_enforce_workspace_ownership(
    canonical_app: FastAPI,
) -> None:
    with (
        TestClient(canonical_app, raise_server_exceptions=False) as owner_client,
        TestClient(canonical_app, raise_server_exceptions=False) as other_client,
        TestClient(canonical_app, raise_server_exceptions=False) as guest_client,
    ):
        login_response = owner_client.post(
            "/api/v1/auth/login",
            json={
                "email": "operator@novel.engine",
                "password": "demo-password",
            },
        )
        assert login_response.status_code == 200

        forged_response = owner_client.post(
            "/api/v1/story",
            json={
                "title": "Forged Story",
                "genre": "fantasy",
                "premise": "A false owner tries to cross the author boundary.",
                "target_chapters": 3,
                "author_id": "user-writer",
            },
        )
        assert forged_response.status_code == 403

        create_response = owner_client.post(
            "/api/v1/story",
            json={
                "title": "Private Story",
                "genre": "fantasy",
                "premise": "A hidden archive follows only its real owner.",
                "target_chapters": 3,
            },
        )
        assert create_response.status_code == 200
        story_id = create_response.json()["story"]["id"]

        register_response = other_client.post(
            "/api/v1/auth/register",
            json={
                "email": "writer@example.com",
                "username": "writer",
                "password": "supersecret",
            },
        )
        assert register_response.status_code == 201
        other_login = other_client.post(
            "/api/v1/auth/login",
            json={"username": "writer", "password": "supersecret"},
        )
        assert other_login.status_code == 200

        assert other_client.get(f"/api/v1/story/{story_id}").status_code == 404
        assert (
            other_client.post(f"/api/v1/story/{story_id}/runs", json={}).status_code
            == 404
        )
        assert (
            other_client.get(
                "/api/v1/story",
                params={"author_id": "user-operator"},
            ).status_code
            == 403
        )

        guest_session = guest_client.post("/api/v1/guest/session")
        assert guest_session.status_code == 200
        assert guest_client.get(f"/api/v1/story/{story_id}").status_code == 404
