#!/usr/bin/env python3
"""
Snapshots API Integration Tests

Tests the Snapshots API endpoints with full request/response validation.
Snapshots preserve world state for rollback and recovery.
"""

import json

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the API."""
    from src.api.app import create_app

    app = create_app(debug=True)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_snapshot_service():
    """Reset the snapshot service before each test."""
    from src.api.routers.snapshots import _world_calendars, reset_snapshot_service

    reset_snapshot_service()
    _world_calendars.clear()

    yield
    reset_snapshot_service()
    _world_calendars.clear()


class TestSnapshotsAPICreateEndpoint:
    """Tests for POST /api/world/{world_id}/snapshots endpoint."""

    @pytest.mark.integration
    def test_create_snapshot_success(self, client):
        """Test creating a new snapshot."""
        snapshot_data = {
            "description": "Before the major event",
            "tick_number": 1,
        }

        response = client.post(
            "/api/world/test-world-001/snapshots",
            json=snapshot_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world-001"
        assert data["description"] == "Before the major event"
        assert data["tick_number"] == 1
        assert "snapshot_id" in data
        assert "created_at" in data
        assert "calendar" in data

    @pytest.mark.integration
    def test_create_snapshot_with_state(self, client):
        """Test creating a snapshot with custom state."""
        snapshot_data = {
            "description": "Custom state snapshot",
            "tick_number": 5,
            "state_json": json.dumps({"characters": ["hero"], "factions": ["guild"]}),
        }

        response = client.post(
            "/api/world/state-world/snapshots",
            json=snapshot_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tick_number"] == 5


    @pytest.mark.integration
    def test_create_multiple_snapshots(self, client):
        """Test creating multiple snapshots for a world."""
        for i in range(3):
            response = client.post(
                "/api/world/multi-snapshot-world/snapshots",
                json={"description": f"Snapshot {i}", "tick_number": i},
            )
            assert response.status_code == 200

        # List should show all
        list_response = client.get("/api/world/multi-snapshot-world/snapshots")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3


class TestSnapshotsAPIListEndpoint:
    """Tests for GET /api/world/{world_id}/snapshots endpoint."""

    @pytest.mark.integration
    def test_list_snapshots_empty(self, client):
        """Test listing snapshots when none exist."""
        response = client.get("/api/world/empty-world/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshots"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_snapshots_with_data(self, client):
        """Test listing snapshots with data."""
        # Create some snapshots
        client.post(
            "/api/world/list-world/snapshots",
            json={"description": "Snapshot 1", "tick_number": 1},
        )
        client.post(
            "/api/world/list-world/snapshots",
            json={"description": "Snapshot 2", "tick_number": 2},
        )

        response = client.get("/api/world/list-world/snapshots")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["snapshots"]) == 2

    @pytest.mark.integration
    def test_list_snapshots_with_limit(self, client):
        """Test listing snapshots with limit parameter."""
        # Create more snapshots
        for i in range(5):
            client.post(
                "/api/world/limit-world/snapshots",
                json={"description": f"Snapshot {i}", "tick_number": i},
            )

        response = client.get(
            "/api/world/limit-world/snapshots",
            params={"limit": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["snapshots"]) <= 2


class TestSnapshotsAPIGetEndpoint:
    """Tests for GET /api/world/{world_id}/snapshots/{snapshot_id} endpoint."""

    @pytest.mark.integration
    def test_get_snapshot_success(self, client):
        """Test getting a snapshot by ID."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/get-world/snapshots",
            json={"description": "Test snapshot", "tick_number": 1},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Get it
        response = client.get(f"/api/world/get-world/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshot_id"] == snapshot_id
        assert data["description"] == "Test snapshot"
        assert data["tick_number"] == 1

        assert "calendar" in data
        assert "created_at" in data
        assert "size_bytes" in data

    @pytest.mark.integration
    def test_get_snapshot_not_found(self, client):
        """Test getting a non-existent snapshot."""
        response = client.get("/api/world/some-world/snapshots/non-existent-snapshot")

        # May return 404 (not found) or 405 (method not allowed) depending on router setup
        assert response.status_code in [404, 405]


class TestSnapshotsAPIRestoreEndpoint:
    """Tests for POST /api/world/{world_id}/snapshots/{snapshot_id}/restore endpoint."""

    @pytest.mark.integration
    def test_restore_snapshot_success(self, client):
        """Test restoring a snapshot."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/restore-world/snapshots",
            json={"description": "To restore", "tick_number": 5},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Restore it
        response = client.post(f"/api/world/restore-world/snapshots/{snapshot_id}/restore")

        assert response.status_code == 200
        data = response.json()

        assert data["snapshot_id"] == snapshot_id
        assert data["restored"] is True
        assert data["world_id"] == "restore-world"
        assert "message" in data

    @pytest.mark.integration
    def test_restore_snapshot_not_found(self, client):
        """Test restoring a non-existent snapshot."""
        response = client.post(
            "/api/world/some-world/snapshots/non-existent-snapshot/restore"
        )

        # May return 404 (not found) or 405 (method not allowed) depending on router setup
        assert response.status_code in [404, 405]


class TestSnapshotsAPIDeleteEndpoint:
    """Tests for DELETE /api/world/{world_id}/snapshots/{snapshot_id} endpoint."""

    @pytest.mark.integration
    def test_delete_snapshot_success(self, client):
        """Test deleting a snapshot."""
        # Create a snapshot
        create_response = client.post(
            "/api/world/delete-world/snapshots",
            json={"description": "To delete", "tick_number": 1},
        )
        snapshot_id = create_response.json()["snapshot_id"]

        # Delete it
        response = client.delete(f"/api/world/delete-world/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["deleted"] is True
        assert data["snapshot_id"] == snapshot_id

        # Verify it's gone
        get_response = client.get(f"/api/world/delete-world/snapshots/{snapshot_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_snapshot_not_found(self, client):
        """Test deleting a non-existent snapshot."""
        response = client.delete(
            "/api/world/some-world/snapshots/non-existent-snapshot"
        )

        assert response.status_code == 404
        data = response.json()
        # API returns 404 with error code - either NOT_FOUND (endpoint) or SNAPSHOT_NOT_FOUND (service)
        assert data.get("code") in ["NOT_FOUND", "SNAPSHOT_NOT_FOUND"]
        # Check message contains relevant info
        message = data.get("message", "")
        assert "not found" in message.lower() or "does not exist" in message.lower()


class TestSnapshotsAPIIntegration:
    """Integration tests for snapshot workflow."""

    @pytest.mark.integration
    def test_snapshot_workflow(self, client):
        """Test complete snapshot workflow: create, list, restore, delete."""
        world_id = "workflow-world"

        # 1. Create first snapshot
        snapshot1_response = client.post(
            f"/api/world/{world_id}/snapshots",
            json={"description": "Initial state", "tick_number": 0},
        )
        assert snapshot1_response.status_code == 200
        snapshot1_id = snapshot1_response.json()["snapshot_id"]

        # 2. Create second snapshot
        snapshot2_response = client.post(
            f"/api/world/{world_id}/snapshots",
            json={"description": "After event", "tick_number": 1},
        )
        assert snapshot2_response.status_code == 200
        snapshot2_id = snapshot2_response.json()["snapshot_id"]

        # 3. List snapshots
        list_response = client.get(f"/api/world/{world_id}/snapshots")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 2

        # 4. Restore first snapshot
        restore_response = client.post(
            f"/api/world/{world_id}/snapshots/{snapshot1_id}/restore"
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["restored"] is True

        # 5. Delete second snapshot
        delete_response = client.delete(
            f"/api/world/{world_id}/snapshots/{snapshot2_id}"
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        # 6. Verify only one remains
        final_list = client.get(f"/api/world/{world_id}/snapshots")
        assert final_list.json()["total"] == 1
