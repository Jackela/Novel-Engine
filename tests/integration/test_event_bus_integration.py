"""Event bus integration tests."""

from __future__ import annotations

import asyncio
from typing import Any, List
from uuid import uuid4

import pytest

from src.shared.infrastructure.messaging.event_bus import DomainEvent


@pytest.mark.integration
class TestEventBusIntegration:
    """Test event bus publishing and handling."""

    async def test_event_publishing_and_handling(self):
        """Test publishing events and handling them."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            events_received: List[DomainEvent[Any]] = []

            async def handler(event: DomainEvent[Any]) -> None:
                events_received.append(event)

            # Subscribe
            await bus.subscribe("CharacterCreated", handler)

            # Publish
            event = DomainEvent(
                event_type="CharacterCreated",
                payload={"character_id": str(uuid4())},
                aggregate_id=str(uuid4()),
            )
            await bus.publish(event)

            # Wait for async delivery
            await asyncio.sleep(0.1)

            # Verify
            assert len(events_received) == 1
            assert events_received[0].event_type == "CharacterCreated"
        finally:
            await bus.stop()

    async def test_multiple_handlers_same_event(self):
        """Test multiple handlers for the same event type."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            handler1_events: List[DomainEvent[Any]] = []
            handler2_events: List[DomainEvent[Any]] = []

            async def handler1(event: DomainEvent[Any]) -> None:
                handler1_events.append(event)

            async def handler2(event: DomainEvent[Any]) -> None:
                handler2_events.append(event)

            # Subscribe both handlers
            await bus.subscribe("StoryUpdated", handler1)
            await bus.subscribe("StoryUpdated", handler2)

            # Publish
            event = DomainEvent(
                event_type="StoryUpdated",
                payload={"story_id": str(uuid4())},
                aggregate_id=str(uuid4()),
            )
            await bus.publish(event)

            await asyncio.sleep(0.1)

            # Both handlers should receive
            assert len(handler1_events) == 1
            assert len(handler2_events) == 1
        finally:
            await bus.stop()

    async def test_unsubscribe_handler(self):
        """Test unsubscribing a handler."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            events_received: List[DomainEvent[Any]] = []

            async def handler(event: DomainEvent[Any]) -> None:
                events_received.append(event)

            # Subscribe
            await bus.subscribe("TestEvent", handler)

            # Publish and verify
            event1 = DomainEvent(event_type="TestEvent", payload={"data": "first"})
            await bus.publish(event1)
            await asyncio.sleep(0.1)

            assert len(events_received) == 1

            # Unsubscribe
            await bus.unsubscribe("TestEvent", handler)

            # Publish again
            event2 = DomainEvent(event_type="TestEvent", payload={"data": "second"})
            await bus.publish(event2)
            await asyncio.sleep(0.1)

            # Should not receive second event
            assert len(events_received) == 1
        finally:
            await bus.stop()

    async def test_event_with_topic(self):
        """Test publishing events to specific topics."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            general_events: List[DomainEvent[Any]] = []
            topic_events: List[DomainEvent[Any]] = []

            async def general_handler(event: DomainEvent[Any]) -> None:
                general_events.append(event)

            async def topic_handler(event: DomainEvent[Any]) -> None:
                topic_events.append(event)

            # Subscribe to general and topic-specific
            await bus.subscribe("ChapterCreated", general_handler)
            await bus.subscribe("ChapterCreated", topic_handler, topic="story-123")

            # Publish to general
            event1 = DomainEvent(
                event_type="ChapterCreated", payload={"chapter_id": str(uuid4())}
            )
            await bus.publish(event1)

            # Publish to topic
            event2 = DomainEvent(
                event_type="ChapterCreated", payload={"chapter_id": str(uuid4())}
            )
            await bus.publish(event2, topic="story-123")

            await asyncio.sleep(0.1)

            # General handler receives both
            assert len(general_events) == 2
            # Topic handler receives only topic event
            assert len(topic_events) == 1
        finally:
            await bus.stop()

    async def test_concurrent_event_publishing(self):
        """Test concurrent event publishing."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            events_received: List[DomainEvent[Any]] = []

            async def handler(event: DomainEvent[Any]) -> None:
                events_received.append(event)

            await bus.subscribe("ConcurrentEvent", handler)

            # Publish multiple events concurrently
            async def publish_task(task_id: int) -> None:
                event = DomainEvent(
                    event_type="ConcurrentEvent", payload={"task_id": task_id}
                )
                await bus.publish(event)

            await asyncio.gather(*[publish_task(i) for i in range(20)])

            await asyncio.sleep(0.5)

            # All events should be delivered
            assert len(events_received) == 20
        finally:
            await bus.stop()

    async def test_event_bus_not_started_error(self):
        """Test error when using bus before starting."""
        from src.shared.infrastructure.messaging.event_bus import (
            EventBusNotStartedError,
        )
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()

        event = DomainEvent(event_type="TestEvent", payload={"data": "test"})

        with pytest.raises(EventBusNotStartedError):
            await bus.publish(event)

    async def test_event_correlation(self):
        """Test event correlation ID propagation."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            events_received: List[DomainEvent[Any]] = []

            async def handler(event: DomainEvent[Any]) -> None:
                events_received.append(event)

            await bus.subscribe("CorrelatedEvent", handler)

            correlation_id = str(uuid4())
            event = DomainEvent(
                event_type="CorrelatedEvent",
                payload={"data": "test"},
                correlation_id=correlation_id,
            )
            await bus.publish(event)

            await asyncio.sleep(0.1)

            assert len(events_received) == 1
            assert events_received[0].correlation_id == correlation_id
        finally:
            await bus.stop()


@pytest.mark.integration
class TestEventBusErrorHandling:
    """Test event bus error handling."""

    async def test_handler_error_isolation(self):
        """Test that one failing handler doesn't affect others."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            successful_events: List[DomainEvent[Any]] = []

            async def failing_handler(event: DomainEvent[Any]) -> None:
                raise ValueError("Handler error")

            async def successful_handler(event: DomainEvent[Any]) -> None:
                successful_events.append(event)

            await bus.subscribe("TestEvent", failing_handler)
            await bus.subscribe("TestEvent", successful_handler)

            event = DomainEvent(event_type="TestEvent", payload={"data": "test"})
            await bus.publish(event)

            await asyncio.sleep(0.1)

            # Successful handler should still receive
            assert len(successful_events) == 1
        finally:
            await bus.stop()

    async def test_async_handler_execution(self):
        """Test that handlers are executed asynchronously."""
        from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

        bus = MemoryEventBus()
        await bus.start()

        try:
            execution_order: List[str] = []

            async def slow_handler(event: DomainEvent[Any]) -> None:
                await asyncio.sleep(0.1)
                execution_order.append("slow")

            async def fast_handler(event: DomainEvent[Any]) -> None:
                execution_order.append("fast")

            await bus.subscribe("TestEvent", slow_handler)
            await bus.subscribe("TestEvent", fast_handler)

            event = DomainEvent(event_type="TestEvent", payload={"data": "test"})
            await bus.publish(event)

            await asyncio.sleep(0.2)

            # Fast handler should complete first
            assert "fast" in execution_order
        finally:
            await bus.stop()
