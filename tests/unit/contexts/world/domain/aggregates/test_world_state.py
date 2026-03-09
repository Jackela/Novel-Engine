#!/usr/bin/env python3
"""
Unit tests for WorldState aggregate calendar integration.

Tests the integration of WorldCalendar value object into the WorldState aggregate,
including the advance_time method, serialization, and backward compatibility.
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Mock aioredis before any imports that might use it
sys.modules["aioredis"] = MagicMock()

from src.contexts.world.domain.aggregates.world_state import (
    WorldState,
    WorldStatus,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

pytestmark = pytest.mark.unit


class TestWorldStateCalendarIntegration:
    """Tests for WorldCalendar integration in WorldState."""

    def test_world_state_has_calendar_field(self) -> None:
        """WorldState should have a calendar field instead of world_time."""
        world = WorldState(name="Test World")

        assert hasattr(world, "calendar")
        assert isinstance(world.calendar, WorldCalendar)
        # Should not have world_time anymore
        assert not hasattr(world, "world_time")

    def test_world_state_default_calendar(self) -> None:
        """WorldState should have a default calendar."""
        world = WorldState(name="Test World")

        assert world.calendar.year == 1
        assert world.calendar.month == 1
        assert world.calendar.day == 1
        assert world.calendar.era_name == "First Age"

    def test_world_state_custom_calendar(self) -> None:
        """WorldState should accept a custom calendar."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        world = WorldState(name="Test World", calendar=calendar)

        assert world.calendar.year == 1042
        assert world.calendar.month == 3
        assert world.calendar.day == 15
        assert world.calendar.era_name == "Third Age"


class TestAdvanceTime:
    """Tests for the advance_time method."""

    def test_advance_time_positive_days(self) -> None:
        """advanc_time with positive days should advance calendar."""
        world = WorldState(name="Test World")

        result = world.advance_time(10)

        assert result.is_ok
        assert world.calendar.day == 11  # Started at day 1

    def test_advance_time_zero_days(self) -> None:
        """advance_time with zero days should return same calendar."""
        world = WorldState(
            name="Test World",
            calendar=WorldCalendar(year=100, month=5, day=10, era_name="Test Era"),
        )

        result = world.advance_time(0)

        assert result.is_ok
        assert world.calendar.year == 100
        assert world.calendar.month == 5
        assert world.calendar.day == 10

    def test_advance_time_negative_days_returns_error(self) -> None:
        """advance_time with negative days should return error."""
        world = WorldState(name="Test World")

        result = world.advance_time(-1)

        assert result.is_error
        assert "must be >= 0" in str(result.error)

    def test_advance_time_month_rollover(self) -> None:
        """advance_time should handle month rollover correctly."""
        world = WorldState(
            name="Test World",
            calendar=WorldCalendar(year=100, month=1, day=25, era_name="Test Era"),
        )

        result = world.advance_time(10)  # Should roll to month 2

        assert result.is_ok
        assert world.calendar.month == 2
        assert world.calendar.day == 5

    def test_advance_time_year_rollover(self) -> None:
        """advance_time should handle year rollover correctly."""
        world = WorldState(
            name="Test World",
            calendar=WorldCalendar(
                year=100,
                month=12,
                day=25,
                era_name="Test Era",
                days_per_month=30,
                months_per_year=12,
            ),
        )

        result = world.advance_time(10)  # Should roll to year 101

        assert result.is_ok
        assert world.calendar.year == 101
        assert world.calendar.month == 1
        assert world.calendar.day == 5

    def test_advance_time_emits_domain_event(self) -> None:
        """advance_time should emit a time_advanced domain event."""
        from src.contexts.world.domain.events.world_events import WorldChangeType

        world = WorldState(name="Test World")
        world.clear_domain_events()

        result = world.advance_time(5)

        assert result.is_ok
        assert world.has_domain_events()
        events = world.get_domain_events()
        assert len(events) == 1
        assert events[0].change_type == WorldChangeType.TIME_ADVANCED

    def test_advance_time_updates_version(self) -> None:
        """advance_time should increment the version."""
        world = WorldState(name="Test World")
        initial_version = world.version

        result = world.advance_time(1)

        assert result.is_ok
        assert world.version == initial_version + 1


class TestFromDatetimeWorldTime:
    """Tests for the from_datetime_world_time migration method."""

    def test_from_datetime_creates_world_state(self) -> None:
        """from_datetime_world_time should create a WorldState."""
        dt = datetime(2024, 6, 15)

        world = WorldState.from_datetime_world_time(
            world_id="test-id", name="Test World", dt=dt
        )

        assert world.id == "test-id"
        assert world.name == "Test World"
        assert isinstance(world.calendar, WorldCalendar)

    def test_from_datetime_converts_correctly(self) -> None:
        """from_datetime_world_time should convert datetime to calendar fields."""
        dt = datetime(1042, 3, 15)

        world = WorldState.from_datetime_world_time(
            world_id="test-id", name="Test World", dt=dt, era_name="Third Age"
        )

        assert world.calendar.year == 1042
        assert world.calendar.month == 3
        assert world.calendar.day == 15
        assert world.calendar.era_name == "Third Age"

    def test_from_datetime_default_era(self) -> None:
        """from_datetime_world_time should use 'Modern Era' as default."""
        dt = datetime(2024, 1, 1)

        world = WorldState.from_datetime_world_time(
            world_id="test-id", name="Test World", dt=dt
        )

        assert world.calendar.era_name == "Modern Era"

    def test_from_datetime_with_additional_kwargs(self) -> None:
        """from_datetime_world_time should accept additional kwargs."""
        dt = datetime(2024, 1, 1)

        world = WorldState.from_datetime_world_time(
            world_id="test-id",
            name="Test World",
            dt=dt,
            description="A test world",
            status=WorldStatus.ACTIVE,
        )

        assert world.description == "A test world"
        assert world.status == WorldStatus.ACTIVE


class TestSerialization:
    """Tests for serialization and deserialization."""

    def test_to_dict_includes_calendar(self) -> None:
        """to_dict should include calendar data."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        world = WorldState(name="Test World", calendar=calendar)

        data = world.to_dict()

        assert "calendar" in data
        assert data["calendar"]["year"] == 1042
        assert data["calendar"]["month"] == 3
        assert data["calendar"]["day"] == 15
        assert data["calendar"]["era_name"] == "Third Age"

    def test_to_dict_no_world_time(self) -> None:
        """to_dict should not include world_time field."""
        world = WorldState(name="Test World")

        data = world.to_dict()

        assert "world_time" not in data

    def test_from_dict_with_calendar(self) -> None:
        """from_dict should deserialize calendar data."""
        data = {
            "id": "test-id",
            "name": "Test World",
            "description": "A test",
            "status": "active",
            "calendar": {
                "year": 1042,
                "month": 3,
                "day": 15,
                "era_name": "Third Age",
                "days_per_month": 30,
                "months_per_year": 12,
            },
            "entities": {},
            "environment": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "version": 1,
        }

        world = WorldState.from_dict(data)

        assert world.calendar.year == 1042
        assert world.calendar.month == 3
        assert world.calendar.day == 15
        assert world.calendar.era_name == "Third Age"

    def test_from_dict_backward_compatibility_world_time(self) -> None:
        """from_dict should handle old world_time field for backward compatibility."""
        data = {
            "id": "test-id",
            "name": "Test World",
            "description": "A test",
            "status": "active",
            "world_time": "1042-03-15T10:30:00",  # Old format
            "entities": {},
            "environment": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "version": 1,
        }

        world = WorldState.from_dict(data)

        # Should convert world_time to calendar
        assert world.calendar.year == 1042
        assert world.calendar.month == 3
        assert world.calendar.day == 15

    def test_from_dict_defaults_calendar_if_missing(self) -> None:
        """from_dict should use default calendar if neither calendar nor world_time present."""
        data = {
            "id": "test-id",
            "name": "Test World",
            "status": "initializing",
            "entities": {},
            "environment": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "version": 1,
        }

        world = WorldState.from_dict(data)

        assert world.calendar.year == 1
        assert world.calendar.month == 1
        assert world.calendar.day == 1

    def test_round_trip_serialization(self) -> None:
        """WorldState should survive to_dict -> from_dict round trip."""
        original = WorldState(
            id="test-id",
            name="Test World",
            description="A test world",
            status=WorldStatus.ACTIVE,
            calendar=WorldCalendar(year=500, month=7, day=20, era_name="Second Age"),
        )

        data = original.to_dict()
        restored = WorldState.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.calendar.year == original.calendar.year
        assert restored.calendar.month == original.calendar.month
        assert restored.calendar.day == original.calendar.day
        assert restored.calendar.era_name == original.calendar.era_name


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_get_statistics_includes_calendar(self) -> None:
        """get_statistics should include formatted calendar."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        world = WorldState(name="Test World", calendar=calendar)

        stats = world.get_statistics()

        assert "calendar" in stats
        assert "Year 1042" in stats["calendar"]
        assert "Month 3" in stats["calendar"]
        assert "Day 15" in stats["calendar"]
        assert "Third Age" in stats["calendar"]

    def test_get_statistics_no_world_time(self) -> None:
        """get_statistics should not include world_time field."""
        world = WorldState(name="Test World")

        stats = world.get_statistics()

        assert "world_time" not in stats


class TestResetState:
    """Tests for reset_state method."""

    def test_reset_state_resets_calendar(self) -> None:
        """reset_state should reset calendar to default."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        world = WorldState(name="Test World", calendar=calendar)

        world.reset_state("Testing reset")

        assert world.calendar.year == 1
        assert world.calendar.month == 1
        assert world.calendar.day == 1
        assert world.calendar.era_name == "First Age"


class TestCreateSnapshot:
    """Tests for create_snapshot method."""

    def test_create_snapshot_includes_calendar(self) -> None:
        """create_snapshot should include calendar data."""
        calendar = WorldCalendar(year=1042, month=3, day=15, era_name="Third Age")
        world = WorldState(name="Test World", calendar=calendar)

        snapshot = world.create_snapshot("Test snapshot")

        assert "calendar" in snapshot
        assert snapshot["calendar"]["year"] == 1042
        assert snapshot["calendar"]["month"] == 3
        assert snapshot["calendar"]["day"] == 15
        assert snapshot["calendar"]["era_name"] == "Third Age"

    def test_create_snapshot_no_world_time(self) -> None:
        """create_snapshot should not include world_time field."""
        world = WorldState(name="Test World")

        snapshot = world.create_snapshot("Test snapshot")

        assert "world_time" not in snapshot
