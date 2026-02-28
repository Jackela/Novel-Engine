"""Tests for the World Time API router.

Verifies the endpoints for managing world time operations including
retrieving and advancing the world time.
"""

import pytest
from fastapi.testclient import TestClient

import api_server
from src.api.routers.world_time import _repository, _service

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory calendar storage before each test.

    Why this fixture:
        Ensures test isolation by clearing calendar state between tests,
        preventing data pollution across test cases.
    """
    _repository.clear()
    _service.clear_pending_events()
    yield
    _repository.clear()
    _service.clear_pending_events()


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(api_server.app)


@pytest.mark.integration
class TestWorldTimeEndpoints:
    """Tests for world time API operations."""

    def test_get_world_time_default(self, client):
        """Getting world time returns default calendar state."""
        response = client.get("/api/world/time")
        assert response.status_code == 200
        data = response.json()

        # Default calendar state
        assert data["year"] == 1
        assert data["month"] == 1
        assert data["day"] == 1
        assert data["era_name"] == "First Age"
        assert "display_string" in data
        assert data["display_string"] == "Year 1, Month 1, Day 1 - First Age"

    def test_get_world_time_after_advance(self, client):
        """Getting world time after advance shows updated state."""
        # Advance time first
        client.post("/api/world/time/advance", json={"days": 5})

        response = client.get("/api/world/time")
        assert response.status_code == 200
        data = response.json()

        assert data["day"] == 6  # 1 + 5 = 6

    def test_advance_world_time_success(self, client):
        """Advancing world time returns updated calendar state."""
        response = client.post(
            "/api/world/time/advance",
            json={"days": 15},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["year"] == 1
        assert data["month"] == 1
        assert data["day"] == 16  # 1 + 15 = 16

    def test_advance_world_time_month_rollover(self, client):
        """Advancing past month end rolls over to next month."""
        # Advance to day 28 first, then add 5 more days
        client.post("/api/world/time/advance", json={"days": 27})  # day 28
        response = client.post("/api/world/time/advance", json={"days": 5})

        assert response.status_code == 200
        data = response.json()
        assert data["month"] == 2
        assert data["day"] == 3  # 28 + 5 = 33, 33 - 30 = 3

    def test_advance_world_time_year_rollover(self, client):
        """Advancing past year end rolls over to next year."""
        # Set up: advance to day 28 of month 12
        # 11 months * 30 days = 330 days to reach month 12, day 1
        # +27 more days to reach day 28
        client.post("/api/world/time/advance", json={"days": 357})  # Month 12, day 28
        response = client.post("/api/world/time/advance", json={"days": 5})

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2
        assert data["month"] == 1
        assert data["day"] == 3

    def test_advance_time_invalid_days_zero(self, client):
        """Advancing with 0 days returns validation error."""
        response = client.post(
            "/api/world/time/advance",
            json={"days": 0},
        )
        assert response.status_code == 422  # Validation error

    def test_advance_time_invalid_days_negative(self, client):
        """Advancing with negative days returns validation error."""
        response = client.post(
            "/api/world/time/advance",
            json={"days": -5},
        )
        assert response.status_code == 422  # Validation error

    def test_advance_time_missing_days_parameter(self, client):
        """Advancing without days parameter returns validation error."""
        response = client.post(
            "/api/world/time/advance",
            json={},
        )
        assert response.status_code == 422  # Validation error

    def test_display_string_format(self, client):
        """Display string follows expected format."""
        # Advance to a specific date: Year 2, Month 5, Day 14
        # 1 year = 360 days, so 360 + 4 months * 30 + 13 days = 360 + 120 + 13 = 493
        client.post("/api/world/time/advance", json={"days": 493})

        response = client.get("/api/world/time")
        assert response.status_code == 200
        data = response.json()

        assert data["year"] == 2
        assert data["month"] == 5
        assert data["day"] == 14
        assert "display_string" in data

    def test_response_includes_all_required_fields(self, client):
        """Response includes all required fields per spec."""
        response = client.get("/api/world/time")
        assert response.status_code == 200
        data = response.json()

        required_fields = ["year", "month", "day", "era_name", "display_string"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_sequential_advances_accumulate(self, client):
        """Multiple advances accumulate correctly."""
        client.post("/api/world/time/advance", json={"days": 5})
        client.post("/api/world/time/advance", json={"days": 10})
        response = client.post("/api/world/time/advance", json={"days": 3})

        assert response.status_code == 200
        data = response.json()
        assert data["day"] == 19  # 1 + 5 + 10 + 3 = 19

    def test_large_advance_multiple_years(self, client):
        """Advancing multiple years works correctly."""
        # Advance 720 days = 2 years
        response = client.post("/api/world/time/advance", json={"days": 720})
        assert response.status_code == 200
        data = response.json()

        assert data["year"] == 3  # Year 1 + 2 years = Year 3
        assert data["month"] == 1
        assert data["day"] == 1

    def test_advance_time_service_error_returns_400(self, client, monkeypatch):
        """When service returns an error, API returns 400 with proper error detail."""
        from src.core.result import Err

        def mock_advance_time(world_id, days):
            return Err("Simulated service failure")

        monkeypatch.setattr(_service, "advance_time", mock_advance_time)

        response = client.post(
            "/api/world/time/advance",
            json={"days": 5},
        )

        assert response.status_code == 400
        data = response.json()
        # The app's exception handler wraps the detail
        assert "error" in data
        assert data["error"] == "Bad Request"
        assert "detail" in data
        # Detail contains the error code and message from our ErrorDetail
        assert "TIME_ADVANCE_FAILED" in str(data["detail"])
        assert "Simulated service failure" in str(data["detail"])


@pytest.mark.integration
class TestWorldTimeEventBusWiring:
    """Tests for event bus wiring in world_time router."""

    def test_event_bus_is_configured_on_startup(self) -> None:
        """Test that the event bus is configured when app starts."""
        from src.api.app import create_app
        from fastapi.testclient import TestClient

        # Create app and use TestClient to trigger the lifespan
        app = create_app()

        # The world_time router should have access to event bus
        from src.api.routers import world_time

        # Reset the event bus to None to simulate fresh start
        world_time._event_bus = None

        # Use TestClient to trigger the lifespan (startup/shutdown)
        with TestClient(app):
            # Inside the context, the startup event should have wired the event bus
            assert world_time._event_bus is not None, "Event bus should be wired on startup"
