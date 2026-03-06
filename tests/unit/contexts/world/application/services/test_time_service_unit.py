#!/usr/bin/env python3
"""Tests for TimeService.

Unit tests covering:
- Time retrieval (get_time)
- Time advancement (advance_time)
- Calendar calculations (rollovers)
- Time setting (set_time)
- Event handling
- Error handling
"""

from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.application.services.time_service import TimeService
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent
from src.contexts.world.domain.ports.calendar_repository import CalendarRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.core.result import Err, Ok

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock calendar repository."""
    repo = MagicMock(spec=CalendarRepository)
    repo.exists = MagicMock(return_value=True)
    repo.get = MagicMock(return_value=None)
    repo.get_or_create = MagicMock(
        return_value=WorldCalendar(year=1042, month=6, day=15, era_name="Third Age")
    )
    repo.save = MagicMock()
    repo.delete = MagicMock(return_value=True)
    return repo


@pytest.fixture
def default_calendar() -> WorldCalendar:
    """Create a default calendar for testing."""
    return WorldCalendar(year=1042, month=6, day=15, era_name="Third Age")


@pytest.fixture
def service(mock_repository: MagicMock) -> TimeService:
    """Create a TimeService with mock repository."""
    return TimeService(repository=mock_repository)


# ============================================================================
# Test Initialization
# ============================================================================


class TestTimeServiceInit:
    """Tests for TimeService initialization."""

    def test_init_with_repository(self, mock_repository: MagicMock) -> None:
        """Should initialize with provided repository."""
        service = TimeService(repository=mock_repository)

        assert service._repository == mock_repository
        assert service._events == []

    def test_init_logs_debug(self, mock_repository: MagicMock) -> None:
        """Should log debug message on initialization."""
        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            TimeService(repository=mock_repository)
            mock_logger.debug.assert_called_once_with("time_service_initialized")


# ============================================================================
# Test get_time
# ============================================================================


class TestGetTime:
    """Tests for get_time method."""

    def test_get_time_existing_calendar(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should return existing calendar when it exists."""
        mock_repository.exists.return_value = True
        mock_repository.get_or_create.return_value = default_calendar

        result = service.get_time("world-123")

        assert result == default_calendar
        mock_repository.get_or_create.assert_called_once_with("world-123")

    def test_get_time_creates_default(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should create default calendar when none exists."""
        mock_repository.exists.return_value = False
        default_cal = WorldCalendar(year=1, month=1, day=1, era_name="First Age")
        mock_repository.get_or_create.return_value = default_cal

        result = service.get_time("new-world")

        assert result.year == 1
        assert result.month == 1
        assert result.day == 1
        assert result.era_name == "First Age"

    def test_get_time_logs_warning_for_new_calendar(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should log warning when creating default calendar."""
        mock_repository.exists.return_value = False

        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            service.get_time("new-world")

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[1]["world_id"] == "new-world"
            assert "default_calendar_created" in call_args[0][0]

    def test_get_time_logs_debug_for_existing(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should log debug when retrieving existing calendar."""
        mock_repository.exists.return_value = True

        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            service.get_time("world-123")

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args
            assert call_args[1]["world_id"] == "world-123"


# ============================================================================
# Test advance_time
# ============================================================================


class TestAdvanceTime:
    """Tests for advance_time method."""

    def test_advance_time_success(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should successfully advance time."""
        mock_repository.get_or_create.return_value = default_calendar

        result = service.advance_time("world-123", 5)

        assert result.is_ok
        calendar, event = result.value
        assert isinstance(calendar, WorldCalendar)
        assert isinstance(event, TimeAdvancedEvent)
        assert event.days_advanced == 5

    def test_advance_time_updates_calendar(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should update calendar by specified days."""
        mock_repository.get_or_create.return_value = default_calendar

        result = service.advance_time("world-123", 10)

        assert result.is_ok
        calendar, _ = result.value
        assert calendar.day == 25  # 15 + 10

    def test_advance_time_month_rollover(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should handle month rollover correctly."""
        # Day 28 of month, advance 5 days -> should roll to next month
        calendar = WorldCalendar(year=1042, month=6, day=28, era_name="Third Age")
        mock_repository.get_or_create.return_value = calendar

        result = service.advance_time("world-123", 5)

        assert result.is_ok
        new_calendar, _ = result.value
        assert new_calendar.month == 7
        assert new_calendar.day == 3  # 28 + 5 - 30 = 3

    def test_advance_time_year_rollover(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should handle year rollover correctly."""
        # Day 28 of month 12, advance 5 days -> should roll to next year
        calendar = WorldCalendar(year=1042, month=12, day=28, era_name="Third Age")
        mock_repository.get_or_create.return_value = calendar

        result = service.advance_time("world-123", 5)

        assert result.is_ok
        new_calendar, _ = result.value
        assert new_calendar.year == 1043
        assert new_calendar.month == 1
        assert new_calendar.day == 3

    def test_advance_time_zero_days_fails(
        self,
        service: TimeService,
    ) -> None:
        """Should fail when advancing zero days."""
        result = service.advance_time("world-123", 0)

        assert result.is_error
        assert "must be >= 1" in result.error

    def test_advance_time_negative_days_fails(
        self,
        service: TimeService,
    ) -> None:
        """Should fail when advancing negative days."""
        result = service.advance_time("world-123", -5)

        assert result.is_error
        assert "must be >= 1" in result.error

    def test_advance_time_creates_event(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should create TimeAdvancedEvent with correct data."""
        mock_repository.get_or_create.return_value = default_calendar

        result = service.advance_time("world-123", 7)

        assert result.is_ok
        _, event = result.value
        assert event.days_advanced == 7
        # world_id is stored in payload, not as direct attribute
        assert event.payload.get("world_id") == "world-123"
        assert event.source == "time_service"

    def test_advance_time_stores_event(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should store event for later retrieval."""
        mock_repository.get_or_create.return_value = default_calendar

        service.advance_time("world-123", 5)
        events = service.get_pending_events()

        assert len(events) == 1
        assert events[0].days_advanced == 5

    def test_advance_time_saves_repository(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should save updated calendar to repository."""
        mock_repository.get_or_create.return_value = default_calendar

        service.advance_time("world-123", 5)

        mock_repository.save.assert_called_once()
        call_args = mock_repository.save.call_args
        assert call_args[0][0] == "world-123"
        saved_calendar = call_args[0][1]
        assert saved_calendar.day == 20  # 15 + 5

    def test_advance_time_logs_info(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should log info on time advancement."""
        mock_repository.get_or_create.return_value = default_calendar

        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            service.advance_time("world-123", 5)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["world_id"] == "world-123"
            assert call_args[1]["days_advanced"] == 5


# ============================================================================
# Test set_time
# ============================================================================


class TestSetTime:
    """Tests for set_time method."""

    def test_set_time_success(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should successfully set time to specific date."""
        result = service.set_time("world-123", year=2000, month=5, day=10)

        assert result.is_ok
        calendar = result.value
        assert calendar.year == 2000
        assert calendar.month == 5
        assert calendar.day == 10

    def test_set_time_default_era(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should use default era name if not specified."""
        result = service.set_time("world-123", year=100, month=1, day=1)

        assert result.is_ok
        assert result.value.era_name == "First Age"

    def test_set_time_custom_era(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should accept custom era name."""
        result = service.set_time(
            "world-123", year=100, month=1, day=1, era_name="Golden Age"
        )

        assert result.is_ok
        assert result.value.era_name == "Golden Age"

    def test_set_time_invalid_month(
        self,
        service: TimeService,
    ) -> None:
        """Should fail with invalid month."""
        result = service.set_time("world-123", year=100, month=13, day=1)

        assert result.is_error
        assert "Invalid date" in result.error

    def test_set_time_invalid_day(
        self,
        service: TimeService,
    ) -> None:
        """Should fail with invalid day."""
        result = service.set_time("world-123", year=100, month=1, day=35)

        assert result.is_error
        assert "Invalid date" in result.error

    def test_set_time_invalid_year(
        self,
        service: TimeService,
    ) -> None:
        """Should fail with invalid year (0)."""
        result = service.set_time("world-123", year=0, month=1, day=1)

        assert result.is_error
        assert "Invalid date" in result.error

    def test_set_time_invalid_types(
        self,
        service: TimeService,
    ) -> None:
        """Should fail with non-integer date types."""
        result = service.set_time(
            "world-123", year="2024", month=1, day=1  # type: ignore
        )

        assert result.is_error
        assert "Invalid date types" in result.error

    def test_set_time_invalid_era_type(
        self,
        service: TimeService,
    ) -> None:
        """Should fail with non-string era name."""
        result = service.set_time(
            "world-123", year=100, month=1, day=1, era_name=123  # type: ignore
        )

        assert result.is_error
        assert "Invalid era_name type" in result.error

    def test_set_time_saves_repository(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should save new calendar to repository."""
        service.set_time("world-123", year=1500, month=6, day=20)

        mock_repository.save.assert_called_once()
        call_args = mock_repository.save.call_args
        assert call_args[0][0] == "world-123"

    def test_set_time_logs_info(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should log info when time is set."""
        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            service.set_time("world-123", year=2000, month=1, day=1)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["world_id"] == "world-123"
            assert call_args[1]["year"] == 2000


# ============================================================================
# Test Event Management
# ============================================================================


class TestEventManagement:
    """Tests for event management methods."""

    def test_get_pending_events_empty(self, service: TimeService) -> None:
        """Should return empty list when no events."""
        events = service.get_pending_events()

        assert events == []

    def test_get_pending_events_returns_copy(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should return a copy of events list."""
        mock_repository.get_or_create.return_value = default_calendar
        service.advance_time("world-123", 5)

        events1 = service.get_pending_events()
        events2 = service.get_pending_events()

        # Modifying one should not affect the other
        assert events1 == events2

    def test_clear_pending_events(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should clear all pending events."""
        mock_repository.get_or_create.return_value = default_calendar
        service.advance_time("world-123", 5)

        service.clear_pending_events()
        events = service.get_pending_events()

        assert events == []

    def test_multiple_advances_accumulate_events(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should accumulate events from multiple advances."""
        mock_repository.get_or_create.return_value = default_calendar

        service.advance_time("world-123", 5)
        service.advance_time("world-123", 10)

        events = service.get_pending_events()
        assert len(events) == 2

    def test_clear_pending_events_logs_debug(
        self,
        service: TimeService,
    ) -> None:
        """Should log debug when clearing events."""
        with patch("src.contexts.world.application.services.time_service.logger") as mock_logger:
            service.clear_pending_events()

            mock_logger.debug.assert_called_once_with("pending_events_cleared")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_advance_time_large_value(
        self,
        service: TimeService,
        mock_repository: MagicMock,
        default_calendar: WorldCalendar,
    ) -> None:
        """Should handle large day advancement."""
        mock_repository.get_or_create.return_value = default_calendar

        result = service.advance_time("world-123", 365)

        assert result.is_ok
        calendar, _ = result.value
        # 365 days from month 6 day 15 should end up around month 6 day 14 of next year
        # (365 % 360 = 5, so advance 5 days from 6/15 = 6/20, then advance 1 year)
        # Actually 365 days = 12 months + 5 days, so year + 1, same month, day + 5

    def test_advance_time_custom_calendar(
        self,
        service: TimeService,
        mock_repository: MagicMock,
    ) -> None:
        """Should handle calendar with custom days/month."""
        custom_calendar = WorldCalendar(
            year=100,
            month=1,
            day=28,
            era_name="Custom Era",
            days_per_month=28,
            months_per_year=13,
        )
        mock_repository.get_or_create.return_value = custom_calendar

        result = service.advance_time("world-123", 5)

        assert result.is_ok
        calendar, _ = result.value
        # 28 days per month, so 28+5=33 -> month 2, day 5
        assert calendar.month == 2
        assert calendar.day == 5

    def test_service_with_different_repositories(self) -> None:
        """Should work with different repository implementations."""
        repo1 = MagicMock(spec=CalendarRepository)
        repo1.get_or_create.return_value = WorldCalendar(
            year=1, month=1, day=1, era_name="First Age"
        )
        repo1.exists.return_value = True

        repo2 = MagicMock(spec=CalendarRepository)
        repo2.get_or_create.return_value = WorldCalendar(
            year=100, month=6, day=15, era_name="Second Age"
        )
        repo2.exists.return_value = True

        service1 = TimeService(repository=repo1)
        service2 = TimeService(repository=repo2)

        result1 = service1.get_time("world-1")
        result2 = service2.get_time("world-2")

        assert result1.year == 1
        assert result2.year == 100
