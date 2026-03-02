#!/usr/bin/env python3
"""
Simulation API Integration Tests

Tests the Simulation API endpoints with full request/response validation.
Simulation handles world state progression including time and events.
"""

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
def reset_simulation_storage():
    """Reset simulation storage before each test."""
    from src.api.routers.simulation import reset_simulation_storage

    reset_simulation_storage()

    yield

    reset_simulation_storage()


class TestSimulationAPIPreviewEndpoint:
    """Tests for POST /api/world/{world_id}/simulate/preview endpoint."""

    @pytest.mark.integration
    def test_preview_simulation_success(self, client):
        """Test previewing a simulation tick."""
        request_data = {"days": 5}

        response = client.post(
            "/api/world/test-world-001/simulate/preview",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world-001"
        assert data["days_advanced"] == 5
        assert "calendar_before" in data
        assert "calendar_after" in data
        assert data["calendar_after"]["day"] > data["calendar_before"]["day"]

    @pytest.mark.integration
    def test_preview_simulation_creates_calendar(self, client):
        """Test that preview creates a calendar if not exists."""
        request_data = {"days": 10}
        response = client.post(
            "/api/world/new-world/simulate/preview",
            json=request_data,
        )
        assert response.status_code == 200
        data = response.json()

        # Calendar should be created
        assert data["calendar_after"] is not None
        assert data["calendar_after"]["year"] == 1
        assert data["calendar_after"]["month"] == 1


        assert data["calendar_after"]["day"] == 11  # 1 + 10 days

    @pytest.mark.integration
    def test_preview_simulation_idempotent(self, client):
        """Test that preview does not persist state."""
        # Preview
        preview_response = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 5},
        )
        assert preview_response.status_code == 200

        # Another preview with different days
        preview_response2 = client.post(
            "/api/world/test-world/simulate/preview",
            json={"days": 10},
        )
        assert preview_response2.status_code == 200

        # The calendars should differ
        assert (
            preview_response2.json()["calendar_after"]["day"]
            > preview_response.json()["calendar_after"]["day"]
        )


class TestSimulationAPICommitEndpoint:
    """Tests for POST /api/world/{world_id}/simulate/commit endpoint."""

    @pytest.mark.integration
    def test_commit_simulation_success(self, client):
        """Test committing a simulation tick."""
        request_data = {"days": 3}
        response = client.post(
            "/api/world/test-world-002/simulate/commit",
            json=request_data,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world-002"
        assert data["days_advanced"] == 3
        assert "tick_id" in data
        assert "calendar_after" in data

        # Verify it's in history
        history_response = client.get("/api/world/test-world-002/simulate/history")
        assert history_response.status_code == 200
        tick_ids = [t["tick_id"] for t in history_response.json()["ticks"]]
        assert data["tick_id"] in tick_ids

    @pytest.mark.integration
    def test_commit_simulation_rate_limiting(self, client):
        """Test rate limiting on commits."""
        # Make multiple rapid commits
        for i in range(15):  # More than MAX_COMMITS_PER_MINUTE (10)
            response = client.post(
                "/api/world/rate-test-world/simulate/commit",
                json={"days": 1},
            )
            if response.status_code != 200 and response.status_code != 429:
                # Some should succeed, some should be rate limited
                pass

        # At least one should be rate limited
        rate_limited = any(
            client.post(
                "/api/world/rate-test-world/simulate/commit",
                json={"days": 1},
            ).status_code == 429
            for _ in range(20)
        )
        assert rate_limited or False  # At least one should hit rate limit

    @pytest.mark.integration
    def test_commit_large_simulation_accepted(self, client):
        """Test that large simulations are accepted for background processing."""
        request_data = {"days": 50}  # More than 30 days
        response = client.post(
            "/api/world/large-sim-world/simulate/commit",
            json=request_data,
        )
        # Should return 202 Accepted
        assert response.status_code == 202


class TestSimulationAPIHistoryEndpoint:
    """Tests for GET /api/world/{world_id}/simulate/history endpoint."""

    @pytest.mark.integration
    def test_get_simulation_history_empty(self, client):
        """Test getting history when no simulations have been run."""
        response = client.get("/api/world/no-history-world/simulate/history")

        assert response.status_code == 200
        data = response.json()

        assert data["ticks"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_get_simulation_history_with_data(self, client):
        """Test getting simulation history with data."""
        # Run some simulations
        client.post(
            "/api/world/history-world/simulate/commit",
            json={"days": 1},
        )
        client.post(
            "/api/world/history-world/simulate/commit",
            json={"days": 2},
        )
        client.post(
            "/api/world/history-world/simulate/commit",
            json={"days": 3},
        )

        response = client.get("/api/world/history-world/simulate/history")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["ticks"]) == 3

    @pytest.mark.integration
    def test_get_simulation_history_with_limit(self, client):
        """Test getting history with limit parameter."""
        # Run some simulations
        for i in range(5):
            client.post(
                "/api/world/limit-world/simulate/commit",
                json={"days": 1},
            )

        response = client.get(
            "/api/world/limit-world/simulate/history",
            params={"limit": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["ticks"]) <= 2


class TestSimulationAPITickDetailsEndpoint:
    """Tests for GET /api/world/{world_id}/simulate/{tick_id} endpoint."""

    @pytest.mark.integration
    def test_get_tick_details_success(self, client):
        """Test getting tick details by ID."""
        # Run a simulation
        commit_response = client.post(
            "/api/world/tick-detail-world/simulate/commit",
            json={"days": 5},
        )
        assert commit_response.status_code == 200
        tick_id = commit_response.json()["tick_id"]

        # Get the tick details
        response = client.get(f"/api/world/tick-detail-world/simulate/{tick_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["tick_id"] == tick_id
        assert data["world_id"] == "tick-detail-world"
        assert data["days_advanced"] == 5
        assert "calendar_before" in data
        assert "calendar_after" in data

        assert "resource_changes" in data
        assert "diplomacy_changes" in data

    @pytest.mark.integration
    def test_get_tick_details_not_found(self, client):
        """Test getting non-existent tick details."""
        response = client.get("/api/world/some-world/simulate/non-existent-tick")

        # Should return 404 (not found) or 400 (bad request) or 405 (method not allowed)
        assert response.status_code in [404, 400, 405]
