"""Event store for event sourcing and persistence.

This module provides storage and retrieval of domain events,
supporting event sourcing patterns and event replay capabilities.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import UUID

from .event_bus import DomainEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredEvent:
    """An event as stored in the event store.

    Includes database-specific fields like position/version.
    """

    position: int
    event_id: UUID
    event_type: str
    aggregate_id: Optional[str]
    aggregate_version: int
    payload: Any
    metadata: Dict[str, Any]
    occurred_on: datetime
    correlation_id: Optional[str]
    causation_id: Optional[str]


class EventStore(ABC):
    """Abstract base class for event stores.

    Provides persistence for domain events with support for:
    - Append-only storage
    - Optimistic concurrency control
    - Event stream queries by aggregate
    - Event replay capabilities
    """

    @abstractmethod
    async def append(
        self,
        aggregate_id: str,
        events: List[DomainEvent[Any]],
        expected_version: Optional[int] = None,
    ) -> List[StoredEvent]:
        """Append events to an aggregate's event stream.

        Args:
            aggregate_id: The aggregate's unique identifier
            events: List of events to append
            expected_version: Expected current version for optimistic locking

        Returns:
            The stored events with their positions

        Raises:
            ConcurrencyError: If expected_version doesn't match current version
            EventStoreError: If storage fails
        """
        raise NotImplementedError

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None,
    ) -> List[StoredEvent]:
        """Get events for an aggregate.

        Args:
            aggregate_id: The aggregate's unique identifier
            from_version: Start from this version (inclusive)
            to_version: Stop at this version (inclusive), None for all

        Returns:
            List of stored events
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_events(
        self,
        from_position: int = 0,
        to_position: Optional[int] = None,
        event_types: Optional[List[str]] = None,
    ) -> List[StoredEvent]:
        """Get all events from the store.

        Args:
            from_position: Start from this position
            to_position: Stop at this position, None for all
            event_types: Filter by event types, None for all

        Returns:
            List of stored events
        """
        raise NotImplementedError

    @abstractmethod
    async def get_current_version(self, aggregate_id: str) -> int:
        """Get the current version of an aggregate.

        Returns 0 if the aggregate doesn't exist.
        """
        raise NotImplementedError


class InMemoryEventStore(EventStore):
    """In-memory event store for testing.

    Not suitable for production use as events are lost on restart.
    """

    def __init__(self) -> None:
        """Initialize the in-memory event store."""
        self._streams: Dict[str, List[StoredEvent]] = {}
        self._all_events: List[StoredEvent] = []
        self._lock_position: int = 0

    def _next_position(self) -> int:
        """Get the next global position."""
        self._lock_position += 1
        return self._lock_position

    def _serialize_payload(self, payload: Any) -> Any:
        """Serialize payload to ensure immutability."""
        return json.loads(json.dumps(payload, default=str))

    async def append(
        self,
        aggregate_id: str,
        events: List[DomainEvent[Any]],
        expected_version: Optional[int] = None,
    ) -> List[StoredEvent]:
        """Append events to an aggregate stream."""
        # Check optimistic locking
        current_version = await self.get_current_version(aggregate_id)
        if expected_version is not None and current_version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version} but found {current_version}"
            )

        if aggregate_id not in self._streams:
            self._streams[aggregate_id] = []

        stored_events: List[StoredEvent] = []

        for i, event in enumerate(events):
            version = current_version + i + 1
            position = self._next_position()

            stored = StoredEvent(
                position=position,
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_id=aggregate_id,
                aggregate_version=version,
                payload=self._serialize_payload(event.payload),
                metadata=dict(event.metadata),
                occurred_on=event.occurred_on,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
            )

            self._streams[aggregate_id].append(stored)
            self._all_events.append(stored)
            stored_events.append(stored)

        logger.debug(f"Appended {len(events)} events to aggregate {aggregate_id}")
        return stored_events

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: Optional[int] = None,
    ) -> List[StoredEvent]:
        """Get events for an aggregate."""
        stream = self._streams.get(aggregate_id, [])

        events = [
            e
            for e in stream
            if e.aggregate_version >= from_version
            and (to_version is None or e.aggregate_version <= to_version)
        ]

        return events

    async def get_all_events(
        self,
        from_position: int = 0,
        to_position: Optional[int] = None,
        event_types: Optional[List[str]] = None,
    ) -> List[StoredEvent]:
        """Get all events from the store."""
        events = [
            e
            for e in self._all_events
            if e.position >= from_position
            and (to_position is None or e.position <= to_position)
            and (event_types is None or e.event_type in event_types)
        ]

        return events

    async def get_current_version(self, aggregate_id: str) -> int:
        """Get current version of an aggregate."""
        stream = self._streams.get(aggregate_id, [])
        if not stream:
            return 0
        return stream[-1].aggregate_version


class EventStoreError(Exception):
    """Base exception for event store errors."""

    pass


class ConcurrencyError(EventStoreError):
    """Raised when optimistic concurrency check fails."""

    pass


class EventNotFoundError(EventStoreError):
    """Raised when an event cannot be found."""

    pass
