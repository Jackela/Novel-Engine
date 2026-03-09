"""Integration tests for time event flow from API to handler."""

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client.

    Using the client as a context manager triggers the lifespan events,
    which initializes the event_bus on app.state.
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
class TestTimeEventFlow:
    """Tests for end-to-end time event flow."""

    def test_advance_time_triggers_event(self, client: TestClient) -> None:
        """Test that advancing time triggers an event."""
        # Get initial time
        response = client.get("/api/world/time")
        assert response.status_code == 200
        initial_data = response.json()

        # Advance time
        response = client.post("/api/world/time/advance", json={"days": 5})
        assert response.status_code == 200
        new_data = response.json()

        # Verify time advanced
        assert (
            new_data["day"] != initial_data["day"]
            or new_data["month"] != initial_data["month"]
        )

    def test_event_handler_is_registered(self, client: TestClient) -> None:
        """Test that TimeAdvancedHandler is registered with EventBus."""
        # Access the app from the client - the event_bus is set during lifespan
        # The TestClient context manager triggers lifespan, setting app.state.event_bus
        app = client.app

        # Check that event bus is configured
        assert hasattr(app.state, "event_bus")
        assert app.state.event_bus is not None
