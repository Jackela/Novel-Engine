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
from typing import Dict, List, Optional

from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.contexts.world.domain.errors import (
    SnapshotError,
    SnapshotNotFoundError,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.core.result import Err, Error, Ok, Result

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
    ) -> Result[WorldSnapshot, Error]:
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
            Result containing:
            - Ok: The created WorldSnapshot
            - Err: Error if creation fails

        Example:
            >>> result = service.create_snapshot(
            ...     world_id="world-123",
            ...     calendar=calendar,
            ...     state_json='{"factions": []}',
            ...     tick_number=5,
            ... )
            >>> if result.is_ok:
            ...     snapshot = result.value
        """
        try:
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

            return Ok(snapshot)
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to create snapshot: {e}",
                    details={"world_id": world_id},
                )
            )

    def restore_snapshot(
        self, snapshot_id: str
    ) -> Result[WorldSnapshot, Error]:
        """Restore world state from a snapshot.

        Finds the snapshot by ID and returns it for restoration.
        The actual state restoration is done by calling snapshot.restore().

        Args:
            snapshot_id: ID of the snapshot to restore.

        Returns:
            Result containing:
            - Ok: WorldSnapshot if found and valid
            - Err: SnapshotNotFoundError if snapshot doesn't exist
            - Err: SnapshotError if restoration fails

        Example:
            >>> result = service.restore_snapshot("snap-123")
            >>> if result.is_ok:
            ...     world_state = result.value.restore()
        """
        # Find snapshot across all worlds
        snapshot = self._find_snapshot(snapshot_id)

        if snapshot is None:
            return Err(SnapshotNotFoundError(snapshot_id))

        # Verify snapshot can be restored
        try:
            # Just verify the state_json is valid JSON
            import json

            json.loads(snapshot.state_json)
        except (json.JSONDecodeError, Exception) as e:
            return Err(
                SnapshotError(
                    f"Failed to restore snapshot: {e}",
                    details={"snapshot_id": snapshot_id},
                )
            )

        return Ok(snapshot)

    def list_snapshots(
        self, world_id: str, limit: int = 10
    ) -> Result[List[WorldSnapshot], Error]:
        """List snapshots for a world.

        Returns snapshots ordered by creation time (newest first).

        Args:
            world_id: ID of the world.
            limit: Maximum number of snapshots to return (default 10).

        Returns:
            Result containing:
            - Ok: List of WorldSnapshot objects, newest first
            - Err: Error if operation fails

        Example:
            >>> result = service.list_snapshots("world-123", limit=5)
            >>> if result.is_ok:
            ...     snapshots = result.value
        """
        try:
            if world_id not in self._storage:
                return Ok([])

            world_snapshots = self._storage[world_id]
            snapshots = list(world_snapshots.values())

            # Return newest first (reverse of insertion order for OrderedDict)
            return Ok(snapshots[::-1][:limit])
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to list snapshots: {e}",
                    details={"world_id": world_id},
                )
            )

    def delete_snapshot(self, snapshot_id: str) -> Result[bool, Error]:
        """Delete a snapshot.

        Args:
            snapshot_id: ID of the snapshot to delete.

        Returns:
            Result containing:
            - Ok: True if deleted, False if not found
            - Err: Error if operation fails

        Example:
            >>> result = service.delete_snapshot("snap-123")
            >>> if result.is_ok:
            ...     deleted = result.value
        """
        try:
            # Find and delete snapshot
            for world_id, world_snapshots in self._storage.items():
                if snapshot_id in world_snapshots:
                    del world_snapshots[snapshot_id]
                    return Ok(True)

            return Ok(False)
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to delete snapshot: {e}",
                    details={"snapshot_id": snapshot_id},
                )
            )

    def get_latest_snapshot(
        self, world_id: str
    ) -> Result[Optional[WorldSnapshot], Error]:
        """Get the most recent snapshot for a world.

        Args:
            world_id: ID of the world.

        Returns:
            Result containing:
            - Ok: The most recent WorldSnapshot, or None if no snapshots exist
            - Err: Error if operation fails

        Example:
            >>> result = service.get_latest_snapshot("world-123")
            >>> if result.is_ok:
            ...     latest = result.value
            ...     if latest:
            ...         print(f"Latest tick: {latest.tick_number}")
        """
        try:
            if world_id not in self._storage:
                return Ok(None)

            world_snapshots = self._storage[world_id]
            if not world_snapshots:
                return Ok(None)

            # Return last (most recent) item in OrderedDict
            return Ok(list(world_snapshots.values())[-1])
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to get latest snapshot: {e}",
                    details={"world_id": world_id},
                )
            )

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

    def clear_storage(self) -> Result[None, Error]:
        """Clear all stored snapshots.

        Used for testing.

        Returns:
            Result containing:
            - Ok: None on success
            - Err: Error if operation fails
        """
        try:
            self._storage.clear()
            return Ok(None)
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to clear storage: {e}",
                )
            )

    def get_snapshot_count(self, world_id: str) -> Result[int, Error]:
        """Get the number of snapshots for a world.

        Args:
            world_id: ID of the world.

        Returns:
            Result containing:
            - Ok: Number of snapshots for the world
            - Err: Error if operation fails
        """
        try:
            if world_id not in self._storage:
                return Ok(0)
            return Ok(len(self._storage[world_id]))
        except Exception as e:
            return Err(
                SnapshotError(
                    f"Failed to get snapshot count: {e}",
                    details={"world_id": world_id},
                )
            )
