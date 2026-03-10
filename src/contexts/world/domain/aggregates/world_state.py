#!/usr/bin/env python3
"""
WorldState Aggregate Root

This module contains the WorldState aggregate root, which serves as the consistency
boundary for all world-related operations. It encapsulates business logic and
ensures invariants are maintained across the entire world state.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from src.core.result import Err, Ok, Result

from ..entities.entity import Entity
from ..events.world_events import WorldStateChanged
from ..value_objects.coordinates import Coordinates
from ..value_objects.world_calendar import WorldCalendar

if TYPE_CHECKING:
    from src.core.result import SaveError


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

    def update_properties(self, **properties: Any) -> None:
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
        calendar: Current in-game calendar (WorldCalendar value object)
        entities: Dictionary of entities within the world, keyed by ID
        environment: Environmental properties and settings
        spatial_index: Spatial indexing for efficient location queries
        metadata: Additional metadata for the world state
    """

    name: str = ""
    description: Optional[str] = None
    status: WorldStatus = WorldStatus.INITIALIZING
    calendar: WorldCalendar = field(
        default_factory=lambda: WorldCalendar(
            year=1, month=1, day=1, era_name="First Age"
        )
    )
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldState):
            return False
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate world-specific business rules."""
        errors: list[Any] = []
        if not self.name or not self.name.strip():
            errors.append("World name cannot be empty")

        if len(self.entities) > self.max_entities:
            errors.append(
                f"World cannot contain more than {self.max_entities} entities"
            )

        # Validate entity consistency
        for entity_id, entity in self.entities.items():
            if entity.id != entity_id:
                errors.append(f"Entity ID mismatch: {entity.id} != {entity_id}")

        # Calendar validation is handled by WorldCalendar's __post_init__

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
            raise ValueError(f"Entity with ID {entity_id} already exists in world")

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
        self, entity_id: str, new_coordinates: Coordinates, reason: Optional[str] = None
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
                reason=reason or f"Moved {entity.entity_type.value} '{entity.name}'",
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
        changed_fields: set[Any] = set()
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
                reason=reason or f"Updated {entity.entity_type.value} '{entity.name}'",
            )
        )

        return True

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> List[WorldEntity]:
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
        matching_entities: list[Any] = []
        # Get candidate entities from spatial index
        candidate_entity_ids = self._get_entities_from_spatial_index(center, radius)

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
        self, days: int, reason: Optional[str] = None
    ) -> Result["WorldState", ValueError]:
        """
        Advance the world calendar by a specified number of days.

        Args:
            days: Number of days to advance (must be >= 0)
            reason: Optional reason for time advancement

        Returns:
            Result containing the updated WorldState or ValueError

        Raises:
            ValueError: If days is negative (via calendar.advance)
        """
        advance_result = self.calendar.advance(days)
        if advance_result.is_error:
            # Return the error wrapped in the correct Result type
            err = advance_result.error
            if err is None:
                err = ValueError("Calendar advance failed with unknown error")
            return Err(err)

        previous_calendar = self.calendar
        updated_calendar = advance_result.value
        if updated_calendar is None:
            return Err(ValueError("Calendar advance returned None"))
        self.calendar = updated_calendar
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.time_advanced(
                previous_time=previous_calendar.format(),
                new_time=self.calendar.format(),
                reason=reason or f"World time advanced by {days} days",
            )
        )

        return Ok(self)

    @classmethod
    def from_datetime_world_time(
        cls,
        world_id: str,
        name: str,
        dt: datetime,
        era_name: str = "Modern Era",
        **kwargs: Any,
    ) -> "WorldState":
        """
        Create a WorldState from a datetime for migration purposes.

        This class method facilitates migration from the old world_time: datetime
        field to the new calendar: WorldCalendar field.

        Args:
            world_id: Unique identifier for the world
            name: Human-readable name for the world
            dt: Datetime to convert to WorldCalendar
            era_name: Name of the era (default: "Modern Era")
            **kwargs: Additional arguments passed to WorldState constructor

        Returns:
            New WorldState instance with calendar derived from datetime
        """
        calendar = WorldCalendar.from_datetime(dt)
        # Create a new calendar with the specified era_name
        calendar = WorldCalendar(
            year=calendar.year,
            month=calendar.month,
            day=calendar.day,
            era_name=era_name,
            days_per_month=calendar.days_per_month,
            months_per_year=calendar.months_per_year,
        )
        return cls(id=world_id, name=name, calendar=calendar, **kwargs)

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
            "calendar": self.calendar.to_dict(),
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
            WorldStateChanged.state_snapshot(snapshot_data=snapshot_data, reason=reason)
        )

        return snapshot_data

    def reset_state(self, reason: str, preserve_entities: bool = False) -> None:
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
        self.calendar = WorldCalendar(year=1, month=1, day=1, era_name="First Age")
        self.status = WorldStatus.INITIALIZING
        self.touch()

        # Raise domain event
        self.raise_domain_event(
            WorldStateChanged.state_reset(reason=reason, previous_state=previous_state)
        )

        # Reactivate if appropriate
        if self.status == WorldStatus.INITIALIZING:
            self.activate()

    def get_statistics(self) -> Dict[str, Any]:
        """Get world state statistics."""
        entity_type_counts: dict[Any, Any] = {}
        for entity in self.entities.values():
            entity_type = entity.entity_type.value
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "entity_count": len(self.entities),
            "entity_types": entity_type_counts,
            "environment_properties": len(self.environment),
            "calendar": self.calendar.format(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "spatial_grid_cells": len(self.spatial_index),
        }

    def save(self, file_path: Optional[str] = None) -> Result[None, "SaveError"]:
        """
        Save the world state to JSON.

        Serializes the complete world state to a JSON file for persistence.
        Uses the to_dict() method to create a serializable representation.

        Args:
            file_path: Optional file path to save to. If not provided,
                      returns Ok(None) after validating serialization works.

        Returns:
            Result[None, SaveError]: Ok(None) on success, Error on failure.

        Example:
            result = world_state.save("world_backup.json")
            if result.is_ok:
                print("World state saved successfully")
            else:
                print(f"Save failed: {result.error.message}")
        """
        from src.core.result import SaveError

        try:
            # Serialize to JSON to validate it works
            state_dict = self.to_dict()
            json_data = json.dumps(state_dict, indent=2, ensure_ascii=False)

            if file_path:
                # Write to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)

            return Ok(None)

        except (TypeError, ValueError) as e:
            return Err(
                SaveError(
                    message=f"Failed to serialize world state: {e}",
                    entity_type="WorldState",
                    details={"error_type": type(e).__name__},
                )
            )
        except OSError as e:
            return Err(
                SaveError(
                    message=f"Failed to write world state file: {e}",
                    entity_type="WorldState",
                    details={"file_path": file_path, "error_type": type(e).__name__},
                )
            )
        except Exception as e:
            return Err(
                SaveError(
                    message=f"Unexpected error saving world state: {e}",
                    entity_type="WorldState",
                    details={"error_type": type(e).__name__},
                )
            )

    # Spatial Index Management

    def _get_spatial_grid_key(self, coordinates: Coordinates) -> str:
        """Get spatial grid key for coordinates."""
        grid_x = int(coordinates.x // self.spatial_grid_size)
        grid_y = int(coordinates.y // self.spatial_grid_size)
        return f"{grid_x},{grid_y}"

    def _add_to_spatial_index(self, entity_id: str, coordinates: Coordinates) -> None:
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
                return  # Entity wasn't in the grid cell

    def _get_entities_from_spatial_index(
        self, center: Coordinates, radius: float
    ) -> Set[str]:
        """Get candidate entity IDs from spatial index within radius."""
        candidate_ids: set[Any] = set()
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
            "calendar": self.calendar.to_dict(),
            "entities": {
                eid: entity.to_dict() for eid, entity in self.entities.items()
            },
            "environment": self.environment,
            "metadata": self.metadata,
            "entity_count": len(self.entities),
            "spatial_grid_size": self.spatial_grid_size,
            "max_entities": self.max_entities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldState":
        """
        Create a WorldState from dictionary representation.

        Supports backward compatibility with the old world_time field by
        automatically converting it to a WorldCalendar.

        Args:
            data: Dictionary containing world state data

        Returns:
            New WorldState instance

        Raises:
            KeyError: If required keys are missing
            ValueError: If values are invalid
        """
        # Handle calendar field with backward compatibility
        if "calendar" in data:
            calendar = WorldCalendar.from_dict(data["calendar"])
        elif "world_time" in data:
            # Backward compatibility: convert old world_time to calendar
            dt = datetime.fromisoformat(data["world_time"])
            calendar = WorldCalendar.from_datetime(dt)
        else:
            # Default calendar if neither is present
            calendar = WorldCalendar(year=1, month=1, day=1, era_name="First Age")

        # Parse entities
        entities: Dict[str, WorldEntity] = {}
        entities_data = data.get("entities", {})
        for eid, entity_data in entities_data.items():
            entities[eid] = WorldEntity.from_dict(entity_data)

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description"),
            status=WorldStatus(data.get("status", "initializing")),
            calendar=calendar,
            entities=entities,
            environment=data.get("environment", {}),
            spatial_index=data.get("spatial_index", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
            max_entities=data.get("max_entities", 10000),
            spatial_grid_size=data.get("spatial_grid_size", 100.0),
        )
