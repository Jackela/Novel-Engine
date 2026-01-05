from datetime import datetime

import api_server
from fastapi.testclient import TestClient


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_characters_list_returns_summaries_ordered_by_updated_at():
    client = TestClient(api_server.app)
    response = client.get("/api/characters")
    assert response.status_code == 200
    characters = response.json().get("characters", [])
    assert isinstance(characters, list)
    assert len(characters) > 0, "Expected at least one public character summary"

    # All summaries must include the required fields
    required_fields = {"id", "name", "status", "type", "updated_at"}
    for summary in characters:
        assert required_fields.issubset(
            summary.keys()
        ), "Missing required summary fields"
        assert isinstance(summary["updated_at"], str)

    timestamps = [_parse_iso(summary["updated_at"]) for summary in characters]
    assert timestamps == sorted(
        timestamps, reverse=True
    ), "Characters are not sorted by updated_at desc"


def test_guest_workspace_characters_provide_workspace_id_and_cache_hints():
    client = TestClient(api_server.app)
    session_resp = client.post("/api/guest/session")
    assert session_resp.status_code == 200
    manager = getattr(api_server.app.state, "guest_session_manager", None)
    assert manager, "Guest session manager must be available"
    token = client.cookies.get(manager.cookie_name)
    assert token, "Guest session cookie must be set"
    workspace_id = manager.decode(token)
    assert workspace_id, "Decoded workspace id must be present"

    store = getattr(api_server.app.state, "workspace_character_store", None)
    assert store, "Workspace character store must be available"
    record_payload = {
        "name": "Workspace Test Character",
        "background_summary": "Scoped to guest workspace",
        "personality_traits": "Adaptive",
        "skills": {"strength": 10},
        "relationships": {"pilot": 0.8},
        "metadata": {"source": "test"},
        "structured_data": {"role": "protagonist"},
        "current_location": "Command Deck",
        "inventory": [],
        "current_status": "active",
    }
    created_record = store.create(workspace_id, "workspace_test_char", record_payload)
    assert created_record.get("id") == "workspace_test_char"
    stored_ids = store.list_ids(workspace_id)
    assert (
        "workspace_test_char" in stored_ids
    ), "Workspace character store must contain created entry"

    cookie_value = f"{manager.cookie_name}={token}"
    list_resp = client.get("/api/characters", headers={"Cookie": cookie_value})
    assert list_resp.status_code == 200
    summaries = list_resp.json().get("characters", [])
    workspace_entries = [
        entry for entry in summaries if entry.get("workspace_id") == workspace_id
    ]
    assert workspace_entries, "Workspace characters should appear in list"

    etag = list_resp.headers.get("etag")
    assert etag, "ETag header must be exposed"

    cached_resp = client.get(
        "/api/characters", headers={"if-none-match": etag, "Cookie": cookie_value}
    )
    assert (
        cached_resp.status_code == 304
    ), "Cache validator should trigger 304 when data is unchanged"
    store.delete(workspace_id, "workspace_test_char")
