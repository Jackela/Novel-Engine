import pytest
from fastapi.testclient import TestClient

from api_server import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_metrics_contract_shape(client):
    resp = client.get("/cache/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # required keys per contract
    for key in (
        "ts",
        "cache_exact_hits",
        "cache_semantic_hits",
        "cache_tool_hits",
        "cache_size",
        "evictions",
        "invalidations",
        "single_flight_merged",
        "replay_hits",
        "saved_tokens",
        "saved_cost",
    ):
        assert key in data


def test_invalidate_contract_shape(client):
    resp = client.post("/cache/invalidate", json={"all_of": ["model:test-model"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "removed" in data
    assert isinstance(data["removed"], int)

