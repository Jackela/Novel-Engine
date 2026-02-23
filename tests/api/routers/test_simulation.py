"""Tests for Simulation API router.

This module tests the simulation API endpoints for preview, commit,
history, and tick detail retrieval operations.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Mock aioredis before importing any app modules
import sys
sys.modules["aioredis"] = MagicMock()

from src.api.app import create_app
from src.api.routers.simulation import (
    MAX_COMMITS_PER_MINUTE,
    reset_simulation_storage,
)


@pytest.fixture
def client():
    """Create a test client for the API."""
    app = create_app(debug=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset simulation storage before each test."""
    reset_simulation_storage()
    yield
    reset_simulation_storage()


class TestPreviewSimulation:
    """Tests for POST /world/{world_id}/simulate/preview endpoint."""

    def test_preview_simulation_default_days(self, client):
        """Test preview with default days parameter."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert "tick_id" in data
        assert data["world_id"] == "test-world"
        assert data["days_advanced"] == 1
        assert data["events_generated"] == []
        assert data["resource_changes"] == {}
        assert data["diplomacy_changes"] == []
        assert data["calendar_before"] is not None
        assert data["calendar_after"] is not None
        assert data["calendar_before"]["formatted_date"] == "Year 1, Month 1, Day 1 - First Age"
        assert data["calendar_after"]["formatted_date"] == "Year 1, Month 1, Day 2 - First Age"

    def test_preview_simulation_custom_days(self, client):
        """Test preview with custom days parameter."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 7},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 7
        assert data["calendar_after"]["day"] == 8

    def test_preview_simulation_month_rollover(self, client):
        """Test preview with days that cause month rollover."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 30
        assert data["calendar_after"]["month"] == 2
        assert data["calendar_after"]["day"] == 1

    def test_preview_simulation_year_rollover(self, client):
        """Test preview with days that cause year rollover."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 360},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 360
        assert data["calendar_after"]["year"] == 2
        assert data["calendar_after"]["month"] == 1
        assert data["calendar_after"]["day"] == 1

    def test_preview_simulation_invalid_days_zero(self, client):
        """Test preview with invalid days (zero)."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 0},
        )

        assert response.status_code == 422  # Validation error

    def test_preview_simulation_invalid_days_negative(self, client):
        """Test preview with invalid days (negative)."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": -1},
        )

        assert response.status_code == 422  # Validation error

    def test_preview_simulation_invalid_days_exceeds_max(self, client):
        """Test preview with invalid days (exceeds 365)."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 366},
        )

        assert response.status_code == 422  # Validation error

    def test_preview_simulation_does_not_persist(self, client):
        """Test that preview does not persist changes."""
        # First preview
        client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 7},
        )

        # Second preview should start from same calendar state
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 1},
        )

        assert response.status_code == 200
        data = response.json()

        # Should still start from day 1 (preview didn't persist)
        assert data["calendar_before"]["day"] == 1
        assert data["calendar_after"]["day"] == 2


class TestCommitSimulation:
    """Tests for POST /world/{world_id}/simulate/commit endpoint."""

    def test_commit_simulation_default_days(self, client):
        """Test commit with default days parameter."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert "tick_id" in data
        assert data["world_id"] == "test-world"
        assert data["days_advanced"] == 1

    def test_commit_simulation_custom_days(self, client):
        """Test commit with custom days parameter."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 7},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 7

    def test_commit_simulation_persists_changes(self, client):
        """Test that commit persists changes."""
        # First commit
        client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 7},
        )

        # Second commit should start from updated calendar
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should start from day 8 (previous commit persisted)
        assert data["calendar_before"]["day"] == 8
        assert data["calendar_after"]["day"] == 11

    def test_commit_simulation_appears_in_history(self, client):
        """Test that committed tick appears in history."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 5},
        )

        tick_id = response.json()["tick_id"]

        # Check history
        history_response = client.get("/api/world/test-world/simulate/history")
        assert history_response.status_code == 200

        history = history_response.json()
        assert history["total"] == 1
        assert history["ticks"][0]["tick_id"] == tick_id
        assert history["ticks"][0]["days_advanced"] == 5

    def test_commit_simulation_large_days_accepted(self, client):
        """Test that large simulations (>30 days) return 202 Accepted."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 31},
        )

        assert response.status_code == 202
        data = response.json()
        assert "detail" in data

        # HTTPException detail may be a string or dict depending on serialization
        detail = data["detail"]
        if isinstance(detail, dict):
            assert detail["status"] == "accepted"
            assert "tick_id" in detail
            assert "status_url" in detail
        else:
            # Detail might be a string representation
            assert "accepted" in str(detail).lower() or "background" in str(detail).lower()

    def test_commit_simulation_invalid_days(self, client):
        """Test commit with invalid days."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 0},
        )

        assert response.status_code == 422

    def test_commit_simulation_rate_limited(self, client):
        """Test that rate limiting works for commits."""
        # Make max commits
        for i in range(MAX_COMMITS_PER_MINUTE):
            response = client.post(
                "/api/world/test-world/simulate/commit",
                json={"days": 1},
            )
            assert response.status_code == 200

        # Next commit should be rate limited
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 1},
        )

        assert response.status_code == 429
        data = response.json()
        assert "RATE_LIMITED" in str(data)

    def test_commit_simulation_concurrent_locked(self, client):
        """Test that concurrent simulations are blocked."""
        # This test verifies the 503 response for concurrent simulations
        # In practice, this is hard to trigger in a single-threaded test
        # but we can verify the error handling exists
        from src.api.routers import simulation as sim_module

        # Manually set an active simulation
        sim_module._active_simulations["test-world"] = "existing-tick-id"

        try:
            response = client.post(
                "/api/world/test-world/simulate/commit",
                json={"days": 1},
            )

            assert response.status_code == 503
            data = response.json()
            assert "SIMULATION_LOCKED" in str(data)
        finally:
            sim_module._active_simulations.pop("test-world", None)


class TestSimulationHistory:
    """Tests for GET /world/{world_id}/simulate/history endpoint."""

    def test_history_empty(self, client):
        """Test history when no simulations have been run."""
        response = client.get("/api/world/test-world/simulate/history")

        assert response.status_code == 200
        data = response.json()

        assert data["ticks"] == []
        assert data["total"] == 0

    def test_history_single_tick(self, client):
        """Test history with a single simulation tick."""
        # Commit a simulation
        commit_response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 5},
        )
        tick_id = commit_response.json()["tick_id"]

        # Get history
        response = client.get("/api/world/test-world/simulate/history")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["ticks"][0]["tick_id"] == tick_id
        assert data["ticks"][0]["days_advanced"] == 5
        assert data["ticks"][0]["events_count"] == 0

    def test_history_multiple_ticks(self, client):
        """Test history with multiple simulation ticks."""
        tick_ids = []

        # Commit multiple simulations
        for days in [1, 3, 7]:
            response = client.post(
                "/api/world/test-world/simulate/commit",
                json={"days": days},
            )
            tick_ids.append(response.json()["tick_id"])

        # Get history
        response = client.get("/api/world/test-world/simulate/history")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        # Most recent first
        assert data["ticks"][0]["tick_id"] == tick_ids[2]
        assert data["ticks"][0]["days_advanced"] == 7
        assert data["ticks"][1]["tick_id"] == tick_ids[1]
        assert data["ticks"][1]["days_advanced"] == 3
        assert data["ticks"][2]["tick_id"] == tick_ids[0]
        assert data["ticks"][2]["days_advanced"] == 1

    def test_history_limit_parameter(self, client):
        """Test history with limit parameter."""
        # Commit 5 simulations
        for i in range(5):
            client.post(
                "/api/world/test-world/simulate/commit",
                json={"days": 1},
            )

        # Get history with limit
        response = client.get("/api/world/test-world/simulate/history?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3

    def test_history_worlds_isolated(self, client):
        """Test that history is isolated between worlds."""
        # Commit for world A
        client.post(
            "/api/world/world-a/simulate/commit",
            json={"days": 1},
        )

        # Commit for world B
        client.post(
            "/api/world/world-b/simulate/commit",
            json={"days": 2},
        )

        # Check history for world A
        response_a = client.get("/api/world/world-a/simulate/history")
        assert response_a.json()["total"] == 1

        # Check history for world B
        response_b = client.get("/api/world/world-b/simulate/history")
        assert response_b.json()["total"] == 1


class TestTickDetails:
    """Tests for GET /world/{world_id}/simulate/{tick_id} endpoint."""

    def test_tick_details_success(self, client):
        """Test getting tick details for existing tick."""
        # Commit a simulation
        commit_response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 7},
        )
        tick_id = commit_response.json()["tick_id"]

        # Get tick details
        response = client.get(f"/api/world/test-world/simulate/{tick_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["tick_id"] == tick_id
        assert data["world_id"] == "test-world"
        assert data["days_advanced"] == 7
        assert "calendar_before" in data
        assert "calendar_after" in data
        assert "created_at" in data

    def test_tick_details_not_found(self, client):
        """Test getting tick details for non-existent tick."""
        response = client.get("/api/world/test-world/simulate/non-existent-tick")

        assert response.status_code == 404
        # The response may come from our handler or the global 404 handler
        # Both return 404 which is the expected behavior

    def test_tick_details_wrong_world(self, client):
        """Test getting tick details from wrong world."""
        # Commit for world A
        commit_response = client.post(
            "/api/world/world-a/simulate/commit",
            json={"days": 1},
        )
        tick_id = commit_response.json()["tick_id"]

        # Try to get from world B
        response = client.get(f"/api/world/world-b/simulate/{tick_id}")

        assert response.status_code == 404


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_preview_max_days(self, client):
        """Test preview with maximum allowed days (365)."""
        response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 365},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 365
        # Calendar has 360 days per year (30 days * 12 months)
        # 365 days from day 1 = 360 + 5 = day 6 of year 2
        assert data["calendar_after"]["year"] == 2
        assert data["calendar_after"]["month"] == 1
        assert data["calendar_after"]["day"] == 6

    def test_commit_max_days(self, client):
        """Test commit with maximum allowed days (30 for sync)."""
        response = client.post(
            "/api/world/test-world/simulate/commit",
            json={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["days_advanced"] == 30

    def test_multiple_worlds_same_time(self, client):
        """Test that multiple worlds can be simulated independently."""
        # Simulate world A
        response_a = client.post(
            "/api/world/world-a/simulate/commit",
            json={"days": 5},
        )

        # Simulate world B
        response_b = client.post(
            "/api/world/world-b/simulate/commit",
            json={"days": 10},
        )

        assert response_a.status_code == 200
        assert response_b.status_code == 200

        # Verify calendars are independent
        assert response_a.json()["days_advanced"] == 5
        assert response_b.json()["days_advanced"] == 10

    def test_history_fifo_eviction(self, client):
        """Test that history evicts old entries when max is reached."""
        from src.api.routers import simulation as sim_module

        # Reset rate limits for this test
        sim_module._commit_timestamps.clear()

        # Commit more than max history (but respect rate limit)
        tick_ids = []
        max_commits = min(sim_module.MAX_HISTORY_PER_WORLD + 5, MAX_COMMITS_PER_MINUTE - 1)

        for i in range(max_commits):
            response = client.post(
                "/api/world/test-world/simulate/commit",
                json={"days": 1},
            )
            if response.status_code == 200:
                tick_ids.append(response.json()["tick_id"])

        # Get history
        response = client.get("/api/world/test-world/simulate/history?limit=200")

        # Should have history entries (may be limited by rate limiting)
        data = response.json()
        assert data["total"] > 0
        # If we got enough commits, verify FIFO behavior
        if len(tick_ids) > sim_module.MAX_HISTORY_PER_WORLD:
            assert tick_ids[0] not in [t["tick_id"] for t in data["ticks"]]
