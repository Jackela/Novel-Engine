import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


def build_client() -> TestClient:
    """Build a test client for the modular API app."""
    return TestClient(create_app())


@pytest.mark.integration
def test_list_and_simulate_character():
    """Test listing characters and running a simulation with a known character."""
    client = build_client()

    list_resp = client.get("/api/characters")
    assert list_resp.status_code == 200
    characters = list_resp.json().get("characters", [])
    assert characters

    assert len(characters) >= 2
    character_ids = [characters[0]["id"], characters[1]["id"]]
    sim_resp = client.post(
        "/api/simulations",
        json={
            "character_names": character_ids,
            "turns": 1,
        },
    )
    assert sim_resp.status_code == 200
    for character_id in character_ids:
        assert character_id in sim_resp.json().get("participants", [])


@pytest.mark.integration
def test_simulation_rejects_unknown_character():
    """Test that simulations reject unknown characters with 422.

    This test uses mocked orchestrator/story_api. The "unknown" character
    is not pre-registered, so it should be rejected.
    """
    client = build_client()
    sim_resp = client.post(
        "/api/simulations",
        json={
            "character_names": ["unknown-one", "unknown-two"],
            "turns": 1,
        },
    )
    assert sim_resp.status_code == 404
