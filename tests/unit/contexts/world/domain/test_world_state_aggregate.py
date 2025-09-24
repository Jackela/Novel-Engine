#!/usr/bin/env python3
"""
Unit tests for WorldState Aggregate Root

Comprehensive test suite for the WorldState aggregate root business logic,
covering entity management, state transitions, spatial operations, and domain events.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

# Mock problematic dependencies
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock the aioredis dependency to avoid import errors
sys.modules["aioredis"] = MagicMock()


# Create proper mock classes for event_bus module to support dataclass decorator
class MockEventPriority(Enum):
    """Mock EventPriority for testing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockEvent:
    """Mock Event class that supports dataclass functionality."""

    event_id: str
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    priority: MockEventPriority = MockEventPriority.NORMAL
    timestamp: datetime = None
    tags: set = field(default_factory=set)
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


# Create a proper mock module for src.events.event_bus
class MockEventBusModule:
    Event = MockEvent
    EventPriority = MockEventPriority


sys.modules["src.events.event_bus"] = MockEventBusModule()

# Now import the actual modules we're testing
from contexts.world.domain.aggregates.world_state import (
    EntityType,
    WorldState,
    WorldStatus,
)
from contexts.world.domain.value_objects.coordinates import Coordinates


class TestWorldStateAggregate:
    """Test suite for WorldState aggregate root."""

    @pytest.fixture
    def world_state(self) -> WorldState:
        """Create a test WorldState instance."""
        return WorldState(
            name="Test World", description="A test world for unit testing"
        )

    @pytest.fixture
    def sample_coordinates(self) -> Coordinates:
        """Create sample coordinates for testing."""
        return Coordinates(x=10.0, y=20.0, z=5.0)

    @pytest.fixture
    def sample_entity_data(self, sample_coordinates) -> Dict[str, Any]:
        """Create sample entity data for testing."""
        return {
            "entity_id": "test-entity-001",
            "entity_type": EntityType.CHARACTER,
            "name": "Test Character",
            "coordinates": sample_coordinates,
            "properties": {"health": 100, "level": 1},
            "metadata": {"created_by": "test"},
        }

    # ==================== Initialization and Validation Tests ====================

    def test_world_state_initialization(self):
        """Test WorldState proper initialization."""
        world = WorldState(name="Test World", description="Test Description")

        assert world.name == "Test World"
        assert world.description == "Test Description"
        assert world.status == WorldStatus.ACTIVE
        assert isinstance(world.world_time, datetime)
        assert world.entities == {}
        assert world.environment == {}
        assert world.spatial_index == {}
        assert world.metadata == {}
        assert world.max_entities == 10000
        assert world.spatial_grid_size == 100.0
        assert len(world.id) > 0
        assert (
            world.version == 2
        )  # Version increments during creation (1) and activation (2)

    def test_world_state_auto_name_generation(self):
        """Test automatic name generation when name is empty."""
        world = WorldState(name="")
        assert world.name.startswith("World_")
        assert len(world.name) > 6  # "World_" + 8-char ID prefix

    def test_world_state_validation_empty_name(self):
        """Test validation fails for empty name after initialization."""
        with pytest.raises(ValueError) as exc_info:
            WorldState(name="   ")  # Whitespace-only name
        assert "World name cannot be empty" in str(exc_info.value)

    def test_world_state_validation_future_time(self):
        """Test validation for world time in far future."""
        future_time = datetime.now() + timedelta(days=400)  # More than a year
        with pytest.raises(ValueError) as exc_info:
            WorldState(name="Test", world_time=future_time)
        assert "World time is more than a year in the future" in str(
            exc_info.value
        )

    def test_world_state_validation_entity_limit(self):
        """Test validation for entity limit exceeded."""
        world = WorldState(name="Test", max_entities=2)
        coords = Coordinates(0, 0, 0)

        # Add entities up to the limit
        world.add_entity("entity1", EntityType.CHARACTER, "Char1", coords)
        world.add_entity("entity2", EntityType.OBJECT, "Obj1", coords)

        # Adding one more should fail
        with pytest.raises(ValueError) as exc_info:
            world.add_entity("entity3", EntityType.CHARACTER, "Char2", coords)
        assert "World has reached maximum entity limit of 2" in str(
            exc_info.value
        )

    # ==================== State Transition Tests ====================

    def test_activate_world_state(self, world_state):
        """Test activating world state."""
        world_state.status = WorldStatus.PAUSED
        initial_version = world_state.version

        world_state.activate()

        assert world_state.status == WorldStatus.ACTIVE
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        assert len(events) > 0
        activation_event = next(
            (e for e in events if "activated" in e.change_reason), None
        )
        assert activation_event is not None

    def test_pause_world_state(self, world_state):
        """Test pausing active world state."""
        world_state.activate()  # Ensure it's active
        initial_version = world_state.version
        world_state.clear_domain_events()

        world_state.pause()

        assert world_state.status == WorldStatus.PAUSED
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        pause_event = next(
            (e for e in events if "paused" in e.change_reason), None
        )
        assert pause_event is not None

    def test_pause_non_active_world_state(self, world_state):
        """Test pausing non-active world state does nothing."""
        world_state.status = WorldStatus.ARCHIVED
        initial_version = world_state.version

        world_state.pause()

        # Should not change status or version
        assert world_state.status == WorldStatus.ARCHIVED
        assert world_state.version == initial_version

    def test_archive_world_state(self, world_state):
        """Test archiving world state."""
        initial_version = world_state.version

        world_state.archive()

        assert world_state.status == WorldStatus.ARCHIVED
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        archive_event = next(
            (e for e in events if "archived" in e.change_reason), None
        )
        assert archive_event is not None

    # ==================== Entity Management Tests ====================

    def test_add_entity_success(self, world_state, sample_entity_data):
        """Test successfully adding an entity."""
        initial_count = len(world_state.entities)
        initial_version = world_state.version

        entity = world_state.add_entity(**sample_entity_data)

        assert len(world_state.entities) == initial_count + 1
        assert world_state.entities[sample_entity_data["entity_id"]] == entity
        assert entity.id == sample_entity_data["entity_id"]
        assert entity.entity_type == sample_entity_data["entity_type"]
        assert entity.name == sample_entity_data["name"]
        assert entity.coordinates == sample_entity_data["coordinates"]
        assert entity.properties == sample_entity_data["properties"]
        assert entity.metadata == sample_entity_data["metadata"]
        assert world_state.version == initial_version + 1

        # Check spatial index was updated
        grid_key = world_state._get_spatial_grid_key(
            sample_entity_data["coordinates"]
        )
        assert grid_key in world_state.spatial_index
        assert (
            sample_entity_data["entity_id"]
            in world_state.spatial_index[grid_key]
        )

        # Check domain event was raised
        events = world_state.get_domain_events()
        add_event = next(
            (e for e in events if e.change_type.value == "entity_added"), None
        )
        assert add_event is not None

    def test_add_duplicate_entity_fails(self, world_state, sample_entity_data):
        """Test adding entity with duplicate ID fails."""
        world_state.add_entity(**sample_entity_data)

        with pytest.raises(ValueError) as exc_info:
            world_state.add_entity(**sample_entity_data)
        assert (
            f"Entity with ID {sample_entity_data['entity_id']} already exists"
            in str(exc_info.value)
        )

    def test_remove_entity_success(self, world_state, sample_entity_data):
        """Test successfully removing an entity."""
        # First add the entity
        world_state.add_entity(**sample_entity_data)
        initial_count = len(world_state.entities)
        initial_version = world_state.version
        world_state.clear_domain_events()

        removed_entity = world_state.remove_entity(
            sample_entity_data["entity_id"], "Test removal"
        )

        assert len(world_state.entities) == initial_count - 1
        assert sample_entity_data["entity_id"] not in world_state.entities
        assert removed_entity is not None
        assert removed_entity.id == sample_entity_data["entity_id"]
        assert world_state.version == initial_version + 1

        # Check spatial index was updated
        grid_key = world_state._get_spatial_grid_key(
            sample_entity_data["coordinates"]
        )
        assert grid_key not in world_state.spatial_index or sample_entity_data[
            "entity_id"
        ] not in world_state.spatial_index.get(grid_key, [])

        # Check domain event was raised
        events = world_state.get_domain_events()
        remove_event = next(
            (e for e in events if e.change_type.value == "entity_removed"),
            None,
        )
        assert remove_event is not None

    def test_remove_nonexistent_entity(self, world_state):
        """Test removing non-existent entity returns None."""
        result = world_state.remove_entity("nonexistent-id", "Test")
        assert result is None

    def test_move_entity_success(self, world_state, sample_entity_data):
        """Test successfully moving an entity."""
        # Add entity first
        world_state.add_entity(**sample_entity_data)
        initial_version = world_state.version
        world_state.clear_domain_events()

        new_coordinates = Coordinates(
            x=150.0, y=260.0, z=10.0
        )  # Different grid cell
        success = world_state.move_entity(
            sample_entity_data["entity_id"], new_coordinates, "Test move"
        )

        assert success is True
        entity = world_state.entities[sample_entity_data["entity_id"]]
        assert entity.coordinates == new_coordinates
        assert world_state.version == initial_version + 1

        # Check spatial index was updated
        old_grid_key = world_state._get_spatial_grid_key(
            sample_entity_data["coordinates"]
        )
        new_grid_key = world_state._get_spatial_grid_key(new_coordinates)

        assert sample_entity_data[
            "entity_id"
        ] not in world_state.spatial_index.get(old_grid_key, [])
        assert (
            sample_entity_data["entity_id"]
            in world_state.spatial_index[new_grid_key]
        )

        # Check domain event was raised
        events = world_state.get_domain_events()
        move_event = next(
            (e for e in events if e.change_type.value == "entity_moved"), None
        )
        assert move_event is not None

    def test_move_nonexistent_entity(self, world_state):
        """Test moving non-existent entity returns False."""
        new_coordinates = Coordinates(x=50.0, y=60.0, z=10.0)
        success = world_state.move_entity(
            "nonexistent-id", new_coordinates, "Test"
        )
        assert success is False

    def test_update_entity_success(self, world_state, sample_entity_data):
        """Test successfully updating an entity."""
        # Add entity first
        world_state.add_entity(**sample_entity_data)
        initial_version = world_state.version
        world_state.clear_domain_events()

        new_properties = {"health": 150, "mana": 100}
        new_metadata = {"updated_by": "admin"}

        success = world_state.update_entity(
            sample_entity_data["entity_id"],
            properties=new_properties,
            metadata=new_metadata,
            reason="Test update",
        )

        assert success is True
        entity = world_state.entities[sample_entity_data["entity_id"]]
        assert entity.properties["health"] == 150
        assert entity.properties["mana"] == 100
        assert entity.properties["level"] == 1  # Original property preserved
        assert entity.metadata["updated_by"] == "admin"
        assert (
            entity.metadata["created_by"] == "test"
        )  # Original metadata preserved
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        update_event = next(
            (e for e in events if e.change_type.value == "entity_updated"),
            None,
        )
        assert update_event is not None

    def test_update_nonexistent_entity(self, world_state):
        """Test updating non-existent entity returns False."""
        success = world_state.update_entity(
            "nonexistent-id", properties={"test": "value"}
        )
        assert success is False

    # ==================== Query Operations Tests ====================

    def test_get_entity_success(self, world_state, sample_entity_data):
        """Test getting entity by ID."""
        world_state.add_entity(**sample_entity_data)

        entity = world_state.get_entity(sample_entity_data["entity_id"])

        assert entity is not None
        assert entity.id == sample_entity_data["entity_id"]

    def test_get_nonexistent_entity(self, world_state):
        """Test getting non-existent entity returns None."""
        entity = world_state.get_entity("nonexistent-id")
        assert entity is None

    def test_get_entities_by_type(self, world_state):
        """Test filtering entities by type."""
        coords1 = Coordinates(0, 0, 0)
        coords2 = Coordinates(10, 10, 10)

        world_state.add_entity(
            "char1", EntityType.CHARACTER, "Character 1", coords1
        )
        world_state.add_entity(
            "char2", EntityType.CHARACTER, "Character 2", coords2
        )
        world_state.add_entity("obj1", EntityType.OBJECT, "Object 1", coords1)

        characters = world_state.get_entities_by_type(EntityType.CHARACTER)
        objects = world_state.get_entities_by_type(EntityType.OBJECT)
        locations = world_state.get_entities_by_type(EntityType.LOCATION)

        assert len(characters) == 2
        assert len(objects) == 1
        assert len(locations) == 0
        assert all(
            entity.entity_type == EntityType.CHARACTER for entity in characters
        )
        assert all(
            entity.entity_type == EntityType.OBJECT for entity in objects
        )

    def test_get_entities_in_area(self, world_state):
        """Test spatial query for entities within radius."""
        center = Coordinates(0, 0, 0)
        coords_near = Coordinates(5, 5, 0)  # ~7.07 units away
        coords_far = Coordinates(20, 20, 0)  # ~28.28 units away

        world_state.add_entity(
            "near_entity", EntityType.CHARACTER, "Near", coords_near
        )
        world_state.add_entity(
            "far_entity", EntityType.CHARACTER, "Far", coords_far
        )
        world_state.add_entity(
            "center_entity", EntityType.OBJECT, "Center", center
        )

        # Query with radius 10 should get near and center entities
        entities_in_area = world_state.get_entities_in_area(
            center, radius=10.0
        )
        entity_ids = [entity.id for entity in entities_in_area]

        assert "near_entity" in entity_ids
        assert "center_entity" in entity_ids
        assert "far_entity" not in entity_ids
        assert len(entities_in_area) == 2

    def test_get_entities_in_area_with_type_filter(self, world_state):
        """Test spatial query with entity type filtering."""
        center = Coordinates(0, 0, 0)
        coords_near = Coordinates(5, 5, 0)

        world_state.add_entity(
            "near_char", EntityType.CHARACTER, "Near Char", coords_near
        )
        world_state.add_entity(
            "near_obj", EntityType.OBJECT, "Near Obj", coords_near
        )

        # Query for only characters
        characters_in_area = world_state.get_entities_in_area(
            center, radius=10.0, entity_types=[EntityType.CHARACTER]
        )

        assert len(characters_in_area) == 1
        assert characters_in_area[0].entity_type == EntityType.CHARACTER

    def test_get_entities_at_coordinates_exact(self, world_state):
        """Test getting entities at exact coordinates."""
        coords = Coordinates(10, 20, 5)
        world_state.add_entity(
            "exact_entity", EntityType.CHARACTER, "Exact", coords
        )
        world_state.add_entity(
            "other_entity",
            EntityType.CHARACTER,
            "Other",
            Coordinates(15, 25, 5),
        )

        entities = world_state.get_entities_at_coordinates(
            coords, tolerance=0.0
        )

        assert len(entities) == 1
        assert entities[0].id == "exact_entity"

    def test_get_entities_at_coordinates_with_tolerance(self, world_state):
        """Test getting entities at coordinates with tolerance."""
        coords = Coordinates(10, 20, 5)
        nearby_coords = Coordinates(10.5, 20.5, 5)  # ~0.71 units away

        world_state.add_entity(
            "exact_entity", EntityType.CHARACTER, "Exact", coords
        )
        world_state.add_entity(
            "nearby_entity", EntityType.CHARACTER, "Nearby", nearby_coords
        )

        entities = world_state.get_entities_at_coordinates(
            coords, tolerance=1.0
        )

        assert len(entities) == 2
        entity_ids = [entity.id for entity in entities]
        assert "exact_entity" in entity_ids
        assert "nearby_entity" in entity_ids

    # ==================== Time Management Tests ====================

    def test_advance_time_success(self, world_state):
        """Test advancing world time."""
        initial_time = world_state.world_time
        initial_version = world_state.version
        new_time = initial_time + timedelta(hours=1)
        world_state.clear_domain_events()

        world_state.advance_time(new_time, "Time progression")

        assert world_state.world_time == new_time
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        time_event = next(
            (e for e in events if e.change_type.value == "time_advanced"), None
        )
        assert time_event is not None

    def test_advance_time_backwards_fails(self, world_state):
        """Test advancing time backwards fails."""
        initial_time = world_state.world_time
        past_time = initial_time - timedelta(hours=1)

        with pytest.raises(ValueError) as exc_info:
            world_state.advance_time(past_time, "Invalid time")
        assert "New time must be after current world time" in str(
            exc_info.value
        )

    def test_advance_time_same_time_fails(self, world_state):
        """Test advancing to same time fails."""
        current_time = world_state.world_time

        with pytest.raises(ValueError) as exc_info:
            world_state.advance_time(current_time, "Same time")
        assert "New time must be after current world time" in str(
            exc_info.value
        )

    # ==================== Environment Tests ====================

    def test_update_environment_success(self, world_state):
        """Test updating environment properties."""
        initial_version = world_state.version
        environment_changes = {
            "weather": "rainy",
            "temperature": 15,
            "visibility": "low",
        }
        world_state.clear_domain_events()

        world_state.update_environment(environment_changes, "Weather change")

        assert world_state.environment["weather"] == "rainy"
        assert world_state.environment["temperature"] == 15
        assert world_state.environment["visibility"] == "low"
        assert world_state.version == initial_version + 1

        # Check domain event was raised
        events = world_state.get_domain_events()
        env_event = next(
            (
                e
                for e in events
                if e.change_type.value == "environment_changed"
            ),
            None,
        )
        assert env_event is not None

    def test_update_environment_merge_properties(self, world_state):
        """Test environment updates merge with existing properties."""
        world_state.environment = {
            "existing_prop": "value",
            "weather": "sunny",
        }

        environment_changes = {"weather": "cloudy", "new_prop": "new_value"}
        world_state.update_environment(environment_changes, "Update")

        assert world_state.environment["existing_prop"] == "value"  # Preserved
        assert world_state.environment["weather"] == "cloudy"  # Updated
        assert world_state.environment["new_prop"] == "new_value"  # Added

    # ==================== Spatial Indexing Tests ====================

    def test_get_spatial_grid_key(self, world_state):
        """Test spatial grid key calculation."""
        coords = Coordinates(150.5, 250.7, 0)

        grid_key = world_state._get_spatial_grid_key(coords)

        # With grid size 100.0: x=150.5 -> grid_x=1, y=250.7 -> grid_y=2
        assert grid_key == "1,2"

    def test_get_spatial_grid_key_negative_coordinates(self, world_state):
        """Test spatial grid key for negative coordinates."""
        coords = Coordinates(-150.5, -250.7, 0)

        grid_key = world_state._get_spatial_grid_key(coords)

        # With grid size 100.0: x=-150.5 -> grid_x=-2, y=-250.7 -> grid_y=-3
        assert grid_key == "-2,-3"

    def test_add_to_spatial_index(self, world_state):
        """Test adding entity to spatial index."""
        coords = Coordinates(50, 50, 0)
        entity_id = "test-entity"

        world_state._add_to_spatial_index(entity_id, coords)

        grid_key = world_state._get_spatial_grid_key(coords)
        assert grid_key in world_state.spatial_index
        assert entity_id in world_state.spatial_index[grid_key]

    def test_remove_from_spatial_index(self, world_state):
        """Test removing entity from spatial index."""
        coords = Coordinates(50, 50, 0)
        entity_id = "test-entity"

        # First add it
        world_state._add_to_spatial_index(entity_id, coords)
        grid_key = world_state._get_spatial_grid_key(coords)
        assert entity_id in world_state.spatial_index[grid_key]

        # Then remove it
        world_state._remove_from_spatial_index(entity_id, coords)

        # Grid cell should be removed when empty
        assert grid_key not in world_state.spatial_index

    def test_remove_from_spatial_index_nonexistent(self, world_state):
        """Test removing non-existent entity from spatial index."""
        coords = Coordinates(50, 50, 0)

        # Should not raise exception
        world_state._remove_from_spatial_index("nonexistent", coords)

    def test_get_entities_from_spatial_index(self, world_state):
        """Test getting candidate entities from spatial index."""
        # Add entities in different grid cells
        world_state._add_to_spatial_index(
            "entity1", Coordinates(50, 50, 0)
        )  # Grid 0,0
        world_state._add_to_spatial_index(
            "entity2", Coordinates(150, 150, 0)
        )  # Grid 1,1
        world_state._add_to_spatial_index(
            "entity3", Coordinates(250, 250, 0)
        )  # Grid 2,2

        # Query center at (100, 100) with radius 100 should cover grids 0,0 to 2,2
        center = Coordinates(100, 100, 0)
        candidate_ids = world_state._get_entities_from_spatial_index(
            center, radius=100.0
        )

        # Should include entities from multiple grid cells
        assert "entity1" in candidate_ids
        assert "entity2" in candidate_ids
        # entity3 might or might not be included depending on exact grid coverage

    # ==================== Utility Operations Tests ====================

    def test_create_snapshot(self, world_state, sample_entity_data):
        """Test creating world state snapshot."""
        world_state.add_entity(**sample_entity_data)
        world_state.update_environment({"weather": "sunny"}, "Setup")
        world_state.clear_domain_events()

        snapshot = world_state.create_snapshot("Testing snapshot")

        assert snapshot["id"] == world_state.id
        assert snapshot["name"] == world_state.name
        assert snapshot["description"] == world_state.description
        assert snapshot["status"] == world_state.status.value
        assert snapshot["entity_count"] == 1
        assert sample_entity_data["entity_id"] in snapshot["entities"]
        assert snapshot["environment"]["weather"] == "sunny"
        assert "created_at" in snapshot
        assert "updated_at" in snapshot
        assert "version" in snapshot

        # Check domain event was raised
        events = world_state.get_domain_events()
        snapshot_event = next(
            (e for e in events if e.change_type.value == "state_snapshot"),
            None,
        )
        assert snapshot_event is not None

    def test_reset_state_preserve_entities(
        self, world_state, sample_entity_data
    ):
        """Test resetting state while preserving entities."""
        world_state.add_entity(**sample_entity_data)
        world_state.update_environment({"weather": "sunny"}, "Setup")
        initial_version = world_state.version
        world_state.clear_domain_events()

        world_state.reset_state("Testing reset", preserve_entities=True)

        assert (
            world_state.status == WorldStatus.ACTIVE
        )  # Should be reactivated
        assert len(world_state.entities) == 1  # Entities preserved
        assert len(world_state.environment) == 0  # Environment cleared
        assert (
            world_state.version == initial_version + 2
        )  # +1 for reset, +1 for reactivation

        # Check domain event was raised
        events = world_state.get_domain_events()
        reset_event = next(
            (e for e in events if e.change_type.value == "state_reset"), None
        )
        assert reset_event is not None

    def test_reset_state_clear_entities(self, world_state, sample_entity_data):
        """Test resetting state and clearing entities."""
        world_state.add_entity(**sample_entity_data)
        world_state.update_environment({"weather": "sunny"}, "Setup")
        world_state.clear_domain_events()

        world_state.reset_state("Testing full reset", preserve_entities=False)

        assert world_state.status == WorldStatus.ACTIVE
        assert len(world_state.entities) == 0  # Entities cleared
        assert len(world_state.environment) == 0  # Environment cleared
        assert len(world_state.spatial_index) == 0  # Spatial index cleared

    def test_get_statistics(self, world_state):
        """Test getting world state statistics."""
        # Add various entities
        coords = Coordinates(0, 0, 0)
        world_state.add_entity("char1", EntityType.CHARACTER, "Char 1", coords)
        world_state.add_entity("char2", EntityType.CHARACTER, "Char 2", coords)
        world_state.add_entity("obj1", EntityType.OBJECT, "Obj 1", coords)
        world_state.update_environment(
            {"prop1": "value1", "prop2": "value2"}, "Setup"
        )

        stats = world_state.get_statistics()

        assert stats["id"] == world_state.id
        assert stats["name"] == world_state.name
        assert stats["status"] == WorldStatus.ACTIVE.value
        assert stats["entity_count"] == 3
        assert stats["entity_types"]["character"] == 2
        assert stats["entity_types"]["object"] == 1
        assert stats["environment_properties"] == 2
        assert "world_time" in stats
        assert "created_at" in stats
        assert "updated_at" in stats
        assert "version" in stats
        assert "spatial_grid_cells" in stats

    # ==================== Domain Events Tests ====================

    def test_domain_events_generation(self, world_state, sample_entity_data):
        """Test that domain events are properly generated."""
        # Clear any initialization events
        world_state.clear_domain_events()

        # Perform various operations
        world_state.add_entity(**sample_entity_data)
        world_state.pause()
        world_state.activate()

        events = world_state.get_domain_events()
        assert len(events) >= 3  # At least add, pause, activate events

        # Check that events have proper correlation
        for event in events:
            assert event.correlation_id == world_state.id
            assert event.source == "world_context"

    def test_domain_events_clear(self, world_state):
        """Test clearing domain events."""
        world_state.pause()
        assert len(world_state.get_domain_events()) > 0

        world_state.clear_domain_events()
        assert len(world_state.get_domain_events()) == 0

    def test_has_domain_events(self, world_state):
        """Test checking for pending domain events."""
        world_state.clear_domain_events()
        assert not world_state.has_domain_events()

        world_state.pause()
        assert world_state.has_domain_events()

    # ==================== Edge Cases and Error Conditions ====================

    def test_entity_operations_empty_spatial_index(self, world_state):
        """Test entity operations work with empty spatial index."""
        coords = Coordinates(0, 0, 0)

        # Should not raise exceptions
        entities = world_state.get_entities_in_area(coords, 10.0)
        assert len(entities) == 0

        entities = world_state.get_entities_at_coordinates(coords, 0.0)
        assert len(entities) == 0

    def test_large_coordinate_values(self, world_state):
        """Test handling of large coordinate values."""
        large_coords = Coordinates(x=1e9, y=1e9, z=1e9)

        # Should not raise validation errors
        world_state.add_entity(
            "large_entity", EntityType.OBJECT, "Large", large_coords
        )

        entity = world_state.get_entity("large_entity")
        assert entity.coordinates == large_coords

    def test_boundary_spatial_grid(self, world_state):
        """Test spatial grid boundary conditions."""
        # Test coordinates exactly on grid boundaries
        boundary_coords = Coordinates(100.0, 200.0, 0)  # Exactly on grid lines

        grid_key = world_state._get_spatial_grid_key(boundary_coords)
        assert grid_key == "1,2"  # Should consistently assign to one grid

    def test_concurrent_entity_modifications(
        self, world_state, sample_entity_data
    ):
        """Test entity modifications update timestamps correctly."""
        world_state.add_entity(**sample_entity_data)
        entity = world_state.get_entity(sample_entity_data["entity_id"])
        initial_updated_at = entity.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.001)

        world_state.update_entity(
            sample_entity_data["entity_id"], properties={"test": "value"}
        )

        updated_entity = world_state.get_entity(
            sample_entity_data["entity_id"]
        )
        assert updated_entity.updated_at > initial_updated_at

    def test_entity_id_consistency(self, world_state):
        """Test entity ID consistency in aggregate."""
        coords = Coordinates(0, 0, 0)
        world_state.add_entity("test-id", EntityType.CHARACTER, "Test", coords)

        # Entity should be retrievable by the same ID
        entity = world_state.get_entity("test-id")
        assert entity.id == "test-id"

        # Entity should be in entities dict with same ID
        assert "test-id" in world_state.entities
        assert world_state.entities["test-id"].id == "test-id"

    def test_world_state_version_consistency(self, world_state):
        """Test version increments consistently across operations."""
        initial_version = world_state.version
        coords = Coordinates(0, 0, 0)

        # Each state-changing operation should increment version
        world_state.add_entity("entity1", EntityType.CHARACTER, "Test", coords)
        assert world_state.version == initial_version + 1

        world_state.pause()
        assert world_state.version == initial_version + 2

        world_state.activate()
        assert world_state.version == initial_version + 3

    # ==================== Integration-like Tests ====================

    def test_complete_entity_lifecycle(self, world_state):
        """Test complete entity lifecycle from creation to removal."""
        coords = Coordinates(10, 20, 0)
        entity_id = "lifecycle-entity"

        # Create entity
        entity = world_state.add_entity(
            entity_id,
            EntityType.CHARACTER,
            "Lifecycle Test",
            coords,
            properties={"health": 100},
            metadata={"test": True},
        )
        assert entity.id == entity_id

        # Update entity properties
        success = world_state.update_entity(
            entity_id, properties={"health": 150, "mana": 50}
        )
        assert success
        updated_entity = world_state.get_entity(entity_id)
        assert updated_entity.properties["health"] == 150
        assert updated_entity.properties["mana"] == 50

        # Move entity
        new_coords = Coordinates(30, 40, 5)
        success = world_state.move_entity(entity_id, new_coords)
        assert success
        moved_entity = world_state.get_entity(entity_id)
        assert moved_entity.coordinates == new_coords

        # Remove entity
        removed_entity = world_state.remove_entity(entity_id, "Test cleanup")
        assert removed_entity.id == entity_id
        assert world_state.get_entity(entity_id) is None

    def test_spatial_query_integration(self, world_state):
        """Test spatial queries work correctly with entity management."""
        center = Coordinates(0, 0, 0)

        # Add entities at various distances
        world_state.add_entity(
            "close1", EntityType.CHARACTER, "Close 1", Coordinates(1, 1, 0)
        )
        world_state.add_entity(
            "close2", EntityType.OBJECT, "Close 2", Coordinates(2, 2, 0)
        )
        world_state.add_entity(
            "far1", EntityType.CHARACTER, "Far 1", Coordinates(20, 20, 0)
        )

        # Query nearby entities
        nearby_entities = world_state.get_entities_in_area(center, radius=5.0)
        nearby_ids = [entity.id for entity in nearby_entities]

        assert "close1" in nearby_ids
        assert "close2" in nearby_ids
        assert "far1" not in nearby_ids

        # Move a far entity closer
        world_state.move_entity("far1", Coordinates(3, 3, 0))

        # Query again
        nearby_entities_after_move = world_state.get_entities_in_area(
            center, radius=5.0
        )
        nearby_ids_after_move = [
            entity.id for entity in nearby_entities_after_move
        ]

        assert "far1" in nearby_ids_after_move
        assert len(nearby_ids_after_move) == 3

    def test_environment_and_time_integration(self, world_state):
        """Test environment updates and time advancement work together."""
        # Set initial environment
        world_state.update_environment(
            {"weather": "sunny", "temperature": 25}, "Day setup"
        )

        # Advance time
        new_time = world_state.world_time + timedelta(hours=6)
        world_state.advance_time(new_time, "Evening transition")

        # Update environment for evening
        world_state.update_environment(
            {"weather": "cloudy", "temperature": 18}, "Evening weather"
        )

        assert world_state.environment["weather"] == "cloudy"
        assert world_state.environment["temperature"] == 18
        assert world_state.world_time == new_time

        # Check all changes generated events
        events = world_state.get_domain_events()
        env_events = [
            e for e in events if e.change_type.value == "environment_changed"
        ]
        time_events = [
            e for e in events if e.change_type.value == "time_advanced"
        ]

        assert len(env_events) >= 2  # Initial and evening updates
        assert len(time_events) >= 1  # Time advancement
