"""Integration tests for Events API endpoints.

Tests SSE streaming, analytics, and historical events endpoints.
"""

import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app
from src.api.routers.events import reset_events_storage

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Events API."""
    app = create_app()
    reset_events_storage()
    with TestClient(app) as test_client:
        yield test_client
    reset_events_storage()


class TestEventStreamEndpoint:
    """Tests for GET /api/events/stream endpoint.

    Note: SSE streaming endpoints hang with synchronous TestClient.
    These tests are skipped because they require async HTTP client.
    """

    @pytest.mark.skip(reason="SSE streaming hangs with sync TestClient - requires async client")
    def test_stream_events_returns_sse(self, client):
        """Test that stream endpoint returns SSE content type."""
        response = client.get("/api/events/stream")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.skip(reason="SSE streaming hangs with sync TestClient - requires async client")
    def test_stream_events_with_limit(self, client):
        """Test streaming events with a limit."""
        # This test just verifies the endpoint accepts the parameter
        response = client.get("/api/events/stream?limit=5")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.skip(reason="SSE streaming hangs with sync TestClient - requires async client")
    def test_stream_events_with_interval(self, client):
        """Test streaming events with custom interval."""
        response = client.get("/api/events/stream?interval=1.0")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


class TestEmitEventEndpoint:
    """Tests for POST /api/events/emit endpoint."""

    def test_emit_event_success(self, client):
        """Test emitting an event returns success."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "system",
                "title": "Test Event",
                "description": "A test event description",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "event_id" in data
        assert "connected_clients" in data

    def test_emit_event_with_character(self, client):
        """Test emitting a character event."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "character",
                "title": "Character Action",
                "description": "A character did something",
                "character_name": "Hero",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "event_id" in data

    def test_emit_event_with_severity(self, client):
        """Test emitting event with severity level."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "system",
                "title": "Critical Alert",
                "description": "Something critical happened",
                "severity": "high",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_emit_event_missing_title(self, client):
        """Test emitting event without title returns 422."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "system",
                "description": "Missing title",
            },
        )

        assert response.status_code == 422

    def test_emit_event_missing_description(self, client):
        """Test emitting event without description returns 422."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "system",
                "title": "Missing description",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "event_type",
        ["character", "story", "system", "interaction"],
    )
    def test_emit_event_various_types(self, client, event_type):
        """Test emitting events with various types."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": event_type,
                "title": f"Test {event_type}",
                "description": f"Testing {event_type} event type",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.parametrize("severity", ["low", "medium", "high"])
    def test_emit_event_various_severities(self, client, severity):
        """Test emitting events with various severities."""
        response = client.post(
            "/api/events/emit",
            json={
                "type": "system",
                "title": f"Test {severity}",
                "description": f"Testing {severity} severity",
                "severity": severity,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestSSEStatsEndpoint:
    """Tests for GET /api/events/stats endpoint."""

    def test_get_sse_stats_success(self, client):
        """Test getting SSE statistics."""
        response = client.get("/api/events/stats")

        assert response.status_code == 200
        data = response.json()

        assert "connected_clients" in data
        assert "total_events_sent" in data

    def test_get_sse_stats_returns_integers(self, client):
        """Test that SSE stats return integer values."""
        response = client.get("/api/events/stats")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["connected_clients"], int)
        assert isinstance(data["total_events_sent"], int)


class TestAnalyticsMetricsEndpoint:
    """Tests for GET /api/analytics/metrics endpoint."""

    def test_get_analytics_metrics_success(self, client):
        """Test getting analytics metrics."""
        response = client.get("/api/analytics/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check for expected metric fields
        # The actual structure depends on the implementation
        assert isinstance(data, dict)


class TestHistoricalEventsEndpoints:
    """Tests for historical events CRUD endpoints."""

    def test_list_historical_events_empty(self, client):
        """Test listing events when none exist."""
        response = client.get("/api/world/test-world-empty/events")

        assert response.status_code == 200
        data = response.json()

        assert "events" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total_count"] == 0
        assert data["events"] == []

    def test_create_historical_event_success(self, client):
        """Test creating a historical event."""
        response = client.post(
            "/api/world/test-world-events/events",
            json={
                "name": "The Great Battle",
                "description": "A pivotal battle in the war",
                "event_type": "battle",
                "significance": "major",
                "outcome": "positive",
                "date_description": "Year 5, Month 3",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "The Great Battle"
        assert data["event_type"] == "battle"
        assert "id" in data

    def test_create_event_with_all_fields(self, client):
        """Test creating event with all optional fields."""
        response = client.post(
            "/api/world/full-event-world/events",
            json={
                "name": "Complex Event",
                "description": "A complex historical event",
                "event_type": "treaty",
                "significance": "major",
                "outcome": "mixed",
                "date_description": "Year 10",
                "duration_description": "3 months",
                "location_ids": ["loc-1", "loc-2"],
                "faction_ids": ["faction-1"],
                "key_figures": ["King Arthur", "Merlin"],
                "causes": ["Political tension"],
                "consequences": ["Peace treaty signed"],
                "is_secret": False,
                "narrative_importance": 8,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Complex Event"
        assert len(data["location_ids"]) == 2
        assert len(data["key_figures"]) == 2

    def test_create_event_invalid_type(self, client):
        """Test creating event with invalid type returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Bad Event",
                "description": "Invalid event type",
                "event_type": "invalid_type",
                "significance": "major",
                "outcome": "positive",
            },
        )

        # May return 400 (bad request) or 422 (validation error)
        assert response.status_code in [400, 422]

    def test_create_event_invalid_significance(self, client):
        """Test creating event with invalid significance returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Bad Event",
                "description": "Invalid significance",
                "event_type": "battle",
                "significance": "invalid",
                "outcome": "positive",
            },
        )

        # May return 400 (bad request) or 422 (validation error)
        assert response.status_code in [400, 422]

    def test_create_event_missing_required_fields(self, client):
        """Test creating event without required fields returns 422."""
        response = client.post(
            "/api/world/test-world/events",
            json={"name": "Incomplete Event"},
        )

        assert response.status_code == 422

    def test_get_historical_event_success(self, client):
        """Test getting a specific historical event."""
        # Create an event first
        create_response = client.post(
            "/api/world/get-event-world/events",
            json={
                "name": "Event to Retrieve",
                "description": "This event will be retrieved",
                "event_type": "discovery",
                "significance": "minor",
                "outcome": "positive",
                "date_description": "Year 1",
            },
        )
        assert create_response.status_code == 201
        event_id = create_response.json()["id"]

        # Get the event
        response = client.get(f"/api/world/get-event-world/events/{event_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == event_id
        assert data["name"] == "Event to Retrieve"

    def test_get_historical_event_not_found(self, client):
        """Test getting non-existent event returns 404."""
        response = client.get("/api/world/test-world/events/nonexistent-id")

        assert response.status_code == 404

    def test_list_events_with_pagination(self, client):
        """Test listing events with pagination."""
        # Create multiple events
        for i in range(5):
            client.post(
                "/api/world/pagination-world/events",
                json={
                    "name": f"Event {i}",
                    "description": f"Description {i}",
                    "event_type": "battle",
                    "significance": "minor",
                    "outcome": "neutral",
                    "date_description": f"Year {i}",
                },
            )

        # Get first page
        response = client.get(
            "/api/world/pagination-world/events?page=1&page_size=2"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["events"]) <= 2
        assert data["total_count"] == 5

    def test_list_events_with_type_filter(self, client):
        """Test filtering events by type."""
        # Create events of different types
        client.post(
            "/api/world/filter-world/events",
            json={
                "name": "Battle Event",
                "description": "A battle",
                "event_type": "battle",
                "significance": "major",
                "outcome": "positive",
            },
        )
        client.post(
            "/api/world/filter-world/events",
            json={
                "name": "Treaty Event",
                "description": "A treaty",
                "event_type": "treaty",
                "significance": "major",
                "outcome": "positive",
            },
        )

        # Filter by battle
        response = client.get("/api/world/filter-world/events?event_type=battle")

        assert response.status_code == 200
        data = response.json()

        # Should only return battle events
        for event in data["events"]:
            assert event["event_type"] == "battle"

    def test_list_events_with_faction_filter(self, client):
        """Test filtering events by faction."""
        # Create event with faction
        client.post(
            "/api/world/faction-filter-world/events",
            json={
                "name": "Faction Event",
                "description": "Involves a faction",
                "event_type": "battle",
                "significance": "major",
                "outcome": "positive",
                "date_description": "Year 5, Month 3",
                "faction_ids": ["red-faction", "blue-faction"],
            },
        )
        client.post(
            "/api/world/faction-filter-world/events",
            json={
                "name": "No Faction Event",
                "description": "No factions involved",
                "event_type": "discovery",
                "significance": "minor",
                "outcome": "positive",
                "date_description": "Year 6, Month 1",
                "faction_ids": [],
            },
        )

        # Filter by faction
        response = client.get(
            "/api/world/faction-filter-world/events?faction_id=red-faction"
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return events with red-faction
        assert len(data["events"]) >= 1

    def test_list_events_with_secret_filter(self, client):
        """Test filtering events by secret status."""
        # Create secret and public events
        client.post(
            "/api/world/secret-world/events",
            json={
                "name": "Secret Event",
                "description": "A secret",
                "event_type": "betrayal",
                "significance": "major",
                "outcome": "negative",
                "is_secret": True,
            },
        )
        client.post(
            "/api/world/secret-world/events",
            json={
                "name": "Public Event",
                "description": "Public knowledge",
                "event_type": "cultural",
                "significance": "minor",
                "outcome": "positive",
                "is_secret": False,
            },
        )

        # Filter for secret events
        response = client.get("/api/world/secret-world/events?is_secret=true")

        assert response.status_code == 200
        data = response.json()

        for event in data["events"]:
            assert event["is_secret"] is True


class TestEventTypes:
    """Tests for valid event types and outcomes."""

    @pytest.mark.parametrize(
        "event_type",
        [
            "war",
            "battle",
            "treaty",
            "discovery",
            "founding",
            "destruction",
            "betrayal",
            "coronation",
            "disaster",
            "revolution",
            "religious",
            "cultural",
            "economic",
            "conquest",
            "alliance",
        ],
    )
    def test_create_event_with_valid_type(self, client, event_type):
        """Test creating events with all valid types."""
        response = client.post(
            "/api/world/types-world/events",
            json={
                "name": f"Test {event_type}",
                "description": f"Testing {event_type}",
                "event_type": event_type,
                "significance": "minor",
                "outcome": "neutral",
                "date_description": "Year 1",
            },
        )

        assert response.status_code == 201
        assert response.json()["event_type"] == event_type

    @pytest.mark.parametrize(
        "outcome",
        [
            "positive",
            "negative",
            "neutral",
            "mixed",
            "unknown",
        ],
    )
    def test_create_event_with_valid_outcome(self, client, outcome):
        """Test creating events with all valid outcomes."""
        response = client.post(
            "/api/world/outcomes-world/events",
            json={
                "name": f"Test {outcome}",
                "description": f"Testing {outcome}",
                "event_type": "battle",
                "significance": "minor",
                "outcome": outcome,
                "date_description": "Year 1",
            },
        )

        assert response.status_code == 201
        assert response.json()["outcome"] == outcome
