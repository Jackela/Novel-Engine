"""Tests for the WorldState aggregate root.

This module contains comprehensive tests for the WorldState domain aggregate.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.world.domain.aggregates.world_state import WorldState


@pytest.fixture
def valid_world_state() -> WorldState:
    """Create a valid world state for testing."""
    return WorldState(story_id="story-123")


class TestWorldState:
    """Test cases for WorldState aggregate."""

    def test_create_world_state_with_valid_data(self) -> None:
        """Test world state creation with valid data."""
        world_state = WorldState(
            story_id="story-456",
            version=5,
            factions={"faction1": {"name": "The Rebels"}},
            locations={"loc1": {"name": "The Castle"}},
            events=[{"type": "battle", "result": "victory"}],
            metadata={"turn": 10},
        )

        assert world_state.story_id == "story-456"
        assert world_state.version == 5
        assert world_state.factions == {"faction1": {"name": "The Rebels"}}
        assert world_state.locations == {"loc1": {"name": "The Castle"}}
        assert world_state.events == [{"type": "battle", "result": "victory"}]
        assert world_state.metadata == {"turn": 10}
        assert world_state.is_deleted is False
        assert isinstance(world_state.id, str)

    def test_create_world_state_with_minimal_data(self) -> None:
        """Test world state creation with minimal data."""
        world_state = WorldState()

        assert world_state.story_id is None
        assert world_state.version == 1
        assert world_state.factions == {}
        assert world_state.locations == {}
        assert world_state.events == []
        assert world_state.metadata == {}
        assert world_state.is_deleted is False
        assert world_state.calendar is None
        assert world_state.created_at is None
        assert world_state.updated_at is None

    def test_create_world_state_generates_id(self) -> None:
        """Test that world state auto-generates ID."""
        world_state1 = WorldState()
        world_state2 = WorldState()

        assert world_state1.id is not None
        assert world_state2.id is not None
        assert world_state1.id != world_state2.id

        # Should be valid UUID string
        assert UUID(world_state1.id)
        assert UUID(world_state2.id)


class TestWorldStateCollections:
    """Test cases for collections management."""

    def test_factions_collection(self, valid_world_state: WorldState) -> None:
        """Test factions collection."""
        valid_world_state.factions["new_faction"] = {"name": "New Faction", "power": 50}

        assert "new_faction" in valid_world_state.factions
        assert valid_world_state.factions["new_faction"]["power"] == 50

    def test_locations_collection(self, valid_world_state: WorldState) -> None:
        """Test locations collection."""
        valid_world_state.locations["town"] = {"name": "Small Town", "population": 100}

        assert "town" in valid_world_state.locations
        assert valid_world_state.locations["town"]["population"] == 100

    def test_events_collection(self, valid_world_state: WorldState) -> None:
        """Test events collection."""
        valid_world_state.events.append({"type": "discovery", "what": "treasure"})

        assert len(valid_world_state.events) == 1
        assert valid_world_state.events[0]["type"] == "discovery"

    def test_events_collection_multiple(self, valid_world_state: WorldState) -> None:
        """Test adding multiple events."""
        valid_world_state.events.extend(
            [
                {"type": "event1"},
                {"type": "event2"},
                {"type": "event3"},
            ]
        )

        assert len(valid_world_state.events) == 3


class TestWorldStateMetadata:
    """Test cases for metadata management."""

    def test_metadata_storage(self, valid_world_state: WorldState) -> None:
        """Test metadata storage."""
        valid_world_state.metadata["key1"] = "value1"
        valid_world_state.metadata["key2"] = 123
        valid_world_state.metadata["key3"] = ["list", "of", "items"]

        assert valid_world_state.metadata["key1"] == "value1"
        assert valid_world_state.metadata["key2"] == 123
        assert valid_world_state.metadata["key3"] == ["list", "of", "items"]

    def test_nested_metadata(self, valid_world_state: WorldState) -> None:
        """Test nested metadata storage."""
        valid_world_state.metadata["nested"] = {"level1": {"level2": "value"}}

        assert valid_world_state.metadata["nested"]["level1"]["level2"] == "value"


class TestWorldStateVersion:
    """Test cases for version management."""

    def test_version_default(self) -> None:
        """Test default version is 1."""
        world_state = WorldState()
        assert world_state.version == 1

    def test_version_custom(self) -> None:
        """Test custom version can be set."""
        world_state = WorldState(version=10)
        assert world_state.version == 10


class TestWorldStateDeletedFlag:
    """Test cases for deletion flag."""

    def test_is_deleted_default(self) -> None:
        """Test default is_deleted is False."""
        world_state = WorldState()
        assert world_state.is_deleted is False

    def test_is_deleted_can_be_set(self) -> None:
        """Test is_deleted can be set to True."""
        world_state = WorldState(is_deleted=True)
        assert world_state.is_deleted is True


class TestWorldStateDomainEvents:
    """Test cases for domain events (placeholder implementation)."""

    def test_get_domain_events_returns_empty_list(
        self, valid_world_state: WorldState
    ) -> None:
        """Test get_domain_events returns empty list (placeholder)."""
        events = valid_world_state.get_domain_events()

        assert events == []
        assert isinstance(events, list)

    def test_clear_domain_events_does_nothing(
        self, valid_world_state: WorldState
    ) -> None:
        """Test clear_domain_events (placeholder implementation)."""
        # Should not raise
        valid_world_state.clear_domain_events()


class TestWorldStateInvariants:
    """Test cases for invariant validation."""

    def test_world_state_always_has_id(self) -> None:
        """Test that world state always has an ID."""
        world_state = WorldState()

        assert world_state.id is not None
        assert len(world_state.id) > 0

    def test_world_state_version_positive(self) -> None:
        """Test that version is positive."""
        world_state = WorldState(version=5)

        assert world_state.version > 0

    def test_collections_are_mutable(self, valid_world_state: WorldState) -> None:
        """Test that collections are mutable dictionaries/lists."""
        # Factions
        valid_world_state.factions["new"] = {}
        assert "new" in valid_world_state.factions

        # Locations
        valid_world_state.locations["new"] = {}
        assert "new" in valid_world_state.locations

        # Events
        valid_world_state.events.append({})
        assert len(valid_world_state.events) == 1

        # Metadata
        valid_world_state.metadata["new"] = {}
        assert "new" in valid_world_state.metadata

    def test_world_state_equality(self) -> None:
        """Test world state equality (default dataclass equality)."""
        world_state1 = WorldState(story_id="story-1")
        world_state2 = WorldState(story_id="story-1")

        # Should not be equal because IDs are different
        assert world_state1 != world_state2
