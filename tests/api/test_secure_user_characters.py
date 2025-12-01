import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api import secure_main_api as api

# Check if LLM service is available (simulation endpoint requires LLM)
LLM_SERVICE_AVAILABLE = bool(os.environ.get("GEMINI_API_KEY"))


def create_mock_orchestrator(character_names: list[str] | None = None):
    """Create a mock orchestrator for testing.

    Args:
        character_names: List of character names to pre-register as active agents.
    """
    mock = MagicMock()
    mock.get_status = MagicMock(return_value={"status": "ready"})
    # Pre-populate active_agents with the requested character names
    mock.active_agents = {name: MagicMock() for name in (character_names or [])}
    return mock


def create_mock_story_api():
    """Create a mock story API for testing."""
    mock = MagicMock()
    mock.active_generations = {}

    async def mock_generate_story(generation_id: str):
        """Mock async story generation that sets story content."""
        mock.active_generations[generation_id] = {
            "status": "completed",
            "story_content": "Test story content for simulation.",
            "progress": 100,
            "stage": "completed",
        }

    mock._generate_story_async = AsyncMock(side_effect=mock_generate_story)
    return mock


def build_client(character_names: list[str] | None = None):
    """Build a test client with mocked dependencies.

    Args:
        character_names: Character names to pre-register in the mock orchestrator.
    """
    os.environ["SKIP_INPUT_VALIDATION"] = "1"
    os.environ["DISABLE_CHAR_AUTH"] = "1"
    api.user_character_store.clear()
    if api.USER_CHARACTER_STORE_PATH.exists():
        try:
            api.USER_CHARACTER_STORE_PATH.unlink()
        except OSError:
            pass
    app = api.create_secure_app()

    # Set mock orchestrator and story_api to avoid 503 errors
    app.state.orchestrator = create_mock_orchestrator(character_names)
    app.state.story_api = create_mock_story_api()

    dummy_user = api.User(
        id="test-user",
        username="test-user",
        email="test@example.com",
        password_hash="",
        role=api.UserRole.READER,
        is_active=True,
        is_verified=True,
        api_key=None,
    )
    svc = api.get_security_service()
    allow = lambda: dummy_user
    for perm in [
        api.Permission.CHARACTER_CREATE,
        api.Permission.CHARACTER_READ,
        api.Permission.SIMULATION_CREATE,
    ]:
        app.dependency_overrides[svc.require_permission(perm)] = allow

    return TestClient(app)


@pytest.mark.integration
def test_create_list_and_simulate_user_character():
    """Test creating a character, listing it, and running a simulation.

    This test uses mocked orchestrator/story_api to avoid needing actual LLM service.
    """
    # Pre-register "nova" as an active agent in the mock orchestrator
    client = build_client(character_names=["nova"])

    create_resp = client.post(
        "/api/characters",
        json={
            "name": "nova",
            "background_summary": "Systems analyst",
            "personality_traits": "calm",
        },
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["name"] == "nova"

    list_resp = client.get("/api/characters")
    assert list_resp.status_code == 200
    characters = list_resp.json().get("characters", [])
    assert "nova" in characters

    sim_resp = client.post(
        "/simulations",
        json={
            "character_names": ["nova"],
            "turns": 2,
            "style": "narrative",
        },
    )
    assert sim_resp.status_code == 200
    assert "nova" in sim_resp.json().get("participants", [])


@pytest.mark.integration
def test_simulation_rejects_unknown_character():
    """Test that simulations reject unknown characters with 422.

    This test uses mocked orchestrator/story_api. The "unknown" character
    is not pre-registered, so it should be rejected.
    """
    client = build_client()  # No pre-registered characters
    sim_resp = client.post(
        "/simulations",
        json={
            "character_names": ["unknown"],
            "turns": 1,
        },
    )
    assert sim_resp.status_code == 422
