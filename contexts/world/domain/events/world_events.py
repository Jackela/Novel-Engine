#!/usr/bin/env python3
"""
World Domain Events

This module contains domain events related to world state changes.
These events follow the enterprise event bus patterns established in the codebase
and represent significant business events in the World context.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
from uuid import uuid4

from src.events.event_bus import Event, EventPriority


class WorldChangeType(Enum):
    """Types of world state changes."""

    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"
    ENTITY_MOVED = "entity_moved"
    ENTITY_UPDATED = "entity_updated"
    STATE_SNAPSHOT = "state_snapshot"
    STATE_RESET = "state_reset"
    ENVIRONMENT_CHANGED = "environment_changed"
    TIME_ADVANCED = "time_advanced"


class WorldEventSeverity(Enum):
    """Severity levels for world events."""

    MINOR = "minor"  # Small changes, entity updates
    MODERATE = "moderate"  # Entity additions/removals
    MAJOR = "major"  # Environment changes, time advances
    CRITICAL = "critical"  # State resets, system-wide changes


@dataclass
class WorldStateChanged(Event):
    """
    Domain event representing a change in the world state.

    This event is raised whenever the world state is modified in any way,
    providing comprehensive information about what changed and why.

    Inherits from the enterprise Event class to integrate with the
    existing event bus infrastructure.
    """

    # Override base event fields with world-specific defaults
    event_type: str = field(default="world.state_changed", init=False)
    source: str = field(default="world_context")

    # World-specific event data
    change_type: WorldChangeType = WorldChangeType.ENTITY_UPDATED
    severity: WorldEventSeverity = WorldEventSeverity.MINOR
    affected_entity_id: Optional[str] = None
    affected_entity_type: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = None
    batch_id: Optional[str] = None  # For grouping related changes

    # Additional world context
    world_time: Optional[datetime] = None
    affected_area: Optional[Dict[str, Any]] = None  # Spatial bounds of change
    cascade_effects: Set[str] = field(
        default_factory=set
    )  # IDs of affected entities

    def __post_init__(self):
        """Initialize world state changed event with proper validation."""
        # Set world time if not provided
        if self.world_time is None:
            self.world_time = datetime.now()

        # Set priority based on severity
        priority_mapping = {
            WorldEventSeverity.MINOR: EventPriority.LOW,
            WorldEventSeverity.MODERATE: EventPriority.NORMAL,
            WorldEventSeverity.MAJOR: EventPriority.HIGH,
            WorldEventSeverity.CRITICAL: EventPriority.CRITICAL,
        }
        self.priority = priority_mapping[self.severity]

        # Add world-specific tags
        self.tags.update(
            {
                "context:world",
                f"change_type:{self.change_type.value}",
                f"severity:{self.severity.value}",
            }
        )

        if self.affected_entity_type:
            self.tags.add(f"entity_type:{self.affected_entity_type}")

        # Set event payload with world-specific data
        self.payload.update(
            {
                "change_type": self.change_type.value,
                "severity": self.severity.value,
                "affected_entity_id": self.affected_entity_id,
                "affected_entity_type": self.affected_entity_type,
                "previous_state": self.previous_state,
                "new_state": self.new_state,
                "change_reason": self.change_reason,
                "batch_id": self.batch_id,
                "world_time": self.world_time.isoformat()
                if self.world_time
                else None,
                "affected_area": self.affected_area,
                "cascade_effects": list(self.cascade_effects),
            }
        )

        # Call parent post_init
        super().__post_init__()

        # Additional validation
        self._validate_world_event()

    def _validate_world_event(self) -> None:
        """
        Validate world-specific event data.

        Raises:
            ValueError: If event data is invalid
        """
        errors = []

        if not isinstance(self.change_type, WorldChangeType):
            errors.append("change_type must be a WorldChangeType enum value")

        if not isinstance(self.severity, WorldEventSeverity):
            errors.append("severity must be a WorldEventSeverity enum value")

        # Validate entity-related changes
        if self.change_type in [
            WorldChangeType.ENTITY_ADDED,
            WorldChangeType.ENTITY_REMOVED,
            WorldChangeType.ENTITY_MOVED,
            WorldChangeType.ENTITY_UPDATED,
        ]:
            if not self.affected_entity_id:
                errors.append(
                    "affected_entity_id is required for entity changes"
                )

        # Validate state data consistency
        if self.change_type == WorldChangeType.ENTITY_UPDATED:
            if self.previous_state is None and self.new_state is None:
                errors.append(
                    "Either previous_state or new_state must be provided for updates"
                )

        if errors:
            raise ValueError(
                f"World event validation failed: {'; '.join(errors)}"
            )

    @classmethod
    def entity_added(
        cls,
        entity_id: str,
        entity_type: str,
        entity_state: Dict[str, Any],
        reason: Optional[str] = None,
        batch_id: Optional[str] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when an entity is added to the world.

        Args:
            entity_id: ID of the added entity
            entity_type: Type of the added entity
            entity_state: State of the new entity
            reason: Reason for adding the entity
            batch_id: Optional batch ID for grouped operations
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.ENTITY_ADDED,
            severity=WorldEventSeverity.MODERATE,
            affected_entity_id=entity_id,
            affected_entity_type=entity_type,
            new_state=entity_state,
            change_reason=reason or f"Added {entity_type} to world",
            batch_id=batch_id,
        )

    @classmethod
    def entity_removed(
        cls,
        entity_id: str,
        entity_type: str,
        previous_state: Dict[str, Any],
        reason: Optional[str] = None,
        batch_id: Optional[str] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when an entity is removed from the world.

        Args:
            entity_id: ID of the removed entity
            entity_type: Type of the removed entity
            previous_state: Previous state of the entity
            reason: Reason for removing the entity
            batch_id: Optional batch ID for grouped operations
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.ENTITY_REMOVED,
            severity=WorldEventSeverity.MODERATE,
            affected_entity_id=entity_id,
            affected_entity_type=entity_type,
            previous_state=previous_state,
            change_reason=reason or f"Removed {entity_type} from world",
            batch_id=batch_id,
        )

    @classmethod
    def entity_moved(
        cls,
        entity_id: str,
        entity_type: str,
        previous_position: Dict[str, Any],
        new_position: Dict[str, Any],
        reason: Optional[str] = None,
        batch_id: Optional[str] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when an entity is moved in the world.

        Args:
            entity_id: ID of the moved entity
            entity_type: Type of the moved entity
            previous_position: Previous position data
            new_position: New position data
            reason: Reason for moving the entity
            batch_id: Optional batch ID for grouped operations
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.ENTITY_MOVED,
            severity=WorldEventSeverity.MINOR,
            affected_entity_id=entity_id,
            affected_entity_type=entity_type,
            previous_state=previous_position,
            new_state=new_position,
            change_reason=reason or f"Moved {entity_type}",
            batch_id=batch_id,
        )

    @classmethod
    def entity_updated(
        cls,
        entity_id: str,
        entity_type: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[Set[str]] = None,
        reason: Optional[str] = None,
        batch_id: Optional[str] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when an entity is updated in the world.

        Args:
            entity_id: ID of the updated entity
            entity_type: Type of the updated entity
            previous_state: Previous state of the entity
            new_state: New state of the entity
            changed_fields: Set of field names that changed
            reason: Reason for updating the entity
            batch_id: Optional batch ID for grouped operations
            source: Event source

        Returns:
            WorldStateChanged event
        """
        event = cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.ENTITY_UPDATED,
            severity=WorldEventSeverity.MINOR,
            affected_entity_id=entity_id,
            affected_entity_type=entity_type,
            previous_state=previous_state,
            new_state=new_state,
            change_reason=reason or f"Updated {entity_type}",
            batch_id=batch_id,
        )

        if changed_fields:
            event.payload["changed_fields"] = list(changed_fields)
            event.tags.add(f"changed_fields:{len(changed_fields)}")

        return event

    @classmethod
    def state_snapshot(
        cls,
        snapshot_data: Dict[str, Any],
        reason: str,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when a complete world state snapshot is taken.

        Args:
            snapshot_data: Complete world state data
            reason: Reason for taking the snapshot
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.STATE_SNAPSHOT,
            severity=WorldEventSeverity.MAJOR,
            new_state=snapshot_data,
            change_reason=reason,
        )

    @classmethod
    def state_reset(
        cls,
        reason: str,
        previous_state: Optional[Dict[str, Any]] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when the world state is reset.

        Args:
            reason: Reason for resetting the world state
            previous_state: Previous world state before reset
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.STATE_RESET,
            severity=WorldEventSeverity.CRITICAL,
            previous_state=previous_state,
            change_reason=reason,
        )

    @classmethod
    def environment_changed(
        cls,
        environment_changes: Dict[str, Any],
        reason: str,
        affected_area: Optional[Dict[str, Any]] = None,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when the world environment changes.

        Args:
            environment_changes: Dictionary of environment changes
            reason: Reason for the environment change
            affected_area: Spatial area affected by the change
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.ENVIRONMENT_CHANGED,
            severity=WorldEventSeverity.MAJOR,
            new_state=environment_changes,
            change_reason=reason,
            affected_area=affected_area,
        )

    @classmethod
    def time_advanced(
        cls,
        previous_time: datetime,
        new_time: datetime,
        reason: str,
        source: str = "world_context",
    ) -> "WorldStateChanged":
        """
        Create an event for when world time is advanced.

        Args:
            previous_time: Previous world time
            new_time: New world time
            reason: Reason for advancing time
            source: Event source

        Returns:
            WorldStateChanged event
        """
        return cls(
            event_id=str(uuid4()),
            source=source,
            change_type=WorldChangeType.TIME_ADVANCED,
            severity=WorldEventSeverity.MAJOR,
            previous_state={"world_time": previous_time.isoformat()},
            new_state={"world_time": new_time.isoformat()},
            change_reason=reason,
            world_time=new_time,
        )

    def add_cascade_effect(self, entity_id: str) -> None:
        """
        Add an entity ID to the cascade effects set.

        Args:
            entity_id: ID of entity affected by cascade effects
        """
        self.cascade_effects.add(entity_id)
        self.payload["cascade_effects"] = list(self.cascade_effects)

    def is_batch_operation(self) -> bool:
        """
        Check if this event is part of a batch operation.

        Returns:
            True if this event has a batch_id
        """
        return self.batch_id is not None

    def get_change_summary(self) -> str:
        """
        Get a human-readable summary of the change.

        Returns:
            String summary of the change
        """
        base_summary = f"{self.change_type.value.replace('_', ' ').title()}"

        if self.affected_entity_type and self.affected_entity_id:
            base_summary += (
                f" - {self.affected_entity_type} {self.affected_entity_id[:8]}"
            )

        if self.change_reason:
            base_summary += f" ({self.change_reason})"

        return base_summary
