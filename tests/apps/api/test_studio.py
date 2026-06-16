from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.shared.infrastructure.config.settings import get_settings


def test_guest_project_revision_conflict_and_export(canonical_client: TestClient) -> None:
    session = canonical_client.post("/api/session/guest")
    assert session.status_code == 201
    assert session.json()["expires_at"]

    created = canonical_client.post(
        "/api/projects",
        json={"title": "API Story", "description": "Contract test"},
    )
    assert created.status_code == 201
    project = created.json()
    document = project["documents"][0]

    saved = canonical_client.put(
        f"/api/projects/{project['id']}/documents/{document['id']}",
        json={
            "content_markdown": "# Chapter 1\n\nAPI revision.",
            "base_revision_id": document["current_revision_id"],
            "metadata": {"source": "test"},
        },
    )
    assert saved.status_code == 200

    conflict = canonical_client.put(
        f"/api/projects/{project['id']}/documents/{document['id']}",
        json={
            "content_markdown": "silent overwrite",
            "base_revision_id": document["current_revision_id"],
            "metadata": {},
        },
    )
    assert conflict.status_code == 409
    assert (
        conflict.json()["detail"]["current_revision_id"]
        == saved.json()["current_revision_id"]
    )

    review = canonical_client.post(f"/api/projects/{project['id']}/reviews")
    export = canonical_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"format": "markdown"},
    )
    assert review.status_code == 201
    assert export.status_code == 201
    download = canonical_client.get(export.json()["download_url"])
    assert download.status_code == 200
    assert b"API revision." in download.content


def test_owner_setup_login_and_path_isolation(canonical_client: TestClient) -> None:
    setup = canonical_client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
    )
    assert setup.status_code == 201
    login = canonical_client.post(
        "/api/session/login",
        json={"username": "owner", "password": "owner-password-123"},
    )
    assert login.status_code == 200
    project = canonical_client.post("/api/projects", json={"title": "Private"}).json()

    other = TestClient(canonical_client.app, raise_server_exceptions=False)
    with other:
        other.post("/api/session/guest")
        assert other.get(f"/api/projects/{project['id']}").status_code == 404


def test_web_import_is_confined_to_data_imports(canonical_client: TestClient) -> None:
    canonical_client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
    )
    canonical_client.post(
        "/api/session/login",
        json={"username": "owner", "password": "owner-password-123"},
    )

    workspace = get_settings().data_dir / "imports" / "safe-workspace"
    workspace.mkdir(parents=True)
    (workspace / "story.yaml").write_text("title: Safe import\n", encoding="utf-8")

    preview = canonical_client.post(
        "/api/imports/preview",
        json={"source": workspace.name},
    )
    assert preview.status_code == 200
    assert preview.json()["title"] == "Safe import"

    for unsafe_source in ("../safe-workspace", str(Path(workspace).resolve())):
        blocked = canonical_client.post(
            "/api/imports/preview",
            json={"source": unsafe_source},
        )
        assert blocked.status_code == 422


def test_project_and_document_delete_endpoints(canonical_client: TestClient) -> None:
    canonical_client.post("/api/session/guest")
    project = canonical_client.post("/api/projects", json={"title": "Delete Me"}).json()
    document = project["documents"][0]
    saved = canonical_client.put(
        f"/api/projects/{project['id']}/documents/{document['id']}",
        json={
            "content_markdown": "# Chapter 1\n\nDelete marker.",
            "base_revision_id": document["current_revision_id"],
            "metadata": {},
        },
    )
    assert saved.status_code == 200

    deleted_document = canonical_client.delete(
        f"/api/projects/{project['id']}/documents/{document['id']}"
    )
    assert deleted_document.status_code == 204
    assert (
        canonical_client.get(
            f"/api/projects/{project['id']}/documents/{document['id']}"
        ).status_code
        == 404
    )
    assert (
        canonical_client.get(f"/api/projects/{project['id']}/search?q=marker").json()[
            "results"
        ]
        == []
    )

    deleted_project = canonical_client.delete(f"/api/projects/{project['id']}")
    assert deleted_project.status_code == 204
    assert canonical_client.get(f"/api/projects/{project['id']}").status_code == 404


def test_delete_project_with_snapshots(canonical_client: TestClient) -> None:
    """Regression test: projects with export snapshots must be deletable."""
    canonical_client.post("/api/session/guest")
    project = canonical_client.post("/api/projects", json={"title": "Snapshot Delete"}).json()
    document = project["documents"][0]
    saved = canonical_client.put(
        f"/api/projects/{project['id']}/documents/{document['id']}",
        json={
            "content_markdown": "# Chapter 1\n\nSnapshot marker.",
            "base_revision_id": document["current_revision_id"],
            "metadata": {},
        },
    )
    assert saved.status_code == 200

    export = canonical_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"format": "markdown"},
    )
    assert export.status_code == 201

    deleted_project = canonical_client.delete(f"/api/projects/{project['id']}")
    assert deleted_project.status_code == 204
    assert canonical_client.get(f"/api/projects/{project['id']}").status_code == 404
