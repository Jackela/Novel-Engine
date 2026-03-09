#!/usr/bin/env python3
"""Integration tests for TimeService.

These tests verify the TimeService works correctly with its dependencies
(repository, domain objects, events).
"""

import pytest

from src.contexts.world.application.services.time_service import TimeService
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent
from src.contexts.world.infrastructure.persistence.in_memory_calendar_repository import (
    InMemoryCalendarRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def repository():
    """Create a fresh repository for each test."""
    return InMemoryCalendarRepository()


@pytest.fixture
def service(repository):
    """Create a TimeService with in-memory repository."""
    return TimeService(repository)


class TestTimeServiceGetTime:
    """Tests for TimeService.get_time()"""

    def test_get_time_creates_default_calendar(self, service):
        """Getting time for non-existent world creates default calendar."""
        result = service.get_time("new-world")

        assert result.is_ok
        assert result.value.year == 1
        assert result.value.month == 1
        assert result.value.day == 1
        assert result.value.era_name == "First Age"

    def test_get_time_returns_existing_calendar(self, service, repository):
        """Getting time for existing world returns stored calendar."""
        # Set up initial calendar
        result = service.set_time(
            "existing-world", year=1042, month=5, day=14, era_name="Third Age"
        )
        assert result.is_ok

        # Get should return the same calendar
        result = service.get_time("existing-world")
        assert result.is_ok
        assert result.value.year == 1042
        assert result.value.month == 5
        assert result.value.day == 14

    def test_get_time_is_idempotent(self, service):
        """Multiple get_time calls return same calendar."""
        result1 = service.get_time("test-world")
        result2 = service.get_time("test-world")

        assert result1.is_ok
        assert result2.is_ok
        assert result1.value == result2.value


class TestTimeServiceAdvanceTime:
    """Tests for TimeService.advance_time()"""

    def test_advance_time_returns_error_for_zero_days(self, service):
        """Advancing by zero days returns error."""
        result = service.advance_time("test-world", 0)

        assert result.is_error
        assert "must be >= 1" in str(result.error)

    def test_advance_time_returns_error_for_negative_days(self, service):
        """Advancing by negative days returns error."""
        result = service.advance_time("test-world", -5)

        assert result.is_error
        assert "must be >= 1" in str(result.error)

    def test_advance_time_success(self, service):
        """Advancing time returns updated calendar and event."""
        result = service.advance_time("test-world", 5)

        assert result.is_ok
        calendar, event = result.value

        assert calendar.day == 6  # Started at 1, advanced 5
        assert event.days_advanced == 5

    def test_advance_time_creates_event(self, service):
        """Advancing time creates a TimeAdvancedEvent."""
        service.advance_time("test-world", 10)

        events_result = service.get_pending_events()
        assert events_result.is_ok
        events = events_result.value
        assert len(events) == 1
        assert isinstance(events[0], TimeAdvancedEvent)
        assert events[0].days_advanced == 10

    def test_advance_time_event_contains_correct_dates(self, service):
        """Event contains accurate previous and new dates."""
        service.set_time("test-world", year=1042, month=5, day=10, era_name="Third Age")
        result = service.advance_time("test-world", 5)

        assert result.is_ok
        _, event = result.value

        assert event.previous_date["year"] == 1042
        assert event.previous_date["month"] == 5
        assert event.previous_date["day"] == 10

        assert event.new_date["year"] == 1042
        assert event.new_date["month"] == 5
        assert event.new_date["day"] == 15

    def test_advance_time_persists_calendar(self, service, repository):
        """Advancing time persists the updated calendar."""
        service.advance_time("test-world", 15)

        # Retrieve from repository directly
        stored = repository.get("test-world")
        assert stored is not None
        assert stored.day == 16  # Started at 1, advanced 15

    def test_advance_time_month_rollover(self, service):
        """Advancing past month end rolls over correctly."""
        service.set_time("test-world", year=1042, month=5, day=28, era_name="Third Age")
        result = service.advance_time("test-world", 5)

        assert result.is_ok
        calendar, _ = result.value

        assert calendar.month == 6
        assert calendar.day == 3  # 28 + 5 = 33, 33 - 30 = 3

    def test_advance_time_year_rollover(self, service):
        """Advancing past year end rolls over correctly."""
        service.set_time(
            "test-world", year=1042, month=12, day=28, era_name="Third Age"
        )
        result = service.advance_time("test-world", 5)

        assert result.is_ok
        calendar, _ = result.value

        assert calendar.year == 1043
        assert calendar.month == 1
        assert calendar.day == 3

    def test_multiple_advances_accumulate_events(self, service):
        """Multiple advances create multiple events."""
        service.advance_time("test-world", 5)
        service.advance_time("test-world", 10)
        service.advance_time("test-world", 3)

        events_result = service.get_pending_events()
        assert events_result.is_ok
        events = events_result.value
        assert len(events) == 3

        days_list = [e.days_advanced for e in events]
        assert days_list == [5, 10, 3]


class TestTimeServiceSetTime:
    """Tests for TimeService.set_time()"""

    def test_set_time_success(self, service):
        """Setting time creates calendar with specified values."""
        result = service.set_time(
            "test-world", year=1042, month=5, day=14, era_name="Third Age"
        )

        assert result.is_ok
        calendar = result.value

        assert calendar.year == 1042
        assert calendar.month == 5
        assert calendar.day == 14
        assert calendar.era_name == "Third Age"

    def test_set_time_validates_constraints(self, service):
        """Setting time validates date constraints."""
        result = service.set_time("test-world", year=0, month=1, day=1)

        assert result.is_error
        assert "Invalid date" in str(result.error)

    def test_set_time_persists(self, service, repository):
        """Setting time persists the calendar."""
        service.set_time("test-world", year=500, month=6, day=15)

        stored = repository.get("test-world")
        assert stored is not None
        assert stored.year == 500


class TestTimeServiceEvents:
    """Tests for event handling in TimeService"""

    def test_clear_pending_events(self, service):
        """Clearing events removes all pending events."""
        service.advance_time("test-world", 5)
        service.advance_time("test-world", 10)

        events_result = service.get_pending_events()
        assert events_result.is_ok
        assert len(events_result.value) == 2

        service.clear_pending_events()

        events_result = service.get_pending_events()
        assert events_result.is_ok
        assert len(events_result.value) == 0

    def test_event_includes_world_id(self, service):
        """Events include world_id in their payload."""
        service.advance_time("my-world-123", 5)

        events_result = service.get_pending_events()
        assert events_result.is_ok
        events = events_result.value
        assert events[0].payload.get("world_id") == "my-world-123"


class TestTimeServiceRepositoryFailures:
    """Tests for TimeService handling repository failures gracefully."""

    def test_set_time_handles_repository_save_failure(self, repository, monkeypatch):
        """TimeService set_time propagates repository save failures."""
        from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

        def failing_save(world_id: str, calendar: WorldCalendar) -> None:
            raise RuntimeError("Database connection lost")

        # Create service with the repository
        service = TimeService(repository)

        # Patch save to fail
        monkeypatch.setattr(repository, "save", failing_save)

        # set_time currently catches ValueError but not RuntimeError
        # This test documents that RuntimeError propagates
        with pytest.raises(RuntimeError) as exc_info:
            service.set_time("test-world", year=1042, month=5, day=14)

        assert "Database connection lost" in str(exc_info.value)

    def test_set_time_handles_invalid_calendar(self, repository):
        """TimeService set_time returns error for invalid calendar data."""
        service = TimeService(repository)

        # Invalid: year 0 is not allowed
        result = service.set_time("test-world", year=0, month=1, day=1)

        assert result.is_error
        assert "Invalid date" in str(result.error)

    def test_advance_time_handles_repository_save_failure(
        self, repository, monkeypatch
    ):
        """TimeService advance_time propagates repository save failures."""
        from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

        def failing_save(world_id: str, calendar: WorldCalendar) -> None:
            raise RuntimeError("Storage unavailable")

        # Create service with the repository
        service = TimeService(repository)

        # First, advance should work to get to the save step
        # Patch save to fail AFTER get_or_create succeeds
        monkeypatch.setattr(repository, "save", failing_save)

        # advance_time should propagate the RuntimeError during save
        with pytest.raises(RuntimeError) as exc_info:
            service.advance_time("test-world", 5)

        assert "Storage unavailable" in str(exc_info.value)

    def test_get_time_handles_repository_failure(self, repository, monkeypatch):
        """TimeService get_time returns error on repository failures."""

        def failing_get(world_id: str):
            raise RuntimeError("Storage system error")

        # Create service with the repository
        service = TimeService(repository)

        # Patch get to fail (affects get_or_create)
        monkeypatch.setattr(repository, "get", failing_get)

        # get_time should return an error result
        result = service.get_time("test-world")
        assert result.is_error
        assert "Storage system error" in str(result.error)

    def test_set_time_success_after_failure(self, repository):
        """TimeService can successfully set time after initial failure."""
        service = TimeService(repository)

        # First attempt with invalid data fails
        result1 = service.set_time("test-world", year=0, month=1, day=1)
        assert result1.is_error

        # Second attempt with valid data succeeds
        result2 = service.set_time("test-world", year=1042, month=5, day=14)
        assert result2.is_ok
        assert result2.value.year == 1042
