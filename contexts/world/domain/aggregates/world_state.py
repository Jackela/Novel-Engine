#!/usr/bin/env python3
"""
WorldState Aggregate Root

This module contains the WorldState aggregate root, which serves as the consistency
boundary for all world-related operations. It encapsulates business logic and
ensures invariants are maintained across the entire world state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..entities.entity import Entity
from ..events.world_events import WorldStateChanged
from ..value_objects.coordinates import Coordinates


class WorldStatus(Enum):
    """Status of the world state."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


class EntityType(Enum):
    """Types of entities that can exist in the world."""

    CHARACTER = "character"
    OBJECT = "object"
    LOCATION = "location"
    ENVIRONMENT = "environment"
    ABSTRACT = "abstract"


@dataclass
class WorldEntity:
    """
    Represents an entity within the world state.

    This is a lightweight wrapper around entity data that exists within
    the world state aggregate. It maintains the relationship between
    entities and their world coordinates.
    """

    id: str
    entity_type: EntityType
    name: str
    coordinates: Coordinates
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_properties(self, **properties) -> None:
        """Update entity properties and timestamp."""
        self.properties.update(properties)
        self.updated_at = datetime.now()

    def move_to(self, new_coordinates: Coordinates) -> Coordinates:
        """Move entity to new coordinates and return previous coordinates."""
        previous_coordinates = self.coordinates
        self.coordinates = new_coordinates
        self.updated_at = datetime.now()
        return previous_coordinates

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "coordinates": self.coordinates.to_dict(),
            "properties": self.properties,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldEntity":
        """Create WorldEntity from dictionary representation."""
        return cls(
            id=data["id"],
            entity_type=EntityType(data["entity_type"]),
            name=data["name"],
            coordinates=Coordinates.from_dict(data["coordinates"]),
            properties=data.get("properties", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class WorldState(Entity):
    """
    WorldState Aggregate Root

    This is the main aggregate root for the World context, responsible for
    maintaining consistency across all world-related data and operations.
    It serves as the single entry point for all world state modifications
    and enforces business rules and invariants.

    As an aggregate root, it:
    - Maintains consistency boundaries
    - Handles all business logic related to world state
    - Raises domain events for significant changes
    - Provides transactional consistency

    Attributes:
        name: Human-readable name for this world state
        description: Optional description of the world
        status: Current status of the world
        world_time: Current time within the world (game time)
        entities: Dictionary of entities within the world, keyed by ID
        environment: Environmental properties and settings
        spatial_index: Spatial indexing for efficient location queries
        metadata: Additional metadata for the world state
    """

    name: str = ""
    description: Optional[str] = None
    status: WorldStatus = WorldStatus.INITIALIZING
    world_time: datetime = field(default_factory=datetime.now)
    entities: Dict[str, WorldEntity] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    spatial_index: Dict[str, List[str]] = field(
        default_factory=dict
    )  # Grid-based spatial index
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Configuration
    max_entities: int = 10000
    spatial_grid_size: float = 100.0  # Size of each spatial grid cell

    def __post_init__(self) -> None:
        """Initialize world state with validation."""
        # Auto-generate name if empty BEFORE validation
        if not self.name:
            self.name = f"World_{self.id[:8]}"

        super().__post_init__()

        # Initialize spatial index if empty
        if not self.spatial_index:
            self.spatial_index = {}

        # Set status to active if initializing
        if self.status == WorldStatus.INITIALIZING:
            self.activate()

    def _validate_business_rules(self) -> List[str]:
        """Validate world-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("World name cannot be empty")

        if len(self.entities) > self.max_entities:
            errors.append(
                f"World cannot contain more than {self.max_entities} entities"
            )

        # Validate entity consistency
        for entity_id, entity in self.entities.items():
            if entity.id != entity_id:
                errors.append(
                    f"Entity ID mismatch: {entity.id} != {entity_id}"
                )

        # Validate world time
        if self.world_time > datetime.now():
            # Allow future time for simulation purposes, but warn about far future
            time_diff = (self.world_time - datetime.now()).total_seconds()
            if time_diff > 86400 * 365:  # More than a year in the future
                errors.append("World time is more than a year in the future")

        return errors

    def activate(self) -> None:
        """Activate the world state."""
        if self.status != WorldStatus.ACTIVE:
            previous_status = self.status
            self.status = WorldStatus.ACTIVE
            self.touch()

            # Raise domain event
            self.raise_domain_event(
                WorldStateChanged.entity_updated(
                    entity_id=self.id,
                    entity_type="WorldState",
                    previous_state={"status": previous_status.value},
                    new_state={"status": self.status.value},
                    reason="World state activated",
                )
            )

    def pause(self) -> None:
        """Pause the world state."""
        if self.status == WorldStatus.ACTIVE:
            previous_status = self.status
            self.status = WorldStatus.PAUSED
            self.touch()

            # Raise domain event
            self.raise_domain_event(
                WorldStateChanged.entity_updated(
                    entity_id=self.id,
                    entity_type="WorldState",
                    previous_state={"status": previous_status.value},
                    new_state={"status": self.status.value},
                    reason="World state paused",
                )
            )

    def archive(self) -> None:
        """Archive the world state."""
        previous_status = self.status
        self.status = WorldStatus.ARCHIVED
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.entity_updated(
                entity_id=self.id,
                entity_type="WorldState",
                previous_state={"status": previous_status.value},
                new_state={"status": self.status.value},
                reason="World state archived",
            )
        )

    def add_entity(
        self,
        entity_id: str,
        entity_type: EntityType,
        name: str,
        coordinates: Coordinates,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorldEntity:
        """
        Add a new entity to the world state.

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of the entity
            name: Human-readable name for the entity
            coordinates: Position of the entity in the world
            properties: Optional properties for the entity
            metadata: Optional metadata for the entity

        Returns:
            The created WorldEntity

        Raises:
            ValueError: If entity already exists or validation fails
        """
        if entity_id in self.entities:
            raise ValueError(
                f"Entity with ID {entity_id} already exists in world"
            )

        if len(self.entities) >= self.max_entities:
            raise ValueError(
                f"World has reached maximum entity limit of {self.max_entities}"
            )

        # Create the entity
        entity = WorldEntity(
            id=entity_id,
            entity_type=entity_type,
            name=name,
            coordinates=coordinates,
            properties=properties or {},
            metadata=metadata or {},
        )

        # Add to entities dict
        self.entities[entity_id] = entity

        # Update spatial index
        self._add_to_spatial_index(entity_id, coordinates)

        # Update world state
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.entity_added(
                entity_id=entity_id,
                entity_type=entity_type.value,
                entity_state=entity.to_dict(),
                reason=f"Added {entity_type.value} '{name}' to world",
            )
        )

        return entity

    def remove_entity(
        self, entity_id: str, reason: Optional[str] = None
    ) -> Optional[WorldEntity]:
        """
        Remove an entity from the world state.

        Args:
            entity_id: ID of the entity to remove
            reason: Optional reason for removal

        Returns:
            The removed WorldEntity if it existed, None otherwise
        """
        if entity_id not in self.entities:
            return None

        entity = self.entities[entity_id]
        entity_state = entity.to_dict()

        # Remove from entities dict
        del self.entities[entity_id]

        # Remove from spatial index
        self._remove_from_spatial_index(entity_id, entity.coordinates)

        # Update world state
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.entity_removed(
                entity_id=entity_id,
                entity_type=entity.entity_type.value,
                previous_state=entity_state,
                reason=reason
                or f"Removed {entity.entity_type.value} '{entity.name}' from world",
            )
        )

        return entity

    def move_entity(
        self,
        entity_id: str,
        new_coordinates: Coordinates,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Move an entity to new coordinates.

        Args:
            entity_id: ID of the entity to move
            new_coordinates: New position for the entity
            reason: Optional reason for the move

        Returns:
            True if entity was moved, False if entity not found
        """
        if entity_id not in self.entities:
            return False

        entity = self.entities[entity_id]
        previous_coordinates = entity.move_to(new_coordinates)

        # Update spatial index
        self._remove_from_spatial_index(entity_id, previous_coordinates)
        self._add_to_spatial_index(entity_id, new_coordinates)

        # Update world state
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.entity_moved(
                entity_id=entity_id,
                entity_type=entity.entity_type.value,
                previous_position=previous_coordinates.to_dict(),
                new_position=new_coordinates.to_dict(),
                reason=reason
                or f"Moved {entity.entity_type.value} '{entity.name}'",
            )
        )

        return True

    def update_entity(
        self,
        entity_id: str,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Update an entity's properties or metadata.

        Args:
            entity_id: ID of the entity to update
            properties: Optional properties to update
            metadata: Optional metadata to update
            reason: Optional reason for the update

        Returns:
            True if entity was updated, False if entity not found
        """
        if entity_id not in self.entities:
            return False

        entity = self.entities[entity_id]
        previous_state = {
            "properties": entity.properties.copy(),
            "metadata": entity.metadata.copy(),
        }

        # Update properties and metadata
        if properties:
            entity.properties.update(properties)
        if metadata:
            entity.metadata.update(metadata)

        entity.updated_at = datetime.now()

        # Update world state
        self.touch()

        # Determine what changed
        changed_fields = set()
        if properties:
            changed_fields.add("properties")
        if metadata:
            changed_fields.add("metadata")

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.entity_updated(
                entity_id=entity_id,
                entity_type=entity.entity_type.value,
                previous_state=previous_state,
                new_state={
                    "properties": entity.properties,
                    "metadata": entity.metadata,
                },
                changed_fields=changed_fields,
                reason=reason
                or f"Updated {entity.entity_type.value} '{entity.name}'",
            )
        )

        return True

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)

    def get_entities_by_type(
        self, entity_type: EntityType
    ) -> List[WorldEntity]:
        """Get all entities of a specific type."""
        return [
            entity
            for entity in self.entities.values()
            if entity.entity_type == entity_type
        ]

    def get_entities_in_area(
        self,
        center: Coordinates,
        radius: float,
        entity_types: Optional[List[EntityType]] = None,
    ) -> List[WorldEntity]:
        """
        Get all entities within a specified area.

        Args:
            center: Center coordinates of the search area
            radius: Search radius
            entity_types: Optional filter for specific entity types

        Returns:
            List of entities within the area
        """
        matching_entities = []

        # Get candidate entities from spatial index
        candidate_entity_ids = self._get_entities_from_spatial_index(
            center, radius
        )

        for entity_id in candidate_entity_ids:
            entity = self.entities.get(entity_id)
            if not entity:
                continue

            # Check distance
            if entity.coordinates.distance_to(center) <= radius:
                # Apply type filter if specified
                if entity_types is None or entity.entity_type in entity_types:
                    matching_entities.append(entity)

        return matching_entities

    def get_entities_at_coordinates(
        self, coordinates: Coordinates, tolerance: float = 0.0
    ) -> List[WorldEntity]:
        """
        Get all entities at specific coordinates (with tolerance).

        Args:
            coordinates: Target coordinates
            tolerance: Distance tolerance for matching

        Returns:
            List of entities at the coordinates
        """
        return self.get_entities_in_area(coordinates, tolerance)

    def advance_time(
        self, new_time: datetime, reason: Optional[str] = None
    ) -> None:
        """
        Advance the world time.

        Args:
            new_time: New world time
            reason: Optional reason for time advancement
        """
        if new_time <= self.world_time:
            raise ValueError("New time must be after current world time")

        previous_time = self.world_time
        self.world_time = new_time
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.time_advanced(
                previous_time=previous_time,
                new_time=new_time,
                reason=reason or "World time advanced",
            )
        )

    def update_environment(
        self, environment_changes: Dict[str, Any], reason: Optional[str] = None
    ) -> None:
        """
        Update environmental properties.

        Args:
            environment_changes: Dictionary of environment changes
            reason: Optional reason for the change
        """
        self.environment.copy()
        self.environment.update(environment_changes)
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.environment_changed(
                environment_changes=environment_changes,
                reason=reason or "Environment updated",
            )
        )

    def create_snapshot(self, reason: str) -> Dict[str, Any]:
        """
        Create a complete snapshot of the world state.

        Args:
            reason: Reason for creating the snapshot

        Returns:
            Dictionary containing complete world state data
        """
        snapshot_data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "world_time": self.world_time.isoformat(),
            "entities": {
                eid: entity.to_dict() for eid, entity in self.entities.items()
            },
            "environment": self.environment.copy(),
            "metadata": self.metadata.copy(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "entity_count": len(self.entities),
        }

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.state_snapshot(
                snapshot_data=snapshot_data, reason=reason
            )
        )

        return snapshot_data

    def reset_state(
        self, reason: str, preserve_entities: bool = False
    ) -> None:
        """
        Reset the world state to initial conditions.

        Args:
            reason: Reason for resetting the state
            preserve_entities: Whether to preserve existing entities
        """
        previous_state = self.create_snapshot("Pre-reset snapshot")

        if not preserve_entities:
            self.entities.clear()
            self.spatial_index.clear()

        self.environment.clear()
        self.world_time = datetime.now()
        self.status = WorldStatus.INITIALIZING
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.state_reset(
                reason=reason, previous_state=previous_state
            )
        )

        # Reactivate if appropriate
        if self.status == WorldStatus.INITIALIZING:
            self.activate()

    def get_statistics(self) -> Dict[str, Any]:
        """Get world state statistics."""
        entity_type_counts = {}
        for entity in self.entities.values():
            entity_type = entity.entity_type.value
            entity_type_counts[entity_type] = (
                entity_type_counts.get(entity_type, 0) + 1
            )

        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "entity_count": len(self.entities),
            "entity_types": entity_type_counts,
            "environment_properties": len(self.environment),
            "world_time": self.world_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "spatial_grid_cells": len(self.spatial_index),
        }

    # Spatial Index Management

    def _get_spatial_grid_key(self, coordinates: Coordinates) -> str:
        """Get spatial grid key for coordinates."""
        grid_x = int(coordinates.x // self.spatial_grid_size)
        grid_y = int(coordinates.y // self.spatial_grid_size)
        return f"{grid_x},{grid_y}"

    def _add_to_spatial_index(
        self, entity_id: str, coordinates: Coordinates
    ) -> None:
        """Add entity to spatial index."""
        grid_key = self._get_spatial_grid_key(coordinates)
        if grid_key not in self.spatial_index:
            self.spatial_index[grid_key] = []
        self.spatial_index[grid_key].append(entity_id)

    def _remove_from_spatial_index(
        self, entity_id: str, coordinates: Coordinates
    ) -> None:
        """Remove entity from spatial index."""
        grid_key = self._get_spatial_grid_key(coordinates)
        if grid_key in self.spatial_index:
            try:
                self.spatial_index[grid_key].remove(entity_id)
                if not self.spatial_index[grid_key]:
                    del self.spatial_index[grid_key]
            except ValueError:
                pass  # Entity wasn't in the grid cell

    def _get_entities_from_spatial_index(
        self, center: Coordinates, radius: float
    ) -> Set[str]:
        """Get candidate entity IDs from spatial index within radius."""
        candidate_ids = set()

        # Calculate grid cells to check
        min_x = int((center.x - radius) // self.spatial_grid_size)
        max_x = int((center.x + radius) // self.spatial_grid_size)
        min_y = int((center.y - radius) // self.spatial_grid_size)
        max_y = int((center.y + radius) // self.spatial_grid_size)

        for grid_x in range(min_x, max_x + 1):
            for grid_y in range(min_y, max_y + 1):
                grid_key = f"{grid_x},{grid_y}"
                if grid_key in self.spatial_index:
                    candidate_ids.update(self.spatial_index[grid_key])

        return candidate_ids

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert world-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "world_time": self.world_time.isoformat(),
            "entities": {
                eid: entity.to_dict() for eid, entity in self.entities.items()
            },
            "environment": self.environment,
            "metadata": self.metadata,
            "entity_count": len(self.entities),
            "spatial_grid_size": self.spatial_grid_size,
            "max_entities": self.max_entities,
        }
