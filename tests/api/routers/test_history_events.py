"""Tests for the Historical Events API router.

Verifies the endpoints for managing historical events including
creating, listing, and retrieving events with filtering and pagination.
"""

import pytest
from fastapi.testclient import TestClient

import api_server
from src.api.routers.events import reset_events_storage

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory events storage before each test.

    Why this fixture:
        Ensures test isolation by clearing events state between tests,
        preventing data pollution across test cases.
    """
    reset_events_storage()
    yield
    reset_events_storage()


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(api_server.app)


@pytest.mark.integration
class TestListHistoricalEvents:
    """Tests for listing historical events."""

    def test_list_events_empty_world(self, client):
        """Listing events for empty world returns empty list."""
        response = client.get("/api/world/test-world/events")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total_count"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0

    def test_list_events_with_events(self, client):
        """Listing events returns all events for the world."""
        # Create an event first
        create_response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "The Great War",
                "description": "A devastating conflict.",
                "event_type": "war",
                "significance": "major",
                "outcome": "mixed",
                "date_description": "Year 1042 of the Third Age",
            },
        )
        assert create_response.status_code == 201

        # List events
        response = client.get("/api/world/test-world/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["total_count"] == 1
        assert data["events"][0]["name"] == "The Great War"

    def test_list_events_filter_by_type(self, client):
        """Filtering by event_type returns only matching events."""
        # Create events of different types
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "War Event",
                "description": "A war.",
                "event_type": "war",
                "date_description": "Year 1000",
            },
        )
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Treaty Event",
                "description": "A treaty.",
                "event_type": "treaty",
                "date_description": "Year 1001",
            },
        )

        # Filter by war
        response = client.get("/api/world/test-world/events?event_type=war")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "war"

    def test_list_events_filter_by_impact_scope(self, client):
        """Filtering by impact_scope returns only matching events."""
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Global Event",
                "description": "A global event.",
                "event_type": "disaster",
                "date_description": "Year 1000",
                "impact_scope": "global",
            },
        )
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Local Event",
                "description": "A local event.",
                "event_type": "disaster",
                "date_description": "Year 1001",
                "impact_scope": "local",
            },
        )

        response = client.get("/api/world/test-world/events?impact_scope=global")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["impact_scope"] == "global"

    def test_list_events_filter_by_faction_id(self, client):
        """Filtering by faction_id returns events involving that faction."""
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Faction A Event",
                "description": "Involves faction A.",
                "event_type": "war",
                "date_description": "Year 1000",
                "faction_ids": ["faction-a", "faction-b"],
            },
        )
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Faction B Event",
                "description": "Involves faction B only.",
                "event_type": "treaty",
                "date_description": "Year 1001",
                "faction_ids": ["faction-b"],
            },
        )

        response = client.get("/api/world/test-world/events?faction_id=faction-a")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert "faction-a" in data["events"][0]["faction_ids"]

    def test_list_events_filter_by_location_id(self, client):
        """Filtering by location_id returns events at that location."""
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Location A Event",
                "description": "At location A.",
                "event_type": "battle",
                "date_description": "Year 1000",
                "location_ids": ["loc-a", "loc-b"],
            },
        )
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Location B Event",
                "description": "At location B only.",
                "event_type": "founding",
                "date_description": "Year 1001",
                "location_ids": ["loc-b"],
            },
        )

        response = client.get("/api/world/test-world/events?location_id=loc-a")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert "loc-a" in data["events"][0]["location_ids"]

    def test_list_events_filter_by_secret_status(self, client):
        """Filtering by is_secret returns matching events."""
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Secret Event",
                "description": "Hidden from common knowledge.",
                "event_type": "betrayal",
                "date_description": "Year 1000",
                "is_secret": True,
            },
        )
        client.post(
            "/api/world/test-world/events",
            json={
                "name": "Public Event",
                "description": "Common knowledge.",
                "event_type": "coronation",
                "date_description": "Year 1001",
                "is_secret": False,
            },
        )

        response = client.get("/api/world/test-world/events?is_secret=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["is_secret"] is True

    def test_list_events_pagination(self, client):
        """Pagination works correctly."""
        # Create 5 events
        for i in range(5):
            client.post(
                "/api/world/test-world/events",
                json={
                    "name": f"Event {i}",
                    "description": f"Description {i}",
                    "event_type": "political",
                    "date_description": f"Year {1000 + i}",
                },
            )

        # Get page 1 with page_size 2
        response = client.get("/api/world/test-world/events?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["total_count"] == 5
        assert data["page"] == 1
        assert data["total_pages"] == 3

        # Get page 2
        response = client.get("/api/world/test-world/events?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["page"] == 2

        # Get page 3 (last page with 1 item)
        response = client.get("/api/world/test-world/events?page=3&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["page"] == 3

    def test_list_events_worlds_isolated(self, client):
        """Events from different worlds are isolated."""
        # Create events in different worlds
        client.post(
            "/api/world/world-1/events",
            json={
                "name": "World 1 Event",
                "description": "Event in world 1",
                "event_type": "war",
                "date_description": "Year 1000",
            },
        )
        client.post(
            "/api/world/world-2/events",
            json={
                "name": "World 2 Event",
                "description": "Event in world 2",
                "event_type": "treaty",
                "date_description": "Year 2000",
            },
        )

        # Check world 1
        response = client.get("/api/world/world-1/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "World 1 Event"

        # Check world 2
        response = client.get("/api/world/world-2/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "World 2 Event"


@pytest.mark.integration
class TestCreateHistoricalEvent:
    """Tests for creating historical events."""

    def test_create_event_success(self, client):
        """Creating an event returns 201 with event data."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "The Founding",
                "description": "The city was founded by refugees.",
                "event_type": "founding",
                "significance": "moderate",
                "outcome": "positive",
                "date_description": "Year 1 of the First Age",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "The Founding"
        assert data["event_type"] == "founding"
        assert data["significance"] == "moderate"
        assert "id" in data

    def test_create_event_with_all_fields(self, client):
        """Creating an event with all fields stores them correctly."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "The Great Alliance",
                "description": "Three kingdoms united against the darkness.",
                "event_type": "alliance",
                "significance": "major",
                "outcome": "positive",
                "date_description": "Year 500 of the Second Age",
                "duration_description": "Lasted 50 years",
                "location_ids": ["loc-1", "loc-2"],
                "faction_ids": ["faction-1", "faction-2", "faction-3"],
                "key_figures": ["King Aldric", "Queen Mira"],
                "causes": ["Rising darkness", "Need for unity"],
                "consequences": ["Defeat of the shadow", "New era of peace"],
                "preceding_event_ids": ["evt-1"],
                "following_event_ids": ["evt-2"],
                "related_event_ids": ["evt-3"],
                "is_secret": False,
                "sources": ["Royal Chronicles", "Oral Traditions"],
                "narrative_importance": 85,
                "impact_scope": "regional",
                "affected_faction_ids": ["faction-1", "faction-2", "faction-3"],
                "affected_location_ids": ["loc-1", "loc-2"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "The Great Alliance"
        assert len(data["faction_ids"]) == 3
        assert len(data["key_figures"]) == 2
        assert data["narrative_importance"] == 85
        assert data["impact_scope"] == "regional"

    def test_create_event_invalid_event_type(self, client):
        """Creating event with invalid event_type returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Invalid Event",
                "description": "Bad type.",
                "event_type": "invalid_type",
                "date_description": "Year 1000",
            },
        )
        assert response.status_code == 400
        data = response.json()
        # Error message includes the invalid type in the list of valid types
        assert "Invalid event_type" in data["detail"] or "invalid_type" in str(data)

    def test_create_event_invalid_significance(self, client):
        """Creating event with invalid significance returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Invalid Event",
                "description": "Bad significance.",
                "event_type": "war",
                "significance": "ultra_epic",
                "date_description": "Year 1000",
            },
        )
        assert response.status_code == 400

    def test_create_event_invalid_outcome(self, client):
        """Creating event with invalid outcome returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Invalid Event",
                "description": "Bad outcome.",
                "event_type": "war",
                "outcome": "disastrous",
                "date_description": "Year 1000",
            },
        )
        assert response.status_code == 400

    def test_create_event_invalid_impact_scope(self, client):
        """Creating event with invalid impact_scope returns 400."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Invalid Event",
                "description": "Bad scope.",
                "event_type": "war",
                "date_description": "Year 1000",
                "impact_scope": "universal",
            },
        )
        assert response.status_code == 400

    def test_create_event_empty_name(self, client):
        """Creating event with empty name returns validation error."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "",
                "description": "Empty name.",
                "event_type": "war",
                "date_description": "Year 1000",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_event_default_values(self, client):
        """Creating event uses default values for optional fields."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Default Event",
                "description": "Using defaults.",
                "date_description": "Year 1000",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "political"  # Default
        assert data["significance"] == "moderate"  # Default
        assert data["outcome"] == "neutral"  # Default
        assert data["narrative_importance"] == 50  # Default
        assert data["is_secret"] is False  # Default


@pytest.mark.integration
class TestGetHistoricalEvent:
    """Tests for getting a single historical event."""

    def test_get_event_success(self, client):
        """Getting an existing event returns the event data."""
        # Create an event
        create_response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "The Battle",
                "description": "A great battle.",
                "event_type": "battle",
                "date_description": "Year 1042",
            },
        )
        event_id = create_response.json()["id"]

        # Get the event
        response = client.get(f"/api/world/test-world/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event_id
        assert data["name"] == "The Battle"
        assert data["event_type"] == "battle"

    def test_get_event_not_found(self, client):
        """Getting a non-existent event returns 404."""
        response = client.get("/api/world/test-world/events/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        # Error response format varies - check for "detail" or "message" key
        error_text = data.get("detail", data.get("message", ""))
        assert (
            "not found" in error_text.lower() or "does not exist" in error_text.lower()
        )

    def test_get_event_wrong_world(self, client):
        """Getting event from wrong world returns 404."""
        # Create event in world-1
        create_response = client.post(
            "/api/world/world-1/events",
            json={
                "name": "World 1 Event",
                "description": "Event.",
                "event_type": "war",
                "date_description": "Year 1000",
            },
        )
        event_id = create_response.json()["id"]

        # Try to get from world-2
        response = client.get(f"/api/world/world-2/events/{event_id}")
        assert response.status_code == 404


@pytest.mark.integration
class TestEventResponseFields:
    """Tests for verifying all response fields are present."""

    def test_response_includes_all_fields(self, client):
        """Response includes all required fields from schema."""
        response = client.post(
            "/api/world/test-world/events",
            json={
                "name": "Complete Event",
                "description": "All fields test.",
                "event_type": "war",
                "significance": "major",
                "outcome": "mixed",
                "date_description": "Year 1000",
                "duration_description": "10 years",
                "location_ids": ["loc-1"],
                "faction_ids": ["faction-1"],
                "key_figures": ["Hero"],
                "causes": ["Cause"],
                "consequences": ["Effect"],
                "is_secret": False,
                "narrative_importance": 75,
            },
        )
        assert response.status_code == 201
        data = response.json()

        # Check all required fields
        required_fields = [
            "id",
            "name",
            "description",
            "event_type",
            "significance",
            "outcome",
            "date_description",
            "duration_description",
            "location_ids",
            "faction_ids",
            "key_figures",
            "causes",
            "consequences",
            "preceding_event_ids",
            "following_event_ids",
            "related_event_ids",
            "is_secret",
            "sources",
            "narrative_importance",
            "impact_scope",
            "affected_faction_ids",
            "affected_location_ids",
            "structured_date",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_response_event_types(self, client):
        """Test that various event types are accepted and returned."""
        event_types = [
            "war",
            "battle",
            "treaty",
            "founding",
            "destruction",
            "discovery",
            "invention",
            "coronation",
            "death",
            "birth",
            "marriage",
            "revolution",
            "migration",
            "disaster",
            "miracle",
            "prophecy",
            "conquest",
            "liberation",
            "alliance",
            "betrayal",
            "religious",
            "cultural",
            "economic",
            "scientific",
            "magical",
            "political",
            "trade",
            "natural",
        ]

        for i, event_type in enumerate(event_types):
            response = client.post(
                "/api/world/test-world/events",
                json={
                    "name": f"Event {i}",
                    "description": f"Type: {event_type}",
                    "event_type": event_type,
                    "date_description": f"Year {1000 + i}",
                },
            )
            assert response.status_code == 201, f"Failed for type: {event_type}"
            assert response.json()["event_type"] == event_type
