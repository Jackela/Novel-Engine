#!/usr/bin/env python3
"""
World CQRS Read Model

Denormalized read model optimized for fast query performance.
This model is updated by the WorldProjector service based on
WorldStateChanged domain events to maintain eventual consistency.

Design Principles:
- Aggressive denormalization for query performance
- Spatial indexing for geographic queries
- Pre-computed aggregations to minimize runtime calculations
- Eventually consistent with the write model
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core_platform.persistence.models import BaseModel
from sqlalchemy import (
    ARRAY,
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID


@dataclass
class EntitySummary:
    """Lightweight entity summary for read model optimization."""

    id: str
    entity_type: str
    name: str
    x: float
    y: float
    z: float
    properties_summary: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "name": self.name,
            "coordinates": {"x": self.x, "y": self.y, "z": self.z},
            "properties_summary": self.properties_summary,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_world_entity(cls, world_entity: Dict[str, Any]) -> "EntitySummary":
        """Create EntitySummary from WorldEntity dict."""
        coords = world_entity["coordinates"]

        # Extract key properties for summary (first 3 properties to avoid bloat)
        props_summary = {}
        if world_entity.get("properties"):
            sorted_props = sorted(world_entity["properties"].items())
            props_summary = dict(sorted_props[:3])

        return cls(
            id=world_entity["id"],
            entity_type=world_entity["entity_type"],
            name=world_entity["name"],
            x=coords["x"],
            y=coords["y"],
            z=coords["z"],
            properties_summary=props_summary,
            last_updated=datetime.fromisoformat(world_entity["updated_at"]),
        )


class WorldSliceReadModel(BaseModel):
    """
    Denormalized read model for world state queries.

    This table is optimized for the GetWorldSlice query and other
    common read patterns. It maintains a flattened, indexed view
    of world state data for maximum query performance.

    Key optimizations:
    - Spatial indexing on entity coordinates
    - JSON columns for flexible querying
    - Pre-computed entity counts and summaries
    - Optimized for geographic range queries
    """

    __tablename__ = "world_slice_read_model"

    # World identification
    world_state_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    world_name = Column(String(255), nullable=False, index=True)
    world_description = Column(Text, nullable=True)

    # World status and timing
    status = Column(String(50), nullable=False, index=True)
    world_time = Column(DateTime(timezone=True), nullable=False, index=True)
    last_event_timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    # Version tracking for consistency
    world_version = Column(Integer, nullable=False, default=1, index=True)
    projection_version = Column(Integer, nullable=False, default=1)

    # Pre-computed entity statistics
    total_entities = Column(Integer, nullable=False, default=0)
    entity_type_counts = Column(
        JSON, nullable=False, default=dict
    )  # {"character": 5, "object": 10}

    # Spatial bounds for quick area queries
    min_x = Column(Float, nullable=True, index=True)
    max_x = Column(Float, nullable=True, index=True)
    min_y = Column(Float, nullable=True, index=True)
    max_y = Column(Float, nullable=True, index=True)
    min_z = Column(Float, nullable=True, index=True)
    max_z = Column(Float, nullable=True, index=True)

    # Denormalized entity data for fast access
    entities_by_type = Column(
        JSON, nullable=False, default=dict
    )  # Pre-grouped by entity type
    entities_by_location = Column(
        JSON, nullable=False, default=dict
    )  # Spatial grid index
    all_entities = Column(JSON, nullable=False, default=dict)  # Complete entity data

    # Environment and world properties
    environment_summary = Column(JSON, nullable=False, default=dict)
    world_metadata = Column(JSON, nullable=False, default=dict)

    # Query optimization fields
    active_entity_ids = Column(
        ARRAY(String), nullable=False, default=list
    )  # For fast ID lookups
    searchable_content = Column(Text, nullable=True, index=True)  # For text search

    # Performance indexes
    __table_args__ = (
        # Core identification indexes
        Index("idx_world_slice_world_id", "world_state_id"),
        Index("idx_world_slice_name_status", "world_name", "status"),
        # Temporal indexes
        Index("idx_world_slice_world_time", "world_time"),
        Index("idx_world_slice_last_event", "last_event_timestamp"),
        # Spatial indexes for geographic queries
        Index("idx_world_slice_spatial_x", "min_x", "max_x"),
        Index("idx_world_slice_spatial_y", "min_y", "max_y"),
        Index("idx_world_slice_spatial_z", "min_z", "max_z"),
        # Entity count indexes for filtering
        Index("idx_world_slice_entity_count", "total_entities"),
        Index("idx_world_slice_version", "world_version", "projection_version"),
        # Search optimization
        Index("idx_world_slice_search", "searchable_content"),
        # Compound indexes for common query patterns
        Index("idx_world_slice_status_time", "status", "world_time"),
        Index("idx_world_slice_name_entities", "world_name", "total_entities"),
    )

    def get_entities_in_area(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get entities within a circular area around a center point.

        This method performs in-memory filtering on the denormalized data
        for maximum performance. Spatial bounds are pre-filtered at the
        database level for efficiency.

        Args:
            center_x: X coordinate of search center
            center_y: Y coordinate of search center
            radius: Search radius
            entity_types: Optional list of entity types to filter

        Returns:
            List of entities within the specified area
        """
        matching_entities = []

        if not self.all_entities:
            return matching_entities

        radius_squared = radius * radius  # Avoid sqrt in distance calculation

        for entity_id, entity_data in self.all_entities.items():
            try:
                coords = entity_data["coordinates"]
                entity_x, entity_y = coords["x"], coords["y"]

                # Calculate squared distance (faster than sqrt)
                distance_squared = (entity_x - center_x) ** 2 + (
                    entity_y - center_y
                ) ** 2

                if distance_squared <= radius_squared:
                    # Apply entity type filter if specified
                    if (
                        entity_types is None
                        or entity_data["entity_type"] in entity_types
                    ):
                        # Add distance for sorting
                        entity_copy = entity_data.copy()
                        entity_copy["distance"] = distance_squared**0.5
                        matching_entities.append(entity_copy)

            except (KeyError, TypeError, ValueError):
                # Skip malformed entity data
                continue

        # Sort by distance
        matching_entities.sort(key=lambda e: e.get("distance", float("inf")))
        return matching_entities

    def get_entities_by_type(
        self, entity_type: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entities of a specific type using pre-computed type grouping.

        Args:
            entity_type: Type of entities to retrieve
            limit: Optional limit on number of results

        Returns:
            List of entities of the specified type
        """
        if not self.entities_by_type or entity_type not in self.entities_by_type:
            return []

        entities = self.entities_by_type[entity_type]
        if limit:
            return entities[:limit]
        return entities

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific entity by ID using the denormalized data.

        Args:
            entity_id: ID of the entity to retrieve

        Returns:
            Entity data if found, None otherwise
        """
        return self.all_entities.get(entity_id)

    def get_entities_in_bounds(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get entities within rectangular bounds.

        Args:
            min_x: Minimum X coordinate
            max_x: Maximum X coordinate
            min_y: Minimum Y coordinate
            max_y: Maximum Y coordinate
            entity_types: Optional entity type filter

        Returns:
            List of entities within bounds
        """
        matching_entities = []

        if not self.all_entities:
            return matching_entities

        for entity_id, entity_data in self.all_entities.items():
            try:
                coords = entity_data["coordinates"]
                entity_x, entity_y = coords["x"], coords["y"]

                if min_x <= entity_x <= max_x and min_y <= entity_y <= max_y:
                    # Apply entity type filter if specified
                    if (
                        entity_types is None
                        or entity_data["entity_type"] in entity_types
                    ):
                        matching_entities.append(entity_data)

            except (KeyError, TypeError, ValueError):
                # Skip malformed entity data
                continue

        return matching_entities

    def get_world_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the world state optimized for dashboard views.

        Returns:
            Dictionary with world summary statistics
        """
        return {
            "world_id": str(self.world_state_id),
            "name": self.world_name,
            "description": self.world_description,
            "status": self.status,
            "world_time": self.world_time.isoformat() if self.world_time else None,
            "total_entities": self.total_entities,
            "entity_types": self.entity_type_counts,
            "spatial_bounds": (
                {
                    "min_x": self.min_x,
                    "max_x": self.max_x,
                    "min_y": self.min_y,
                    "max_y": self.max_y,
                    "min_z": self.min_z,
                    "max_z": self.max_z,
                }
                if self.min_x is not None
                else None
            ),
            "environment_summary": self.environment_summary,
            "last_updated": (
                self.last_event_timestamp.isoformat()
                if self.last_event_timestamp
                else None
            ),
            "version": {
                "world_version": self.world_version,
                "projection_version": self.projection_version,
            },
        }

    @classmethod
    def create_from_world_state(
        cls, world_state_data: Dict[str, Any]
    ) -> "WorldSliceReadModel":
        """
        Create a new read model from world state domain aggregate data.

        Args:
            world_state_data: Dictionary representation of WorldState aggregate

        Returns:
            New WorldSliceReadModel instance
        """
        # Extract basic world information
        world_id = world_state_data["id"]
        entities = world_state_data.get("entities", {})

        # Calculate spatial bounds
        min_x = max_x = min_y = max_y = min_z = max_z = None
        if entities:
            coordinates = []
            for entity_data in entities.values():
                if "coordinates" in entity_data:
                    coords = entity_data["coordinates"]
                    coordinates.append((coords["x"], coords["y"], coords["z"]))

            if coordinates:
                min_x = min(c[0] for c in coordinates)
                max_x = max(c[0] for c in coordinates)
                min_y = min(c[1] for c in coordinates)
                max_y = max(c[1] for c in coordinates)
                min_z = min(c[2] for c in coordinates)
                max_z = max(c[2] for c in coordinates)

        # Group entities by type for optimized queries
        entities_by_type = {}
        entity_type_counts = {}
        active_entity_ids = []

        for entity_id, entity_data in entities.items():
            entity_type = entity_data.get("entity_type", "unknown")

            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
                entity_type_counts[entity_type] = 0

            entities_by_type[entity_type].append(entity_data)
            entity_type_counts[entity_type] += 1
            active_entity_ids.append(entity_id)

        # Create spatial grid index (simplified version)
        entities_by_location = {}
        grid_size = world_state_data.get("spatial_grid_size", 100.0)

        for entity_id, entity_data in entities.items():
            if "coordinates" in entity_data:
                coords = entity_data["coordinates"]
                grid_x = int(coords["x"] // grid_size)
                grid_y = int(coords["y"] // grid_size)
                grid_key = f"{grid_x},{grid_y}"

                if grid_key not in entities_by_location:
                    entities_by_location[grid_key] = []
                entities_by_location[grid_key].append(entity_id)

        # Create searchable content for text search
        searchable_parts = [
            world_state_data.get("name", ""),
            world_state_data.get("description", "") or "",
        ]

        # Add entity names to searchable content
        for entity_data in entities.values():
            searchable_parts.append(entity_data.get("name", ""))

        searchable_content = " ".join(filter(None, searchable_parts))

        # Extract environment summary (first 5 keys to avoid bloat)
        environment_data = world_state_data.get("environment", {})
        environment_summary = (
            dict(list(environment_data.items())[:5]) if environment_data else {}
        )

        return cls(
            world_state_id=uuid.UUID(world_id),
            world_name=world_state_data.get("name", f"World_{world_id[:8]}"),
            world_description=world_state_data.get("description"),
            status=world_state_data.get("status", "active"),
            world_time=(
                datetime.fromisoformat(world_state_data["world_time"])
                if isinstance(world_state_data.get("world_time"), str)
                else world_state_data.get("world_time", datetime.now())
            ),
            world_version=world_state_data.get("version", 1),
            projection_version=1,
            total_entities=len(entities),
            entity_type_counts=entity_type_counts,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            min_z=min_z,
            max_z=max_z,
            entities_by_type=entities_by_type,
            entities_by_location=entities_by_location,
            all_entities=entities,
            environment_summary=environment_summary,
            world_metadata=world_state_data.get("metadata", {}),
            active_entity_ids=active_entity_ids,
            searchable_content=searchable_content[
                :1000
            ],  # Truncate for index efficiency
            last_event_timestamp=datetime.now(),
        )

    def update_from_entity_event(self, event_data: Dict[str, Any]) -> None:
        """
        Update the read model based on an entity-related event.

        This method handles incremental updates to maintain consistency
        with the write model while preserving query performance.

        Args:
            event_data: WorldStateChanged event data
        """
        change_type = event_data.get("change_type")
        entity_id = event_data.get("affected_entity_id")
        entity_type = event_data.get("affected_entity_type")
        new_state = event_data.get("new_state")
        event_data.get("previous_state")

        if not entity_id:
            return

        # Ensure JSON fields are mutable dictionaries
        if not isinstance(self.all_entities, dict):
            self.all_entities = {}
        if not isinstance(self.entities_by_type, dict):
            self.entities_by_type = {}
        if not isinstance(self.entity_type_counts, dict):
            self.entity_type_counts = {}
        if not isinstance(self.active_entity_ids, list):
            self.active_entity_ids = []

        if change_type == "entity_added" and new_state:
            # Add new entity
            self.all_entities[entity_id] = new_state

            # Update type grouping
            if entity_type:
                if entity_type not in self.entities_by_type:
                    self.entities_by_type[entity_type] = []
                    self.entity_type_counts[entity_type] = 0

                self.entities_by_type[entity_type].append(new_state)
                self.entity_type_counts[entity_type] += 1

                if entity_id not in self.active_entity_ids:
                    self.active_entity_ids.append(entity_id)

            # Update entity count
            self.total_entities = len(self.all_entities)

        elif change_type == "entity_removed":
            # Remove entity
            if entity_id in self.all_entities:
                del self.all_entities[entity_id]

                # Update type grouping
                if entity_type and entity_type in self.entities_by_type:
                    # Remove from type list
                    self.entities_by_type[entity_type] = [
                        e
                        for e in self.entities_by_type[entity_type]
                        if e.get("id") != entity_id
                    ]
                    self.entity_type_counts[entity_type] = max(
                        0, self.entity_type_counts[entity_type] - 1
                    )

                # Remove from active IDs
                if entity_id in self.active_entity_ids:
                    self.active_entity_ids.remove(entity_id)

                # Update entity count
                self.total_entities = len(self.all_entities)

        elif change_type in ["entity_updated", "entity_moved"] and new_state:
            # Update existing entity
            self.all_entities[entity_id] = new_state

            # Update type grouping if entity type changed
            if entity_type and entity_type in self.entities_by_type:
                # Find and update in type list
                for i, entity in enumerate(self.entities_by_type[entity_type]):
                    if entity.get("id") == entity_id:
                        self.entities_by_type[entity_type][i] = new_state
                        break

        # Recalculate spatial bounds if entities changed
        if (
            change_type in ["entity_added", "entity_removed", "entity_moved"]
            and self.all_entities
        ):
            coordinates = []
            for entity_data in self.all_entities.values():
                if "coordinates" in entity_data:
                    coords = entity_data["coordinates"]
                    coordinates.append((coords["x"], coords["y"], coords["z"]))

            if coordinates:
                self.min_x = min(c[0] for c in coordinates)
                self.max_x = max(c[0] for c in coordinates)
                self.min_y = min(c[1] for c in coordinates)
                self.max_y = max(c[1] for c in coordinates)
                self.min_z = min(c[2] for c in coordinates)
                self.max_z = max(c[2] for c in coordinates)
            else:
                self.min_x = self.max_x = self.min_y = self.max_y = self.min_z = (
                    self.max_z
                ) = None

        # Update timestamps
        self.last_event_timestamp = datetime.now()
        self.projection_version += 1

    def validate(self) -> List[str]:
        """Validate the read model data."""
        errors = []

        if not self.world_state_id:
            errors.append("World state ID is required")

        if not self.world_name or not self.world_name.strip():
            errors.append("World name cannot be empty")

        if self.total_entities < 0:
            errors.append("Total entities cannot be negative")

        if self.world_version < 1:
            errors.append("World version must be positive")

        if self.projection_version < 1:
            errors.append("Projection version must be positive")

        return errors

    def __repr__(self) -> str:
        return f"<WorldSliceReadModel(world_id={self.world_state_id}, name='{self.world_name}', entities={self.total_entities})>"
