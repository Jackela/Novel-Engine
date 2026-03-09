"""
Test suite for Event Bus module.

Tests event publishing, subscribing, async handlers, and error handling.
"""

import asyncio

import pytest

pytestmark = pytest.mark.unit

from datetime import datetime
from unittest.mock import AsyncMock, Mock

from src.core.event_bus import (
    DeadLetterEntry,
    Event,
    EventBus,
    EventPriority,
    InMemoryEventBus,
)


class TestEventPriority:
    """Test EventPriority enum."""

    def test_priority_values(self):
        """Test that EventPriority has expected values."""
        assert EventPriority.LOW == 0
        assert EventPriority.NORMAL == 1
        assert EventPriority.HIGH == 2
        assert EventPriority.CRITICAL == 3

    def test_priority_ordering(self):
        """Test priority ordering."""
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL


class TestEvent:
    """Test Event dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            event_type="test_event",
            data={"key": "value"},
            priority=EventPriority.HIGH,
            source="test_source",
        )
        assert event.event_type == "test_event"
        assert event.data == {"key": "value"}
        assert event.priority == EventPriority.HIGH
        assert event.source == "test_source"
        assert event.event_id is not None
        assert event.retry_count == 0
        assert event.max_retries == 3

    def test_event_comparison_by_priority(self):
        """Test event comparison by priority."""
        event_low = Event(event_type="low", data={}, priority=EventPriority.LOW)
        event_high = Event(event_type="high", data={}, priority=EventPriority.HIGH)

        # Higher priority should come first
        assert event_high < event_low

    def test_event_comparison_by_timestamp(self):
        """Test event comparison by timestamp."""
        import time

        event1 = Event(event_type="first", data={}, priority=EventPriority.NORMAL)
        time.sleep(0.001)
        event2 = Event(event_type="second", data={}, priority=EventPriority.NORMAL)

        # Older event should come first
        assert event1 < event2

    def test_event_equality(self):
        """Test event equality."""
        event1 = Event(event_type="test", data={})
        event2 = Event(event_type="test", data={})
        # Different IDs, so not equal
        assert event1 != event2

        # Same event
        assert event1 == event1


class TestDeadLetterEntry:
    """Test DeadLetterEntry dataclass."""

    def test_dead_letter_creation(self):
        """Test creating a dead letter entry."""
        event = Event(event_type="test", data={})
        entry = DeadLetterEntry(
            event=event,
            error="Test error",
            handler_name="test_handler",
        )
        assert entry.event == event
        assert entry.error == "Test error"
        assert entry.handler_name == "test_handler"
        assert isinstance(entry.failed_at, datetime)


class TestEventBus:
    """Test EventBus implementation."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        bus = EventBus()
        yield bus
        bus.clear()

    def test_subscribe(self, event_bus):
        """Test subscribing to events."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)

        assert "test_event" in event_bus._subscribers
        assert handler in event_bus._subscribers["test_event"]

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)
        event_bus.unsubscribe("test_event", handler)

        assert "test_event" not in event_bus._subscribers

    def test_unsubscribe_nonexistent_handler(self, event_bus):
        """Test unsubscribing a handler that wasn't subscribed."""
        handler = Mock()
        # Should not raise error
        event_bus.unsubscribe("test_event", handler)

    def test_emit_sync_handler(self, event_bus):
        """Test emitting to synchronous handler."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)

        event_id = event_bus.emit("test_event", key="value")

        assert event_id is not None
        handler.assert_called_once()
        assert handler.call_args[1] == {"key": "value"}

    def test_emit_no_subscribers(self, event_bus):
        """Test emitting event with no subscribers."""
        event_id = event_bus.emit("no_subscribers_event", data="test")

        # Should still return event_id
        assert event_id is not None

    def test_emit_multiple_handlers(self, event_bus):
        """Test emitting to multiple handlers."""
        handler1 = Mock()
        handler2 = Mock()
        event_bus.subscribe("test_event", handler1)
        event_bus.subscribe("test_event", handler2)

        event_bus.emit("test_event", data="test")

        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_emit_handler_error(self, event_bus):
        """Test that handler errors don't crash the bus."""
        error_handler = Mock(side_effect=Exception("Handler error"))
        good_handler = Mock()

        event_bus.subscribe("test_event", error_handler)
        event_bus.subscribe("test_event", good_handler)

        _ = event_bus.emit("test_event", data="test")

        # Both handlers should be called
        error_handler.assert_called_once()
        good_handler.assert_called_once()

        # Error should be recorded in dead letter
        assert len(event_bus._dead_letters) == 1

    @pytest.mark.asyncio
    async def test_publish_async(self, event_bus):
        """Test publishing to async handler."""
        async_handler = AsyncMock()
        event_bus.subscribe("test_event", async_handler)

        event_id = await event_bus.publish("test_event", data="test")

        assert event_id is not None
        async_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_sync_handler(self, event_bus):
        """Test publishing to synchronous handler."""
        sync_handler = Mock()
        event_bus.subscribe("test_event", sync_handler)

        await event_bus.publish("test_event", data="test")

        sync_handler.assert_called_once()

    def test_pause_resume_event_type(self, event_bus):
        """Test pausing and resuming event types."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)

        # Pause the event type
        event_bus.pause_event_type("test_event")
        assert event_bus.is_paused("test_event")

        # Event should not be emitted
        event_id = event_bus.emit("test_event", data="test")
        assert event_id is None
        handler.assert_not_called()

        # Resume the event type
        event_bus.resume_event_type("test_event")
        assert not event_bus.is_paused("test_event")

        # Now event should be emitted
        event_bus.emit("test_event", data="test")
        handler.assert_called_once()

    def test_get_history(self, event_bus):
        """Test getting event history."""
        event_bus.subscribe("test_event", Mock())

        event_bus.emit("test_event", data="1")
        event_bus.emit("test_event", data="2")
        event_bus.emit("other_event", data="3")

        history = event_bus.get_history()
        assert len(history) == 3

        # Test filtering by type
        filtered_history = event_bus.get_history(event_type="test_event")
        assert len(filtered_history) == 2

    def test_get_history_with_limit(self, event_bus):
        """Test getting limited event history."""
        event_bus.subscribe("test_event", Mock())

        for i in range(10):
            event_bus.emit("test_event", data=i)

        history = event_bus.get_history(limit=5)
        assert len(history) == 5

    def test_get_dead_letters(self, event_bus):
        """Test getting dead letter entries."""
        error_handler = Mock(side_effect=Exception("Error"))
        event_bus.subscribe("test_event", error_handler)

        event_bus.emit("test_event", data="test")

        dead_letters = event_bus.get_dead_letters()
        assert len(dead_letters) == 1
        assert dead_letters[0].event.event_type == "test_event"

    def test_clear_dead_letters(self, event_bus):
        """Test clearing dead letter entries."""
        error_handler = Mock(side_effect=Exception("Error"))
        event_bus.subscribe("test_event", error_handler)
        event_bus.subscribe("other_event", error_handler)

        event_bus.emit("test_event", data="1")
        event_bus.emit("other_event", data="2")

        # Clear specific type
        cleared = event_bus.clear_dead_letters(event_type="test_event")
        assert cleared == 1

        # Clear all
        cleared = event_bus.clear_dead_letters()
        assert cleared == 1

    @pytest.mark.asyncio
    async def test_retry_dead_letters(self, event_bus):
        """Test retrying dead letter entries."""
        handler = Mock(side_effect=[Exception("Error"), None])  # Fail then succeed
        event_bus.subscribe("test_event", handler)

        # First emit fails
        event_bus.emit("test_event", data="test")
        assert len(event_bus._dead_letters) == 1

        # Retry should succeed
        retried = await event_bus.retry_dead_letters()
        assert retried == 1
        assert len(event_bus._dead_letters) == 0

    @pytest.mark.asyncio
    async def test_retry_dead_letters_max_retries_exceeded(self, event_bus):
        """Test retry with max retries exceeded."""
        handler = Mock(side_effect=Exception("Error"))
        event_bus.subscribe("test_event", handler)

        event_bus.emit("test_event", data="test")
        event_bus._dead_letters[0].event.retry_count = 3  # Max retries

        retried = await event_bus.retry_dead_letters()
        assert retried == 0  # Should not retry

    def test_get_metrics(self, event_bus):
        """Test getting event bus metrics."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)

        event_bus.emit("test_event", data="test")

        metrics = event_bus.get_metrics()
        assert metrics["events_emitted"] == 1
        assert metrics["events_processed"] == 1
        assert "history_size" in metrics
        assert "subscriber_counts" in metrics

    def test_reset_metrics(self, event_bus):
        """Test resetting metrics."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)
        event_bus.emit("test_event", data="test")

        event_bus.reset_metrics()

        metrics = event_bus.get_metrics()
        assert metrics["events_emitted"] == 0
        assert metrics["events_processed"] == 0

    @pytest.mark.asyncio
    async def test_start_stop(self, event_bus):
        """Test starting and stopping the event bus."""
        await event_bus.start()
        await event_bus.stop()
        # Should complete without error

    def test_clear(self, event_bus):
        """Test clearing all event bus state."""
        handler = Mock()
        event_bus.subscribe("test_event", handler)
        event_bus.emit("test_event", data="test")

        event_bus.clear()

        assert len(event_bus._subscribers) == 0
        assert len(event_bus._history) == 0
        assert len(event_bus._dead_letters) == 0
        assert len(event_bus._paused_types) == 0
        metrics = event_bus.get_metrics()
        assert metrics["events_emitted"] == 0


class TestInMemoryEventBus:
    """Test InMemoryEventBus implementation."""

    @pytest.fixture
    def in_memory_bus(self):
        """Create a fresh in-memory event bus."""
        bus = InMemoryEventBus()
        yield bus
        bus.clear()

    def test_publish_and_subscribe(self, in_memory_bus):
        """Test basic publish and subscribe."""
        received = []

        def handler(payload):
            received.append(payload)

        in_memory_bus.subscribe("test_topic", handler)
        in_memory_bus.publish("test_topic", {"data": "test"})

        assert len(received) == 1
        assert received[0] == {"data": "test"}

    def test_replay(self, in_memory_bus):
        """Test event replay."""
        in_memory_bus.subscribe("test_topic", lambda x: None)

        in_memory_bus.publish("test_topic", {"id": 1})
        in_memory_bus.publish("test_topic", {"id": 2})
        in_memory_bus.publish("other_topic", {"id": 3})

        # Replay all
        all_events = in_memory_bus.replay()
        assert len(all_events) == 3

        # Replay from index
        from_index = in_memory_bus.replay(from_index=1)
        assert len(from_index) == 2

        # Replay by topic
        topic_events = in_memory_bus.replay(topic="test_topic")
        assert len(topic_events) == 2

    def test_stats(self, in_memory_bus):
        """Test getting stats."""
        in_memory_bus.subscribe("topic1", lambda x: None)
        in_memory_bus.subscribe("topic2", lambda x: None)
        in_memory_bus.publish("topic1", {"data": 1})
        in_memory_bus.publish("topic2", {"data": 2})

        stats = in_memory_bus.stats()
        assert stats["total_events"] == 2
        assert stats["subscriber_count"] == 2


class TestEventBusEdgeCases:
    """Test edge cases and error conditions."""

    def test_handler_with_no_name(self):
        """Test handler without __name__ attribute."""
        bus = EventBus()
        handler = lambda x: x  # noqa: E731

        # Should not raise error
        bus.subscribe("test", handler)
        bus.emit("test", data="value")

    def test_emit_with_empty_data(self):
        """Test emitting with empty data."""
        bus = EventBus()
        handler = Mock()
        bus.subscribe("test", handler)

        bus.emit("test")
        handler.assert_called_once()

    def test_concurrent_subscribe_unsubscribe(self):
        """Test concurrent subscribe and unsubscribe."""
        bus = EventBus()
        handlers = [Mock() for _ in range(10)]

        for i, handler in enumerate(handlers):
            bus.subscribe("test", handler)
            if i % 2 == 0:
                bus.unsubscribe("test", handler)

        # Should have 5 subscribers
        assert len(bus._subscribers["test"]) == 5

    @pytest.mark.asyncio
    async def test_async_handler_with_sync_bus(self):
        """Test async handler with sync emit."""
        bus = EventBus()

        async def async_handler(data):
            await asyncio.sleep(0.001)
            return data

        bus.subscribe("test", async_handler)

        # Emit is sync, should handle async handler gracefully
        event_id = bus.emit("test", data="value")
        assert event_id is not None
