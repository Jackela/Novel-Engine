#!/usr/bin/env python3
"""Comprehensive tests for TimeService.

This module provides test coverage for the TimeService including:
- Getting current world time
- Advancing time with validation
- Setting time directly
- Event emission on time changes

Total: 30 tests
"""


import pytest

from src.contexts.world.application.services.time_service import TimeService
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.contexts.world.infrastructure.persistence.in_memory_calendar_repository import (
    InMemoryCalendarRepository,
)

pytestmark = pytest.mark.unit



@pytest.fixture
def calendar_repo():
    """Create a fresh calendar repository for each test."""
    repo = InMemoryCalendarRepository()
    yield repo


@pytest.fixture
def time_service(calendar_repo):
    """Create a fresh TimeService for each test."""
    return TimeService(repository=calendar_repo)


@pytest.fixture
def sample_calendar():
    """Create a sample calendar for testing."""
    return WorldCalendar(
        year=1000,
        month=5,
        day=15,
        era_name="Third Age",
    )


# =============================================================================
# Test TimeService Initialization (3 tests)
# =============================================================================


class TestTimeServiceInitialization:
    """Tests for TimeService initialization."""

    def test_service_initialization_with_repository(self, calendar_repo):
        """Test that service initializes with valid repository."""
        service = TimeService(repository=calendar_repo)
        assert service._repository is calendar_repo

    def test_service_initialization_sets_repository_correctly(self, calendar_repo):
        """Test that repository is set correctly during initialization."""
        service = TimeService(repository=calendar_repo)
        assert isinstance(service._repository, InMemoryCalendarRepository)

    def test_service_initialization_creates_empty_events_list(self, calendar_repo):
        """Test that service initializes with empty events list."""
        service = TimeService(repository=calendar_repo)
        assert service._events == []


# =============================================================================
# Test get_time (8 tests)
# =============================================================================


class TestGetTime:
    """Tests for get_time method."""

    def test_get_time_existing_calendar(self, time_service, calendar_repo, sample_calendar):
        """Test getting time for world with existing calendar."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.get_time("world-1")
        assert result.is_ok
        assert result.value.year == 1000
        assert result.value.month == 5
        assert result.value.day == 15
        assert result.value.era_name == "Third Age"

    def test_get_time_creates_default(self, time_service):
        """Test that get_time creates default calendar if none exists."""
        result = time_service.get_time("new-world")

        assert result.is_ok
        assert result.value.year == 1
        assert result.value.month == 1
        assert result.value.day == 1
        assert result.value.era_name == "First Age"

    def test_get_time_returns_world_calendar(self, time_service, calendar_repo, sample_calendar):
        """Test that get_time returns WorldCalendar type."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.get_time("world-1")
        assert result.is_ok
        assert isinstance(result.value, WorldCalendar)

    def test_get_time_retrieves_correct_world(self, time_service, calendar_repo):
        """Test that correct world's calendar is retrieved."""
        cal1 = WorldCalendar(year=1000, month=1, day=1, era_name="First Age")
        cal2 = WorldCalendar(year=2000, month=6, day=15, era_name="Second Age")
        calendar_repo.save("world-1", cal1)
        calendar_repo.save("world-2", cal2)

        result1 = time_service.get_time("world-1")
        result2 = time_service.get_time("world-2")

        assert result1.is_ok
        assert result2.is_ok
        assert result1.value.year == 1000
        assert result2.value.year == 2000

    def test_get_time_different_eras(self, time_service, calendar_repo):
        """Test getting calendars with different eras."""
        cal = WorldCalendar(year=500, month=1, day=1, era_name="Second Age")
        calendar_repo.save("world-1", cal)

        result = time_service.get_time("world-1")
        assert result.is_ok
        assert result.value.era_name == "Second Age"

    def test_get_time_preserves_month_day(self, time_service, calendar_repo):
        """Test that month and day are preserved."""
        cal = WorldCalendar(year=1500, month=12, day=30, era_name="First Age")
        calendar_repo.save("world-1", cal)

        result = time_service.get_time("world-1")
        assert result.is_ok
        assert result.value.month == 12
        assert result.value.day == 30


# =============================================================================
# Test advance_time (12 tests)
# =============================================================================


class TestAdvanceTime:
    """Tests for advance_time method."""

    def test_advance_time_success(self, time_service, calendar_repo, sample_calendar):
        """Test successful time advancement."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.advance_time("world-1", days=10)

        assert result.is_ok
        new_calendar, event = result.value
        assert new_calendar.day == 25  # 15 + 10

    def test_advance_time_emits_event(self, time_service, calendar_repo, sample_calendar):
        """Test that time advancement emits event."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.advance_time("world-1", days=5)

        assert result.is_ok
        _, event = result.value
        assert isinstance(event, TimeAdvancedEvent)
        assert event.days_advanced == 5

    def test_advance_time_invalid_days_negative(self, time_service):
        """Test that negative days returns error."""
        result = time_service.advance_time("world-1", days=-1)

        assert result.is_error

    def test_advance_time_invalid_days_zero(self, time_service):
        """Test that zero days returns error."""
        result = time_service.advance_time("world-1", days=0)

        assert result.is_error

    def test_advance_time_updates_repository(self, time_service, calendar_repo, sample_calendar):
        """Test that advanced time is saved to repository."""
        calendar_repo.save("world-1", sample_calendar)

        time_service.advance_time("world-1", days=10)

        updated = calendar_repo.get("world-1")
        assert updated.day == 25

    def test_advance_time_event_contains_dates(self, time_service, calendar_repo, sample_calendar):
        """Test that event contains previous and new dates."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.advance_time("world-1", days=20)

        assert result.is_ok
        _, event = result.value
        assert event.payload["previous_date"]["year"] == 1000
        assert event.payload["previous_date"]["day"] == 15
        assert event.payload["new_date"]["day"] == 5  # Rolled over to next month

    def test_advance_time_across_months(self, time_service, calendar_repo):
        """Test advancing time across month boundary."""
        cal = WorldCalendar(year=1000, month=1, day=25, era_name="First Age")
        calendar_repo.save("world-1", cal)

        result = time_service.advance_time("world-1", days=10)

        assert result.is_ok
        new_calendar, _ = result.value
        assert new_calendar.month == 2
        assert new_calendar.day == 5

    def test_advance_time_across_years(self, time_service, calendar_repo):
        """Test advancing time across year boundary."""
        cal = WorldCalendar(year=1000, month=12, day=25, era_name="First Age")
        calendar_repo.save("world-1", cal)

        result = time_service.advance_time("world-1", days=10)

        assert result.is_ok
        new_calendar, _ = result.value
        assert new_calendar.year == 1001
        assert new_calendar.month == 1
        assert new_calendar.day == 5

    def test_advance_time_large_amount(self, time_service, calendar_repo, sample_calendar):
        """Test advancing time by large amount."""
        calendar_repo.save("world-1", sample_calendar)

        result = time_service.advance_time("world-1", days=365)

        assert result.is_ok
        new_calendar, _ = result.value
        assert new_calendar.year == 1001


# =============================================================================
# Test set_time (7 tests)
# =============================================================================


class TestSetTime:
    """Tests for set_time method."""

    def test_set_time_success(self, time_service):
        """Test successful time setting."""
        result = time_service.set_time("world-1", year=1500, month=6, day=20, era_name="Fourth Age")

        assert result.is_ok
        calendar = result.value
        assert calendar.year == 1500
        assert calendar.month == 6
        assert calendar.day == 20
        assert calendar.era_name == "Fourth Age"

    def test_set_time_saves_to_repository(self, time_service, calendar_repo):
        """Test that set time is saved to repository."""
        time_service.set_time("world-1", year=2000, month=1, day=1, era_name="First Age")

        saved = calendar_repo.get("world-1")
        assert saved.year == 2000

    def test_set_time_invalid_year_type(self, time_service):
        """Test that invalid year type returns error."""
        result = time_service.set_time("world-1", year="invalid", month=1, day=1, era_name="First Age")

        assert result.is_error

    def test_set_time_invalid_month_type(self, time_service):
        """Test that invalid month type returns error."""
        result = time_service.set_time("world-1", year=1000, month="invalid", day=1, era_name="First Age")

        assert result.is_error

    def test_set_time_invalid_day_type(self, time_service):
        """Test that invalid day type returns error."""
        result = time_service.set_time("world-1", year=1000, month=1, day="invalid", era_name="First Age")

        assert result.is_error

    def test_set_time_invalid_era_name_type(self, time_service):
        """Test that invalid era_name type returns error."""
        result = time_service.set_time("world-1", year=1000, month=1, day=1, era_name=123)

        assert result.is_error
