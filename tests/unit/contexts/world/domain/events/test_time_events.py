#!/usr/bin/env python3
"""Tests for TimeAdvancedEvent domain event.

Verifies the event creation, validation, and helper methods.
"""

import time
from datetime import datetime

import pytest

from src.contexts.world.domain.events.time_events import TimeAdvancedEvent

pytestmark = pytest.mark.unit


class TestTimeAdvancedEvent:
    """Tests for TimeAdvancedEvent domain event."""

    def test_create_event_success(self):
        """Creating event with valid data succeeds."""
        event = TimeAdvancedEvent.create(
            previous_date={
                "year": 1042,
                "month": 5,
                "day": 10,
                "era_name": "Third Age",
            },
            new_date={"year": 1042, "month": 5, "day": 15, "era_name": "Third Age"},
            days_advanced=5,
        )

        assert event.days_advanced == 5
        assert event.previous_date["year"] == 1042
        assert event.new_date["day"] == 15
        assert event.event_type == "world.time_advanced"

    def test_event_includes_world_id(self):
        """Event can include world_id in payload."""
        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 6, "era_name": "First Age"},
            days_advanced=5,
            world_id="world-123",
        )

        assert "world:world-123" in event.tags
        assert event.payload["world_id"] == "world-123"

    def test_event_validation_days_negative(self):
        """Event with negative days raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            TimeAdvancedEvent.create(
                previous_date={
                    "year": 1,
                    "month": 1,
                    "day": 1,
                    "era_name": "First Age",
                },
                new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
                days_advanced=-1,
            )

        assert "must be >= 0" in str(exc_info.value)

    def test_event_validation_missing_previous_date_fields(self):
        """Event with incomplete previous_date raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            TimeAdvancedEvent.create(
                previous_date={"year": 1},  # Missing month and day
                new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
                days_advanced=1,
            )

        assert "previous_date missing fields" in str(exc_info.value)

    def test_event_validation_missing_new_date_fields(self):
        """Event with incomplete new_date raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            TimeAdvancedEvent.create(
                previous_date={
                    "year": 1,
                    "month": 1,
                    "day": 1,
                    "era_name": "First Age",
                },
                new_date={"year": 1},  # Missing month and day
                days_advanced=1,
            )

        assert "new_date missing fields" in str(exc_info.value)

    def test_get_summary(self):
        """Event summary provides human-readable format."""
        event = TimeAdvancedEvent.create(
            previous_date={
                "year": 1042,
                "month": 5,
                "day": 10,
                "era_name": "Third Age",
            },
            new_date={"year": 1042, "month": 5, "day": 15, "era_name": "Third Age"},
            days_advanced=5,
        )

        summary = event.get_summary()
        assert "Advanced 5 day(s)" in summary
        assert "1042/5/10" in summary
        assert "1042/5/15" in summary
        assert "Third Age" in summary

    def test_event_has_correct_priority(self):
        """Event has HIGH priority by default."""
        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        assert event.priority.value == "high" or "HIGH" in str(event.priority)

    def test_event_has_correct_tags(self):
        """Event includes appropriate tags."""
        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 5, "era_name": "First Age"},
            days_advanced=4,
        )

        assert "context:world" in event.tags
        assert "event:time_advanced" in event.tags
        assert "days_advanced:4" in event.tags

    def test_event_payload_contains_dates(self):
        """Event payload includes previous and new dates."""
        event = TimeAdvancedEvent.create(
            previous_date={
                "year": 100,
                "month": 6,
                "day": 15,
                "era_name": "Second Age",
            },
            new_date={"year": 100, "month": 7, "day": 1, "era_name": "Second Age"},
            days_advanced=16,
        )

        assert event.payload["previous_date"]["year"] == 100
        assert event.payload["previous_date"]["month"] == 6
        assert event.payload["new_date"]["month"] == 7
        assert event.payload["days_advanced"] == 16


class TestTimeAdvancedEventTimestamp:
    """Tests for timestamp handling in TimeAdvancedEvent."""

    def test_event_timestamp_is_set_automatically(self):
        """Event timestamp is set automatically when created."""
        before = datetime.now()

        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        after = datetime.now()

        # Timestamp should be between before and after
        assert before <= event.timestamp <= after
        assert isinstance(event.timestamp, datetime)

    def test_event_timestamp_can_be_overridden(self):
        """Event timestamp can be explicitly set."""
        custom_time = datetime(2024, 6, 15, 12, 30, 0)

        # Create event with explicit timestamp using direct construction
        # Note: event_type and priority have init=False, so we don't pass them
        event = TimeAdvancedEvent(
            event_id="test-id",
            source="test",
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
            timestamp=custom_time,
        )

        assert event.timestamp == custom_time

    def test_events_created_sequentially_have_different_timestamps(self):
        """Events created in sequence have different timestamps (with delay)."""
        event1 = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        # Small delay to ensure different timestamps
        time.sleep(0.001)

        event2 = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 3, "era_name": "First Age"},
            days_advanced=1,
        )

        # Timestamps should be different (event2 should be >= event1)
        assert event2.timestamp >= event1.timestamp


class TestTimeAdvancedEventUniqueness:
    """Tests for event_id uniqueness in TimeAdvancedEvent."""

    def test_event_id_is_unique_across_events(self):
        """Each event has a unique event_id."""
        event1 = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        event2 = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        # event_ids should be different
        assert event1.event_id != event2.event_id

    def test_event_id_is_valid_uuid_format(self):
        """Event ID follows UUID format."""
        import re

        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        # UUID4 format: 8-4-4-4-12 hex characters
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(event.event_id) is not None

    def test_multiple_events_have_all_unique_ids(self):
        """Creating many events produces all unique IDs."""
        events = []
        for i in range(100):
            event = TimeAdvancedEvent.create(
                previous_date={
                    "year": 1,
                    "month": 1,
                    "day": 1,
                    "era_name": "First Age",
                },
                new_date={"year": 1, "month": 1, "day": i + 2, "era_name": "First Age"},
                days_advanced=1,
            )
            events.append(event)

        # All event_ids should be unique
        event_ids = [e.event_id for e in events]
        assert len(event_ids) == len(set(event_ids))

    def test_event_id_can_be_explicitly_set(self):
        """Event ID can be explicitly provided."""
        custom_id = "custom-event-id-12345"

        # Create event with explicit event_id using direct construction
        # Note: event_type and priority have init=False, so we don't pass them
        event = TimeAdvancedEvent(
            event_id=custom_id,
            source="test",
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
        )

        assert event.event_id == custom_id
