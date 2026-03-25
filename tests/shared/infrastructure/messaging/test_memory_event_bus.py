"""Tests for in-memory event bus implementation."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.shared.infrastructure.messaging.event_bus import (
    DomainEvent,
    EventBusNotStartedError,
)
from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus


@pytest.fixture
async def event_bus():
    """Create and start a MemoryEventBus for testing."""
    bus = MemoryEventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def sample_event():
    """Create a sample domain event."""
    return DomainEvent(
        event_type="test.event",
        payload={"message": "hello"},
        aggregate_id="agg-123",
    )


class TestMemoryEventBusLifecycle:
    """Tests for MemoryEventBus lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start_clears_state(self) -> None:
        """Test that start clears any previous state."""
        bus = MemoryEventBus()

        # Add some state
        await bus.start()
        await bus.subscribe("test.event", AsyncMock())
        await bus.stop()

        # Restart should clear state
        await bus.start()
        count = await bus.get_subscriber_count("test.event")
        assert count == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_stop_prevents_operations(self) -> None:
        """Test that stop prevents further operations."""
        bus = MemoryEventBus()
        await bus.start()
        await bus.stop()

        test_event = DomainEvent(event_type="test.event", payload={})
        with pytest.raises(EventBusNotStartedError):
            await bus.publish(test_event)

    @pytest.mark.asyncio
    async def test_operations_before_start_raise_error(self) -> None:
        """Test that operations before start raise error."""
        bus = MemoryEventBus()

        test_event = DomainEvent(event_type="test.event", payload={})
        with pytest.raises(EventBusNotStartedError):
            await bus.publish(test_event)

        with pytest.raises(EventBusNotStartedError):
            await bus.subscribe("test", AsyncMock())


class TestMemoryEventBusPublish:
    """Tests for publishing events."""

    @pytest.mark.asyncio
    async def test_publish_without_handlers(self, event_bus, sample_event) -> None:
        """Test publishing when no handlers are subscribed."""
        await event_bus.publish(sample_event)  # Should not raise

    @pytest.mark.asyncio
    async def test_publish_calls_handler(self, event_bus, sample_event) -> None:
        """Test that publish calls the registered handler."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        await event_bus.publish(sample_event)
        await asyncio.sleep(0.01)  # Allow async processing

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.event_id == sample_event.event_id

    @pytest.mark.asyncio
    async def test_publish_calls_multiple_handlers(
        self, event_bus, sample_event
    ) -> None:
        """Test that publish calls all registered handlers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        await event_bus.subscribe("test.event", handler1)
        await event_bus.subscribe("test.event", handler2)

        await event_bus.publish(sample_event)
        await asyncio.sleep(0.01)

        handler1.assert_called_once()
        handler2.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_only_calls_matching_handlers(
        self, event_bus, sample_event
    ) -> None:
        """Test that only matching handlers are called."""
        matching_handler = AsyncMock()
        other_handler = AsyncMock()
        await event_bus.subscribe("test.event", matching_handler)
        await event_bus.subscribe("other.event", other_handler)

        await event_bus.publish(sample_event)
        await asyncio.sleep(0.01)

        matching_handler.assert_called_once()
        other_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_with_different_payloads(self, event_bus) -> None:
        """Test publishing events with various payload types."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        await event_bus.subscribe("test.event", handler)

        # String payload
        string_event = DomainEvent(event_type="test.event", payload="hello")
        await event_bus.publish(string_event)

        # Dict payload
        dict_event = DomainEvent(event_type="test.event", payload={"key": "value"})
        await event_bus.publish(dict_event)

        # List payload
        list_event = DomainEvent(event_type="test.event", payload=[1, 2, 3])
        await event_bus.publish(list_event)

        await asyncio.sleep(0.05)

        assert len(received_events) == 3
        assert received_events[0].payload == "hello"
        assert received_events[1].payload == {"key": "value"}
        assert received_events[2].payload == [1, 2, 3]


class TestMemoryEventBusSubscribe:
    """Tests for subscribing to events."""

    @pytest.mark.asyncio
    async def test_subscribe_single_handler(self, event_bus) -> None:
        """Test subscribing a single handler."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        count = await event_bus.get_subscriber_count("test.event")
        assert count == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers_same_type(self, event_bus) -> None:
        """Test subscribing multiple handlers to same event type."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("test.event", handler1)
        await event_bus.subscribe("test.event", handler2)

        count = await event_bus.get_subscriber_count("test.event")
        assert count == 2

    @pytest.mark.asyncio
    async def test_subscribe_handlers_different_types(self, event_bus) -> None:
        """Test subscribing handlers to different event types."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("event.type1", handler1)
        await event_bus.subscribe("event.type2", handler2)

        assert await event_bus.get_subscriber_count("event.type1") == 1
        assert await event_bus.get_subscriber_count("event.type2") == 1

    @pytest.mark.asyncio
    async def test_subscribe_with_topic(self, event_bus) -> None:
        """Test subscribing to a specific topic."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler, topic="my-topic")

        count = await event_bus.get_subscriber_count("test.event", topic="my-topic")
        assert count == 1

        # Global count should be 0
        global_count = await event_bus.get_subscriber_count("test.event")
        assert global_count == 0


class TestMemoryEventBusUnsubscribe:
    """Tests for unsubscribing from events."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, event_bus) -> None:
        """Test unsubscribing removes the handler."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)
        await event_bus.unsubscribe("test.event", handler)

        count = await event_bus.get_subscriber_count("test.event")
        assert count == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_one_of_many(self, event_bus) -> None:
        """Test unsubscribing one handler leaves others."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("test.event", handler1)
        await event_bus.subscribe("test.event", handler2)
        await event_bus.unsubscribe("test.event", handler1)

        count = await event_bus.get_subscriber_count("test.event")
        assert count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self, event_bus) -> None:
        """Test unsubscribing a handler that was never subscribed."""
        handler = AsyncMock()
        # Should not raise
        await event_bus.unsubscribe("test.event", handler)

    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic(self, event_bus) -> None:
        """Test unsubscribing from a specific topic."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler, topic="my-topic")
        await event_bus.unsubscribe("test.event", handler, topic="my-topic")

        count = await event_bus.get_subscriber_count("test.event", topic="my-topic")
        assert count == 0


class TestMemoryEventBusConcurrency:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_publishes(self, event_bus) -> None:
        """Test handling multiple concurrent publishes."""
        received_count = 0

        async def handler(event):
            nonlocal received_count
            received_count += 1

        await event_bus.subscribe("test.event", handler)

        # Publish multiple events concurrently
        events = [
            DomainEvent(event_type="test.event", payload={"n": i}) for i in range(10)
        ]
        await asyncio.gather(*[event_bus.publish(e) for e in events])
        await asyncio.sleep(0.1)

        assert received_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self, event_bus) -> None:
        """Test concurrent subscribe/unsubscribe operations."""
        handlers = [AsyncMock() for _ in range(10)]

        # Subscribe all concurrently
        await asyncio.gather(
            *[event_bus.subscribe(f"event.{i}", handlers[i]) for i in range(10)]
        )

        # Verify all subscribed
        for i in range(10):
            assert await event_bus.get_subscriber_count(f"event.{i}") == 1

        # Unsubscribe all concurrently
        await asyncio.gather(
            *[event_bus.unsubscribe(f"event.{i}", handlers[i]) for i in range(10)]
        )

        # Verify all unsubscribed
        for i in range(10):
            assert await event_bus.get_subscriber_count(f"event.{i}") == 0

    @pytest.mark.asyncio
    async def test_handler_exception_doesnt_block_others(
        self, event_bus, sample_event
    ) -> None:
        """Test that one handler's exception doesn't block others."""
        bad_handler = AsyncMock(side_effect=Exception("Handler error"))
        good_handler = AsyncMock()

        await event_bus.subscribe("test.event", bad_handler)
        await event_bus.subscribe("test.event", good_handler)

        await event_bus.publish(sample_event)
        await asyncio.sleep(0.05)

        bad_handler.assert_called_once()
        good_handler.assert_called_once()


class TestMemoryEventBusUtilityMethods:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_get_subscriber_count_empty(self, event_bus) -> None:
        """Test subscriber count for non-subscribed event type."""
        count = await event_bus.get_subscriber_count("nonexistent")
        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_subscriptions(self, event_bus) -> None:
        """Test clearing all subscriptions."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("event1", handler1)
        await event_bus.subscribe("event2", handler2)

        await event_bus.clear_subscriptions()

        assert await event_bus.get_subscriber_count("event1") == 0
        assert await event_bus.get_subscriber_count("event2") == 0

    @pytest.mark.asyncio
    async def test_clear_subscriptions_while_started(self, event_bus) -> None:
        """Test that clear_subscriptions works while bus is running."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        await event_bus.clear_subscriptions()

        count = await event_bus.get_subscriber_count("test.event")
        assert count == 0
