"""Integration tests for Factions API endpoints.

Tests faction membership management including joining, leaving factions,
and setting leaders.
"""

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Factions API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_store():
    """Create a mock store for testing."""
    store = MagicMock()
    store.world_store = {}
    store.workspace_character_store = {}
    return store


class TestFactionDetailEndpoint:
    """Tests for GET /api/factions/{faction_id} endpoint."""

    def test_get_faction_not_found(self, client):
        """Test getting a non-existent faction returns 404."""
        response = client.get("/api/factions/nonexistent-faction")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

        assert "not found" in data["detail"].lower()

    def test_get_faction_without_workspace(self, client):
        """Test getting faction without workspace ID."""
        response = client.get(
            "/api/factions/some-faction",
            headers={"X-Workspace-Id": ""},
        )

        # Without workspace, may return 404 or empty data
        assert response.status_code in [200, 404]


class TestFactionsJoinEndpoint:
    """Tests for POST /api/factions/{faction_id}/join endpoint."""

    def test_join_faction_faction_not_found(self, client):
        """Test joining a non-existent faction returns 404."""
        response = client.post(
            "/api/factions/nonexistent-faction/join",
            json={"character_id": "char-001"},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404

    def test_join_faction_missing_workspace(self, client):
        """Test joining faction without workspace ID returns 422."""
        response = client.post(
            "/api/factions/some-faction/join",
            json={"character_id": "char-001"},
        )

        # Should require workspace ID
        assert response.status_code in [400, 422]

    def test_join_faction_missing_character_id(self, client):
        """Test joining faction without character_id returns 422."""
        response = client.post(
            "/api/factions/some-faction/join",
            json={},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 422


class TestFactionsLeaveEndpoint:
    """Tests for POST /api/factions/{faction_id}/leave endpoint."""

    def test_leave_faction_faction_not_found(self, client):
        """Test leaving a non-existent faction returns 404."""
        response = client.post(
            "/api/factions/nonexistent-faction/leave",
            json={"character_id": "char-001"},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404

    def test_leave_faction_missing_workspace(self, client):
        """Test leaving faction without workspace ID returns 422."""
        response = client.post(
            "/api/factions/some-faction/leave",
            json={"character_id": "char-001"},
        )

        # Should require workspace ID
        assert response.status_code in [400, 422]

    def test_leave_faction_missing_character_id(self, client):
        """Test leaving faction without character_id returns 422."""
        response = client.post(
            "/api/factions/some-faction/leave",
            json={},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 422


class TestFactionsLeaderEndpoint:
    """Tests for POST /api/factions/{faction_id}/leader endpoint."""

    def test_set_leader_faction_not_found(self, client):
        """Test setting leader for non-existent faction returns 404."""
        response = client.post(
            "/api/factions/nonexistent-faction/leader",
            json={"character_id": "char-001"},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404

    def test_set_leader_missing_workspace(self, client):
        """Test setting leader without workspace ID returns 422."""
        response = client.post(
            "/api/factions/some-faction/leader",
            json={"character_id": "char-001"},
        )

        # Should require workspace ID
        assert response.status_code in [400, 422]

    def test_set_leader_missing_character_id(self, client):
        """Test setting leader without character_id returns 422."""
        response = client.post(
            "/api/factions/some-faction/leader",
            json={},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 422

