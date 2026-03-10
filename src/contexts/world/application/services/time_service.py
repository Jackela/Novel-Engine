#!/usr/bin/env python3
"""Time Service for Calendar Operations.

This module provides the application-layer service for managing world time.
It orchestrates domain objects and repositories to handle time-related
operations while emitting domain events.

The TimeService follows the Command Query Separation principle:
- get_time() is a query (read-only)
- advance_time() is a command (modifies state)
"""

from typing import Tuple

import structlog

from src.contexts.world.domain.errors import TimeError, TimeValidationError
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent
from src.contexts.world.domain.ports.calendar_repository import CalendarRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.core.result import Err, Error, Ok, Result

logger = structlog.get_logger()


class TimeService:
    """Application service for managing world time.

    This service provides the primary interface for time operations,
    abstracting the complexity of calendar management and event emission.

    Responsibilities:
        - Retrieving current world time
        - Advancing time with validation
        - Emitting TimeAdvancedEvent on time changes

    Attributes:
        _repository: The calendar repository for persistence
        _events: List of events emitted during operations (for collection)
    """

    def __init__(self, repository: CalendarRepository) -> None:
        """Initialize the time service with a repository.

        Args:
            repository: The calendar repository to use for persistence
        """
        self._repository = repository
        self._events: list[TimeAdvancedEvent] = []
        logger.debug("time_service_initialized")

    def get_time(self, world_id: str) -> Result[WorldCalendar, Error]:
        """Get the current time for a world.

        If no calendar exists for the world, a default calendar is created
        (year=1, month=1, day=1, era_name="First Age").

        Args:
            world_id: Unique identifier for the world

        Returns:
            Result containing:
            - Ok: The current WorldCalendar for the world
            - Err: Error if operation fails

        Example:
            >>> service = TimeService(repository)
            >>> result = service.get_time("world-123")
            >>> if result.is_ok:
            ...     print(result.value.format())
        """
        try:
            # Check if calendar exists before get_or_create to detect missing world state
            existed = self._repository.exists(world_id)
            calendar = self._repository.get_or_create(world_id)

            if not existed:
                # WARNING: Creating default calendar - may indicate missing world initialization
                logger.warning(
                    "default_calendar_created",
                    world_id=world_id,
                    year=calendar.year,
                    month=calendar.month,
                    day=calendar.day,
                    era_name=calendar.era_name,
                    details="No calendar found for world; created default. This may indicate missing world state initialization.",
                )
            else:
                logger.debug(
                    "time_retrieved",
                    world_id=world_id,
                    year=calendar.year,
                    month=calendar.month,
                    day=calendar.day,
                )
            return Ok(calendar)
        except Exception as e:
            logger.error(
                "get_time_failed",
                world_id=world_id,
                error=str(e),
            )
            return Err(
                TimeError(
                    f"Failed to get time: {e}",
                    details={"world_id": world_id},
                )
            )

    def advance_time(
        self, world_id: str, days: int
    ) -> Result[Tuple[WorldCalendar, TimeAdvancedEvent], Error]:
        """Advance time for a world by a specified number of days.

        This command modifies the world's calendar state and emits a
        TimeAdvancedEvent. The event is stored internally and can be
        retrieved with get_pending_events().

        Args:
            world_id: Unique identifier for the world
            days: Number of days to advance (must be >= 1)

        Returns:
            Result containing:
            - Ok: Tuple of (updated_calendar, event)
            - Err: Error message string

        Example:
            >>> result = service.advance_time("world-123", 5)
            >>> if result.is_ok:
            ...     calendar, event = result.value
            ...     print(f"Advanced to: {calendar.format()}")
        """
        if days < 1:
            error_msg = f"Days to advance must be >= 1, got {days}"
            logger.warning("advance_time_validation_failed", error=error_msg)
            return Err(TimeValidationError(error_msg, details={"days": days}))

        # Get current calendar
        current = self._repository.get_or_create(world_id)
        if current is None:
            return Err(
                TimeError(
                    f"Failed to get or create calendar for world {world_id}",
                    details={"world_id": world_id},
                )
            )

        # Store current values before advancing
        current_year = current.year
        current_month = current.month
        current_day = current.day
        current_era = current.era_name

        # Advance the calendar
        advance_result = current.advance(days)
        if advance_result.is_error:
            error_msg = f"Failed to advance calendar: {advance_result.error}"
            logger.error("advance_time_failed", error=error_msg)
            return Err(
                TimeError(
                    error_msg,
                    details={"world_id": world_id, "days": days},
                )
            )

        updated = advance_result.value

        # Create event
        event = TimeAdvancedEvent.create(
            previous_date={
                "year": current_year,
                "month": current_month,
                "day": current_day,
                "era_name": current_era,
            },
            new_date={
                "year": updated.year,
                "month": updated.month,
                "day": updated.day,
                "era_name": updated.era_name,
            },
            days_advanced=days,
            world_id=world_id,
            source="time_service",
        )

        # Store event for collection
        self._events.append(event)

        # Persist the updated calendar
        self._repository.save(world_id, updated)

        logger.info(
            "time_advanced",
            world_id=world_id,
            days_advanced=days,
            previous_year=current_year,
            previous_month=current_month,
            previous_day=current_day,
            new_year=updated.year,
            new_month=updated.month,
            new_day=updated.day,
        )

        return Ok((updated, event))

    def get_pending_events(self) -> Result[list[TimeAdvancedEvent], Error]:
        """Get all pending events that haven't been cleared.

        Returns:
            Result containing:
            - Ok: List of TimeAdvancedEvent instances
            - Err: Error if operation fails
        """
        try:
            return Ok(list(self._events))
        except Exception as e:
            return Err(
                TimeError(
                    f"Failed to get pending events: {e}",
                )
            )

    def clear_pending_events(self) -> Result[None, Error]:
        """Clear all pending events after they've been processed.

        Returns:
            Result containing:
            - Ok: None on success
            - Err: Error if operation fails
        """
        try:
            self._events.clear()
            logger.debug("pending_events_cleared")
            return Ok(None)
        except Exception as e:
            return Err(
                TimeError(
                    f"Failed to clear pending events: {e}",
                )
            )

    def set_time(
        self,
        world_id: str,
        year: int,
        month: int,
        day: int,
        era_name: str = "First Age",
    ) -> Result[WorldCalendar, Error]:
        """Set the time for a world to a specific date.

        This is primarily useful for testing or world initialization.
        Note: This does not emit an event as it's a direct set operation.

        Args:
            world_id: Unique identifier for the world
            year: Year to set (must be >= 1)
            month: Month to set (1-12)
            day: Day to set (1-30)
            era_name: Era name to set

        Returns:
            Result containing the new WorldCalendar or error message
        """
        # Type validation before attempting to create WorldCalendar
        if (
            not isinstance(year, int)
            or not isinstance(month, int)
            or not isinstance(day, int)
        ):
            error_msg = f"Invalid date types: year={type(year).__name__}, month={type(month).__name__}, day={type(day).__name__}. All must be integers."
            logger.error(
                "set_time_type_validation_failed",
                world_id=world_id,
                year_type=type(year).__name__,
                month_type=type(month).__name__,
                day_type=type(day).__name__,
            )
            return Err(
                TimeValidationError(
                    error_msg,
                    details={
                        "world_id": world_id,
                        "year": year,
                        "month": month,
                        "day": day,
                    },
                )
            )

        if not isinstance(era_name, str):
            error_msg = (
                f"Invalid era_name type: {type(era_name).__name__}. Must be string."
            )
            logger.error(
                "set_time_era_name_validation_failed",
                world_id=world_id,
                era_name_type=type(era_name).__name__,
            )
            return Err(
                TimeValidationError(
                    error_msg,
                    details={"world_id": world_id, "era_name": era_name},
                )
            )

        try:
            calendar = WorldCalendar(year=year, month=month, day=day, era_name=era_name)
            self._repository.save(world_id, calendar)
            logger.info(
                "time_set",
                world_id=world_id,
                year=year,
                month=month,
                day=day,
                era_name=era_name,
            )
            return Ok(calendar)
        except ValueError as e:
            error_msg = f"Invalid date: {e}"
            logger.error("set_time_failed", error=error_msg, world_id=world_id)
            return Err(
                TimeValidationError(
                    error_msg,
                    details={
                        "world_id": world_id,
                        "year": year,
                        "month": month,
                        "day": day,
                    },
                )
            )
