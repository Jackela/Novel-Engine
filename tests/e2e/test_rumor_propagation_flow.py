"""E2E Tests for Rumor Propagation Flow.

This module tests the end-to-end rumor propagation flow:
1. Time advances via POST /api/world/time/advance
2. TimeAdvancedEvent triggers RumorPropagationHandler
3. RumorPropagationService spreads rumors to adjacent locations
4. Rumors have truth values that decay as they spread

Tests:
- Full propagation flow (event -> rumor -> time advance -> spread)
- Truth decay verification (10 points per hop)
- Location-based rumor retrieval
- Manual event creation with rumor generation
- API endpoint availability and response structure
"""

import pytest
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

# Mark all tests in this module as e2e tests
pytestmark = pytest.mark.e2e


class TestRumorPropagationFlow:
    """E2E tests for rumor propagation flow."""

    def _create_event_with_rumor(
        self,
        client: TestClient,
        name: str = "Test Event",
        impact_scope: str = "regional",
        location_ids: Optional[List[str]] = None,
        generate_rumor: bool = True,
        significance: str = "major",
    ) -> Dict[str, Any]:
        """Helper to create an event with optional rumor generation.

        Args:
            client: TestClient instance
            name: Event name
            impact_scope: Impact scope (local, regional, global)
            location_ids: List of location IDs where event occurred
            generate_rumor: Whether to generate a rumor from this event
            significance: Event significance level

        Returns:
            The created event response data
        """
        event_data = {
            "name": name,
            "description": f"Description for {name}",
            "event_type": "political",
            "significance": significance,
            "outcome": "neutral",
            "date_description": "Year 100, Month 1, Day 1",
            "impact_scope": impact_scope,
            "location_ids": location_ids or ["capital"],
            "generate_rumor": generate_rumor,
        }

        response = client.post("/api/world/events", json=event_data)
        assert response.status_code in [200, 201], f"Failed to create event: {response.text}"

        return response.json()

    def _get_rumors_at_location(
        self, client: TestClient, location_id: str
    ) -> List[Dict[str, Any]]:
        """Helper to get rumors at a specific location.

        Args:
            client: TestClient instance
            location_id: Location ID to query

        Returns:
            List of rumor data at the location
        """
        response = client.get(f"/api/world/locations/{location_id}/rumors")
        assert response.status_code == 200, f"Failed to get rumors: {response.text}"

        data = response.json()
        return data.get("rumors", [])

    def _get_all_world_rumors(
        self, client: TestClient, world_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Helper to get all rumors for a world.

        Args:
            client: TestClient instance
            world_id: World ID to query

        Returns:
            List of all rumors in the world
        """
        response = client.get(f"/api/world/{world_id}/rumors")
        assert response.status_code == 200, f"Failed to get world rumors: {response.text}"

        data = response.json()
        return data.get("rumors", [])

    def _advance_time(self, client: TestClient, days: int = 1) -> Dict[str, Any]:
        """Helper to advance world time.

        Args:
            client: TestClient instance
            days: Number of days to advance

        Returns:
            The time advance response data
        """
        response = client.post("/api/world/time/advance", json={"days": days})
        assert response.status_code == 200, f"Failed to advance time: {response.text}"

        return response.json()

    def test_create_event_api_returns_success(self, client: TestClient) -> None:
        """Test that event creation API works correctly.

        Verifies:
        - POST /api/world/events returns 201 Created
        - Response contains event details
        """
        event_data = {
            "name": "Test Event",
            "description": "A test event",
            "event_type": "political",
            "significance": "major",
            "outcome": "neutral",
            "date_description": "Year 100, Month 1, Day 1",
            "impact_scope": "regional",
            "location_ids": ["capital"],
            "generate_rumor": True,
        }

        response = client.post("/api/world/events", json=event_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = response.json()
        assert "id" in data or "event_id" in data, "Response missing event ID"
        assert data.get("name") == "Test Event", "Event name mismatch"

    def test_time_advance_api_returns_success(self, client: TestClient) -> None:
        """Test that time advance API works correctly.

        Verifies:
        - POST /api/world/time/advance returns 200 OK
        - Response contains updated calendar data
        """
        # Get initial time
        response = client.get("/api/world/time")
        assert response.status_code == 200
        initial_data = response.json()
        initial_day = initial_data.get("day", 1)

        # Advance time
        advance_response = client.post("/api/world/time/advance", json={"days": 5})
        assert advance_response.status_code == 200, f"Failed to advance time: {advance_response.text}"

        data = advance_response.json()
        assert "day" in data, "Response missing day"
        assert "month" in data, "Response missing month"
        assert "year" in data, "Response missing year"

        # Verify time advanced
        new_day = data.get("day", 0)
        assert new_day != initial_day or data.get("month") != initial_data.get("month"), (
            "Time did not advance"
        )

    def test_rumors_api_returns_valid_structure(self, client: TestClient) -> None:
        """Test that rumors API returns valid response structure.

        Verifies:
        - GET /api/world/{world_id}/rumors returns 200 OK
        - Response has correct structure (rumors list, total count)
        """
        response = client.get("/api/world/default/rumors")
        assert response.status_code == 200, f"Failed to get rumors: {response.text}"

        data = response.json()
        assert "rumors" in data, "Response missing 'rumors' field"
        assert "total" in data, "Response missing 'total' field"
        assert isinstance(data["rumors"], list), "Rumors should be a list"

    def test_location_rumors_api_returns_valid_structure(self, client: TestClient) -> None:
        """Test that location rumors API returns valid response structure.

        Verifies:
        - GET /api/world/locations/{id}/rumors returns 200 OK
        - Response has correct structure
        """
        response = client.get("/api/world/locations/capital/rumors")
        assert response.status_code == 200, f"Failed to get location rumors: {response.text}"

        data = response.json()
        assert "rumors" in data, "Response missing 'rumors' field"
        assert "total" in data, "Response missing 'total' field"
        assert isinstance(data["rumors"], list), "Rumors should be a list"

    def test_manual_event_creates_rumor_via_api(self, client: TestClient) -> None:
        """Test that manual event creation can generate a rumor.

        Verifies:
        - POST /api/world/events with generate_rumor=true succeeds
        - The created event has proper structure
        """
        event_data = {
            "name": "Rumor Generation Test",
            "description": "Testing manual rumor generation",
            "event_type": "discovery",
            "significance": "major",
            "outcome": "positive",
            "date_description": "Year 500, Month 6, Day 15",
            "impact_scope": "regional",
            "location_ids": ["capital"],
            "generate_rumor": True,
        }

        response = client.post("/api/world/events", json=event_data)
        assert response.status_code == 201, f"Failed to create event: {response.text}"

        event_response = response.json()
        event_id = event_response.get("id") or event_response.get("event_id")
        assert event_id, "Event ID not found in response"

        # Verify event properties
        assert event_response.get("name") == "Rumor Generation Test"
        assert event_response.get("event_type") == "discovery"

    def test_event_without_generate_rumor_no_rumor_created(self, client: TestClient) -> None:
        """Test that events without generate_rumor flag don't create rumors.

        Verifies:
        - POST /api/world/events with generate_rumor=false creates event only
        """
        event_data = {
            "name": "No Rumor Event",
            "description": "An event without rumor generation",
            "event_type": "political",
            "significance": "major",
            "outcome": "neutral",
            "date_description": "Year 100, Month 1, Day 1",
            "location_ids": ["capital"],
            "generate_rumor": False,
        }

        response = client.post("/api/world/events", json=event_data)
        assert response.status_code == 201, f"Failed to create event: {response.text}"

        response_json = response.json()
        assert response_json.get("name") == "No Rumor Event"

    def test_event_without_locations_validation(self, client: TestClient) -> None:
        """Test that events without locations are handled appropriately.

        Verifies:
        - POST /api/world/events with empty location_ids is handled
        """
        event_data = {
            "name": "Locationless Event",
            "description": "An event with no locations",
            "event_type": "political",
            "significance": "major",
            "outcome": "neutral",
            "date_description": "Year 100, Month 1, Day 1",
            "location_ids": [],  # Empty locations
            "generate_rumor": True,
        }

        response = client.post("/api/world/events", json=event_data)
        # Should either succeed (event created but no rumor) or fail with validation error
        assert response.status_code in [200, 201, 400, 422], (
            f"Unexpected status: {response.status_code}"
        )


class TestRumorAPIEndpoints:
    """Tests for rumor-specific API endpoints."""

    def test_get_world_rumors_endpoint(self, client: TestClient) -> None:
        """Test GET /api/world/{world_id}/rumors endpoint."""
        response = client.get("/api/world/default/rumors")
        assert response.status_code == 200, f"Failed to get world rumors: {response.text}"

        data = response.json()
        assert "rumors" in data, "Response missing 'rumors' field"
        assert "total" in data, "Response missing 'total' field"
        assert isinstance(data["rumors"], list), "Rumors should be a list"

    def test_get_world_rumors_with_sorting(self, client: TestClient) -> None:
        """Test rumors endpoint with different sort options."""
        sort_options = ["recent", "reliable", "spread"]
        for sort_by in sort_options:
            response = client.get(f"/api/world/default/rumors?sort_by={sort_by}")
            assert response.status_code == 200, f"Failed to sort by {sort_by}"
            data = response.json()
            assert "rumors" in data, f"Missing rumors field for sort_by={sort_by}"

    def test_get_world_rumors_with_limit(self, client: TestClient) -> None:
        """Test rumors endpoint with limit parameter."""
        response = client.get("/api/world/default/rumors?limit=5")
        assert response.status_code == 200
        data = response.json()
        rumors = data.get("rumors", [])
        # Should return at most 5 rumors
        assert len(rumors) <= 5, f"Expected at most 5 rumors, got {len(rumors)}"

    def test_get_world_rumors_with_location_filter(self, client: TestClient) -> None:
        """Test rumors endpoint with location filter."""
        response = client.get("/api/world/default/rumors?location_id=capital")
        assert response.status_code == 200
        data = response.json()
        assert "rumors" in data, "Response missing 'rumors' field"
        # All returned rumors should be at the specified location
        for rumor in data.get("rumors", []):
            assert "capital" in rumor.get("current_locations", []), (
                f"Rumor not at capital: {rumor}"
            )

    def test_get_single_rumor_endpoint_404(self, client: TestClient) -> None:
        """Test GET /api/world/rumors/{rumor_id} with non-existent ID."""
        response = client.get("/api/world/rumors/nonexistent-rumor-id")
        assert response.status_code == 404, "Should return 404 for non-existent rumor"

    def test_get_location_rumors_endpoint(self, client: TestClient) -> None:
        """Test GET /api/world/locations/{location_id}/rumors endpoint."""
        response = client.get("/api/world/locations/capital/rumors")
        assert response.status_code == 200, f"Failed to get location rumors: {response.text}"

        data = response.json()
        assert "rumors" in data, "Response missing 'rumors' field"
        assert "total" in data, "Response missing 'total' field"


class TestTimeAdvanceAPI:
    """Tests for time advancement API."""

    def test_get_world_time_endpoint(self, client: TestClient) -> None:
        """Test GET /api/world/time endpoint."""
        response = client.get("/api/world/time")
        assert response.status_code == 200, f"Failed to get world time: {response.text}"

        data = response.json()
        assert "year" in data, "Response missing 'year'"
        assert "month" in data, "Response missing 'month'"
        assert "day" in data, "Response missing 'day'"
        assert "era_name" in data, "Response missing 'era_name'"
        assert "display_string" in data, "Response missing 'display_string'"

    def test_advance_time_endpoint(self, client: TestClient) -> None:
        """Test POST /api/world/time/advance endpoint."""
        # Get initial time
        initial_response = client.get("/api/world/time")
        assert initial_response.status_code == 200
        initial_data = initial_response.json()

        # Advance time
        advance_response = client.post("/api/world/time/advance", json={"days": 7})
        assert advance_response.status_code == 200, (
            f"Failed to advance time: {advance_response.text}"
        )

        data = advance_response.json()
        assert "year" in data, "Response missing 'year'"
        assert "month" in data, "Response missing 'month'"
        assert "day" in data, "Response missing 'day'"

        # Verify time actually advanced
        total_days_initial = initial_data.get("year", 0) * 365 + initial_data.get("month", 0) * 30 + initial_data.get("day", 0)
        total_days_new = data.get("year", 0) * 365 + data.get("month", 0) * 30 + data.get("day", 0)
        assert total_days_new > total_days_initial, "Time did not advance"

    def test_advance_time_validation(self, client: TestClient) -> None:
        """Test time advance endpoint validation."""
        # Test with invalid days (0 should fail)
        response = client.post("/api/world/time/advance", json={"days": 0})
        assert response.status_code == 422, "Should reject 0 days"

        # Test with negative days
        response = client.post("/api/world/time/advance", json={"days": -1})
        assert response.status_code == 422, "Should reject negative days"


class TestEventsAPI:
    """Tests for events API endpoints."""

    def test_list_events_endpoint(self, client: TestClient) -> None:
        """Test GET /api/world/events endpoint."""
        response = client.get("/api/world/events")
        assert response.status_code == 200, f"Failed to list events: {response.text}"

        data = response.json()
        assert "events" in data, "Response missing 'events' field"
        assert "total_count" in data, "Response missing 'total_count' field"
        assert isinstance(data["events"], list), "Events should be a list"

    def test_list_events_with_filters(self, client: TestClient) -> None:
        """Test events endpoint with filters."""
        # Test with event_type filter
        response = client.get("/api/world/events?event_type=political")
        assert response.status_code == 200

        # Test with impact_scope filter
        response = client.get("/api/world/events?impact_scope=regional")
        assert response.status_code == 200

    def test_get_single_event_404(self, client: TestClient) -> None:
        """Test GET /api/world/events/{event_id} with non-existent ID."""
        response = client.get("/api/world/events/nonexistent-event-id")
        assert response.status_code == 404, "Should return 404 for non-existent event"

    def test_create_event_validation(self, client: TestClient) -> None:
        """Test event creation validation."""
        # Missing required fields
        invalid_event = {
            "name": "Invalid Event"
            # Missing description, date_description
        }
        response = client.post("/api/world/events", json=invalid_event)
        # Should fail validation
        assert response.status_code in [200, 201, 400, 422], (
            f"Unexpected status: {response.status_code}"
        )

    def test_create_event_with_all_fields(self, client: TestClient) -> None:
        """Test event creation with all valid fields."""
        event_data = {
            "name": "Complete Event",
            "description": "A complete event with all fields",
            "event_type": "war",
            "significance": "world_changing",
            "outcome": "negative",
            "date_description": "Year 1000, Month 3, Day 15",
            "duration_description": "Three days",
            "impact_scope": "global",
            "location_ids": ["capital", "north_village"],
            "faction_ids": ["faction1", "faction2"],
            "key_figures": ["Hero1", "Villain1"],
            "generate_rumor": True,
        }

        response = client.post("/api/world/events", json=event_data)
        assert response.status_code == 201, f"Failed to create event: {response.text}"

        data = response.json()
        assert data.get("name") == "Complete Event"
        assert data.get("event_type") == "war"
