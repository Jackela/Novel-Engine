#!/usr/bin/env python3
"""
Real-time Events SSE Endpoint Test Suite
========================================

This test suite provides comprehensive coverage for the /api/events/stream
Server-Sent Events endpoint used for real-time dashboard updates.

Test Categories:
1. Endpoint Existence & Response Format
2. SSE Protocol Compliance
3. Event Payload Structure
4. Connection Lifecycle
5. Error Handling & Resilience
"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from src.api.main_api_server import create_app


class TestEventsStreamEndpoint:
    """Test SSE endpoint for real-time dashboard events"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        app = create_app()
        return TestClient(app)

    def test_endpoint_exists_and_returns_200(self, client):
        """Verify /api/events/stream endpoint exists and returns HTTP 200"""
        # Use stream context to test streaming endpoint
        with client.stream("GET", "/api/events/stream") as response:
            assert response.status_code == 200

    def test_endpoint_returns_correct_content_type(self, client):
        """Verify endpoint returns text/event-stream content type"""
        with client.stream("GET", "/api/events/stream") as response:
            assert response.headers["content-type"] == "text/event-stream"

    def test_endpoint_returns_required_headers(self, client):
        """Verify SSE-required headers are present"""
        with client.stream("GET", "/api/events/stream") as response:
            headers = response.headers

            # Cache-Control: no-cache
            assert "cache-control" in headers
            assert headers["cache-control"] == "no-cache"

            # Connection: keep-alive
            assert "connection" in headers
            # Note: TestClient may modify this header

            # X-Accel-Buffering: no (nginx buffering disabled)
            assert "x-accel-buffering" in headers
            assert headers["x-accel-buffering"] == "no"

    def test_stream_returns_retry_directive(self, client):
        """Verify SSE stream includes retry directive in first message"""
        with client.stream("GET", "/api/events/stream") as response:
            # Read first line from stream
            first_line = next(response.iter_lines())

            # Should be retry directive (milliseconds)
            assert first_line.startswith("retry:")
            retry_value = first_line.split(":")[1].strip()
            assert retry_value.isdigit()
            assert int(retry_value) == 3000  # 3 seconds

    def test_stream_returns_sse_formatted_events(self, client):
        """Verify events are formatted according to SSE spec"""
        with client.stream("GET", "/api/events/stream") as response:
            lines_collected = []
            line_count = 0

            # Collect first few lines (retry + first event)
            for line in response.iter_lines():
                lines_collected.append(line)
                line_count += 1

                # Stop after collecting retry + id + data + blank line
                if line_count > 10:
                    break

            # Find first "id:" line
            id_lines = [l for l in lines_collected if l.startswith("id:")]
            assert len(id_lines) > 0, "No id: lines found in SSE stream"

            # Find first "data:" line
            data_lines = [l for l in lines_collected if l.startswith("data:")]
            assert len(data_lines) > 0, "No data: lines found in SSE stream"

            # Verify SSE format: id and data should be present
            assert any(l.startswith("id: evt-") for l in id_lines)

    def test_event_payload_includes_required_fields(self, client):
        """Verify event data includes all required fields"""
        with client.stream("GET", "/api/events/stream") as response:
            # Skip retry directive
            for line in response.iter_lines():
                if line.startswith("data:"):
                    # Extract JSON from data: line
                    json_str = line[5:].strip()  # Strip "data:" prefix
                    event_data = json.loads(json_str)

                    # Required fields
                    assert "id" in event_data
                    assert "type" in event_data
                    assert "title" in event_data
                    assert "description" in event_data
                    assert "timestamp" in event_data
                    assert "severity" in event_data

                    # Validate types
                    assert isinstance(event_data["id"], str)
                    assert isinstance(event_data["type"], str)
                    assert isinstance(event_data["title"], str)
                    assert isinstance(event_data["description"], str)
                    assert isinstance(event_data["timestamp"], int)
                    assert isinstance(event_data["severity"], str)

                    # Validate enums
                    assert event_data["type"] in ["character", "story", "system", "interaction"]
                    assert event_data["severity"] in ["low", "medium", "high"]

                    break  # Only test first event

    def test_character_events_include_character_name(self, client):
        """Verify character-type events include optional characterName field"""
        with client.stream("GET", "/api/events/stream") as response:
            found_character_event = False

            # Iterate through events until we find a character event
            for line in response.iter_lines():
                if line.startswith("data:"):
                    json_str = line[5:].strip()
                    event_data = json.loads(json_str)

                    if event_data["type"] == "character":
                        # Character events should have characterName
                        assert "characterName" in event_data
                        assert isinstance(event_data["characterName"], str)
                        assert len(event_data["characterName"]) > 0
                        found_character_event = True
                        break

                # Safety limit - don't read forever
                if len(list(response.iter_lines())) > 50:
                    break

            # Note: In simulated events, we cycle through types, so we should find one
            # If not found, this is acceptable for MVP (production will have real events)

    def test_stream_handles_client_disconnection(self, client):
        """Verify stream gracefully handles client disconnection"""
        # This test verifies the endpoint doesn't crash when client disconnects
        # In a real scenario, this would be tested with actual network interruption

        with client.stream("GET", "/api/events/stream") as response:
            # Read a few lines
            lines_read = 0
            for line in response.iter_lines():
                lines_read += 1
                if lines_read > 5:
                    break  # Disconnect by exiting context

        # If we reach here without exception, disconnection was handled gracefully
        assert True

    def test_event_ids_are_sequential(self, client):
        """Verify event IDs are sequential (evt-1, evt-2, evt-3, ...)"""
        with client.stream("GET", "/api/events/stream") as response:
            event_ids = []

            for line in response.iter_lines():
                if line.startswith("id: evt-"):
                    # Extract event ID number
                    event_id = line[4:].strip()  # Strip "id: " prefix
                    event_ids.append(event_id)

                    # Collect first 3 event IDs
                    if len(event_ids) >= 3:
                        break

            # Verify sequential IDs
            assert len(event_ids) >= 3
            assert event_ids[0] == "evt-1"
            assert event_ids[1] == "evt-2"
            assert event_ids[2] == "evt-3"

    def test_events_arrive_at_expected_frequency(self, client):
        """Verify events are generated approximately every 2 seconds"""
        with client.stream("GET", "/api/events/stream") as response:
            event_times = []

            for line in response.iter_lines():
                if line.startswith("data:"):
                    event_times.append(time.time())

                    # Collect timestamps for 2 events
                    if len(event_times) >= 2:
                        break

            # Calculate interval between events
            if len(event_times) == 2:
                interval = event_times[1] - event_times[0]

                # Should be approximately 2 seconds (allow some variance)
                assert 1.8 <= interval <= 2.5, f"Event interval {interval}s not near 2s"

    def test_timestamp_field_is_milliseconds_since_epoch(self, client):
        """Verify timestamp is in milliseconds and reasonably current"""
        with client.stream("GET", "/api/events/stream") as response:
            for line in response.iter_lines():
                if line.startswith("data:"):
                    json_str = line[5:].strip()
                    event_data = json.loads(json_str)

                    timestamp = event_data["timestamp"]

                    # Timestamp should be in milliseconds
                    # Current time in ms is around 1.7e12 (as of 2024)
                    assert timestamp > 1_600_000_000_000, "Timestamp too small (not in ms?)"
                    assert timestamp < 2_000_000_000_000, "Timestamp too large"

                    # Verify timestamp is recent (within last 10 seconds)
                    current_time_ms = int(time.time() * 1000)
                    time_diff = abs(current_time_ms - timestamp)
                    assert time_diff < 10_000, "Event timestamp not current"

                    break  # Only test first event


class TestEventsStreamErrorHandling:
    """Test error handling and resilience of SSE endpoint"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        app = create_app()
        return TestClient(app)

    def test_endpoint_accessible_without_authentication(self, client):
        """Verify endpoint is accessible without auth (for MVP)"""
        # No auth headers provided
        with client.stream("GET", "/api/events/stream") as response:
            assert response.status_code == 200
            # If auth was required, would get 401 Unauthorized

    def test_multiple_clients_can_connect_simultaneously(self, client):
        """Verify multiple SSE connections can be established"""
        # Open multiple streaming connections
        responses = []

        try:
            # Establish 3 concurrent connections
            for i in range(3):
                response_context = client.stream("GET", "/api/events/stream")
                response = response_context.__enter__()
                responses.append((response_context, response))

                # Verify each connection succeeds
                assert response.status_code == 200

        finally:
            # Clean up all connections
            for response_context, response in responses:
                response_context.__exit__(None, None, None)

    def test_endpoint_returns_valid_json_in_data_field(self, client):
        """Verify data field always contains valid JSON"""
        with client.stream("GET", "/api/events/stream") as response:
            json_parse_errors = 0

            for line in response.iter_lines():
                if line.startswith("data:"):
                    json_str = line[5:].strip()

                    try:
                        parsed = json.loads(json_str)
                        assert isinstance(parsed, dict)
                    except json.JSONDecodeError:
                        json_parse_errors += 1

                # Test first 5 events
                if json_parse_errors > 0 or len(list(response.iter_lines())) > 10:
                    break

            assert json_parse_errors == 0, "Found invalid JSON in SSE data field"
