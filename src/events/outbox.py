"""
Event Outbox Pattern Implementation

Implements the outbox pattern for reliable event delivery in the simulation engine.
Events are stored in an outbox before being processed, ensuring at-least-once delivery
even in case of failures.

Constitution Compliance:
    - Article II (Hexagonal): Infrastructure component for event reliability
    - Article V (SOLID): SRP - outbox management only

Usage:
    >>> outbox = Outbox()
    >>> event = OutboxEvent(event_type="SIMULATION_TICK", payload={"tick": 1})
    >>> outbox.enqueue(event, priority=EventPriority.HIGH)
    >>> pending = outbox.get_pending(limit=10)
    >>> for event in pending:
    ...     # Process event...
    ...     outbox.mark_processed(event.event_id)
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class EventPriority(Enum):
    """Event priority levels for processing optimization.

    Higher values = higher priority (processed first).
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class OutboxStatus(Enum):
    """Status of an outbox event."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class OutboxEvent:
    """
    Event stored in the outbox for reliable delivery.

    The outbox pattern ensures that events are persisted before being
    processed, allowing for recovery from failures.

    Attributes:
        event_id: Unique identifier for the event
        event_type: Type/category of the event
        payload: Event data
        created_at: When the event was created
        processed_at: When the event was processed (None if pending)
        priority: Processing priority
        status: Current status
        retry_count: Number of processing attempts
        max_retries: Maximum retries before moving to dead letter
        metadata: Additional metadata
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    priority: EventPriority = EventPriority.NORMAL
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event structure."""
        if not self.event_type:
            raise ValueError("event_type is required")

    def __lt__(self, other: "OutboxEvent") -> bool:
        """Compare events by priority (for heap-based priority queue).

        Higher priority values come first, then earlier creation times.
        """
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutboxEvent":
        """Deserialize event from dictionary."""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("processed_at"):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        data["priority"] = EventPriority(data["priority"])
        data["status"] = OutboxStatus(data["status"])
        return cls(**data)


@dataclass
class OutboxMetrics:
    """Metrics for outbox monitoring."""

    total_enqueued: int = 0
    total_processed: int = 0
    total_failed: int = 0
    current_pending: int = 0
    current_processing: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Return metrics as dictionary."""
        return {
            "total_enqueued": self.total_enqueued,
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "current_pending": self.current_pending,
            "current_processing": self.current_processing,
        }


class Outbox:
    """
    Thread-safe outbox for reliable event delivery.

    Implements the outbox pattern with priority queuing:
    - Events are enqueued with priority
    - Pending events can be fetched in priority order
    - Processed events are marked and removed
    - Failed events are tracked with retry counts

    Example:
        >>> outbox = Outbox()
        >>> event = OutboxEvent(event_type="TICK", payload={"n": 1})
        >>> outbox.enqueue(event, priority=EventPriority.HIGH)
        >>> pending = outbox.get_pending(limit=10)
        >>> outbox.mark_processed(event.event_id)
    """

    def __init__(self, max_size: int = 10000):
        """Initialize the outbox.

        Args:
            max_size: Maximum number of pending events (older events evicted)
        """
        self._max_size = max_size
        self._heap: List[OutboxEvent] = []  # Priority queue
        self._events: Dict[str, OutboxEvent] = {}  # event_id -> event
        self._processing: Dict[str, OutboxEvent] = {}  # Currently being processed
        self._lock = Lock()
        self._metrics = OutboxMetrics()

        logger.info(
            "outbox_initialized",
            max_size=max_size,
        )

    def enqueue(
        self,
        event: OutboxEvent,
        priority: Optional[EventPriority] = None,
    ) -> str:
        """Add an event to the outbox.

        Args:
            event: Event to enqueue
            priority: Optional priority override

        Returns:
            Event ID

        Raises:
            ValueError: If event already exists
        """
        if priority is not None:
            event.priority = priority

        with self._lock:
            if event.event_id in self._events:
                raise ValueError(f"Event {event.event_id} already exists in outbox")

            # Evict oldest low-priority events if at capacity
            self._evict_if_needed()

            self._events[event.event_id] = event
            heapq.heappush(self._heap, event)

            self._metrics.total_enqueued += 1
            self._metrics.current_pending = len(self._events)

        logger.debug(
            "outbox_event_enqueued",
            event_id=event.event_id,
            event_type=event.event_type,
            priority=event.priority.name,
        )

        return event.event_id

    def get_pending(self, limit: int = 10) -> List[OutboxEvent]:
        """Get pending events in priority order.

        Events are marked as PROCESSING when fetched.

        Args:
            limit: Maximum number of events to fetch

        Returns:
            List of pending events (highest priority first)
        """
        events = []

        with self._lock:
            while len(events) < limit and self._heap:
                event = heapq.heappop(self._heap)

                # Skip already processed or failed events
                if event.event_id not in self._events:
                    continue
                if event.status != OutboxStatus.PENDING:
                    continue

                event.status = OutboxStatus.PROCESSING
                self._processing[event.event_id] = event
                events.append(event)

            self._metrics.current_pending = len(self._events) - len(self._processing)
            self._metrics.current_processing = len(self._processing)

        if events:
            logger.debug(
                "outbox_events_fetched",
                count=len(events),
            )

        return events

    def mark_processed(self, event_id: str) -> bool:
        """Mark an event as successfully processed.

        Args:
            event_id: ID of the processed event

        Returns:
            True if event was found and marked
        """
        with self._lock:
            event = self._processing.pop(event_id, None)
            if event is None:
                event = self._events.get(event_id)
                if event is None:
                    return False

            event.status = OutboxStatus.PROCESSED
            event.processed_at = datetime.now()
            del self._events[event_id]

            self._metrics.total_processed += 1
            self._metrics.current_pending = len(self._events) - len(self._processing)
            self._metrics.current_processing = len(self._processing)

        logger.debug(
            "outbox_event_processed",
            event_id=event_id,
        )

        return True

    def mark_failed(
        self,
        event_id: str,
        retry: bool = True,
    ) -> Optional[OutboxEvent]:
        """Mark an event as failed.

        Args:
            event_id: ID of the failed event
            retry: Whether to retry the event

        Returns:
            The failed event if retries exceeded, None otherwise
        """
        with self._lock:
            event = self._processing.pop(event_id, None)
            if event is None:
                return None

            event.retry_count += 1

            if retry and event.retry_count < event.max_retries:
                # Re-queue for retry
                event.status = OutboxStatus.PENDING
                heapq.heappush(self._heap, event)
                logger.info(
                    "outbox_event_retry",
                    event_id=event_id,
                    retry_count=event.retry_count,
                    max_retries=event.max_retries,
                )
            else:
                # Max retries exceeded - mark as failed
                event.status = OutboxStatus.FAILED
                del self._events[event_id]
                self._metrics.total_failed += 1

                logger.warning(
                    "outbox_event_failed",
                    event_id=event_id,
                    retry_count=event.retry_count,
                )
                return event

            self._metrics.current_pending = len(self._events) - len(self._processing)
            self._metrics.current_processing = len(self._processing)

        return None

    def requeue_processing(self) -> int:
        """Requeue all events currently in PROCESSING state.

        Call this on startup to recover from crashes.

        Returns:
            Number of events requeued
        """
        count = 0

        with self._lock:
            for event_id, event in list(self._processing.items()):
                event.status = OutboxStatus.PENDING
                heapq.heappush(self._heap, event)
                del self._processing[event_id]
                count += 1

            self._metrics.current_pending = len(self._events) - len(self._processing)
            self._metrics.current_processing = 0

        if count > 0:
            logger.info(
                "outbox_events_requeued",
                count=count,
            )

        return count

    def get_event(self, event_id: str) -> Optional[OutboxEvent]:
        """Get an event by ID."""
        with self._lock:
            return self._events.get(event_id) or self._processing.get(event_id)

    def get_metrics(self) -> OutboxMetrics:
        """Get current metrics."""
        with self._lock:
            return OutboxMetrics(
                total_enqueued=self._metrics.total_enqueued,
                total_processed=self._metrics.total_processed,
                total_failed=self._metrics.total_failed,
                current_pending=len(self._events) - len(self._processing),
                current_processing=len(self._processing),
            )

    def clear(self) -> int:
        """Clear all events from the outbox.

        Returns:
            Number of events cleared
        """
        with self._lock:
            count = len(self._events)
            self._heap.clear()
            self._events.clear()
            self._processing.clear()
            self._metrics.current_pending = 0
            self._metrics.current_processing = 0

        logger.info(
            "outbox_cleared",
            count=count,
        )

        return count

    def _evict_if_needed(self) -> None:
        """Evict oldest events if at capacity."""
        while len(self._events) >= self._max_size and self._heap:
            # Remove lowest priority/oldest event
            evicted = heapq.heappop(self._heap)
            if evicted.event_id in self._events:
                del self._events[evicted.event_id]
                logger.debug(
                    "outbox_event_evicted",
                    event_id=evicted.event_id,
                )
                break
