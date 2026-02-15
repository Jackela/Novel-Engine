import pytest
from fastapi.testclient import TestClient

import api_server

pytestmark = pytest.mark.integration

client = TestClient(api_server.app)


@pytest.mark.smoke
@pytest.mark.timeout(30)
@pytest.mark.integration
def test_health_endpoint_reports_healthy():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in {"healthy", "degraded"}
    assert data.get("api") == "running"


@pytest.mark.smoke
@pytest.mark.timeout(30)
@pytest.mark.integration
def test_cache_metrics_endpoint_available():
    response = client.get("/api/cache/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "cache_exact_hits" in payload
    assert "saved_tokens" in payload


@pytest.mark.smoke
@pytest.mark.timeout(30)
@pytest.mark.integration
def test_cache_invalidate_noops_without_tags():
    response = client.post("/api/cache/invalidate", json={"all_of": []})
    assert response.status_code == 200
    assert response.json()["removed"] == 0
