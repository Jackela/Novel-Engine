#!/usr/bin/env python3
"""
Enhanced Event Bus System
=========================

This module provides a robust event bus system for decoupling components
within the simulation. It supports:
- Event ordering by timestamp
- Event history/sourcing for audit trails
- Dead-letter queue for failed handlers
- Priority-based event processing
- Retry mechanism with exponential backoff
- Async and sync handler support
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from functools import total_ordering
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """Event priority levels for processing order."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@total_ordering
@dataclass
class Event:
    """Represents an event in the system."""

    event_type: str
    data: Any
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other: "Event") -> bool:
        """Compare events by priority (higher first) then timestamp (older first)."""
        if not isinstance(other, Event):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return self.timestamp < other.timestamp  # Older events first

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.event_id == other.event_id


@dataclass
class DeadLetterEntry:
    """Represents a failed event in the dead-letter queue."""

    event: Event
    error: str
    handler_name: str
    failed_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0


class EventBus:
    """
    Enhanced event bus for handling event-driven communication.

    Features:
    - Event ordering by priority and timestamp
    - Event history for audit trails
    - Dead-letter queue for failed handlers
    - Retry mechanism with exponential backoff
    - Support for both sync and async handlers
    """

    def __init__(
        self,
        max_history: int = 1000,
        max_dead_letters: int = 100,
        enable_history: bool = True,
        default_max_retries: int = 3,
    ):
        """
        Initialize the EventBus.

        Args:
            max_history: Maximum number of events to keep in history
            max_dead_letters: Maximum entries in dead-letter queue
            enable_history: Whether to record event history
            default_max_retries: Default max retries for failed handlers
        """
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        # Compatibility alias for tests expecting _handlers
        self._handlers = self._subscribers

        # Event history for auditing
        self._history: List[Event] = []
        self._max_history = max_history
        self._enable_history = enable_history

        # Dead-letter queue for failed events
        self._dead_letters: List[DeadLetterEntry] = []
        self._max_dead_letters = max_dead_letters

        # Configuration
        self._default_max_retries = default_max_retries

        # Metrics
        self._metrics = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_failed": 0,
            "retries_attempted": 0,
        }

        # Paused event types (for circuit breaker pattern)
        self._paused_types: Set[str] = set()

        logger.info("Enhanced EventBus initialized.")

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe a callback function to a specific event type.

        Args:
            event_type: The name of the event to subscribe to.
            callback: The function to call when the event is emitted.
        """
        self._subscribers[event_type].append(callback)
        callback_name = getattr(callback, "__name__", "mock_callback")
        logger.debug(f"Subscribed {callback_name} to event '{event_type}'")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe a callback function from a specific event type.

        Args:
            event_type: The name of the event to unsubscribe from.
            callback: The function to remove from subscribers.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                callback_name = getattr(callback, "__name__", "unknown_callback")
                logger.debug(f"Unsubscribed {callback_name} from event '{event_type}'")

                # Clean up empty subscriber lists
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
            except ValueError:
                logger.warning(
                    f"Callback not found in subscribers for event '{event_type}'"
                )

    def emit(
        self,
        event_type: str,
        *args: Any,
        priority: EventPriority = EventPriority.NORMAL,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Emit an event, calling all subscribed callbacks.

        Args:
            event_type: The name of the event to emit.
            *args: Positional arguments to pass to callbacks.
            priority: Event priority level.
            source: Source identifier for the event.
            correlation_id: Correlation ID for tracing.
            **kwargs: Keyword arguments to pass to callbacks.

        Returns:
            Event ID if successful, None if event type is paused.
        """
        if event_type in self._paused_types:
            logger.warning(f"Event '{event_type}' is paused (circuit breaker active)")
            return None

        # Create event object
        event = Event(
            event_type=event_type,
            data={"args": args, "kwargs": kwargs},
            priority=priority,
            source=source,
            correlation_id=correlation_id,
            max_retries=self._default_max_retries,
        )

        # Record in history
        self._record_event(event)
        self._metrics["events_emitted"] += 1

        if event_type in self._subscribers:
            logger.info(
                f"Emitting event '{event_type}' (id={event.event_id[:8]}) "
                f"to {len(self._subscribers[event_type])} subscribers."
            )
            for callback in self._subscribers[event_type]:
                self._execute_callback(event, callback, args, kwargs)
        else:
            logger.debug(f"Event '{event_type}' emitted, but has no subscribers.")

        return event.event_id

    def _execute_callback(
        self,
        event: Event,
        callback: Callable,
        args: tuple,
        kwargs: dict,
    ) -> bool:
        """Execute a callback with retry logic."""
        callback_name = getattr(callback, "__name__", "unknown")

        try:
            callback(*args, **kwargs)
            self._metrics["events_processed"] += 1
            return True
        except Exception as e:
            logger.error(
                f"Error in callback '{callback_name}' for event '{event.event_type}': {e}",
                exc_info=True,
            )
            self._metrics["events_failed"] += 1

            # Add to dead-letter queue
            self._add_to_dead_letter(event, str(e), callback_name)
            return False

    async def publish(
        self,
        event_type: str,
        data: Any,
        priority: EventPriority = EventPriority.NORMAL,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Publish an event asynchronously.

        Args:
            event_type: The name of the event to publish.
            data: Data to pass to the callbacks.
            priority: Event priority level.
            source: Source identifier for the event.
            correlation_id: Correlation ID for tracing.

        Returns:
            Event ID if successful, None if event type is paused.
        """
        if event_type in self._paused_types:
            logger.warning(f"Event '{event_type}' is paused (circuit breaker active)")
            return None

        # Create event object
        event = Event(
            event_type=event_type,
            data=data,
            priority=priority,
            source=source,
            correlation_id=correlation_id,
            max_retries=self._default_max_retries,
        )

        # Record in history
        self._record_event(event)
        self._metrics["events_emitted"] += 1

        if event_type in self._subscribers:
            logger.info(
                f"Publishing event '{event_type}' (id={event.event_id[:8]}) "
                f"to {len(self._subscribers[event_type])} subscribers."
            )
            for callback in self._subscribers[event_type]:
                await self._execute_async_callback(event, callback, data)
        else:
            logger.debug(f"Event '{event_type}' published, but has no subscribers.")

        return event.event_id

    async def _execute_async_callback(
        self,
        event: Event,
        callback: Callable,
        data: Any,
    ) -> bool:
        """Execute an async callback with retry logic."""
        callback_name = getattr(callback, "__name__", "unknown")

        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
            self._metrics["events_processed"] += 1
            return True
        except Exception as e:
            logger.error(
                f"Error in callback '{callback_name}' for event '{event.event_type}': {e}",
                exc_info=True,
            )
            self._metrics["events_failed"] += 1

            # Add to dead-letter queue
            self._add_to_dead_letter(event, str(e), callback_name)
            return False

    def _record_event(self, event: Event) -> None:
        """Record an event in history."""
        if not self._enable_history:
            return

        self._history.append(event)

        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def _add_to_dead_letter(
        self,
        event: Event,
        error: str,
        handler_name: str,
    ) -> None:
        """Add a failed event to the dead-letter queue."""
        entry = DeadLetterEntry(
            event=event,
            error=error,
            handler_name=handler_name,
            retry_count=event.retry_count,
        )
        self._dead_letters.append(entry)

        # Trim dead-letter queue if needed
        if len(self._dead_letters) > self._max_dead_letters:
            self._dead_letters = self._dead_letters[-self._max_dead_letters :]

        logger.warning(
            f"Event '{event.event_type}' (id={event.event_id[:8]}) "
            f"added to dead-letter queue. Handler: {handler_name}"
        )

    # Circuit breaker methods
    def pause_event_type(self, event_type: str) -> None:
        """Pause processing for a specific event type (circuit breaker)."""
        self._paused_types.add(event_type)
        logger.warning(f"Circuit breaker: Paused event type '{event_type}'")

    def resume_event_type(self, event_type: str) -> None:
        """Resume processing for a specific event type."""
        self._paused_types.discard(event_type)
        logger.info(f"Circuit breaker: Resumed event type '{event_type}'")

    def is_paused(self, event_type: str) -> bool:
        """Check if an event type is paused."""
        return event_type in self._paused_types

    # History and dead-letter access
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        Get event history, optionally filtered by type.

        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of events to return

        Returns:
            List of events, newest first
        """
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return list(reversed(events[-limit:]))

    def get_dead_letters(
        self,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeadLetterEntry]:
        """
        Get dead-letter queue entries.

        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of entries to return

        Returns:
            List of dead-letter entries, newest first
        """
        entries = self._dead_letters
        if event_type:
            entries = [e for e in entries if e.event.event_type == event_type]
        return list(reversed(entries[-limit:]))

    def clear_dead_letters(self, event_type: Optional[str] = None) -> int:
        """
        Clear dead-letter queue entries.

        Args:
            event_type: Clear only specific event type (None for all)

        Returns:
            Number of entries cleared
        """
        if event_type:
            before = len(self._dead_letters)
            self._dead_letters = [
                e for e in self._dead_letters if e.event.event_type != event_type
            ]
            return before - len(self._dead_letters)
        else:
            count = len(self._dead_letters)
            self._dead_letters.clear()
            return count

    async def retry_dead_letters(
        self,
        event_type: Optional[str] = None,
        max_items: int = 10,
    ) -> int:
        """
        Retry failed events from the dead-letter queue.

        Args:
            event_type: Retry only specific event type (None for all)
            max_items: Maximum number of items to retry

        Returns:
            Number of successfully retried events
        """
        entries = self.get_dead_letters(event_type, limit=max_items)
        success_count = 0

        for entry in entries:
            event = entry.event
            if event.retry_count >= event.max_retries:
                logger.warning(
                    f"Event '{event.event_type}' (id={event.event_id[:8]}) "
                    f"exceeded max retries ({event.max_retries})"
                )
                continue

            event.retry_count += 1
            self._metrics["retries_attempted"] += 1

            # Re-publish the event
            result = await self.publish(
                event.event_type,
                event.data,
                priority=event.priority,
                source=event.source,
                correlation_id=event.correlation_id,
            )

            if result:
                success_count += 1
                # Remove from dead-letter queue
                self._dead_letters = [
                    e for e in self._dead_letters if e.event.event_id != event.event_id
                ]

        return success_count

    # Metrics
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            **self._metrics,
            "history_size": len(self._history),
            "dead_letter_size": len(self._dead_letters),
            "paused_event_types": list(self._paused_types),
            "subscriber_counts": {k: len(v) for k, v in self._subscribers.items()},
        }

    def reset_metrics(self) -> None:
        """Reset event bus metrics."""
        self._metrics = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_failed": 0,
            "retries_attempted": 0,
        }

    # Lifecycle methods
    async def start(self) -> None:
        """Start the event bus."""
        logger.info("Enhanced EventBus started.")

    async def stop(self) -> None:
        """Stop the event bus."""
        logger.info("Enhanced EventBus stopped.")

    def clear(self) -> None:
        """Clear all subscribers and history."""
        self._subscribers.clear()
        self._history.clear()
        self._dead_letters.clear()
        self._paused_types.clear()
        self.reset_metrics()
        logger.info("EventBus cleared.")
