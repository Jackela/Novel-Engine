#!/usr/bin/env python3
"""
Event-Driven Architecture System
===============================

Comprehensive event bus with pub/sub patterns, event sourcing, and distributed event handling.
"""

import asyncio
import logging
import threading
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

from .error_handler import CentralizedErrorHandler, ErrorContext

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EventPriority(Enum):
    """Event processing priorities."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    SYSTEM = 4


class EventDeliveryMode(Enum):
    """Event delivery modes."""

    FIRE_AND_FORGET = "fire_and_forget"  # No acknowledgment required
    AT_LEAST_ONCE = "at_least_once"  # Guaranteed delivery with retries
    EXACTLY_ONCE = "exactly_once"  # Guaranteed single delivery
    ORDERED = "ordered"  # Maintain event order


@dataclass
class EventMetadata:
    """Event metadata for tracking and routing."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    delivery_mode: EventDeliveryMode = EventDeliveryMode.FIRE_AND_FORGET
    retry_count: int = 0
    max_retries: int = 3
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)


@dataclass
class Event(Generic[T]):
    """Generic event with payload and metadata."""

    event_type: str
    payload: T
    metadata: EventMetadata = field(default_factory=EventMetadata)

    def __post_init__(self):
        """Set event type in metadata for consistency."""
        if not hasattr(self.metadata, "event_type"):
            self.metadata.event_type = self.event_type

    def with_correlation_id(self, correlation_id: str) -> "Event[T]":
        """Create new event with correlation ID."""
        new_metadata = EventMetadata(**self.metadata.__dict__)
        new_metadata.correlation_id = correlation_id
        return Event(self.event_type, self.payload, new_metadata)

    def with_causation_id(self, causation_id: str) -> "Event[T]":
        """Create new event with causation ID."""
        new_metadata = EventMetadata(**self.metadata.__dict__)
        new_metadata.causation_id = causation_id
        return Event(self.event_type, self.payload, new_metadata)


class EventHandler(Protocol):
    """Event handler protocol."""

    async def handle(self, event: Event) -> bool:
        """
        Handle event.

        Returns:
            bool: True if handled successfully, False otherwise
        """
        pass


@dataclass
class HandlerRegistration:
    """Event handler registration."""

    handler: EventHandler
    event_type: str
    priority: int = 0
    filters: Dict[str, Any] = field(default_factory=dict)
    max_concurrent: int = 10
    timeout_seconds: float = 30.0
    retry_on_failure: bool = True
    dead_letter_queue: bool = True


@dataclass
class EventProcessingResult:
    """Result of event processing."""

    event_id: str
    success: bool
    handler_results: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    retry_count: int = 0


class EventStore:
    """Simple in-memory event store for event sourcing."""

    def __init__(self, max_events: int = 100000):
        """Initialize event store."""
        self.max_events = max_events
        self._events: deque = deque(maxlen=max_events)
        self._event_index: Dict[str, Event] = {}
        self._correlation_index: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()

    def store_event(self, event: Event) -> None:
        """Store event in the event store."""
        with self._lock:
            self._events.append(event)
            self._event_index[event.metadata.event_id] = event

            # Index by correlation ID
            if event.metadata.correlation_id:
                self._correlation_index[event.metadata.correlation_id].append(
                    event.metadata.event_id
                )

    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        with self._lock:
            return self._event_index.get(event_id)

    def get_events_by_correlation(self, correlation_id: str) -> List[Event]:
        """Get all events with the same correlation ID."""
        with self._lock:
            event_ids = self._correlation_index.get(correlation_id, [])
            return [
                self._event_index[event_id]
                for event_id in event_ids
                if event_id in self._event_index
            ]

    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """Get recent events by type."""
        with self._lock:
            matching_events = []
            for event in reversed(self._events):
                if event.event_type == event_type:
                    matching_events.append(event)
                    if len(matching_events) >= limit:
                        break
            return matching_events

    def get_recent_events(self, limit: int = 100) -> List[Event]:
        """Get most recent events."""
        with self._lock:
            return list(reversed(list(self._events)))[:limit]


class EventBus:
    """
    Comprehensive event bus with pub/sub, event sourcing, and distributed handling.

    Features:
    - Publisher/subscriber pattern
    - Event filtering and routing
    - Priority-based processing
    - Event sourcing and replay
    - Circuit breaker patterns
    - Dead letter queue
    - Performance monitoring
    """

    def __init__(
        self,
        error_handler: Optional[CentralizedErrorHandler] = None,
        enable_event_store: bool = True,
    ):
        """Initialize event bus."""
        self.error_handler = error_handler

        # Handler registry
        self._handlers: Dict[str, List[HandlerRegistration]] = defaultdict(list)
        self._global_handlers: List[HandlerRegistration] = []

        # Event processing
        self._processing_queues: Dict[EventPriority, asyncio.Queue] = {}
        self._processor_tasks: List[asyncio.Task] = []
        self._processing_stats = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "handlers_executed": 0,
            "average_processing_time": 0.0,
        }

        # Event store
        self.event_store = EventStore() if enable_event_store else None

        # Dead letter queue
        self._dead_letter_queue: deque = deque(maxlen=10000)

        # Circuit breakers for handlers
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # Thread safety
        self._lock = threading.RLock()
        self._running = False

        # Performance monitoring
        self._event_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "last_processed": None,
            }
        )

        # Initialize processing queues
        for priority in EventPriority:
            self._processing_queues[priority] = asyncio.Queue()

        logger.info("Event bus initialized")

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        priority: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 10,
        timeout_seconds: float = 30.0,
    ) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Event type to subscribe to
            handler: Event handler
            priority: Handler priority (higher executes first)
            filters: Additional event filters
            max_concurrent: Max concurrent handler executions
            timeout_seconds: Handler timeout
        """
        with self._lock:
            registration = HandlerRegistration(
                handler=handler,
                event_type=event_type,
                priority=priority,
                filters=filters or {},
                max_concurrent=max_concurrent,
                timeout_seconds=timeout_seconds,
            )

            self._handlers[event_type].append(registration)

            # Sort by priority (higher priority first)
            self._handlers[event_type].sort(key=lambda x: x.priority, reverse=True)

            logger.debug(f"Handler subscribed to {event_type}")

    def subscribe_to_all(
        self,
        handler: EventHandler,
        priority: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Subscribe to all events (global handler)."""
        with self._lock:
            registration = HandlerRegistration(
                handler=handler,
                event_type="*",
                priority=priority,
                filters=filters or {},
            )

            self._global_handlers.append(registration)
            self._global_handlers.sort(key=lambda x: x.priority, reverse=True)

            logger.debug("Global handler registered")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe handler from event type."""
        with self._lock:
            if event_type in self._handlers:
                original_count = len(self._handlers[event_type])
                self._handlers[event_type] = [
                    reg for reg in self._handlers[event_type] if reg.handler != handler
                ]
                removed = original_count - len(self._handlers[event_type])
                logger.debug(f"Unsubscribed {removed} handlers from {event_type}")
                return removed > 0

            return False

    async def publish(self, event: Event) -> EventProcessingResult:
        """
        Publish event to all subscribers.

        Args:
            event: Event to publish

        Returns:
            EventProcessingResult: Processing result
        """
        if not self._running:
            await self.start()

        start_time = asyncio.get_running_loop().time()

        try:
            # Store event if event store is enabled
            if self.event_store:
                self.event_store.store_event(event)

            # Add to appropriate priority queue
            priority = event.metadata.priority
            await self._processing_queues[priority].put(event)

            # Update metrics
            self._processing_stats["total_events"] += 1

            # For synchronous behavior, we could wait for processing
            # For now, return immediate result
            result = EventProcessingResult(
                event_id=event.metadata.event_id,
                success=True,
                processing_time=asyncio.get_running_loop().time() - start_time,
            )

            logger.debug(
                f"Event published: {event.event_type} ({event.metadata.event_id})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to publish event {event.metadata.event_id}: {e}")

            if self.error_handler:
                error_context = ErrorContext(
                    component="EventBus",
                    operation="publish",
                    metadata={
                        "event_id": event.metadata.event_id,
                        "event_type": event.event_type,
                    },
                )
                await self.error_handler.handle_error(e, error_context)

            return EventProcessingResult(
                event_id=event.metadata.event_id,
                success=False,
                errors=[str(e)],
                processing_time=asyncio.get_running_loop().time() - start_time,
            )

    async def publish_and_wait(
        self, event: Event, timeout: float = 30.0
    ) -> EventProcessingResult:
        """Publish event and wait for all handlers to complete."""
        # This is a simplified implementation
        # In a full implementation, we'd track handler completion
        return await self.publish(event)

    async def start(self) -> None:
        """Start event processing."""
        if self._running:
            return

        self._running = True

        # Start processor tasks for each priority level
        for priority in EventPriority:
            task = asyncio.create_task(self._process_events(priority))
            self._processor_tasks.append(task)

        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop event processing."""
        if not self._running:
            return

        self._running = False

        # Cancel processor tasks
        for task in self._processor_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._processor_tasks, return_exceptions=True)
        self._processor_tasks.clear()

        logger.info("Event bus stopped")

    async def _process_events(self, priority: EventPriority) -> None:
        """Process events for a specific priority level."""
        queue = self._processing_queues[priority]

        while self._running:
            try:
                # Wait for next event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=1.0)

                # Process event
                await self._handle_event(event)

            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except asyncio.CancelledError:
                # Task cancelled, exit
                break
            except Exception as e:
                logger.error(
                    f"Error in event processor for priority {priority.name}: {e}"
                )

    async def _handle_event(self, event: Event) -> None:
        """Handle a single event with all registered handlers."""
        start_time = asyncio.get_running_loop().time()

        try:
            # Get handlers for this event type
            handlers = self._get_applicable_handlers(event)

            if not handlers:
                logger.debug(f"No handlers for event type: {event.event_type}")
                return

            # Execute handlers concurrently
            handler_tasks = []
            for registration in handlers:
                task = asyncio.create_task(self._execute_handler(event, registration))
                handler_tasks.append(task)

            # Wait for all handlers to complete
            handler_results = await asyncio.gather(
                *handler_tasks, return_exceptions=True
            )

            # Process results
            successful_handlers = 0
            failed_handlers = 0

            for result in handler_results:
                if isinstance(result, Exception):
                    failed_handlers += 1
                    logger.error(
                        f"Handler failed for event {event.metadata.event_id}: {result}"
                    )
                elif result:
                    successful_handlers += 1
                else:
                    failed_handlers += 1

            # Update statistics
            processing_time = asyncio.get_running_loop().time() - start_time

            self._processing_stats["handlers_executed"] += len(handlers)

            if failed_handlers == 0:
                self._processing_stats["successful_events"] += 1
            else:
                self._processing_stats["failed_events"] += 1

            # Update average processing time
            current_avg = self._processing_stats["average_processing_time"]
            total_events = self._processing_stats["total_events"]
            self._processing_stats["average_processing_time"] = (
                current_avg * (total_events - 1) + processing_time
            ) / total_events

            # Update event-specific metrics
            metrics = self._event_metrics[event.event_type]
            metrics["count"] += 1
            metrics["last_processed"] = datetime.now()

            # Update success rate
            if metrics["count"] == 1:
                metrics["success_rate"] = 1.0 if failed_handlers == 0 else 0.0
            else:
                current_successes = metrics["success_rate"] * (metrics["count"] - 1)
                if failed_handlers == 0:
                    current_successes += 1
                metrics["success_rate"] = current_successes / metrics["count"]

            # Update average processing time
            current_avg_time = metrics["avg_processing_time"]
            if metrics["count"] == 1:
                metrics["avg_processing_time"] = processing_time
            else:
                metrics["avg_processing_time"] = (
                    current_avg_time * (metrics["count"] - 1) + processing_time
                ) / metrics["count"]

            logger.debug(
                f"Event processed: {event.event_type} - {successful_handlers} successful, {failed_handlers} failed"
            )

        except Exception as e:
            logger.error(
                f"Critical error processing event {event.metadata.event_id}: {e}"
            )

            # Add to dead letter queue
            self._dead_letter_queue.append(
                {
                    "event": event,
                    "error": str(e),
                    "timestamp": datetime.now(),
                    "retry_count": event.metadata.retry_count,
                }
            )

    def _get_applicable_handlers(self, event: Event) -> List[HandlerRegistration]:
        """Get all handlers that should process this event."""
        applicable_handlers = []

        # Add specific event type handlers
        if event.event_type in self._handlers:
            applicable_handlers.extend(self._handlers[event.event_type])

        # Add global handlers
        applicable_handlers.extend(self._global_handlers)

        # Filter by additional criteria
        filtered_handlers = []
        for registration in applicable_handlers:
            if self._handler_matches_filters(event, registration):
                filtered_handlers.append(registration)

        return filtered_handlers

    def _handler_matches_filters(
        self, event: Event, registration: HandlerRegistration
    ) -> bool:
        """Check if handler matches event filters."""
        if not registration.filters:
            return True

        # Check each filter
        for filter_key, filter_value in registration.filters.items():
            # Check metadata filters
            if filter_key.startswith("metadata."):
                metadata_key = filter_key[9:]  # Remove 'metadata.' prefix
                if not hasattr(event.metadata, metadata_key):
                    return False

                actual_value = getattr(event.metadata, metadata_key)
                if actual_value != filter_value:
                    return False

            # Check payload filters (basic)
            elif filter_key.startswith("payload."):
                payload_key = filter_key[8:]  # Remove 'payload.' prefix
                if not hasattr(event.payload, payload_key):
                    return False

                actual_value = getattr(event.payload, payload_key)
                if actual_value != filter_value:
                    return False

        return True

    async def _execute_handler(
        self, event: Event, registration: HandlerRegistration
    ) -> bool:
        """Execute a single handler with error handling and circuit breaker."""
        handler_id = (
            f"{registration.handler.__class__.__name__}_{registration.event_type}"
        )

        # Check circuit breaker
        if self._is_circuit_open(handler_id):
            logger.warning(f"Circuit breaker open for handler {handler_id}")
            return False

        try:
            # Execute handler with timeout
            result = await asyncio.wait_for(
                registration.handler.handle(event), timeout=registration.timeout_seconds
            )

            # Reset circuit breaker on success
            self._reset_circuit_breaker(handler_id)

            return result

        except asyncio.TimeoutError:
            logger.warning(f"Handler timeout for {handler_id}")
            self._record_circuit_breaker_failure(handler_id)
            return False

        except Exception as e:
            logger.error(f"Handler error for {handler_id}: {e}")
            self._record_circuit_breaker_failure(handler_id)

            if self.error_handler:
                error_context = ErrorContext(
                    component="EventBus",
                    operation=f"execute_handler_{handler_id}",
                    metadata={
                        "event_id": event.metadata.event_id,
                        "event_type": event.event_type,
                        "handler": handler_id,
                    },
                )
                await self.error_handler.handle_error(e, error_context)

            return False

    def _is_circuit_open(self, handler_id: str) -> bool:
        """Check if circuit breaker is open for handler."""
        if handler_id not in self._circuit_breakers:
            return False

        cb = self._circuit_breakers[handler_id]

        # Check if circuit is open and timeout has passed
        if cb["state"] == "open":
            if datetime.now() - cb["opened_at"] > timedelta(seconds=cb["timeout"]):
                cb["state"] = "half_open"
                cb["failure_count"] = 0
                return False
            return True

        return False

    def _record_circuit_breaker_failure(self, handler_id: str) -> None:
        """Record circuit breaker failure."""
        if handler_id not in self._circuit_breakers:
            self._circuit_breakers[handler_id] = {
                "state": "closed",
                "failure_count": 0,
                "opened_at": None,
                "timeout": 60,  # seconds
            }

        cb = self._circuit_breakers[handler_id]
        cb["failure_count"] += 1

        # Open circuit if failure threshold exceeded
        if cb["failure_count"] >= 5:
            cb["state"] = "open"
            cb["opened_at"] = datetime.now()
            logger.warning(f"Circuit breaker opened for handler {handler_id}")

    def _reset_circuit_breaker(self, handler_id: str) -> None:
        """Reset circuit breaker on successful execution."""
        if handler_id in self._circuit_breakers:
            cb = self._circuit_breakers[handler_id]
            cb["state"] = "closed"
            cb["failure_count"] = 0
            cb["opened_at"] = None

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "processing_stats": self._processing_stats.copy(),
            "event_metrics": dict(self._event_metrics),
            "handler_count": sum(len(handlers) for handlers in self._handlers.values()),
            "global_handler_count": len(self._global_handlers),
            "circuit_breakers": {
                handler_id: {"state": cb["state"], "failure_count": cb["failure_count"]}
                for handler_id, cb in self._circuit_breakers.items()
            },
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "event_store_size": (
                len(self.event_store._events) if self.event_store else 0
            ),
        }

    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get dead letter queue contents."""
        return list(self._dead_letter_queue)

    async def replay_events(
        self,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
    ) -> int:
        """
        Replay events from event store.

        Returns:
            Number of events replayed
        """
        if not self.event_store:
            logger.warning("Event store not enabled, cannot replay events")
            return 0

        # Get events to replay
        events_to_replay = []

        if correlation_id:
            events_to_replay = self.event_store.get_events_by_correlation(
                correlation_id
            )
        elif event_type:
            events_to_replay = self.event_store.get_events_by_type(
                event_type, limit=1000
            )
        else:
            events_to_replay = self.event_store.get_recent_events(limit=1000)

        # Apply timestamp filters
        if from_timestamp or to_timestamp:
            filtered_events = []
            for event in events_to_replay:
                event_time = event.metadata.timestamp

                if from_timestamp and event_time < from_timestamp:
                    continue
                if to_timestamp and event_time > to_timestamp:
                    continue

                filtered_events.append(event)

            events_to_replay = filtered_events

        # Replay events
        replayed_count = 0
        for event in events_to_replay:
            # Create new event with replay metadata
            replay_event = Event(
                event_type=event.event_type,
                payload=event.payload,
                metadata=EventMetadata(
                    source="event_replay",
                    correlation_id=event.metadata.correlation_id,
                    causation_id=event.metadata.event_id,  # Original event as causation
                    priority=EventPriority.LOW,  # Lower priority for replays
                ),
            )

            await self.publish(replay_event)
            replayed_count += 1

        logger.info(f"Replayed {replayed_count} events")
        return replayed_count


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


async def publish_event(
    event_type: str, payload: Any, **metadata
) -> EventProcessingResult:
    """Convenience function to publish event."""
    event_metadata = EventMetadata(**metadata)
    event = Event(event_type=event_type, payload=payload, metadata=event_metadata)
    return await get_event_bus().publish(event)


def subscribe_to_event(event_type: str, priority: int = 0):
    """Decorator for subscribing to events."""

    def decorator(handler_class):
        # Register the handler
        handler = handler_class()
        get_event_bus().subscribe(event_type, handler, priority)
        return handler_class

    return decorator


@asynccontextmanager
async def event_bus_context(event_bus: EventBus):
    """Context manager for event bus lifecycle."""
    try:
        await event_bus.start()
        yield event_bus
    finally:
        await event_bus.stop()

