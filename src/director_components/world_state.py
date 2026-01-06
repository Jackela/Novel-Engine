"""
World State Manager
==================

Manages the persistent world state with efficient updates and versioning.
Handles state persistence, synchronization, and conflict resolution.
"""

import asyncio
import copy
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class StateChangeType(Enum):
    """Types of world state changes."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"


@dataclass
class StateChange:
    """Represents a single state change."""

    change_id: str
    change_type: StateChangeType
    path: str  # Dot notation path like "locations.tavern.occupancy"
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"


@dataclass
class StateSnapshot:
    """Represents a complete state snapshot."""

    snapshot_id: str
    state: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    change_count: int = 0
    checksum: str = ""


class WorldStateManager:
    """
    Manages world state with efficient updates and persistence.

    Features:
    - Incremental state updates
    - Change tracking and history
    - Periodic snapshots
    - Conflict detection and resolution
    - Efficient serialization
    """

    def __init__(
        self, state_file: Optional[str] = None, logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.state_file = Path(state_file) if state_file else Path("world_state.json")

        # Core state management
        self._current_state: Dict[str, Any] = {}
        self._change_history: List[StateChange] = []
        self._snapshots: List[StateSnapshot] = []

        # Configuration
        self._max_history_size = 1000
        self._snapshot_interval = 50  # Create snapshot every N changes
        self._max_snapshots = 20
        self._auto_save_interval = 300  # Auto-save every 5 minutes

        # Synchronization
        self._state_lock = asyncio.Lock()
        self._dirty = False
        self._last_save_time = datetime.now()

        # Auto-save task
        self._auto_save_task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initialize world state manager."""
        try:
            # Load existing state if available
            if self.state_file.exists():
                success = await self.load_world_state()
                if not success:
                    self.logger.warning("Failed to load existing state, starting fresh")
                    self._current_state = self._create_default_state()
            else:
                self._current_state = self._create_default_state()

            # Start auto-save task
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())

            self.logger.info("World state manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"World state manager initialization failed: {e}")
            return False

    async def get_world_state(self) -> Dict[str, Any]:
        """Get a deep copy of the current world state."""
        async with self._state_lock:
            return copy.deepcopy(self._current_state)

    async def update_world_state(self, updates: Dict[str, Any]) -> None:
        """
        Update world state with new data.

        Args:
            updates: Dictionary of updates to apply
        """
        async with self._state_lock:
            try:
                changes = []

                for path, new_value in updates.items():
                    change = await self._apply_single_update(path, new_value)
                    if change:
                        changes.append(change)

                if changes:
                    self._change_history.extend(changes)
                    self._dirty = True

                    # Trim history if too long
                    if len(self._change_history) > self._max_history_size:
                        self._change_history = self._change_history[
                            -self._max_history_size :
                        ]

                    # Create snapshot if needed
                    if len(self._change_history) % self._snapshot_interval == 0:
                        await self._create_snapshot()

                    self.logger.debug(f"Applied {len(changes)} state updates")

            except Exception as e:
                self.logger.error(f"State update failed: {e}")
                raise

    async def _apply_single_update(
        self, path: str, new_value: Any
    ) -> Optional[StateChange]:
        """Apply a single update to the state."""
        try:
            # Navigate to the correct location in the state
            parts = path.split(".")
            current = self._current_state

            # Navigate to parent
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # Convert to dict if needed
                    current[part] = {}
                current = current[part]

            # Apply update
            final_key = parts[-1]
            old_value = current.get(final_key)

            # Determine change type
            if final_key not in current:
                change_type = StateChangeType.CREATE
            elif new_value is None:
                change_type = StateChangeType.DELETE
            else:
                change_type = StateChangeType.UPDATE

            # Apply change
            if change_type == StateChangeType.DELETE:
                if final_key in current:
                    del current[final_key]
            else:
                current[final_key] = new_value

            # Create change record
            change_id = self._generate_change_id(path, change_type)
            return StateChange(
                change_id=change_id,
                change_type=change_type,
                path=path,
                old_value=old_value,
                new_value=new_value,
                source="world_state_manager",
            )

        except Exception as e:
            self.logger.error(f"Failed to apply update to path '{path}': {e}")
            return None

    async def get_state_value(self, path: str, default: Any = None) -> Any:
        """Get a specific value from the world state."""
        async with self._state_lock:
            try:
                parts = path.split(".")
                current = self._current_state

                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return default

                return current

            except Exception as e:
                self.logger.error(f"Failed to get state value for path '{path}': {e}")
                return default

    async def set_state_value(self, path: str, value: Any) -> bool:
        """Set a specific value in the world state."""
        try:
            await self.update_world_state({path: value})
            return True
        except Exception as e:
            self.logger.error(f"Failed to set state value for path '{path}': {e}")
            return False

    async def save_world_state(self) -> bool:
        """Persist world state to file."""
        async with self._state_lock:
            try:
                # Prepare data for saving
                save_data = {
                    "world_state": self._current_state,
                    "metadata": {
                        "last_updated": datetime.now().isoformat(),
                        "change_count": len(self._change_history),
                        "checksum": self._calculate_state_checksum(),
                    },
                }

                # Write to temporary file first
                temp_file = self.state_file.with_suffix(".tmp")
                with temp_file.open("w", encoding="utf-8") as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)

                # Atomic move to final location
                temp_file.replace(self.state_file)

                self._dirty = False
                self._last_save_time = datetime.now()

                self.logger.info(f"World state saved to {self.state_file}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to save world state: {e}")
                return False

    async def load_world_state(self) -> bool:
        """Load world state from file."""
        async with self._state_lock:
            try:
                if not self.state_file.exists():
                    self.logger.info("No existing state file found")
                    return False

                with self.state_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate loaded data
                if "world_state" not in data:
                    self.logger.error("Invalid state file format")
                    return False

                # Load state
                self._current_state = data["world_state"]

                # Validate checksum if available
                if "metadata" in data and "checksum" in data["metadata"]:
                    expected_checksum = data["metadata"]["checksum"]
                    actual_checksum = self._calculate_state_checksum()

                    if expected_checksum != actual_checksum:
                        self.logger.warning(
                            "State checksum mismatch - data may be corrupted"
                        )

                self._dirty = False
                self.logger.info(f"World state loaded from {self.state_file}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to load world state: {e}")
                return False

    async def _create_snapshot(self) -> None:
        """Create a snapshot of the current state."""
        try:
            snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                state=copy.deepcopy(self._current_state),
                change_count=len(self._change_history),
                checksum=self._calculate_state_checksum(),
            )

            self._snapshots.append(snapshot)

            # Trim snapshots if too many
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots :]

            self.logger.debug(f"Created state snapshot: {snapshot_id}")

        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")

    async def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """Restore state from a specific snapshot."""
        async with self._state_lock:
            try:
                # Find snapshot
                snapshot = None
                for s in self._snapshots:
                    if s.snapshot_id == snapshot_id:
                        snapshot = s
                        break

                if not snapshot:
                    self.logger.error(f"Snapshot {snapshot_id} not found")
                    return False

                # Restore state
                self._current_state = copy.deepcopy(snapshot.state)
                self._dirty = True

                self.logger.info(f"State restored from snapshot: {snapshot_id}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to restore from snapshot: {e}")
                return False

    async def get_change_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent change history."""
        async with self._state_lock:
            recent_changes = (
                self._change_history[-limit:] if self._change_history else []
            )

            return [
                {
                    "change_id": change.change_id,
                    "type": change.change_type.value,
                    "path": change.path,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                    "timestamp": change.timestamp.isoformat(),
                    "source": change.source,
                }
                for change in recent_changes
            ]

    async def get_snapshots_info(self) -> List[Dict[str, Any]]:
        """Get information about available snapshots."""
        return [
            {
                "snapshot_id": snapshot.snapshot_id,
                "timestamp": snapshot.timestamp.isoformat(),
                "change_count": snapshot.change_count,
                "checksum": snapshot.checksum[:8] + "...",  # Truncated for display
            }
            for snapshot in self._snapshots
        ]

    async def get_state_statistics(self) -> Dict[str, Any]:
        """Get statistics about the world state."""
        async with self._state_lock:
            try:
                # Calculate state statistics
                def count_objects(obj: Any) -> Dict[str, int]:
                    counts = {
                        "dicts": 0,
                        "lists": 0,
                        "strings": 0,
                        "numbers": 0,
                        "booleans": 0,
                        "nulls": 0,
                    }

                    if isinstance(obj, dict):
                        counts["dicts"] += 1
                        for value in obj.values():
                            sub_counts = count_objects(value)
                            for key, count in sub_counts.items():
                                counts[key] += count
                    elif isinstance(obj, list):
                        counts["lists"] += 1
                        for item in obj:
                            sub_counts = count_objects(item)
                            for key, count in sub_counts.items():
                                counts[key] += count
                    elif isinstance(obj, str):
                        counts["strings"] += 1
                    elif isinstance(obj, (int, float)):
                        counts["numbers"] += 1
                    elif isinstance(obj, bool):
                        counts["booleans"] += 1
                    elif obj is None:
                        counts["nulls"] += 1

                    return counts

                object_counts = count_objects(self._current_state)

                return {
                    "state_size_bytes": len(json.dumps(self._current_state)),
                    "object_counts": object_counts,
                    "total_objects": sum(object_counts.values()),
                    "change_history_size": len(self._change_history),
                    "snapshots_count": len(self._snapshots),
                    "last_save_time": self._last_save_time.isoformat(),
                    "is_dirty": self._dirty,
                    "checksum": self._calculate_state_checksum(),
                }

            except Exception as e:
                self.logger.error(f"Failed to calculate state statistics: {e}")
                return {"error": str(e)}

    def _calculate_state_checksum(self) -> str:
        """Calculate checksum of current state."""
        try:
            state_json = json.dumps(
                self._current_state, sort_keys=True, ensure_ascii=True
            )
            return hashlib.md5(state_json.encode()).hexdigest()
        except Exception:
            return "checksum_error"

    def _generate_change_id(self, path: str, change_type: StateChangeType) -> str:
        """Generate unique ID for a change."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        return f"{change_type.value}_{path_hash}_{timestamp}"

    def _create_default_state(self) -> Dict[str, Any]:
        """Create default world state structure."""
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "simulation_id": f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            },
            "environment": {
                "time": {
                    "current_turn": 0,
                    "simulation_start": datetime.now().isoformat(),
                    "in_game_time": "Day 1, Morning",
                },
                "weather": {
                    "condition": "clear",
                    "temperature": "mild",
                    "visibility": "good",
                },
            },
            "locations": {},
            "characters": {},
            "events": {"recent": [], "scheduled": []},
            "resources": {},
            "statistics": {
                "turns_completed": 0,
                "total_actions": 0,
                "characters_active": 0,
            },
        }

    async def _auto_save_loop(self) -> None:
        """Auto-save loop that runs in background."""
        try:
            while True:
                await asyncio.sleep(self._auto_save_interval)

                if self._dirty:
                    success = await self.save_world_state()
                    if success:
                        self.logger.debug("Auto-save completed")
                    else:
                        self.logger.warning("Auto-save failed")

        except asyncio.CancelledError:
            self.logger.info("Auto-save loop cancelled")
        except Exception as e:
            self.logger.error(f"Auto-save loop error: {e}")

    async def cleanup(self) -> None:
        """Cleanup world state manager."""
        try:
            # Cancel auto-save task
            if self._auto_save_task:
                self._auto_save_task.cancel()
                try:
                    await self._auto_save_task
                except asyncio.CancelledError:
                    logging.getLogger(__name__).debug(
                        "Suppressed exception", exc_info=True
                    )
            if self._dirty:
                await self.save_world_state()

            self.logger.info("World state manager cleanup completed")

        except Exception as e:
            self.logger.error(f"World state cleanup error: {e}")

    async def export_state(
        self, export_path: str, include_history: bool = False
    ) -> bool:
        """Export world state to file with optional history."""
        try:
            export_data = {
                "world_state": await self.get_world_state(),
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "exported_from": str(self.state_file),
                    "statistics": await self.get_state_statistics(),
                },
            }

            if include_history:
                export_data["change_history"] = await self.get_change_history(
                    limit=1000
                )
                export_data["snapshots"] = await self.get_snapshots_info()

            export_file = Path(export_path)
            with export_file.open("w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"State exported to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"State export failed: {e}")
            return False

    async def import_state(self, import_path: str) -> bool:
        """Import world state from file."""
        async with self._state_lock:
            try:
                import_file = Path(import_path)
                if not import_file.exists():
                    self.logger.error(f"Import file not found: {import_path}")
                    return False

                with import_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                if "world_state" not in data:
                    self.logger.error("Invalid import file format")
                    return False

                # Import state
                self._current_state = data["world_state"]
                self._dirty = True

                # Clear history and snapshots (fresh start)
                self._change_history.clear()
                self._snapshots.clear()

                self.logger.info(f"State imported from {import_path}")
                return True

            except Exception as e:
                self.logger.error(f"State import failed: {e}")
                return False
