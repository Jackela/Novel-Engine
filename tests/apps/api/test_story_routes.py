"""Tests for the canonical story workflow routes."""

from __future__ import annotations

from typing import Any


def test_story_route_lifecycle(canonical_client: Any) -> None:
    create_response = canonical_client.post(
        "/api/v1/story",
        json={
            "title": "Route Story",
            "genre": "adventure",
            "premise": "A guild of mapmakers uncovers a path through a living storm.",
            "target_chapters": 3,
            "author_id": "author-route",
        },
    )
    assert create_response.status_code == 200
    story = create_response.json()["story"]
    story_id = story["id"]

    list_response = canonical_client.get("/api/v1/story", params={"author_id": "author-route"})
    assert list_response.status_code == 200
    assert list_response.json()["count"] >= 1

    get_response = canonical_client.get(f"/api/v1/story/{story_id}")
    assert get_response.status_code == 200
    assert get_response.json()["story"]["id"] == story_id

    blueprint_response = canonical_client.post(f"/api/v1/story/{story_id}/blueprint")
    assert blueprint_response.status_code == 200
    assert blueprint_response.json()["blueprint"]["world_bible"]

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

    revise_response = canonical_client.post(f"/api/v1/story/{story_id}/revise")
    assert revise_response.status_code == 200
    assert revise_response.json()["revision_notes"]

    export_response = canonical_client.post(f"/api/v1/story/{story_id}/export")
    assert export_response.status_code == 200
    assert export_response.json()["export"]["story"]["id"] == story_id

    publish_response = canonical_client.post(f"/api/v1/story/{story_id}/publish")
    assert publish_response.status_code == 200
    assert publish_response.json()["story"]["status"] == "active"


def test_story_pipeline_route_builds_complete_story(
    canonical_client: Any,
) -> None:
    response = canonical_client.post(
        "/api/v1/story/pipeline",
        json={
            "title": "Pipeline Story",
            "genre": "fantasy",
            "premise": "A trapped city must bargain with a sentient archive to survive.",
            "target_chapters": 3,
            "publish": True,
            "author_id": "pipeline-author",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["published"] is True
    assert payload["story"]["chapter_count"] == 3
    assert payload["initial_review"]["ready_for_publish"] is True
    assert payload["final_review"]["ready_for_publish"] is True
