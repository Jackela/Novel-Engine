"""Unit tests for InMemoryLocationRepository.

Tests cover CRUD operations, query operations, and adjacency
operations for the in-memory location repository.
"""

import pytest

from src.contexts.world.domain.entities.location import Location, LocationType
from src.contexts.world.infrastructure.persistence.in_memory_location_repository import (
    InMemoryLocationRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def location_repository():
    """Create a fresh location repository for each test."""
    repo = InMemoryLocationRepository()
    return repo


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        id="loc-001",
        name="Test Castle",
        description="A mighty fortress",
        location_type=LocationType.FORTRESS,
        coordinates=None,
        parent_location_id=None,
        connections=[],
    )


@pytest.fixture
def child_location():
    """Create a sample child location for testing."""
    return Location(
        id="loc-002",
        name="Castle Dungeon",
        description="Dark and damp",
        location_type=LocationType.DUNGEON,
        coordinates=None,
        parent_location_id="loc-001",
        connections=[],
    )


class TestLocationRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_returns_location_when_found(
        self, location_repository, sample_location
    ):
        """get_by_id returns location when found."""
        await location_repository.save(sample_location)

        result = await location_repository.get_by_id("loc-001")

        assert result is not None
        assert result.id == "loc-001"
        assert result.name == "Test Castle"

    async def test_get_by_id_returns_none_when_not_found(self, location_repository):
        """get_by_id returns None when location not found."""
        result = await location_repository.get_by_id("nonexistent")

        assert result is None


class TestLocationRepositorySave:
    """Tests for save method."""

    async def test_save_creates_new_location(
        self, location_repository, sample_location
    ):
        """save creates a new location."""
        result = await location_repository.save(sample_location)

        assert result.id == "loc-001"
        retrieved = await location_repository.get_by_id("loc-001")
        assert retrieved is not None

    async def test_save_updates_existing_location(
        self, location_repository, sample_location
    ):
        """save updates an existing location."""
        await location_repository.save(sample_location)

        updated_location = Location(
            id="loc-001",
            name="Updated Castle",
            description="An even mightier fortress",
            location_type=LocationType.FORTRESS,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )

        result = await location_repository.save(updated_location)

        assert result.name == "Updated Castle"
        retrieved = await location_repository.get_by_id("loc-001")
        assert retrieved.name == "Updated Castle"

    async def test_save_updates_parent_child_index(
        self, location_repository, sample_location, child_location
    ):
        """save updates parent-child index correctly."""
        await location_repository.save(sample_location)
        await location_repository.save(child_location)

        children = await location_repository.get_children("loc-001")

        assert len(children) == 1
        assert children[0].id == "loc-002"


class TestLocationRepositoryDelete:
    """Tests for delete method."""

    async def test_delete_removes_location(self, location_repository, sample_location):
        """delete removes the location."""
        await location_repository.save(sample_location)

        result = await location_repository.delete("loc-001")

        assert result is True
        retrieved = await location_repository.get_by_id("loc-001")
        assert retrieved is None

    async def test_delete_returns_false_when_not_found(self, location_repository):
        """delete returns False when location not found."""
        result = await location_repository.delete("nonexistent")

        assert result is False

    async def test_delete_removes_from_parent_index(
        self, location_repository, sample_location, child_location
    ):
        """delete removes location from parent-child index."""
        await location_repository.save(sample_location)
        await location_repository.save(child_location)

        await location_repository.delete("loc-002")

        children = await location_repository.get_children("loc-001")
        assert len(children) == 0


class TestLocationRepositoryGetByWorldId:
    """Tests for get_by_world_id method."""

    async def test_get_by_world_id_returns_locations_for_world(
        self, location_repository, sample_location
    ):
        """get_by_world_id returns locations for a world."""
        await location_repository.save(sample_location)
        location_repository.register_location_world("loc-001", "world-001")

        result = await location_repository.get_by_world_id("world-001")

        assert len(result) == 1
        assert result[0].id == "loc-001"

    async def test_get_by_world_id_returns_empty_list_when_no_locations(
        self, location_repository
    ):
        """get_by_world_id returns empty list when no locations."""
        result = await location_repository.get_by_world_id("empty-world")

        assert result == []

    async def test_get_by_world_id_returns_sorted_by_name(self, location_repository):
        """get_by_world_id returns locations sorted by name."""
        loc_a = Location(
            id="loc-b",
            name="Beta",
            description="B",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )
        loc_b = Location(
            id="loc-a",
            name="Alpha",
            description="A",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )

        await location_repository.save(loc_a)
        await location_repository.save(loc_b)
        location_repository.register_location_world("loc-b", "world-001")
        location_repository.register_location_world("loc-a", "world-001")

        result = await location_repository.get_by_world_id("world-001")

        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"


class TestLocationRepositoryFindAdjacent:
    """Tests for find_adjacent method."""

    async def test_find_adjacent_includes_siblings(self, location_repository):
        """find_adjacent includes sibling locations."""
        parent = Location(
            id="parent",
            name="Parent",
            description="Parent location",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )
        child1 = Location(
            id="child1",
            name="Child 1",
            description="First child",
            location_type=LocationType.BUILDING,
            coordinates=None,
            parent_location_id="parent",
            connections=[],
        )
        child2 = Location(
            id="child2",
            name="Child 2",
            description="Second child",
            location_type=LocationType.BUILDING,
            coordinates=None,
            parent_location_id="parent",
            connections=[],
        )

        await location_repository.save(parent)
        await location_repository.save(child1)
        await location_repository.save(child2)

        result = await location_repository.find_adjacent("child1")

        assert "child2" in result  # Sibling
        assert "parent" in result  # Parent

    async def test_find_adjacent_includes_explicit_connections(
        self, location_repository, sample_location
    ):
        """find_adjacent includes explicitly connected locations."""
        await location_repository.save(sample_location)

        connected = Location(
            id="connected",
            name="Connected",
            description="Connected location",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=["loc-001"],
        )
        await location_repository.save(connected)

        result = await location_repository.find_adjacent("loc-001")

        assert "connected" in result

    async def test_find_adjacent_returns_empty_list_for_nonexistent(
        self, location_repository
    ):
        """find_adjacent returns empty list for nonexistent location."""
        result = await location_repository.find_adjacent("nonexistent")

        assert result == []

    async def test_find_adjacent_excludes_self(
        self, location_repository, sample_location
    ):
        """find_adjacent excludes the location itself."""
        await location_repository.save(sample_location)

        result = await location_repository.find_adjacent("loc-001")

        assert "loc-001" not in result


class TestLocationRepositoryGetChildren:
    """Tests for get_children method."""

    async def test_get_children_returns_child_locations(
        self, location_repository, sample_location, child_location
    ):
        """get_children returns all child locations."""
        await location_repository.save(sample_location)
        await location_repository.save(child_location)

        result = await location_repository.get_children("loc-001")

        assert len(result) == 1
        assert result[0].id == "loc-002"

    async def test_get_children_returns_empty_list_when_no_children(
        self, location_repository, sample_location
    ):
        """get_children returns empty list when no children."""
        await location_repository.save(sample_location)

        result = await location_repository.get_children("loc-001")

        assert result == []

    async def test_get_children_returns_sorted_by_name(self, location_repository):
        """get_children returns children sorted by name."""
        parent = Location(
            id="parent",
            name="Parent",
            description="Parent",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )
        child_z = Location(
            id="child-z",
            name="Zebra",
            description="Z child",
            location_type=LocationType.BUILDING,
            coordinates=None,
            parent_location_id="parent",
            connections=[],
        )
        child_a = Location(
            id="child-a",
            name="Apple",
            description="A child",
            location_type=LocationType.BUILDING,
            coordinates=None,
            parent_location_id="parent",
            connections=[],
        )

        await location_repository.save(parent)
        await location_repository.save(child_z)
        await location_repository.save(child_a)

        result = await location_repository.get_children("parent")

        assert len(result) == 2
        assert result[0].name == "Apple"
        assert result[1].name == "Zebra"


class TestLocationRepositoryGetByType:
    """Tests for get_by_type method."""

    async def test_get_by_type_returns_matching_locations(self, location_repository):
        """get_by_type returns locations of specified type."""
        city = Location(
            id="city",
            name="Test City",
            description="A city",
            location_type=LocationType.CITY,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )
        dungeon = Location(
            id="dungeon",
            name="Test Dungeon",
            description="A dungeon",
            location_type=LocationType.DUNGEON,
            coordinates=None,
            parent_location_id=None,
            connections=[],
        )

        await location_repository.save(city)
        await location_repository.save(dungeon)
        location_repository.register_location_world("city", "world-001")
        location_repository.register_location_world("dungeon", "world-001")

        result = await location_repository.get_by_type("world-001", "city")

        assert len(result) == 1
        assert result[0].id == "city"


class TestLocationRepositoryClear:
    """Tests for clear method."""

    async def test_clear_removes_all_locations(
        self, location_repository, sample_location, child_location
    ):
        """clear removes all locations and indexes."""
        await location_repository.save(sample_location)
        await location_repository.save(child_location)

        await location_repository.clear()

        assert await location_repository.get_by_id("loc-001") is None
        assert await location_repository.get_by_id("loc-002") is None

    async def test_clear_allows_readding_locations(
        self, location_repository, sample_location
    ):
        """clear allows re-adding locations after clearing."""
        await location_repository.save(sample_location)
        await location_repository.clear()

        # Should be able to save again
        result = await location_repository.save(sample_location)
        assert result.id == "loc-001"


class TestLocationRepositoryRegisterLocationWorld:
    """Tests for register_location_world method."""

    async def test_register_location_world_adds_to_index(
        self, location_repository, sample_location
    ):
        """register_location_world adds location to world index."""
        await location_repository.save(sample_location)
        location_repository.register_location_world("loc-001", "world-001")

        result = await location_repository.get_by_world_id("world-001")

        assert len(result) == 1
        assert result[0].id == "loc-001"

    async def test_register_location_world_allows_multiple_worlds(
        self, location_repository, sample_location
    ):
        """register_location_world allows location in multiple worlds."""
        await location_repository.save(sample_location)
        location_repository.register_location_world("loc-001", "world-001")
        location_repository.register_location_world("loc-001", "world-002")

        result1 = await location_repository.get_by_world_id("world-001")
        result2 = await location_repository.get_by_world_id("world-002")

        assert len(result1) == 1
        assert len(result2) == 1


class TestLocationRepositoryThreadSafety:
    """Tests for thread safety."""

    def test_repository_uses_rlock(self, location_repository):
        """repository uses RLock for thread safety."""
        import threading

        assert isinstance(location_repository._lock, threading.RLock)
