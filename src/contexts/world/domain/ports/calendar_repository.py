#!/usr/bin/env python3
"""
Calendar Repository Port

This module defines the repository port (interface) for calendar persistence.
Following Hexagonal Architecture, this port defines the contract that
infrastructure implementations must fulfill, keeping the domain layer
pure and independent of persistence details.

The CalendarRepository follows the Repository Pattern, providing an
abstraction for storing and retrieving WorldCalendar aggregates.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


class CalendarRepository(ABC):
    """
    Abstract repository port for WorldCalendar persistence.

    This interface defines the contract for calendar storage operations.
    Implementations can use different storage backends (in-memory, database, etc.)
    while the domain layer remains decoupled from infrastructure concerns.

    The repository follows the single-world model where there is one calendar
    per world identifier.
    """

    @abstractmethod
    def get(self, world_id: str) -> Optional[WorldCalendar]:
        """
        Retrieve the calendar for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            WorldCalendar if found, None otherwise

        Example:
            >>> calendar = repository.get("world-123")
            >>> if calendar:
            ...     print(calendar.format())
        """
        pass

    @abstractmethod
    def save(self, world_id: str, calendar: WorldCalendar) -> None:
        """
        Persist the calendar for a specific world.

        This operation is idempotent - calling it multiple times with the
        same parameters has the same effect as calling it once.

        Args:
            world_id: Unique identifier for the world
            calendar: The WorldCalendar to persist

        Example:
            >>> calendar = WorldCalendar(year=1042, month=5, day=10, era_name="Third Age")
            >>> repository.save("world-123", calendar)
        """
        pass

    @abstractmethod
    def delete(self, world_id: str) -> bool:
        """
        Remove the calendar for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            True if calendar was deleted, False if it didn't exist

        Example:
            >>> deleted = repository.delete("world-123")
            >>> if deleted:
            ...     print("Calendar removed")
        """
        pass

    @abstractmethod
    def exists(self, world_id: str) -> bool:
        """
        Check if a calendar exists for a specific world.

        Args:
            world_id: Unique identifier for the world

        Returns:
            True if calendar exists, False otherwise

        Example:
            >>> if repository.exists("world-123"):
            ...     calendar = repository.get("world-123")
        """
        pass

    def get_or_create(self, world_id: str) -> WorldCalendar:
        """
        Get existing calendar or create a default one.

        This convenience method combines get and save operations for
        the common pattern of initializing a new world's calendar.

        Args:
            world_id: Unique identifier for the world

        Returns:
            Existing or newly created WorldCalendar

        Example:
            >>> calendar = repository.get_or_create("world-123")
            >>> # Returns existing calendar or creates default (year=1, month=1, day=1)
        """
        calendar = self.get(world_id)
        if calendar is None:
            calendar = WorldCalendar(
                year=1, month=1, day=1, era_name="First Age"
            )
            self.save(world_id, calendar)
        return calendar
