import os
from fastapi.testclient import TestClient

from src.api import secure_main_api as api


def build_client():
    os.environ["SKIP_INPUT_VALIDATION"] = "1"
    os.environ["DISABLE_CHAR_AUTH"] = "1"
    api.user_character_store.clear()
    if api.USER_CHARACTER_STORE_PATH.exists():
        try:
            api.USER_CHARACTER_STORE_PATH.unlink()
        except OSError:
            pass
    app = api.create_secure_app()

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
    for perm in [api.Permission.CHARACTER_CREATE, api.Permission.CHARACTER_READ, api.Permission.SIMULATION_CREATE]:
        app.dependency_overrides[svc.require_permission(perm)] = allow

    return TestClient(app)


@pytest.mark.integration
def test_create_list_and_simulate_user_character():
    client = build_client()

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
    client = build_client()
    sim_resp = client.post(
        "/simulations",
        json={
            "character_names": ["unknown"],
            "turns": 1,
        },
    )
    assert sim_resp.status_code == 422
