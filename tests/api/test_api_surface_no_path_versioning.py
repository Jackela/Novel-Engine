import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app as create_modular_app
from src.api.main_api_server import create_app

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_main_api_does_not_serve_versioned_paths():
    client = TestClient(create_app())

    assert client.get("/api/characters").status_code != 404
    assert client.get("/api/v1/characters").status_code == 404

    # SSE endpoint is served under /api only
    assert client.get("/api/v1/events/stream").status_code == 404


@pytest.mark.integration
def test_modular_api_does_not_serve_versioned_paths():
    client = TestClient(create_modular_app())

    assert client.get("/api/characters").status_code != 404
    assert client.get("/api/v1/characters").status_code == 404
