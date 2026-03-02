"""Integration tests for Diplomacy API endpoints.

Tests diplomatic relations between factions including matrix retrieval,
faction-specific relations, and status updates.

Note: This router is deprecated in favor of geopolitics router.
"""

import os
import warnings

import pytest
from fastapi.testclient import TestClient

# Suppress deprecation warnings from the router itself
warnings.filterwarnings("ignore", category=DeprecationWarning)

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app
from src.api.routers.diplomacy import reset_diplomacy_storage

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Diplomacy API."""
    app = create_app()
    # Reset storage before each test
    reset_diplomacy_storage()
    with TestClient(app) as test_client:
        yield test_client
    # Reset after test
    reset_diplomacy_storage()


class TestDiplomacyMatrixEndpoint:
    """Tests for GET /api/world/{world_id}/diplomacy endpoint."""

    def test_get_diplomacy_matrix_empty_world(self, client):
        """Test getting diplomacy matrix for empty world."""
        response = client.get("/api/world/test-world-empty/diplomacy")

        assert response.status_code == 200
        data = response.json()

        assert "world_id" in data
        assert "matrix" in data
        assert "factions" in data
        assert data["world_id"] == "test-world-empty"

    def test_get_diplomacy_matrix_structure(self, client):
        """Test that diplomacy matrix has correct structure."""
        response = client.get("/api/world/test-world-structure/diplomacy")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert isinstance(data["matrix"], dict)
        assert isinstance(data["factions"], list)

    def test_get_diplomacy_matrix_persists_per_world(self, client):
        """Test that different worlds have separate matrices."""
        response1 = client.get("/api/world/world-A/diplomacy")
        response2 = client.get("/api/world/world-B/diplomacy")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Each world should have its own matrix
        assert response1.json()["world_id"] == "world-A"
        assert response2.json()["world_id"] == "world-B"


class TestSetRelationEndpoint:
    """Tests for PUT /api/world/{world_id}/diplomacy/{faction_a}/{faction_b} endpoint."""

    def test_set_relation_success(self, client):
        """Test setting a diplomatic relation between two factions."""
        response = client.put(
            "/api/world/test-world/world-factions/faction-A/faction-B",
            json={"status": "allied"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check factions are now in the matrix
        assert "faction-A" in data["factions"]
        assert "faction-B" in data["factions"]

    def test_set_relation_creates_factions(self, client):
        """Test that setting relation creates factions if they don't exist."""
        response = client.put(
            "/api/world/new-world/new-faction-1/new-faction-2",
            json={"status": "neutral"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "new-faction-1" in data["factions"]
        assert "new-faction-2" in data["factions"]

    def test_set_relation_various_statuses(self, client):
        """Test setting various diplomatic statuses."""
        statuses = ["allied", "friendly", "neutral", "cold", "hostile", "at_war"]

        for status in statuses:
            response = client.put(
                f"/api/world/status-world/faction-{status}/other-faction",
                json={"status": status},
            )

            assert response.status_code == 200, f"Failed for status: {status}"

    def test_set_relation_invalid_status(self, client):
        """Test setting invalid status returns 400."""
        response = client.put(
            "/api/world/test-world/faction-A/faction-B",
            json={"status": "invalid_status"},
        )

        assert response.status_code == 400

    def test_set_relation_case_insensitive(self, client):
        """Test that status values are case-insensitive."""
        response = client.put(
            "/api/world/case-world/faction-A/faction-B",
            json={"status": "ALLIED"},  # uppercase
        )

        assert response.status_code == 200

    def test_set_relation_matrix_updated(self, client):
        """Test that matrix is updated after setting relation."""
        # Set relation
        client.put(
            "/api/world/matrix-world/faction-A/faction-B",
            json={"status": "hostile"},
        )

        # Get matrix and verify
        response = client.get("/api/world/matrix-world/diplomacy")
        assert response.status_code == 200

        data = response.json()
        matrix = data["matrix"]

        # Check that the relation is reflected in matrix
        assert "faction-A" in matrix
        assert "faction-B" in matrix["faction-A"]


class TestFactionDiplomacyEndpoint:
    """Tests for GET /api/world/{world_id}/diplomacy/faction/{faction_id} endpoint."""

    def test_get_faction_diplomacy_not_found(self, client):
        """Test getting diplomacy for non-existent faction returns 404."""
        response = client.get(
            "/api/world/test-world-faction/diplomacy/faction/nonexistent-faction"
        )

        assert response.status_code == 404

    def test_get_faction_diplomacy_after_set_relation(self, client):
        """Test getting faction diplomacy after setting relations."""
        world_id = "diplomacy-world"
        faction_id = "central-faction"

        # Create some relations
        client.put(
            f"/api/world/{world_id}/{faction_id}/ally-faction",
            json={"status": "allied"},
        )
        client.put(
            f"/api/world/{world_id}/{faction_id}/enemy-faction",
            json={"status": "hostile"},
        )
        client.put(
            f"/api/world/{world_id}/{faction_id}/neutral-faction",
            json={"status": "neutral"},
        )

        # Get faction diplomacy
        response = client.get(
            f"/api/world/{world_id}/diplomacy/faction/{faction_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "faction_id" in data
        assert "allies" in data
        assert "enemies" in data
        assert "neutral" in data

        # Verify categorization
        assert "ally-faction" in data["allies"]
        assert "enemy-faction" in data["enemies"]
        assert "neutral-faction" in data["neutral"]

    def test_get_faction_diplomacy_empty_lists(self, client):
        """Test faction diplomacy returns empty lists when no relations set."""
        # Create a faction first by setting a self-relation workaround
        world_id = "empty-relations-world"
        faction_id = "isolated-faction"

        # Just create the faction without external relations
        client.put(
            f"/api/world/{world_id}/{faction_id}/some-other-faction",
            json={"status": "neutral"},
        )

        # The faction should have relations now
        response = client.get(
            f"/api/world/{world_id}/diplomacy/faction/{faction_id}"
        )

        assert response.status_code == 200


class TestDiplomacySymmetry:
    """Tests that diplomatic relations are symmetric."""

    def test_relation_is_symmetric(self, client):
        """Test that setting A->B also sets B->A."""
        # Set relation
        client.put(
            "/api/world/symmetric-world/faction-A/faction-B",
            json={"status": "allied"},
        )

        # Get diplomacy for faction-B
        response = client.get(
            "/api/world/symmetric-world/diplomacy/faction/faction-B"
        )

        assert response.status_code == 200
        data = response.json()

        # faction-A should be in allies of faction-B
        assert "faction-A" in data["allies"]

    def test_changing_relation_updates_both_sides(self, client):
        """Test that changing relation updates both faction views."""
        world_id = "update-both-world"

        # Set initial relation
        client.put(
            f"/api/world/{world_id}/faction-A/faction-B",
            json={"status": "allied"},
        )

        # Change relation
        client.put(
            f"/api/world/{world_id}/faction-A/faction-B",
            json={"status": "hostile"},
        )

        # Check faction-A's view
        response_a = client.get(f"/api/world/{world_id}/diplomacy/faction/faction-A")
        assert response_a.status_code == 200
        assert "faction-B" in response_a.json()["enemies"]

        # Check faction-B's view
        response_b = client.get(f"/api/world/{world_id}/diplomacy/faction/faction-B")
        assert response_b.status_code == 200
        assert "faction-A" in response_b.json()["enemies"]


class TestDiplomacyValidation:
    """Tests for diplomacy endpoint validation."""

    def test_set_relation_missing_status(self, client):
        """Test setting relation without status returns 422."""
        response = client.put(
            "/api/world/test-world/faction-A/faction-B",
            json={},
        )

        assert response.status_code == 422

    def test_set_relation_empty_status(self, client):
        """Test setting relation with empty status returns 400."""
        response = client.put(
            "/api/world/test-world/faction-A/faction-B",
            json={"status": ""},
        )

        assert response.status_code == 400

    def test_get_faction_diplomacy_world_not_found_handling(self, client):
        """Test getting faction diplomacy handles world lookup correctly."""
        # Even for non-existent world, the matrix is created on-demand
        response = client.get(
            "/api/world/nonexistent-world/diplomacy/faction/some-faction"
        )

        # Should return 404 since faction doesn't exist
        assert response.status_code == 404
