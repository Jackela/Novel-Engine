"""Integration tests for World State API endpoints.

Tests the deprecated world state endpoints for geopolitical queries.

Note: The world_state router is deprecated in favor of the geopolitics router.
These tests verify backward compatibility for existing clients.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestWorldStateEndpoints:
    """Tests for world state endpoints."""

    def test_get_territories_not_found(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/territories with nonexistent world."""
        response = client.get("/api/world/nonexistent-world/territories")

        # Should return 404 for non-existent world
        assert response.status_code == 404

    def test_get_diplomacy_not_found(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/diplomacy with nonexistent world."""
        response = client.get("/api/world/nonexistent-world/diplomacy")

        assert response.status_code == 404

    def test_get_resources_not_found(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/resources with nonexistent world."""
        response = client.get("/api/world/nonexistent-world/resources")

        assert response.status_code == 404
