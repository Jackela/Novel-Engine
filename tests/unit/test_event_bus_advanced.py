import asyncio
from unittest.mock import Mock

import pytest

from src.core.event_bus import EventBus, EventPriority, InMemoryEventBus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dead_letter_retry_clears_on_success():
    event_bus = EventBus()
    calls = {"count": 0}

    def flaky_handler(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("first attempt fails")

    event_bus.subscribe("test_event", flaky_handler)

    event_bus.emit("test_event", payload="data")
    assert event_bus.get_metrics()["events_failed"] == 1
    assert len(event_bus.get_dead_letters()) == 1

    retried = await event_bus.retry_dead_letters(event_type="test_event", max_items=1)

    assert retried == 1
    assert calls["count"] == 2
    assert len(event_bus.get_dead_letters()) == 0
    assert event_bus.get_metrics()["retries_attempted"] == 1


@pytest.mark.unit
def test_pause_and_resume_event_type():
    event_bus = EventBus()
    handler = Mock()
    event_bus.subscribe("paused_event", handler)

    event_bus.pause_event_type("paused_event")
    event_id = event_bus.emit("paused_event", payload="data")

    assert event_id is None
    assert handler.call_count == 0
    assert event_bus.get_history(event_type="paused_event") == []

    event_bus.resume_event_type("paused_event")
    event_id = event_bus.emit("paused_event", payload="data", priority=EventPriority.HIGH)

    assert event_id is not None
    assert handler.call_count == 1
    assert len(event_bus.get_history(event_type="paused_event")) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_supports_sync_and_async_handlers():
    event_bus = EventBus()
    sync_called = {"value": False}
    async_called = {"value": False}

    def sync_handler(data):
        sync_called["value"] = data["sync"]

    async def async_handler(data):
        await asyncio.sleep(0)
        async_called["value"] = data["async"]

    event_bus.subscribe("async_event", sync_handler)
    event_bus.subscribe("async_event", async_handler)

    await event_bus.publish(
        "async_event", {"sync": True, "async": True}, source="test"
    )

    assert sync_called["value"] is True
    assert async_called["value"] is True


@pytest.mark.unit
def test_in_memory_event_bus_replay_and_stats():
    bus = InMemoryEventBus()
    received = []

    bus.subscribe("topic", received.append)
    bus.publish("topic", {"message": "hello"})
    bus.publish("other", {"message": "ignored"})

    assert received == [{"message": "hello"}]
    assert bus.replay(topic="topic")[0]["payload"]["message"] == "hello"
    stats = bus.stats()
    assert stats["total_events"] == 2
    assert "topic" in stats["topics"]
