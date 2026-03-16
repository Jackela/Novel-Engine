"""Event Bus abstraction for event-driven architecture.

This module provides the abstract interface for event bus implementations,
supporting both publish-subscribe and request-response patterns.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

# Type variable for event payloads
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DomainEvent(Generic[T]):
    """Represents a domain event in the system.

    Attributes:
        event_type: The type/category of the event
        aggregate_id: Optional ID of the aggregate that produced the event
        payload: The event data/payload
        event_id: Unique identifier for this event occurrence
        correlation_id: Optional correlation ID for tracing related events
        causation_id: Optional ID of the event that caused this event
        occurred_on: Timestamp when the event occurred
        metadata: Additional metadata for the event
    """

    event_type: str
    payload: T
    aggregate_id: Optional[str] = None
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    occurred_on: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event after initialization."""
        if not self.event_type:
            raise ValueError("event_type cannot be empty")


# Type alias for event handlers
EventHandler = Callable[[DomainEvent[Any]], Awaitable[None]]


class EventBus(abc.ABC):
    """Abstract base class for event bus implementations.

    The EventBus provides a publish-subscribe mechanism for decoupled
    communication between system components. All operations are async
    to support high-throughput scenarios.
    """

    @abc.abstractmethod
    async def publish(
        self,
        event: DomainEvent[Any],
        topic: Optional[str] = None,
    ) -> None:
        """Publish an event to the event bus.

        Args:
            event: The event to publish
            topic: Optional topic/channel to publish to.
                   If None, uses the event_type as topic.

        Raises:
            EventBusError: If publication fails
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Subscribe a handler to events of a specific type.

        Args:
            event_type: The type of events to subscribe to
            handler: Async callback function to handle events
            topic: Optional topic to subscribe to

        Raises:
            EventBusError: If subscription fails
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Unsubscribe a handler from events of a specific type.

        Args:
            event_type: The type of events to unsubscribe from
            handler: The handler to remove
            topic: Optional topic to unsubscribe from

        Raises:
            EventBusError: If unsubscription fails
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the event bus and establish connections.

        Must be called before publishing or subscribing.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the event bus and close connections.

        Should gracefully complete any in-flight operations.
        """
        raise NotImplementedError


class EventBusError(Exception):
    """Base exception for event bus errors."""

    pass


class EventPublishError(EventBusError):
    """Raised when event publication fails."""

    pass


class EventSubscribeError(EventBusError):
    """Raised when event subscription fails."""

    pass


class EventBusNotStartedError(EventBusError):
    """Raised when operations are performed on a stopped event bus."""

    pass
