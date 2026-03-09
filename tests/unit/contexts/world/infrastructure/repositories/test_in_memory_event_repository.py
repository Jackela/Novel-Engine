"""Unit tests for InMemoryEventRepository.

Tests cover CRUD operations, query operations, and world event
management for the in-memory event repository.
"""

import pytest

from src.contexts.world.domain.entities.history_event import HistoryEvent
from src.contexts.world.domain.entities.history_event import EventType
from src.contexts.world.infrastructure.persistence.in_memory_event_repository import (
    InMemoryEventRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def event_repository():
    """Create a fresh event repository for each test."""
    repo = InMemoryEventRepository()
    return repo


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return HistoryEvent(
        id="event-001",
        name="The Great Battle",
        description="A significant battle took place",
        event_type=EventType.BATTLE,
        year=1000,
        location_ids=["loc-001"],
        faction_ids=["faction-001"],
        character_ids=["char-001"],
        narrative_importance=8,
        consequences=["Kingdom fell", "New ruler crowned"],
    )


@pytest.fixture
def second_event():
    """Create a second sample event for testing."""
    return HistoryEvent(
        id="event-002",
        name="The Treaty Signing",
        description="Peace was established",
        event_type=EventType.POLITICAL,
        year=1001,
        location_ids=["loc-002"],
        faction_ids=["faction-001", "faction-002"],
        character_ids=["char-002"],
        narrative_importance=5,
        consequences=["Trade opened", "Alliance formed"],
    )


class TestEventRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_returns_event_when_found(
        self, event_repository, sample_event
    ):
        """get_by_id returns event when found."""
        await event_repository.save(sample_event)

        result = await event_repository.get_by_id("event-001")

        assert result is not None
        assert result.id == "event-001"
        assert result.name == "The Great Battle"

    async def test_get_by_id_returns_none_when_not_found(
        self, event_repository
    ):
        """get_by_id returns None when event not found."""
        result = await event_repository.get_by_id("nonexistent")

        assert result is None


class TestEventRepositorySave:
    """Tests for save method."""

    async def test_save_creates_new_event(
        self, event_repository, sample_event
    ):
        """save creates a new event."""
        result = await event_repository.save(sample_event)

        assert result.id == "event-001"
        retrieved = await event_repository.get_by_id("event-001")
        assert retrieved is not None

    async def test_save_updates_existing_event(
        self, event_repository, sample_event
    ):
        """save updates an existing event."""
        await event_repository.save(sample_event)

        updated_event = HistoryEvent(
            id="event-001",
            name="The REALLY Great Battle",
            description="An even more significant battle",
            event_type=EventType.BATTLE,
            year=1000,
            location_ids=["loc-001"],
            faction_ids=["faction-001"],
            character_ids=["char-001"],
            narrative_importance=10,
            consequences=["Kingdom fell"],
        )

        result = await event_repository.save(updated_event)

        assert result.name == "The REALLY Great Battle"
        retrieved = await event_repository.get_by_id("event-001")
        assert retrieved.name == "The REALLY Great Battle"


class TestEventRepositorySaveAll:
    """Tests for save_all method."""

    async def test_save_all_saves_multiple_events(
        self, event_repository, sample_event, second_event
    ):
        """save_all saves multiple events at once."""
        result = await event_repository.save_all([sample_event, second_event])

        assert len(result) == 2
        assert await event_repository.get_by_id("event-001") is not None
        assert await event_repository.get_by_id("event-002") is not None

    async def test_save_all_returns_empty_list_for_empty_input(
        self, event_repository
    ):
        """save_all returns empty list for empty input."""
        result = await event_repository.save_all([])

        assert result == []


class TestEventRepositoryDelete:
    """Tests for delete method."""

    async def test_delete_removes_event(
        self, event_repository, sample_event
    ):
        """delete removes the event."""
        await event_repository.save(sample_event)

        result = await event_repository.delete("event-001")

        assert result is True
        retrieved = await event_repository.get_by_id("event-001")
        assert retrieved is None

    async def test_delete_returns_false_when_not_found(
        self, event_repository
    ):
        """delete returns False when event not found."""
        result = await event_repository.delete("nonexistent")

        assert result is False

    async def test_delete_removes_from_world_index(
        self, event_repository, sample_event
    ):
        """delete removes event from world index."""
        await event_repository.save(sample_event)
        event_repository.register_world_event("world-001", "event-001")

        await event_repository.delete("event-001")

        world_events = await event_repository.get_by_world_id("world-001")
        assert len(world_events) == 0


class TestEventRepositoryGetByWorldId:
    """Tests for get_by_world_id method."""

    async def test_get_by_world_id_returns_events_for_world(
        self, event_repository, sample_event
    ):
        """get_by_world_id returns events for a world."""
        await event_repository.save(sample_event)
        event_repository.register_world_event("world-001", "event-001")

        result = await event_repository.get_by_world_id("world-001")

        assert len(result) == 1
        assert result[0].id == "event-001"

    async def test_get_by_world_id_uses_pagination(
        self, event_repository
    ):
        """get_by_world_id respects pagination parameters."""
        for i in range(5):
            event = HistoryEvent(
                id=f"event-{i}",
                name=f"Event {i}",
                description="Test event",
                event_type=EventType.BATTLE,
                year=1000 + i,
                narrative_importance=i,
            )
            await event_repository.save(event)
            event_repository.register_world_event("world-001", f"event-{i}")

        result = await event_repository.get_by_world_id("world-001", limit=2, offset=1)

        assert len(result) == 2

    async def test_get_by_world_id_returns_sorted_by_importance(
        self, event_repository
    ):
        """get_by_world_id returns events sorted by narrative importance."""
        low_importance = HistoryEvent(
            id="low",
            name="Low Importance",
            description="Not important",
            event_type=EventType.BATTLE,
            year=1000,
            narrative_importance=2,
        )
        high_importance = HistoryEvent(
            id="high",
            name="High Importance",
            description="Very important",
            event_type=EventType.BATTLE,
            year=1001,
            narrative_importance=9,
        )

        await event_repository.save(low_importance)
        await event_repository.save(high_importance)
        event_repository.register_world_event("world-001", "low")
        event_repository.register_world_event("world-001", "high")

        result = await event_repository.get_by_world_id("world-001")

        assert result[0].id == "high"  # Higher importance first
        assert result[1].id == "low"


class TestEventRepositoryGetByLocationId:
    """Tests for get_by_location_id method."""

    async def test_get_by_location_id_returns_matching_events(
        self, event_repository, sample_event, second_event
    ):
        """get_by_location_id returns events at specified location."""
        await event_repository.save(sample_event)
        await event_repository.save(second_event)

        result = await event_repository.get_by_location_id("loc-001")

        assert len(result) == 1
        assert result[0].id == "event-001"

    async def test_get_by_location_id_returns_empty_list_when_no_matches(
        self, event_repository, sample_event
    ):
        """get_by_location_id returns empty list when no events at location."""
        await event_repository.save(sample_event)

        result = await event_repository.get_by_location_id("nonexistent-loc")

        assert result == []

    async def test_get_by_location_id_returns_sorted_by_importance(
        self, event_repository
    ):
        """get_by_location_id returns events sorted by importance."""
        low = HistoryEvent(
            id="low",
            name="Low",
            description="Low importance",
            event_type=EventType.BATTLE,
            location_ids=["loc-001"],
            narrative_importance=1,
        )
        high = HistoryEvent(
            id="high",
            name="High",
            description="High importance",
            event_type=EventType.BATTLE,
            location_ids=["loc-001"],
            narrative_importance=10,
        )

        await event_repository.save(low)
        await event_repository.save(high)

        result = await event_repository.get_by_location_id("loc-001")

        assert result[0].id == "high"
        assert result[1].id == "low"


class TestEventRepositoryGetByFactionId:
    """Tests for get_by_faction_id method."""

    async def test_get_by_faction_id_returns_matching_events(
        self, event_repository, sample_event, second_event
    ):
        """get_by_faction_id returns events involving faction."""
        await event_repository.save(sample_event)
        await event_repository.save(second_event)

        result = await event_repository.get_by_faction_id("faction-001")

        assert len(result) == 2

    async def test_get_by_faction_id_returns_empty_list_when_no_matches(
        self, event_repository, sample_event
    ):
        """get_by_faction_id returns empty list when no events involve faction."""
        await event_repository.save(sample_event)

        result = await event_repository.get_by_faction_id("nonexistent-faction")

        assert result == []


class TestEventRepositoryClear:
    """Tests for clear method."""

    async def test_clear_removes_all_events(
        self, event_repository, sample_event, second_event
    ):
        """clear removes all events and indexes."""
        await event_repository.save(sample_event)
        await event_repository.save(second_event)
        event_repository.register_world_event("world-001", "event-001")

        await event_repository.clear()

        assert await event_repository.get_by_id("event-001") is None
        assert await event_repository.get_by_id("event-002") is None
        world_events = await event_repository.get_by_world_id("world-001")
        assert world_events == []


class TestEventRepositoryRegisterWorldEvent:
    """Tests for register_world_event method."""

    async def test_register_world_event_adds_to_index(
        self, event_repository, sample_event
    ):
        """register_world_event adds event to world index."""
        await event_repository.save(sample_event)
        event_repository.register_world_event("world-001", "event-001")

        result = await event_repository.get_by_world_id("world-001")

        assert len(result) == 1

    async def test_register_world_event_allows_multiple_events(
        self, event_repository, sample_event, second_event
    ):
        """register_world_event allows multiple events per world."""
        await event_repository.save(sample_event)
        await event_repository.save(second_event)
        event_repository.register_world_event("world-001", "event-001")
        event_repository.register_world_event("world-001", "event-002")

        result = await event_repository.get_by_world_id("world-001")

        assert len(result) == 2


class TestEventRepositoryDeriveWorldId:
    """Tests for _derive_world_id method."""

    def test_derive_world_id_returns_first_location_id(
        self, event_repository
    ):
        """_derive_world_id returns first location ID as world proxy."""
        event = HistoryEvent(
            id="event",
            name="Test Event",
            description="Test",
            event_type=EventType.BATTLE,
            location_ids=["loc-001", "loc-002"],
        )

        result = event_repository._derive_world_id(event)

        assert result == "loc-001"

    def test_derive_world_id_returns_none_when_no_locations(
        self, event_repository
    ):
        """_derive_world_id returns None when event has no locations."""
        event = HistoryEvent(
            id="event",
            name="Test Event",
            description="Test",
            event_type=EventType.BATTLE,
            location_ids=[],
        )

        result = event_repository._derive_world_id(event)

        assert result is None


class TestEventRepositoryThreadSafety:
    """Tests for thread safety."""

    def test_repository_uses_rlock(self, event_repository):
        """repository uses RLock for thread safety."""
        import threading

        assert isinstance(event_repository._lock, threading.RLock)
