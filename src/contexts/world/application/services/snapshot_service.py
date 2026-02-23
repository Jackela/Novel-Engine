#!/usr/bin/env python3
"""Snapshot Service for managing world state snapshots.

This module provides the SnapshotService which handles creating, restoring,
listing, and deleting world state snapshots. Uses in-memory storage with
FIFO eviction when max snapshots per world is exceeded.

Typical usage example:
    >>> from src.contexts.world.application.services.snapshot_service import SnapshotService
    >>> service = SnapshotService()
    >>> snapshot = service.create_snapshot("world-123", calendar, state_json, 5)
    >>> restored = service.restore_snapshot(snapshot.snapshot_id)
"""

from __future__ import annotations

from collections import OrderedDict
from enum import Enum
from typing import Dict, List, Optional

from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.core.result import Err, Ok, Result


class SnapshotError(Enum):
    """Error types for snapshot operations.

    Attributes:
        NOT_FOUND: Snapshot with given ID does not exist.
        RESTORE_FAILED: Failed to restore world state from snapshot.
        STORAGE_ERROR: Failed to store or retrieve snapshot.
    """

    NOT_FOUND = "not_found"
    RESTORE_FAILED = "restore_failed"
    STORAGE_ERROR = "storage_error"


# Maximum snapshots per world before FIFO eviction
MAX_SNAPSHOTS_PER_WORLD = 10


class SnapshotService:
    """Service for managing world state snapshots.

    Provides operations for creating, restoring, listing, and deleting
    snapshots. Uses in-memory storage with FIFO eviction.

    Attributes:
        max_per_world: Maximum snapshots per world before eviction.
    """

    def __init__(self, max_per_world: int = MAX_SNAPSHOTS_PER_WORLD) -> None:
        """Initialize the snapshot service.

        Args:
            max_per_world: Maximum snapshots per world (default 10).
        """
        self._storage: Dict[str, OrderedDict[str, WorldSnapshot]] = {}
        self.max_per_world = max_per_world

    def create_snapshot(
        self,
        world_id: str,
        calendar: WorldCalendar,
        state_json: str,
        tick_number: int,
        description: str = "",
    ) -> WorldSnapshot:
        """Create a new snapshot for a world.

        Creates a snapshot with auto-generated name if description not provided.
        Enforces FIFO eviction if max snapshots exceeded.

        Args:
            world_id: ID of the world to snapshot.
            calendar: WorldCalendar at snapshot time.
            state_json: JSON-serialized world state.
            tick_number: Sequential tick number.
            description: Optional description (auto-generated if empty).

        Returns:
            The created WorldSnapshot.

        Example:
            >>> snapshot = service.create_snapshot(
            ...     world_id="world-123",
            ...     calendar=calendar,
            ...     state_json='{"factions": []}',
            ...     tick_number=5,
            ... )
        """
        snapshot = WorldSnapshot.create(
            world_id=world_id,
            calendar=calendar,
            state_json=state_json,
            tick_number=tick_number,
            description=description,
        )

        # Initialize storage for world if not exists
        if world_id not in self._storage:
            self._storage[world_id] = OrderedDict()

        # Add snapshot
        world_snapshots = self._storage[world_id]
        world_snapshots[snapshot.snapshot_id] = snapshot

        # Enforce FIFO eviction
        while len(world_snapshots) > self.max_per_world:
            oldest_key = next(iter(world_snapshots))
            del world_snapshots[oldest_key]

        return snapshot

    def restore_snapshot(
        self, snapshot_id: str
    ) -> Result["WorldSnapshot", SnapshotError]:
        """Restore world state from a snapshot.

        Finds the snapshot by ID and returns it for restoration.
        The actual state restoration is done by calling snapshot.restore().

        Args:
            snapshot_id: ID of the snapshot to restore.

        Returns:
            Ok(WorldSnapshot) if found and valid.
            Err(SnapshotError.NOT_FOUND) if snapshot doesn't exist.
            Err(SnapshotError.RESTORE_FAILED) if restoration fails.

        Example:
            >>> result = service.restore_snapshot("snap-123")
            >>> if result.is_ok:
            ...     world_state = result.value.restore()
        """
        # Find snapshot across all worlds
        snapshot = self._find_snapshot(snapshot_id)

        if snapshot is None:
            return Err(SnapshotError.NOT_FOUND)

        # Verify snapshot can be restored
        try:
            # Just verify the state_json is valid JSON
            import json
            json.loads(snapshot.state_json)
        except (json.JSONDecodeError, Exception):
            return Err(SnapshotError.RESTORE_FAILED)

        return Ok(snapshot)

    def list_snapshots(
        self, world_id: str, limit: int = 10
    ) -> List[WorldSnapshot]:
        """List snapshots for a world.

        Returns snapshots ordered by creation time (newest first).

        Args:
            world_id: ID of the world.
            limit: Maximum number of snapshots to return (default 10).

        Returns:
            List of WorldSnapshot objects, newest first.

        Example:
            >>> snapshots = service.list_snapshots("world-123", limit=5)
        """
        if world_id not in self._storage:
            return []

        world_snapshots = self._storage[world_id]
        snapshots = list(world_snapshots.values())

        # Return newest first (reverse of insertion order for OrderedDict)
        return snapshots[::-1][:limit]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot.

        Args:
            snapshot_id: ID of the snapshot to delete.

        Returns:
            True if deleted, False if not found.

        Example:
            >>> deleted = service.delete_snapshot("snap-123")
        """
        # Find and delete snapshot
        for world_id, world_snapshots in self._storage.items():
            if snapshot_id in world_snapshots:
                del world_snapshots[snapshot_id]
                return True

        return False

    def get_latest_snapshot(self, world_id: str) -> Optional[WorldSnapshot]:
        """Get the most recent snapshot for a world.

        Args:
            world_id: ID of the world.

        Returns:
            The most recent WorldSnapshot, or None if no snapshots exist.

        Example:
            >>> latest = service.get_latest_snapshot("world-123")
            >>> if latest:
            ...     print(f"Latest tick: {latest.tick_number}")
        """
        if world_id not in self._storage:
            return None

        world_snapshots = self._storage[world_id]
        if not world_snapshots:
            return None

        # Return last (most recent) item in OrderedDict
        return list(world_snapshots.values())[-1]

    def _find_snapshot(self, snapshot_id: str) -> Optional[WorldSnapshot]:
        """Find a snapshot by ID across all worlds.

        Args:
            snapshot_id: ID of the snapshot to find.

        Returns:
            The WorldSnapshot if found, None otherwise.
        """
        for world_snapshots in self._storage.values():
            if snapshot_id in world_snapshots:
                return world_snapshots[snapshot_id]
        return None

    def clear_storage(self) -> None:
        """Clear all stored snapshots.

        Used for testing.
        """
        self._storage.clear()

    def get_snapshot_count(self, world_id: str) -> int:
        """Get the number of snapshots for a world.

        Args:
            world_id: ID of the world.

        Returns:
            Number of snapshots for the world.
        """
        if world_id not in self._storage:
            return 0
        return len(self._storage[world_id])
