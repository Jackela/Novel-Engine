import logging

import pytest
from fastapi.testclient import TestClient

from src.api import secure_main_api as secure_api
from src.api.main_api_server import create_app


@pytest.mark.integration
def test_main_api_does_not_serve_versioned_paths():
    client = TestClient(create_app())

    assert client.get("/api/characters").status_code != 404
    assert client.get("/api/v1/characters").status_code == 404

    # SSE endpoint is served under /api only
    assert client.get("/api/v1/events/stream").status_code == 404


@pytest.mark.integration
def test_secure_api_does_not_serve_versioned_paths(monkeypatch):
    monkeypatch.setenv("SKIP_INPUT_VALIDATION", "1")
    monkeypatch.setenv("DISABLE_CHAR_AUTH", "1")

    secure_api.user_character_store.clear()
    if secure_api.USER_CHARACTER_STORE_PATH.exists():
        try:
            secure_api.USER_CHARACTER_STORE_PATH.unlink()
        except OSError:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    client = TestClient(secure_api.create_secure_app())

    assert client.get("/api/characters").status_code != 404
    assert client.get("/api/v1/characters").status_code == 404
