#!/usr/bin/env python3
"""In-Memory Calendar Repository Implementation.

This module provides an in-memory implementation of CalendarRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

import threading
from typing import Dict, Optional

import structlog

from src.contexts.world.domain.ports.calendar_repository import CalendarRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

logger = structlog.get_logger()


class InMemoryCalendarRepository(CalendarRepository):
    """In-memory implementation of CalendarRepository.

    Stores calendars in a dictionary indexed by world_id. This is a simple
    implementation suitable for MVP and development.

    Thread Safety:
        This implementation IS thread-safe. All operations are protected
        by a reentrant lock (RLock) to ensure safe concurrent access.
        The RLock allows nested calls within the same thread (e.g.,
        get_or_create calling get and save internally).

    Attributes:
        _calendars: Dictionary mapping world_id to WorldCalendar
        _lock: Reentrant lock for thread-safe access
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage and thread lock."""
        self._calendars: Dict[str, WorldCalendar] = {}
        self._lock = threading.RLock()
        logger.debug("in_memory_calendar_repository_initialized")

    def get(self, world_id: str) -> Optional[WorldCalendar]:
        """Retrieve the calendar for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            WorldCalendar if found, None otherwise
        """
        with self._lock:
            calendar = self._calendars.get(world_id)
            if calendar:
                logger.debug(
                    "calendar_retrieved",
                    world_id=world_id,
                    year=calendar.year,
                    month=calendar.month,
                    day=calendar.day,
                )
            return calendar

    def save(self, world_id: str, calendar: WorldCalendar) -> None:
        """Persist the calendar for a specific world.

        Args:
            world_id: Unique identifier for the world
            calendar: The WorldCalendar to persist
        """
        with self._lock:
            self._calendars[world_id] = calendar
            logger.debug(
                "calendar_saved",
                world_id=world_id,
                year=calendar.year,
                month=calendar.month,
                day=calendar.day,
            )

    def delete(self, world_id: str) -> bool:
        """Remove the calendar for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            True if calendar was deleted, False if it didn't exist
        """
        with self._lock:
            if world_id in self._calendars:
                del self._calendars[world_id]
                logger.debug("calendar_deleted", world_id=world_id)
                return True
            return False

    def exists(self, world_id: str) -> bool:
        """Check if a calendar exists for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            True if calendar exists, False otherwise
        """
        with self._lock:
            return world_id in self._calendars

    def clear(self) -> None:
        """Clear all calendars from the repository.

        This is a utility method primarily used for testing.
        """
        with self._lock:
            self._calendars.clear()
            logger.debug("all_calendars_cleared")

    def get_all_world_ids(self) -> list[str]:
        """Get all world IDs that have calendars.

        Returns:
            List of world_id strings
        """
        with self._lock:
            return list(self._calendars.keys())

    def get_or_create(self, world_id: str) -> WorldCalendar:
        """Get existing calendar or create a default one.

        This is an atomic operation protected by the lock to prevent
        race conditions where multiple threads could create duplicate
        default calendars for the same world_id.

        Uses RLock to allow nested calls to get/save within the same thread
        (since get() and save() also acquire the lock).

        Args:
            world_id: Unique identifier for the world

        Returns:
            Existing or newly created WorldCalendar
        """
        with self._lock:
            calendar = self.get(world_id)
            if calendar is None:
                calendar = WorldCalendar(
                    year=1, month=1, day=1, era_name="First Age"
                )
                self.save(world_id, calendar)
                # Note: save() already logs, so we don't log again here
            return calendar
