import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture()
def client():
    from src.api.app import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.integration
def test_create_app_openapi_exposes_core_product_routes(client: TestClient):
    schema = client.app.openapi()
    paths = schema.get("paths", {})

    for path in (
        "/health",
        "/cache/metrics",
        "/cache/invalidate",
        "/api/guest/session",
        "/api/workspace/export",
        "/api/workspace/import",
        "/api/characters",
        "/api/events/stream",
        "/api/auth/login",
    ):
        assert path in paths


@pytest.mark.integration
def test_create_app_does_not_serve_path_versioning(client: TestClient):
    assert client.get("/api/v1/characters").status_code == 404
    assert client.get("/api/v2/characters").status_code == 404


@pytest.mark.integration
def test_error_envelope_includes_stable_code_for_missing_route(client: TestClient):
    resp = client.get("/__does_not_exist__")
    assert resp.status_code == 404
    payload = resp.json()
    assert "error" in payload
    assert "detail" in payload
    assert payload.get("code") == "not_found"


@pytest.mark.integration
def test_validation_errors_are_normalized(client: TestClient):
    resp = client.post("/cache/invalidate", json={})
    assert resp.status_code == 422
    payload = resp.json()
    assert payload.get("code") == "validation_error"
    assert isinstance(payload.get("fields"), list)
