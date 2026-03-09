"""Tests for Snapshots API router.

This module tests the snapshots API endpoints for creating, listing,
restoring, and deleting world state snapshots.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Mock aioredis before importing any app modules
import sys

sys.modules["aioredis"] = MagicMock()

from src.api.app import create_app
from src.api.routers.snapshots import reset_snapshot_service


@pytest.fixture
def client():
    """Create a test client for the API."""
    app = create_app(debug=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset snapshot storage before each test."""
    reset_snapshot_service()
    yield
    reset_snapshot_service()


class TestCreateSnapshot:
    """Tests for POST /world/{world_id}/snapshots endpoint."""

    def test_create_snapshot_basic(self, client):
        """Test creating a basic snapshot."""
        response = client.post(
            "/api/world/test-world/snapshots",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert "snapshot_id" in data
        assert data["world_id"] == "test-world"
        assert data["tick_number"] == 0
        assert data["description"]
        assert "created_at" in data
        assert "size_bytes" in data
        assert data["calendar"] is not None

    def test_create_snapshot_with_description(self, client):
        """Test creating snapshot with custom description."""
        response = client.post(
            "/api/world/test-world/snapshots",
            json={
                "description": "Before major battle",
                "tick_number": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["description"] == "Before major battle"
        assert data["tick_number"] == 5

    def test_create_snapshot_with_state_json(self, client):
        """Test creating snapshot with state JSON."""
        response = client.post(
            "/api/world/test-world/snapshots",
            json={
                "state_json": '{"factions": ["A", "B"]}',
                "tick_number": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tick_number"] == 3
        assert data["size_bytes"] > 0


class TestListSnapshots:
    """Tests for GET /world/{world_id}/snapshots endpoint."""

    def test_list_snapshots_empty(self, client):
        """Test listing when no snapshots exist."""
        response = client.get("/api/world/test-world/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshots"] == []
        assert data["total"] == 0

    def test_list_snapshots_single(self, client):
        """Test listing with single snapshot."""
        # Create a snapshot first
        create_response = client.post(
            "/api/world/test-world/snapshots",
            json={"tick_number": 5},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # List snapshots
        response = client.get("/api/world/test-world/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["snapshots"][0]["snapshot_id"] == snapshot_id
        assert data["snapshots"][0]["tick_number"] == 5

    def test_list_snapshots_multiple(self, client):
        """Test listing with multiple snapshots."""
        # Create multiple snapshots
        for i in range(5):
            client.post(
                "/api/world/test-world/snapshots",
                json={"tick_number": i},
            )

        # List snapshots
        response = client.get("/api/world/test-world/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        # Should be ordered newest first (highest tick first)
        tick_numbers = [s["tick_number"] for s in data["snapshots"]]
        assert tick_numbers == [4, 3, 2, 1, 0]

    def test_list_snapshots_limit(self, client):
        """Test limit parameter."""
        # Create multiple snapshots
        for i in range(10):
            client.post(
                "/api/world/test-world/snapshots",
                json={"tick_number": i},
            )

        # List with limit
        response = client.get("/api/world/test-world/snapshots?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert len(data["snapshots"]) == 3
        assert data["snapshots"][0]["tick_number"] == 9


class TestGetSnapshot:
    """Tests for GET /world/{world_id}/snapshots/{snapshot_id} endpoint."""

    def test_get_snapshot_success(self, client):
        """Test getting existing snapshot."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/test-world/snapshots",
            json={"tick_number": 7, "description": "Test snapshot"},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Get snapshot
        response = client.get(f"/api/world/test-world/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshot_id"] == snapshot_id
        assert data["tick_number"] == 7
        assert data["description"] == "Test snapshot"

    def test_get_snapshot_not_found(self, client):
        """Test getting non-existent snapshot."""
        response = client.get("/api/world/test-world/snapshots/non-existent-id")

        assert response.status_code == 404


class TestRestoreSnapshot:
    """Tests for POST /world/{world_id}/snapshots/{snapshot_id}/restore endpoint."""

    def test_restore_snapshot_success(self, client):
        """Test successful snapshot restoration."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/test-world/snapshots",
            json={"tick_number": 5, "state_json": '{"valid": true}'},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Restore snapshot
        response = client.post(f"/api/world/test-world/snapshots/{snapshot_id}/restore")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshot_id"] == snapshot_id
        assert data["restored"] is True
        assert "successfully" in data["message"].lower()

    def test_restore_snapshot_not_found(self, client):
        """Test restoring non-existent snapshot."""
        response = client.post(
            "/api/world/test-world/snapshots/non-existent-id/restore"
        )

        assert response.status_code == 404


class TestDeleteSnapshot:
    """Tests for DELETE /world/{world_id}/snapshots/{snapshot_id} endpoint."""

    def test_delete_snapshot_success(self, client):
        """Test successful snapshot deletion."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/test-world/snapshots",
            json={"tick_number": 5},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Delete snapshot
        response = client.delete(f"/api/world/test-world/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

        # Verify it's deleted
        list_response = client.get("/api/world/test-world/snapshots")
        assert list_response.json()["total"] == 0

    def test_delete_snapshot_not_found(self, client):
        """Test deleting non-existent snapshot."""
        response = client.delete("/api/world/test-world/snapshots/non-existent-id")

        assert response.status_code == 404


class TestWorldIsolation:
    """Tests for world isolation in snapshots."""

    def test_snapshots_isolated_between_worlds(self, client):
        """Test that snapshots are isolated between worlds."""
        # Create snapshots for world A
        client.post(
            "/api/world/world-a/snapshots",
            json={"tick_number": 1},
        )

        # Create snapshots for world B
        create_b = client.post(
            "/api/world/world-b/snapshots",
            json={"tick_number": 2},
        )
        _ = create_b.json()["snapshot_id"]

        # Verify isolation
        list_a = client.get("/api/world/world-a/snapshots")
        list_b = client.get("/api/world/world-b/snapshots")

        assert list_a.json()["total"] == 1
        assert list_b.json()["total"] == 1
        assert list_a.json()["snapshots"][0]["tick_number"] == 1
        assert list_b.json()["snapshots"][0]["tick_number"] == 2
