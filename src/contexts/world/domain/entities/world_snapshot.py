#!/usr/bin/env python3
"""WorldSnapshot Domain Entity.

This module defines the WorldSnapshot entity which represents a saved state
of the world at a specific point in time. Snapshots enable rollback,
history tracking, and state comparison.

Typical usage example:
    >>> from src.contexts.world.domain.entities import WorldSnapshot
    >>> snapshot = WorldSnapshot.create(
    ...     world_id="world-123",
    ...     calendar=world.calendar,
    ...     state_json=json.dumps(world.to_dict()),
    ...     tick_number=5,
    ... )
    >>> restored = snapshot.restore()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from src.contexts.world.domain.aggregates.world_state import WorldState
    from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


@dataclass(frozen=True)
class WorldSnapshot:
    """WorldSnapshot Entity (Immutable).

    Represents a saved state of the world at a specific point in time.
    Used for rollback, history tracking, and state comparison.

    Why frozen: Snapshots are immutable point-in-time records. Once created,
    a snapshot should never be modified - it represents a fixed state that
    can be restored but not changed.

    Attributes:
        snapshot_id: Unique identifier for this snapshot (UUID).
        world_id: ID of the world this snapshot belongs to.
        calendar: WorldCalendar at the time of snapshot.
        state_json: JSON-serialized WorldState data.
        tick_number: Sequential tick number (0 = initial state).
        description: Human-readable description of the snapshot.
        created_at: When the snapshot was created.
    """

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    world_id: str = ""
    calendar: Optional["WorldCalendar"] = None
    state_json: str = "{}"
    tick_number: int = 0
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate snapshot after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate the snapshot's invariants.

        Raises:
            ValueError: If any validation rule is violated.
        """
        errors: list[Any] = []
        if not self.snapshot_id:
            errors.append("Snapshot ID cannot be empty")

        if not self.world_id:
            errors.append("World ID cannot be empty")

        if self.tick_number < 0:
            errors.append(f"Tick number cannot be negative, got {self.tick_number}")

        if not self.state_json:
            errors.append("State JSON cannot be empty")

        if errors:
            raise ValueError(f"WorldSnapshot validation failed: {'; '.join(errors)}")

    @property
    def size_bytes(self) -> int:
        """Get the size of the snapshot in bytes.

        Returns:
            Length of state_json string in bytes.
        """
        return len(self.state_json.encode("utf-8"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary representation.

        Returns:
            Dictionary with all snapshot fields.
        """
        calendar_dict = None
        if self.calendar is not None:
            calendar_dict = self.calendar.to_dict()

        return {
            "snapshot_id": self.snapshot_id,
            "world_id": self.world_id,
            "calendar": calendar_dict,
            "state_json": self.state_json,
            "tick_number": self.tick_number,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldSnapshot":
        """Create a WorldSnapshot from a dictionary.

        Args:
            data: Dictionary containing snapshot data.

        Returns:
            A new WorldSnapshot instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        # Parse calendar
        calendar = None
        calendar_data = data.get("calendar")
        if calendar_data is not None:
            from src.contexts.world.domain.value_objects.world_calendar import (
                WorldCalendar,
            )

            calendar = WorldCalendar.from_dict(calendar_data)

        # Parse created_at
        created_at = datetime.now()
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            elif isinstance(data["created_at"], datetime):
                created_at = data["created_at"]

        return cls(
            snapshot_id=data.get("snapshot_id", str(uuid4())),
            world_id=data.get("world_id", ""),
            calendar=calendar,
            state_json=data.get("state_json", "{}"),
            tick_number=data.get("tick_number", 0),
            description=data.get("description", ""),
            created_at=created_at,
        )

    def restore(self) -> "WorldState":
        """Restore WorldState from this snapshot.

        Deserializes the state_json and reconstructs the WorldState
        aggregate.

        Returns:
            Restored WorldState aggregate.

        Raises:
            ValueError: If state_json cannot be parsed or is invalid.
        """
        from src.contexts.world.domain.aggregates.world_state import WorldState

        try:
            state_data = json.loads(self.state_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid state_json: {e}") from e

        return WorldState.from_dict(state_data)

    @classmethod
    def create(
        cls,
        world_id: str,
        calendar: "WorldCalendar",
        state_json: str,
        tick_number: int,
        description: str = "",
    ) -> "WorldSnapshot":
        """Factory method to create a snapshot.

        Creates a new WorldSnapshot with auto-generated ID and timestamp.

        Args:
            world_id: ID of the world being snapshotted.
            calendar: WorldCalendar at snapshot time.
            state_json: JSON-serialized WorldState.
            tick_number: Sequential tick number.
            description: Optional description.

        Returns:
            A new WorldSnapshot instance.

        Example:
            >>> snapshot = WorldSnapshot.create(
            ...     world_id="world-123",
            ...     calendar=world.calendar,
            ...     state_json=json.dumps(world.to_dict()),
            ...     tick_number=5,
            ...     description="Before major battle",
            ... )
        """
        # Auto-generate description if not provided
        if not description:
            description = f"Tick {tick_number} - {calendar.format()}"

        return cls(
            world_id=world_id,
            calendar=calendar,
            state_json=state_json,
            tick_number=tick_number,
            description=description,
        )

    @classmethod
    def create_from_world(
        cls,
        world: "WorldState",
        tick_number: int,
        description: str = "",
    ) -> "WorldSnapshot":
        """Factory method to create a snapshot from a WorldState.

        Convenience method that extracts world_id, calendar, and
        serializes the state automatically.

        Args:
            world: WorldState aggregate to snapshot.
            tick_number: Sequential tick number.
            description: Optional description.

        Returns:
            A new WorldSnapshot instance.

        Example:
            >>> snapshot = WorldSnapshot.create_from_world(world, tick_number=5)
        """
        state_json = json.dumps(world.to_dict())

        return cls.create(
            world_id=world.id,
            calendar=world.calendar,
            state_json=state_json,
            tick_number=tick_number,
            description=description,
        )

    def __str__(self) -> str:
        """Return string representation of the snapshot.

        Returns:
            String showing snapshot summary.
        """
        calendar_str = self.calendar.format() if self.calendar else "Unknown"
        return (
            f"WorldSnapshot(world={self.world_id[:8]}..., "
            f"tick={self.tick_number}, "
            f"calendar={calendar_str}, "
            f"size={self.size_bytes} bytes)"
        )

    def __repr__(self) -> str:
        """Return detailed string representation.

        Returns:
            Detailed string representation of the snapshot.
        """
        return (
            f"WorldSnapshot(snapshot_id={self.snapshot_id[:8]}..., "
            f"world_id={self.world_id[:8]}..., "
            f"tick_number={self.tick_number}, "
            f"description='{self.description[:30]}...')"
        )
