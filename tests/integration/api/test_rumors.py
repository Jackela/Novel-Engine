"""Integration tests for Rumors API endpoints.

Tests the rumor system endpoints for listing, filtering, and retrieving rumors.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.routers.rumors import reset_rumors_storage


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestRumorsEndpoints:
    """Tests for rumors management endpoints."""

    def test_list_rumors(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors endpoint."""
        response = client.get("/api/world/test-world/rumors")

        assert response.status_code == 200
        data = response.json()
        assert "rumors" in data
        assert "total" in data
        assert isinstance(data["rumors"], list)

    def test_list_rumors_with_location_filter(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors with location filter."""
        response = client.get(
            "/api/world/test-world/rumors?location_id=loc-capital"
        )

        assert response.status_code == 200
        data = response.json()
        assert "rumors" in data

    def test_list_rumors_with_sorting(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors with sorting."""
        # Test sort by recent
        response = client.get("/api/world/test-world/rumors?sort_by=recent")
        assert response.status_code == 200

        # Test sort by reliable
        response = client.get("/api/world/test-world/rumors?sort_by=reliable")
        assert response.status_code == 200

        # Test sort by spread
        response = client.get("/api/world/test-world/rumors?sort_by=spread")
        assert response.status_code == 200

    def test_list_rumors_with_limit(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors with limit."""
        response = client.get("/api/world/test-world/rumors?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["rumors"]) <= 2

    def test_get_rumor_by_id(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors/{rumor_id} endpoint."""
        # First get list to find a rumor ID
        list_response = client.get("/api/world/test-world/rumors")
        rumors = list_response.json()["rumors"]

        if rumors:
            rumor_id = rumors[0]["rumor_id"]
            response = client.get(f"/api/world/test-world/rumors/{rumor_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["rumor_id"] == rumor_id

    def test_get_nonexistent_rumor(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors/{rumor_id} with invalid ID."""
        response = client.get("/api/world/test-world/rumors/nonexistent-rumor-id")

        assert response.status_code == 404


@pytest.mark.integration
class TestRumorsResponseFormat:
    """Tests for rumors response format validation."""

    def test_rumor_list_response_format(self, client: TestClient) -> None:
        """Test that rumor list response has correct format."""
        response = client.get("/api/world/test-world/rumors")

        assert response.status_code == 200
        data = response.json()

        # Top-level fields
        assert "rumors" in data
        assert "total" in data
        assert isinstance(data["rumors"], list)
        assert isinstance(data["total"], int)

    def test_rumor_response_format(self, client: TestClient) -> None:
        """Test that individual rumor response has correct format."""
        list_response = client.get("/api/world/test-world/rumors")
        rumors = list_response.json()["rumors"]

        if rumors:
            rumor = rumors[0]

            # Required fields
            assert "rumor_id" in rumor
            assert "content" in rumor
            assert "truth_value" in rumor
            assert "origin_type" in rumor
            assert "origin_location_id" in rumor
            assert "current_locations" in rumor
            assert "spread_count" in rumor
            assert "veracity_label" in rumor

            # Type validation
            assert isinstance(rumor["content"], str)
            assert isinstance(rumor["truth_value"], int)
            assert isinstance(rumor["current_locations"], list)

    def test_created_date_format(self, client: TestClient) -> None:
        """Test that created_date has correct format."""
        list_response = client.get("/api/world/test-world/rumors")
        rumors = list_response.json()["rumors"]

        if rumors and rumors[0].get("created_date"):
            created_date = rumors[0]["created_date"]

            # Calendar data fields
            assert "year" in created_date
            assert "month" in created_date
            assert "day" in created_date
            assert "formatted" in created_date


@pytest.mark.integration
class TestRumorsFiltering:
    """Tests for rumors filtering and sorting behavior."""

    def test_sort_by_reliable_orders_by_truth_value(
        self, client: TestClient
    ) -> None:
        """Test that sort_by=reliable orders by truth_value descending."""
        response = client.get("/api/world/test-world/rumors?sort_by=reliable")
        assert response.status_code == 200

        rumors = response.json()["rumors"]
        if len(rumors) > 1:
            # Each rumor should have truth_value >= next one
            for i in range(len(rumors) - 1):
                assert rumors[i]["truth_value"] >= rumors[i + 1]["truth_value"]

    def test_sort_by_spread_orders_by_spread_count(
        self, client: TestClient
    ) -> None:
        """Test that sort_by=spread orders by spread_count descending."""
        response = client.get("/api/world/test-world/rumors?sort_by=spread")
        assert response.status_code == 200

        rumors = response.json()["rumors"]
        if len(rumors) > 1:
            for i in range(len(rumors) - 1):
                assert rumors[i]["spread_count"] >= rumors[i + 1]["spread_count"]

    def test_location_filter_returns_matching_rumors(
        self, client: TestClient
    ) -> None:
        """Test that location filter only returns rumors at that location."""
        location_id = "loc-capital"
        response = client.get(
            f"/api/world/test-world/rumors?location_id={location_id}"
        )

        assert response.status_code == 200
        rumors = response.json()["rumors"]

        for rumor in rumors:
            assert location_id in rumor["current_locations"]


@pytest.mark.integration
class TestRumorsValidation:
    """Tests for rumors endpoint validation."""

    def test_limit_bounds(self, client: TestClient) -> None:
        """Test that limit must be between 1 and 100."""
        # Test lower bound
        response = client.get("/api/world/test-world/rumors?limit=0")
        assert response.status_code == 422

        # Test upper bound
        response = client.get("/api/world/test-world/rumors?limit=101")
        assert response.status_code == 422

        # Valid limits
        response = client.get("/api/world/test-world/rumors?limit=1")
        assert response.status_code == 200

        response = client.get("/api/world/test-world/rumors?limit=100")
        assert response.status_code == 200

    def test_invalid_sort_by(self, client: TestClient) -> None:
        """Test that invalid sort_by value is handled."""
        response = client.get("/api/world/test-world/rumors?sort_by=invalid")

        # Should either default to a valid value or return 422
        assert response.status_code in [200, 422]


@pytest.mark.integration
class TestRumorsVeracityLabels:
    """Tests for rumor veracity label behavior."""

    def test_veracity_label_matches_truth_value(
        self, client: TestClient
    ) -> None:
        """Test that veracity_label corresponds to truth_value."""
        response = client.get("/api/world/test-world/rumors")
        rumors = response.json()["rumors"]

        for rumor in rumors:
            truth_value = rumor["truth_value"]
            label = rumor["veracity_label"]

            # Check label consistency with truth value
            if truth_value >= 80:
                assert label in ["Confirmed", "True"]
            elif truth_value >= 60:
                assert label in ["Likely True", "Probable"]
            elif truth_value >= 40:
                assert label in ["Uncertain", "Mixed"]
            elif truth_value >= 20:
                assert label in ["Likely False", "Doubtful"]
            else:
                assert label in ["False", "Debunked"]
