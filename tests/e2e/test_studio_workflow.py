"""End-to-end workflow test for the Novel Studio API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_guest_full_project_workflow(canonical_client: TestClient) -> None:
    """Exercise a guest session through project, document, review, export, and deletion."""
    session = canonical_client.post("/api/session/guest")
    assert session.status_code == 201
    assert session.json()["kind"] == "guest"

    created = canonical_client.post(
        "/api/projects",
        json={"title": "E2E Story", "description": "End-to-end workflow test"},
    )
    assert created.status_code == 201
    project = created.json()
    document = project["documents"][0]

    saved = canonical_client.put(
        f"/api/projects/{project['id']}/documents/{document['id']}",
        json={
            "content_markdown": "# Chapter 1\n\nThe lighthouse went dark.",
            "base_revision_id": document["current_revision_id"],
            "metadata": {"source": "e2e"},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["content_markdown"] == "# Chapter 1\n\nThe lighthouse went dark."

    review = canonical_client.post(f"/api/projects/{project['id']}/reviews")
    assert review.status_code == 201
    assert "id" in review.json()

    export = canonical_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"format": "markdown"},
    )
    assert export.status_code == 201
    download = canonical_client.get(export.json()["download_url"])
    assert download.status_code == 200
    assert b"The lighthouse went dark." in download.content

    deleted = canonical_client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 204
    assert canonical_client.get(f"/api/projects/{project['id']}").status_code == 404
