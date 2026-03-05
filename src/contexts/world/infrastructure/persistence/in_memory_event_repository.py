#!/usr/bin/env python3
"""In-Memory Event Repository Implementation.

This module provides an in-memory implementation of EventRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

import threading
from typing import Dict, List, Optional

import structlog

from src.contexts.world.domain.entities.history_event import HistoryEvent
from src.contexts.world.domain.ports.event_repository import EventRepository

logger = structlog.get_logger()


class InMemoryEventRepository(EventRepository):
    """In-memory implementation of EventRepository.

    Stores events in dictionaries indexed by event_id and world_id.
    Provides efficient lookups by various criteria.

    Thread Safety:
        This implementation IS thread-safe. All operations are protected
        by a reentrant lock (RLock) to ensure safe concurrent access.

    Attributes:
        _events: Dictionary mapping event_id to HistoryEvent
        _world_events: Dictionary mapping world_id to set of event_ids
        _lock: Reentrant lock for thread-safe access
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage and thread lock."""
        self._events: Dict[str, HistoryEvent] = {}
        self._world_events: Dict[str, set[str]] = {}
        self._lock = threading.RLock()
        logger.debug("in_memory_event_repository_initialized")

    async def get_by_id(self, event_id: str) -> Optional[HistoryEvent]:
        """Retrieve a specific event by its ID.

        Args:
            event_id: Unique identifier for the event

        Returns:
            HistoryEvent if found, None otherwise
        """
        with self._lock:
            return self._events.get(event_id)

    async def get_by_world_id(
        self, world_id: str, limit: int = 100, offset: int = 0
    ) -> List[HistoryEvent]:
        """Retrieve all events for a specific world with pagination.

        Args:
            world_id: ID of the world
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of HistoryEvent objects, sorted by narrative_importance desc
        """
        with self._lock:
            event_ids = self._world_events.get(world_id, set())
            events = [self._events[eid] for eid in event_ids if eid in self._events]

            # Sort by narrative importance (descending), then by name
            events.sort(key=lambda e: (-e.narrative_importance, e.name))

            # Apply pagination
            return events[offset : offset + limit]

    async def save(self, event: HistoryEvent) -> HistoryEvent:
        """Persist a history event.

        Args:
            event: The HistoryEvent to persist

        Returns:
            The saved HistoryEvent
        """
        with self._lock:
            is_new = event.id not in self._events
            self._events[event.id] = event

            # Update world index
            self._update_world_index(event)

            logger.debug(
                "event_saved",
                event_id=event.id,
                event_name=event.name,
                event_type=event.event_type.value,
                is_new=is_new,
            )
            return event

    async def save_all(self, events: List[HistoryEvent]) -> List[HistoryEvent]:
        """Persist multiple history events in a single operation.

        Args:
            events: List of HistoryEvent objects to persist

        Returns:
            List of saved HistoryEvent objects
        """
        with self._lock:
            saved_events: list[Any] = []
            for event in events:
                saved = await self.save(event)
                saved_events.append(saved)

            logger.info(
                "events_batch_saved",
                count=len(saved_events),
            )
            return saved_events

    def _update_world_index(self, event: HistoryEvent) -> None:
        """Update the world index for an event.

        Args:
            event: The HistoryEvent to index
        """
        world_id = self._derive_world_id(event)
        if world_id:
            if world_id not in self._world_events:
                self._world_events[world_id] = set()
            self._world_events[world_id].add(event.id)

    def _derive_world_id(self, event: HistoryEvent) -> Optional[str]:
        """Derive a world_id from the event.

        Since HistoryEvent doesn't have a direct world_id, we use the
        first location_id as a proxy for world identification.
        In a real implementation, we'd look up the location's world.

        Args:
            event: The HistoryEvent to derive world_id from

        Returns:
            World ID string or None
        """
        # Use first location_id as world proxy
        # In production, this would do: location.world_id
        if event.location_ids:
            return event.location_ids[0]
        return None

    async def delete(self, event_id: str) -> bool:
        """Remove an event from the repository.

        Args:
            event_id: Unique identifier for the event

        Returns:
            True if event was deleted, False if it didn't exist
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return False

            del self._events[event_id]

            # Remove from world index if present
            for world_id, event_ids in self._world_events.items():
                if event_id in event_ids:
                    event_ids.discard(event_id)
                    break

            logger.debug("event_deleted", event_id=event_id)
            return True

    async def get_by_location_id(self, location_id: str) -> List[HistoryEvent]:
        """Retrieve all events that occurred at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of HistoryEvent objects associated with the location
        """
        with self._lock:
            events = [
                event
                for event in self._events.values()
                if location_id in event.location_ids
            ]
            # Sort by narrative importance
            events.sort(key=lambda e: (-e.narrative_importance, e.name))
            return events

    async def get_by_faction_id(self, faction_id: str) -> List[HistoryEvent]:
        """Retrieve all events involving a specific faction.

        Args:
            faction_id: ID of the faction

        Returns:
            List of HistoryEvent objects where the faction was involved
        """
        with self._lock:
            events = [
                event
                for event in self._events.values()
                if faction_id in event.faction_ids
            ]
            # Sort by narrative importance
            events.sort(key=lambda e: (-e.narrative_importance, e.name))
            return events

    async def clear(self) -> None:
        """Clear all events from the repository."""
        with self._lock:
            self._events.clear()
            self._world_events.clear()
            logger.debug("all_events_cleared")

    def register_world_event(self, world_id: str, event_id: str) -> None:
        """Register an event as belonging to a specific world.

        This is a helper method since HistoryEvent doesn't have a world_id field.
        Call this after saving an event to explicitly associate it with a world.

        Args:
            world_id: ID of the world
            event_id: ID of the event
        """
        with self._lock:
            if world_id not in self._world_events:
                self._world_events[world_id] = set()
            self._world_events[world_id].add(event_id)
            logger.debug(
                "event_registered_to_world",
                world_id=world_id,
                event_id=event_id,
            )
