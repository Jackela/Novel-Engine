"""Tests for event store implementation."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.shared.infrastructure.messaging.event_bus import DomainEvent
from src.shared.infrastructure.messaging.event_store import (
    ConcurrencyError,
    EventNotFoundError,
    EventStoreError,
    InMemoryEventStore,
    StoredEvent,
)


@pytest.fixture
async def event_store():
    """Create a fresh event store for testing."""
    store = InMemoryEventStore()
    return store


@pytest.fixture
def sample_events():
    """Create sample domain events for testing."""
    return [
        DomainEvent(
            event_type="user.created",
            payload={"username": "john"},
            aggregate_id="user-123",
        ),
        DomainEvent(
            event_type="user.updated",
            payload={"email": "john@example.com"},
            aggregate_id="user-123",
        ),
    ]


class TestStoredEvent:
    """Tests for StoredEvent dataclass."""

    def test_create_stored_event(self) -> None:
        """Test creating a stored event."""
        event_id = uuid4()
        occurred_on = datetime.utcnow()

        stored = StoredEvent(
            position=1,
            event_id=event_id,
            event_type="test.event",
            aggregate_id="agg-123",
            aggregate_version=5,
            payload={"key": "value"},
            metadata={"source": "test"},
            occurred_on=occurred_on,
            correlation_id="corr-456",
            causation_id="cause-789",
        )

        assert stored.position == 1
        assert stored.event_id == event_id
        assert stored.event_type == "test.event"
        assert stored.aggregate_id == "agg-123"
        assert stored.aggregate_version == 5
        assert stored.payload == {"key": "value"}
        assert stored.metadata == {"source": "test"}
        assert stored.occurred_on == occurred_on
        assert stored.correlation_id == "corr-456"
        assert stored.causation_id == "cause-789"

    def test_stored_event_immutability(self) -> None:
        """Test that stored events are immutable."""
        stored = StoredEvent(
            position=1,
            event_id=uuid4(),
            event_type="test.event",
            aggregate_id="agg-123",
            aggregate_version=1,
            payload={},
            metadata={},
            occurred_on=datetime.utcnow(),
            correlation_id=None,
            causation_id=None,
        )

        with pytest.raises(AttributeError):
            stored.position = 2


class TestInMemoryEventStoreAppend:
    """Tests for appending events."""

    @pytest.mark.asyncio
    async def test_append_single_event(self, event_store) -> None:
        """Test appending a single event."""
        events = [
            DomainEvent(event_type="test.event", payload={"key": "value"}),
        ]

        stored = await event_store.append("agg-123", events)

        assert len(stored) == 1
        assert stored[0].position == 1
        assert stored[0].aggregate_id == "agg-123"
        assert stored[0].aggregate_version == 1
        assert stored[0].event_type == "test.event"

    @pytest.mark.asyncio
    async def test_append_multiple_events(self, event_store, sample_events) -> None:
        """Test appending multiple events."""
        stored = await event_store.append("user-123", sample_events)

        assert len(stored) == 2
        assert stored[0].aggregate_version == 1
        assert stored[1].aggregate_version == 2
        assert stored[0].position < stored[1].position

    @pytest.mark.asyncio
    async def test_append_preserves_event_id(self, event_store) -> None:
        """Test that original event ID is preserved."""
        original_id = uuid4()
        events = [
            DomainEvent(
                event_type="test.event",
                payload={},
                event_id=original_id,
            ),
        ]

        stored = await event_store.append("agg-123", events)

        assert stored[0].event_id == original_id

    @pytest.mark.asyncio
    async def test_append_preserves_occurred_on(self, event_store) -> None:
        """Test that original occurred_on is preserved."""
        original_time = datetime(2024, 1, 1, 12, 0, 0)
        events = [
            DomainEvent(
                event_type="test.event",
                payload={},
                occurred_on=original_time,
            ),
        ]

        stored = await event_store.append("agg-123", events)

        assert stored[0].occurred_on == original_time

    @pytest.mark.asyncio
    async def test_append_preserves_correlation_and_causation(
        self, event_store
    ) -> None:
        """Test that correlation and causation IDs are preserved."""
        events = [
            DomainEvent(
                event_type="test.event",
                payload={},
                correlation_id="corr-123",
                causation_id="cause-456",
            ),
        ]

        stored = await event_store.append("agg-123", events)

        assert stored[0].correlation_id == "corr-123"
        assert stored[0].causation_id == "cause-456"

    @pytest.mark.asyncio
    async def test_append_payload_serialization(self, event_store) -> None:
        """Test that payload is serialized properly."""
        events = [
            DomainEvent(
                event_type="test.event",
                payload={"nested": {"key": "value"}, "number": 42},
            ),
        ]

        stored = await event_store.append("agg-123", events)

        assert stored[0].payload == {"nested": {"key": "value"}, "number": 42}


class TestInMemoryEventStoreConcurrency:
    """Tests for optimistic concurrency control."""

    @pytest.mark.asyncio
    async def test_append_with_correct_expected_version(self, event_store) -> None:
        """Test appending with correct expected version."""
        # First append
        events1 = [DomainEvent(event_type="event1", payload={})]
        await event_store.append("agg-123", events1)

        # Second append with correct expected version
        events2 = [DomainEvent(event_type="event2", payload={})]
        stored = await event_store.append("agg-123", events2, expected_version=1)

        assert len(stored) == 1
        assert stored[0].aggregate_version == 2

    @pytest.mark.asyncio
    async def test_append_with_wrong_expected_version(self, event_store) -> None:
        """Test that wrong expected version raises ConcurrencyError."""
        events1 = [DomainEvent(event_type="event1", payload={})]
        await event_store.append("agg-123", events1)

        events2 = [DomainEvent(event_type="event2", payload={})]

        with pytest.raises(ConcurrencyError, match="Expected version 0 but found 1"):
            await event_store.append("agg-123", events2, expected_version=0)

    @pytest.mark.asyncio
    async def test_append_without_expected_version(self, event_store) -> None:
        """Test that append works without expected version."""
        events1 = [DomainEvent(event_type="event1", payload={})]
        await event_store.append("agg-123", events1)

        # No expected version - should work
        events2 = [DomainEvent(event_type="event2", payload={})]
        stored = await event_store.append("agg-123", events2)

        assert stored[0].aggregate_version == 2

    @pytest.mark.asyncio
    async def test_concurrent_appends_to_different_aggregates(
        self, event_store
    ) -> None:
        """Test concurrent appends to different aggregates."""
        import asyncio

        async def append_to_aggregate(agg_id: str, count: int):
            for i in range(count):
                events = [DomainEvent(event_type="test", payload={"i": i})]
                await event_store.append(agg_id, events)

        # Concurrent appends to different aggregates
        await asyncio.gather(
            append_to_aggregate("agg-1", 5),
            append_to_aggregate("agg-2", 5),
        )

        version1 = await event_store.get_current_version("agg-1")
        version2 = await event_store.get_current_version("agg-2")

        assert version1 == 5
        assert version2 == 5


class TestInMemoryEventStoreGetEvents:
    """Tests for retrieving events."""

    @pytest.mark.asyncio
    async def test_get_events_empty_aggregate(self, event_store) -> None:
        """Test getting events for non-existent aggregate."""
        events = await event_store.get_events("non-existent")

        assert events == []

    @pytest.mark.asyncio
    async def test_get_all_events(self, event_store, sample_events) -> None:
        """Test getting all events for an aggregate."""
        await event_store.append("user-123", sample_events)

        events = await event_store.get_events("user-123")

        assert len(events) == 2
        assert events[0].event_type == "user.created"
        assert events[1].event_type == "user.updated"

    @pytest.mark.asyncio
    async def test_get_events_from_version(self, event_store) -> None:
        """Test getting events from a specific version."""
        events = [
            DomainEvent(event_type="event1", payload={}),
            DomainEvent(event_type="event2", payload={}),
            DomainEvent(event_type="event3", payload={}),
        ]
        await event_store.append("agg-123", events)

        # Get from version 2
        result = await event_store.get_events("agg-123", from_version=2)

        assert len(result) == 2
        assert result[0].event_type == "event2"
        assert result[1].event_type == "event3"

    @pytest.mark.asyncio
    async def test_get_events_to_version(self, event_store) -> None:
        """Test getting events up to a specific version."""
        events = [
            DomainEvent(event_type="event1", payload={}),
            DomainEvent(event_type="event2", payload={}),
            DomainEvent(event_type="event3", payload={}),
        ]
        await event_store.append("agg-123", events)

        # Get up to version 2
        result = await event_store.get_events("agg-123", to_version=2)

        assert len(result) == 2
        assert result[0].event_type == "event1"
        assert result[1].event_type == "event2"

    @pytest.mark.asyncio
    async def test_get_events_version_range(self, event_store) -> None:
        """Test getting events within a version range."""
        events = [
            DomainEvent(event_type="event1", payload={}),
            DomainEvent(event_type="event2", payload={}),
            DomainEvent(event_type="event3", payload={}),
            DomainEvent(event_type="event4", payload={}),
        ]
        await event_store.append("agg-123", events)

        # Get versions 2-3
        result = await event_store.get_events("agg-123", from_version=2, to_version=3)

        assert len(result) == 2
        assert result[0].event_type == "event2"
        assert result[1].event_type == "event3"

    @pytest.mark.asyncio
    async def test_get_all_events_global(self, event_store) -> None:
        """Test getting all events globally."""
        events1 = [DomainEvent(event_type="event1", payload={})]
        events2 = [DomainEvent(event_type="event2", payload={})]

        await event_store.append("agg-1", events1)
        await event_store.append("agg-2", events2)

        all_events = await event_store.get_all_events()

        assert len(all_events) == 2
        assert all_events[0].position < all_events[1].position

    @pytest.mark.asyncio
    async def test_get_all_events_with_position_filter(self, event_store) -> None:
        """Test getting events with position filter."""
        for i in range(5):
            events = [DomainEvent(event_type=f"event{i}", payload={})]
            await event_store.append(f"agg-{i}", events)

        # Get from position 3
        result = await event_store.get_all_events(from_position=3)

        assert len(result) == 3  # Positions 3, 4, 5

    @pytest.mark.asyncio
    async def test_get_all_events_with_event_type_filter(self, event_store) -> None:
        """Test getting events filtered by type."""
        await event_store.append(
            "agg-1", [DomainEvent(event_type="type.a", payload={})]
        )
        await event_store.append(
            "agg-2", [DomainEvent(event_type="type.b", payload={})]
        )
        await event_store.append(
            "agg-3", [DomainEvent(event_type="type.a", payload={})]
        )

        result = await event_store.get_all_events(event_types=["type.a"])

        assert len(result) == 2
        assert all(e.event_type == "type.a" for e in result)


class TestInMemoryEventStoreVersion:
    """Tests for version queries."""

    @pytest.mark.asyncio
    async def test_get_current_version_empty(self, event_store) -> None:
        """Test getting version for non-existent aggregate."""
        version = await event_store.get_current_version("non-existent")

        assert version == 0

    @pytest.mark.asyncio
    async def test_get_current_version_with_events(self, event_store) -> None:
        """Test getting version after appending events."""
        events = [
            DomainEvent(event_type="event1", payload={}),
            DomainEvent(event_type="event2", payload={}),
        ]
        await event_store.append("agg-123", events)

        version = await event_store.get_current_version("agg-123")

        assert version == 2


class TestEventStoreExceptions:
    """Tests for event store exceptions."""

    def test_exception_inheritance(self) -> None:
        """Test that exceptions inherit from EventStoreError."""
        assert issubclass(ConcurrencyError, EventStoreError)
        assert issubclass(EventNotFoundError, EventStoreError)

    def test_concurrency_error_message(self) -> None:
        """Test ConcurrencyError message."""
        error = ConcurrencyError("version mismatch")
        assert str(error) == "version mismatch"

    def test_event_not_found_error_message(self) -> None:
        """Test EventNotFoundError message."""
        error = EventNotFoundError("event not found")
        assert str(error) == "event not found"
