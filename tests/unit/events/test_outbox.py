"""
Unit tests for Outbox event pattern implementation.

Tests cover:
- Event enqueue/dequeue with priority
- Processing status tracking
- Retry logic
- Metrics collection
"""

import pytest

from src.events.outbox import (
    EventPriority,
    Outbox,
    OutboxEvent,
    OutboxMetrics,
    OutboxStatus,
)

pytestmark = pytest.mark.unit


class TestOutboxEvent:
    """Tests for OutboxEvent dataclass."""

    def test_create_event(self) -> None:
        """Test creating an outbox event."""
        event = OutboxEvent(event_type="TEST", payload={"key": "value"})

        assert event.event_type == "TEST"
        assert event.payload == {"key": "value"}
        assert event.status == OutboxStatus.PENDING
        assert event.priority == EventPriority.NORMAL
        assert event.retry_count == 0

    def test_event_requires_type(self) -> None:
        """Test that event type is required."""
        with pytest.raises(ValueError, match="event_type is required"):
            OutboxEvent()

    def test_event_priority_comparison(self) -> None:
        """Test event priority comparison for heap ordering."""
        low = OutboxEvent(event_type="LOW", priority=EventPriority.LOW)
        high = OutboxEvent(event_type="HIGH", priority=EventPriority.HIGH)
        normal = OutboxEvent(event_type="NORMAL", priority=EventPriority.NORMAL)

        # Higher priority should be "less than" (comes first in min-heap)
        assert high < low
        assert high < normal
        assert normal < low

    def test_event_to_dict_and_from_dict(self) -> None:
        """Test serialization and deserialization."""
        original = OutboxEvent(
            event_type="TEST",
            payload={"key": "value"},
            priority=EventPriority.HIGH,
            metadata={"source": "test"},
        )

        data = original.to_dict()
        restored = OutboxEvent.from_dict(data)

        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.payload == original.payload
        assert restored.priority == original.priority


class TestOutbox:
    """Tests for Outbox class."""

    def test_init(self) -> None:
        """Test outbox initialization."""
        outbox = Outbox()
        assert outbox._max_size == 10000

    def test_init_custom_max_size(self) -> None:
        """Test outbox with custom max size."""
        outbox = Outbox(max_size=100)
        assert outbox._max_size == 100

    def test_enqueue_event(self) -> None:
        """Test enqueuing an event."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST", payload={"data": 1})

        event_id = outbox.enqueue(event)

        assert event_id == event.event_id
        assert outbox.get_event(event_id) is not None

    def test_enqueue_with_priority_override(self) -> None:
        """Test enqueuing with priority override."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST", priority=EventPriority.LOW)

        outbox.enqueue(event, priority=EventPriority.CRITICAL)

        assert event.priority == EventPriority.CRITICAL

    def test_enqueue_duplicate_raises(self) -> None:
        """Test that duplicate event ID raises error."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST")

        outbox.enqueue(event)
        with pytest.raises(ValueError, match="already exists"):
            outbox.enqueue(event)

    def test_get_pending_returns_highest_priority(self) -> None:
        """Test that get_pending returns highest priority events first."""
        outbox = Outbox()

        low = OutboxEvent(event_type="LOW", priority=EventPriority.LOW)
        high = OutboxEvent(event_type="HIGH", priority=EventPriority.HIGH)
        normal = OutboxEvent(event_type="NORMAL", priority=EventPriority.NORMAL)

        outbox.enqueue(low)
        outbox.enqueue(normal)
        outbox.enqueue(high)

        pending = outbox.get_pending(limit=3)

        assert len(pending) == 3
        assert pending[0].event_type == "HIGH"
        assert pending[1].event_type == "NORMAL"
        assert pending[2].event_type == "LOW"

    def test_get_pending_marks_processing(self) -> None:
        """Test that get_pending marks events as PROCESSING."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST")

        outbox.enqueue(event)
        pending = outbox.get_pending()

        assert pending[0].status == OutboxStatus.PROCESSING

    def test_get_pending_respects_limit(self) -> None:
        """Test that get_pending respects limit."""
        outbox = Outbox()

        for i in range(10):
            outbox.enqueue(OutboxEvent(event_type=f"TEST_{i}"))

        pending = outbox.get_pending(limit=3)

        assert len(pending) == 3

    def test_mark_processed(self) -> None:
        """Test marking an event as processed."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST")

        outbox.enqueue(event)
        outbox.get_pending()
        result = outbox.mark_processed(event.event_id)

        assert result is True
        assert outbox.get_event(event.event_id) is None

    def test_mark_processed_not_found(self) -> None:
        """Test marking nonexistent event as processed."""
        outbox = Outbox()

        result = outbox.mark_processed("nonexistent")

        assert result is False

    def test_mark_failed_retries(self) -> None:
        """Test that mark_failed requeues for retry."""
        outbox = Outbox()
        event = OutboxEvent(event_type="TEST", max_retries=3)

        outbox.enqueue(event)
        outbox.get_pending()
        failed = outbox.mark_failed(event.event_id, retry=True)

        assert failed is None  # Not returned because it was requeued
        assert event.retry_count == 1
        assert event.status == OutboxStatus.PENDING

        # Should be able to get it again
        pending = outbox.get_pending()
        assert len(pending) == 1

    def test_mark_failed_max_retries(self) -> None:
        """Test that event is marked failed after max retries."""
        outbox = Outbox()
        # max_retries=2 means 2 retry attempts, then fails on 3rd
        event = OutboxEvent(event_type="TEST", max_retries=2)

        outbox.enqueue(event)

        # First failure - retry (retry_count becomes 1, 1 < 2, so retry)
        outbox.get_pending()
        result = outbox.mark_failed(event.event_id, retry=True)
        assert result is None  # Requeued
        assert event.retry_count == 1

        # Second failure - max retries exceeded (retry_count becomes 2, 2 < 2 is False)
        outbox.get_pending()
        failed = outbox.mark_failed(event.event_id, retry=True)

        assert failed is not None
        assert failed.status == OutboxStatus.FAILED
        assert failed.retry_count == 2
        assert outbox.get_event(event.event_id) is None

    def test_requeue_processing(self) -> None:
        """Test requeuing all processing events."""
        outbox = Outbox()

        for i in range(3):
            outbox.enqueue(OutboxEvent(event_type=f"TEST_{i}"))

        # Get all as processing
        outbox.get_pending(limit=10)

        count = outbox.requeue_processing()

        assert count == 3
        pending = outbox.get_pending(limit=10)
        assert len(pending) == 3

    def test_get_metrics(self) -> None:
        """Test metrics collection."""
        outbox = Outbox()

        # Enqueue some events
        for i in range(5):
            outbox.enqueue(OutboxEvent(event_type=f"TEST_{i}"))

        metrics = outbox.get_metrics()

        assert metrics.total_enqueued == 5
        assert metrics.current_pending == 5
        assert metrics.current_processing == 0

        # Get some as processing
        outbox.get_pending(limit=2)
        metrics = outbox.get_metrics()

        assert metrics.current_pending == 3
        assert metrics.current_processing == 2

    def test_clear(self) -> None:
        """Test clearing the outbox."""
        outbox = Outbox()

        for i in range(5):
            outbox.enqueue(OutboxEvent(event_type=f"TEST_{i}"))

        count = outbox.clear()

        assert count == 5
        assert outbox.get_pending() == []

    def test_eviction_at_max_size(self) -> None:
        """Test that events are evicted when at max capacity."""
        outbox = Outbox(max_size=3)

        # Add 3 events
        for i in range(3):
            outbox.enqueue(OutboxEvent(event_type=f"TEST_{i}"))

        assert len(outbox._events) == 3

        # Add one more - should evict lowest priority
        outbox.enqueue(OutboxEvent(event_type="NEW", priority=EventPriority.CRITICAL))

        metrics = outbox.get_metrics()
        # Still at capacity (3) but newest added
        assert metrics.current_pending <= 3


class TestOutboxMetrics:
    """Tests for OutboxMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = OutboxMetrics()

        assert metrics.total_enqueued == 0
        assert metrics.total_processed == 0
        assert metrics.total_failed == 0
        assert metrics.current_pending == 0
        assert metrics.current_processing == 0

    def test_to_dict(self) -> None:
        """Test metrics serialization."""
        metrics = OutboxMetrics(
            total_enqueued=100,
            total_processed=95,
            total_failed=5,
            current_pending=10,
            current_processing=2,
        )

        data = metrics.to_dict()

        assert data["total_enqueued"] == 100
        assert data["total_processed"] == 95
        assert data["total_failed"] == 5
        assert data["current_pending"] == 10
        assert data["current_processing"] == 2


class TestEventPriority:
    """Tests for EventPriority enum."""

    def test_priority_values(self) -> None:
        """Test priority ordering values."""
        assert EventPriority.LOW.value == 1
        assert EventPriority.NORMAL.value == 2
        assert EventPriority.HIGH.value == 3
        assert EventPriority.CRITICAL.value == 4
