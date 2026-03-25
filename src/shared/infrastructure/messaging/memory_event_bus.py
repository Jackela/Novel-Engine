"""In-memory event bus implementation for testing and local development.

This module provides a simple, fast event bus implementation that stores
all subscriptions in memory. Not suitable for production use in distributed
systems but excellent for testing and single-process applications.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from .event_bus import (
    DomainEvent,
    EventBus,
    EventBusNotStartedError,
    EventHandler,
    EventPublishError,
    EventSubscribeError,
)

logger = logging.getLogger(__name__)


class MemoryEventBus(EventBus):
    """In-memory event bus implementation.

    This implementation maintains all state in memory and uses asyncio
    for asynchronous event delivery. It's fast and suitable for:
    - Unit and integration testing
    - Single-process applications
    - Local development

    Not suitable for:
    - Distributed systems
    - Persistence across restarts
    - High availability scenarios
    """

    def __init__(self) -> None:
        """Initialize the in-memory event bus."""
        self._subscriptions: Dict[str, Set[EventHandler]] = {}
        self._topic_subscriptions: Dict[str, Dict[str, Set[EventHandler]]] = {}
        self._started: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()
        self._delivery_sem: asyncio.Semaphore = asyncio.Semaphore(100)

    async def start(self) -> None:
        """Start the event bus.

        Resets all internal state and prepares for operation.
        """
        async with self._lock:
            self._subscriptions.clear()
            self._topic_subscriptions.clear()
            self._started = True
            logger.debug("MemoryEventBus started")

    async def stop(self) -> None:
        """Stop the event bus.

        Clears all subscriptions and prevents further operations.
        """
        async with self._lock:
            self._started = False
            self._subscriptions.clear()
            self._topic_subscriptions.clear()
            logger.debug("MemoryEventBus stopped")

    def _ensure_started(self) -> None:
        """Ensure the bus has been started.

        Raises:
            EventBusNotStartedError: If bus is not started
        """
        if not self._started:
            raise EventBusNotStartedError("EventBus must be started before operations")

    async def publish(
        self,
        event: DomainEvent[Any],
        topic: Optional[str] = None,
    ) -> None:
        """Publish an event to subscribers.

        Delivers the event asynchronously to all matching subscribers.

        Args:
            event: The event to publish
            topic: Optional topic override

        Raises:
            EventBusNotStartedError: If bus is not started
            EventPublishError: If delivery fails
        """
        self._ensure_started()

        event_type = event.event_type
        effective_topic = topic or event_type

        # Collect all handlers
        handlers: Set[EventHandler] = set()

        # Add global subscriptions for this event type
        if event_type in self._subscriptions:
            handlers.update(self._subscriptions[event_type])

        # Add topic-specific subscriptions
        if effective_topic in self._topic_subscriptions:
            topic_subs = self._topic_subscriptions[effective_topic]
            if event_type in topic_subs:
                handlers.update(topic_subs[event_type])

        if not handlers:
            logger.debug(f"No handlers for event type: {event_type}")
            return

        # Deliver to all handlers concurrently
        delivery_tasks: List[asyncio.Task[None]] = []
        for handler in handlers:
            task = asyncio.create_task(
                self._deliver_event(handler, event),
                name=f"delivery-{event.event_id}",
            )
            delivery_tasks.append(task)

        # Wait for all deliveries with timeout
        try:
            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Handler {i} failed for event {event.event_id}: {result}"
                    )
        except Exception as e:
            raise EventPublishError(f"Failed to publish event: {e}") from e

    async def _deliver_event(
        self,
        handler: EventHandler,
        event: DomainEvent[Any],
    ) -> None:
        """Deliver an event to a single handler.

        Uses a semaphore to limit concurrent deliveries.
        """
        async with self._delivery_sem:
            try:
                await handler(event)
            except Exception as e:
                logger.exception(f"Event handler failed: {e}")
                raise

    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Subscribe a handler to events.

        Args:
            event_type: The event type to subscribe to
            handler: Async handler function
            topic: Optional topic to scope the subscription

        Raises:
            EventBusNotStartedError: If bus is not started
            EventSubscribeError: If subscription fails
        """
        self._ensure_started()

        async with self._lock:
            try:
                if topic:
                    # Topic-scoped subscription
                    if topic not in self._topic_subscriptions:
                        self._topic_subscriptions[topic] = {}
                    if event_type not in self._topic_subscriptions[topic]:
                        self._topic_subscriptions[topic][event_type] = set()
                    self._topic_subscriptions[topic][event_type].add(handler)
                    logger.debug(f"Subscribed handler to {event_type} on topic {topic}")
                else:
                    # Global subscription
                    if event_type not in self._subscriptions:
                        self._subscriptions[event_type] = set()
                    self._subscriptions[event_type].add(handler)
                    logger.debug(f"Subscribed handler to {event_type}")

            except Exception as e:
                raise EventSubscribeError(f"Failed to subscribe: {e}") from e

    async def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Unsubscribe a handler from events.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
            topic: Optional topic to scope the unsubscription

        Raises:
            EventBusNotStartedError: If bus is not started
        """
        self._ensure_started()

        async with self._lock:
            if topic:
                # Remove from topic-scoped subscriptions
                if topic in self._topic_subscriptions:
                    topic_subs = self._topic_subscriptions[topic]
                    if event_type in topic_subs:
                        topic_subs[event_type].discard(handler)
                        if not topic_subs[event_type]:
                            del topic_subs[event_type]
                        if not topic_subs:
                            del self._topic_subscriptions[topic]
            else:
                # Remove from global subscriptions
                if event_type in self._subscriptions:
                    self._subscriptions[event_type].discard(handler)
                    if not self._subscriptions[event_type]:
                        del self._subscriptions[event_type]

    async def get_subscriber_count(
        self,
        event_type: str,
        topic: Optional[str] = None,
    ) -> int:
        """Get the number of subscribers for an event type.

        Useful for testing and monitoring.
        """
        self._ensure_started()

        async with self._lock:
            count = 0

            if event_type in self._subscriptions:
                count += len(self._subscriptions[event_type])

            if topic and topic in self._topic_subscriptions:
                topic_subs = self._topic_subscriptions[topic]
                if event_type in topic_subs:
                    count += len(topic_subs[event_type])

            return count

    async def clear_subscriptions(self) -> None:
        """Clear all subscriptions. Useful for testing."""
        async with self._lock:
            self._subscriptions.clear()
            self._topic_subscriptions.clear()
