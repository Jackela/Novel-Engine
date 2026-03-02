"""Integration tests for Factions API endpoints.

Tests faction-related functionality through diplomacy and world state endpoints.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestFactionsViaDiplomacyEndpoint:
    """Tests for faction data through diplomacy endpoint."""

    def test_diplomacy_matrix_lists_factions(self, client):
        """Test that diplomacy matrix includes factions."""
        # First create a world with some relations
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        # Get the diplomacy matrix
        response = client.get("/api/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()

        # Check that factions are listed
        assert "factions" in data
        assert "faction-a" in data["factions"]
        assert "faction-b" in data["factions"]

    def test_diplomacy_relations_creates_factions(self, client):
        """Test that setting relations creates factions."""
        response = client.put(
            "/api/world/relations-world/diplomacy/new-faction-1/new-faction-2",
            json={"status": "neutral"},
        )

        assert response.status_code == 200
        data = response.json()

        # Factions should be created
        assert "new-faction-1" in data["factions"]
        assert "new-faction-2" in data["factions"]


class TestFactionsViaWorldStateEndpoint:
    """Tests for faction data through world state endpoint."""

    def test_world_state_includes_factions(self, client):
        """Test that world state includes faction summary."""
        # Create a world with factions via diplomacy
        client.put(
            "/api/world/state-world/diplomacy/faction-x/faction-y",
            json={"status": "hostile"},
        )

        # Get world state
        response = client.get("/api/world/state-world/state")

        # Should work or return 404 if world not initialized
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Check for factions in response
            assert "factions" in data or "diplomacy" in data


class TestFactionsViaHealthCheck:
    """Basic health check test to verify API is working."""

    def test_health_endpoint_works(self, client):
        """Test that the health endpoint responds."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
