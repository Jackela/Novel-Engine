import uuid

import pytest
from fastapi.testclient import TestClient

import api_server
from src.workspaces import (
    FilesystemCharacterStore,
    FilesystemWorkspaceStore,
    GuestSessionManager,
)

pytestmark = pytest.mark.integration


def _character_ids(characters):
    return [entry["id"] if isinstance(entry, dict) else entry for entry in characters]


@pytest.fixture
def guest_app(tmp_path):
    workspace_store = FilesystemWorkspaceStore(tmp_path / "workspaces")
    character_store = FilesystemCharacterStore(workspace_store)
    session_manager = GuestSessionManager(
        workspace_store,
        secret_key=api_server.JWT_SECRET_KEY,
        algorithm=api_server.JWT_ALGORITHM,
    )

    app = api_server.app

    old_state = {
        "workspace_store": getattr(app.state, "workspace_store", None),
        "workspace_character_store": getattr(
            app.state, "workspace_character_store", None
        ),
        "guest_session_manager": getattr(app.state, "guest_session_manager", None),
    }
    app.state.workspace_store = workspace_store
    app.state.workspace_character_store = character_store
    app.state.guest_session_manager = session_manager

    try:
        yield app
    finally:
        app.state.workspace_store = old_state["workspace_store"]
        app.state.workspace_character_store = old_state["workspace_character_store"]
        app.state.guest_session_manager = old_state["guest_session_manager"]


@pytest.mark.integration
def test_guest_sessions_are_isolated_and_portable(guest_app):
    client_a = TestClient(guest_app, base_url="https://testserver")
    client_b = TestClient(guest_app, base_url="https://testserver")

    session_a = client_a.post("/api/guest/session")
    session_b = client_b.post("/api/guest/session")
    assert session_a.status_code == 200
    assert session_b.status_code == 200
    assert session_a.json()["workspace_id"] != session_b.json()["workspace_id"]

    create_a = client_a.post(
        "/api/characters",
        json={
            "agent_id": f"ws_a_{uuid.uuid4().hex}",
            "name": "Workspace A Character",
            "background_summary": "A",
            "personality_traits": "curious",
        },
    )
    assert create_a.status_code == 201
    char_a_id = create_a.json()["character_id"]

    create_b = client_b.post(
        "/api/characters",
        json={
            "agent_id": f"ws_b_{uuid.uuid4().hex}",
            "name": "Workspace B Character",
            "background_summary": "B",
            "personality_traits": "brave",
        },
    )
    assert create_b.status_code == 201
    char_b_id = create_b.json()["character_id"]

    list_a = client_a.get("/api/characters")
    list_b = client_b.get("/api/characters")
    assert list_a.status_code == 200
    assert list_b.status_code == 200

    characters_a = list_a.json()["characters"]
    characters_b = list_b.json()["characters"]
    character_ids_a = _character_ids(characters_a)
    character_ids_b = _character_ids(characters_b)

    assert char_a_id in character_ids_a
    assert char_b_id not in character_ids_a
    assert char_b_id in character_ids_b
    assert char_a_id not in character_ids_b

    exported = client_a.get("/api/workspace/export")
    assert exported.status_code == 200
    assert exported.headers.get("content-type", "").startswith("application/zip")

    imported = client_b.post(
        "/api/workspace/import",
        files={"archive": ("workspace.zip", exported.content, "application/zip")},
    )
    assert imported.status_code == 200

    list_b_after = client_b.get("/api/characters")
    assert list_b_after.status_code == 200
    assert char_a_id in _character_ids(list_b_after.json()["characters"])
