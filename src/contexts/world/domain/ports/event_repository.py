#!/usr/bin/env python3
"""Event Repository Port

This module defines the repository port (interface) for HistoryEvent persistence.
Following Hexagonal Architecture, this port defines the contract that
infrastructure implementations must fulfill, keeping the domain layer
pure and independent of persistence details.

The EventRepository follows the Repository Pattern, providing an
abstraction for storing and retrieving HistoryEvent entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.contexts.world.domain.entities.history_event import HistoryEvent


class EventRepository(ABC):
    """Abstract repository port for HistoryEvent persistence.

    This interface defines the contract for event storage operations.
    Implementations can use different storage backends (in-memory, database, etc.)
    while the domain layer remains decoupled from infrastructure concerns.
    """

    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[HistoryEvent]:
        """Retrieve a specific event by its ID.

        Args:
            event_id: Unique identifier for the event

        Returns:
            HistoryEvent if found, None otherwise

        Example:
            >>> event = await repository.get_by_id("event-uuid")
            >>> if event:
            ...     print(event.name)
        """
        pass

    @abstractmethod
    async def get_by_world_id(
        self, world_id: str, limit: int = 100, offset: int = 0
    ) -> List[HistoryEvent]:
        """Retrieve all events for a specific world with pagination.

        Args:
            world_id: ID of the world
            limit: Maximum number of events to return (default 100)
            offset: Number of events to skip for pagination (default 0)

        Returns:
            List of HistoryEvent objects for the world, sorted by date

        Example:
            >>> events = await repository.get_by_world_id("world-1", limit=50)
            >>> print(f"Found {len(events)} events")
        """
        pass

    @abstractmethod
    async def save(self, event: HistoryEvent) -> HistoryEvent:
        """Persist a history event.

        If an event with the same id exists, it will be updated.
        Otherwise, a new event is created.

        Args:
            event: The HistoryEvent to persist

        Returns:
            The saved HistoryEvent (may have updated timestamps)

        Example:
            >>> event = HistoryEvent.create_war(
            ...     name="The Sundering",
            ...     description="A cataclysmic war.",
            ...     date_description="Year 1042",
            ...     faction_ids=["f1", "f2"]
            ... )
            >>> saved = await repository.save(event)
        """
        pass

    @abstractmethod
    async def delete(self, event_id: str) -> bool:
        """Remove an event from the repository.

        Args:
            event_id: Unique identifier for the event

        Returns:
            True if event was deleted, False if it didn't exist

        Example:
            >>> deleted = await repository.delete("event-uuid")
            >>> if deleted:
            ...     print("Event removed")
        """
        pass

    @abstractmethod
    async def get_by_location_id(self, location_id: str) -> List[HistoryEvent]:
        """Retrieve all events that occurred at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of HistoryEvent objects associated with the location

        Example:
            >>> events = await repository.get_by_location_id("loc-1")
            >>> print(f"Location has {len(events)} historical events")
        """
        pass

    @abstractmethod
    async def get_by_faction_id(self, faction_id: str) -> List[HistoryEvent]:
        """Retrieve all events involving a specific faction.

        Args:
            faction_id: ID of the faction

        Returns:
            List of HistoryEvent objects where the faction was involved

        Example:
            >>> events = await repository.get_by_faction_id("faction-1")
            >>> print(f"Faction participated in {len(events)} events")
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all events from the repository.

        This is a utility method primarily used for testing.
        """
        pass
