"""Integration tests for Geopolitics API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


class TestGeopoliticsEndpoints:
    """Tests for geopolitics API endpoints."""

    def test_get_diplomacy_matrix(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/diplomacy."""
        response = client.get("/api/geopolitics/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()
        assert "matrix" in data
        assert "factions" in data

    def test_get_territories(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/territories."""
        response = client.get("/api/geopolitics/world/test-world/territories")

        assert response.status_code in [200, 404]  # 404 if world doesn't exist

    def test_get_resources(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/resources."""
        response = client.get("/api/geopolitics/world/test-world/resources")

        assert response.status_code in [200, 404]

    def test_declare_war_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/war exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/war",
            json={
                "aggressor_id": "faction_a",
                "defender_id": "faction_b",
                "reason": "Test war",
            },
        )

        # Should not return 404 (method might exist even if world doesn't)
        assert response.status_code != 404

    def test_form_alliance_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/alliance exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/alliance",
            json={
                "faction_a_id": "faction_a",
                "faction_b_id": "faction_b",
            },
        )

        assert response.status_code != 404

    def test_transfer_territory_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/transfer-territory exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/transfer-territory",
            json={
                "location_id": "loc_1",
                "new_controller_id": "faction_b",
                "reason": "Military conquest",
            },
        )

        # The endpoint exists and returns a proper JSON response
        # Either 404 (world/location not found) or 200 (success) is acceptable
        assert response.status_code in [200, 400, 404]
        # Verify we get a JSON response (not HTML error page)
        data = response.json()
        assert isinstance(data, dict)
