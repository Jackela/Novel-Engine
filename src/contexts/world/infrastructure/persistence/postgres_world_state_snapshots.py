"""Snapshot management for world state.

This module provides the PostgresWorldStateSnapshots class for managing
snapshots, including creation, restoration, listing, and deletion.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from core_platform.persistence.database import get_db_session

from ...domain.aggregates.world_state import WorldState
from ...domain.repositories.world_state_repo import (
    EntityNotFoundException,
    RepositoryException,
)
from .models import WorldStateSnapshotModel

logger = structlog.get_logger(__name__)


class PostgresWorldStateSnapshots:
    """Handles snapshot creation and restoration for WorldState.

    This class encapsulates all snapshot-related operations including
    creation, restoration, listing, and deletion of snapshots.
    """

    def __init__(self) -> None:
        """Initialize the snapshots handler."""
        self.logger = logger.bind(component=self.__class__.__name__)

    async def create_snapshot(
        self,
        world_state_id: str,
        snapshot_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a named snapshot of a WorldState aggregate.

        Args:
            world_state_id: The ID of the world state to snapshot.
            snapshot_name: The name for the snapshot.
            metadata: Optional metadata dictionary.

        Returns:
            The ID of the created snapshot.

        Raises:
            EntityNotFoundException: If world state not found.
            RepositoryException: If database error occurs.
        """
        try:
            from .postgres_world_state_crud import PostgresWorldStateCrud

            crud = PostgresWorldStateCrud()
            world_state = await crud.get_by_id_or_raise(world_state_id)

            async with get_db_session() as session:
                # Create snapshot data
                snapshot_data = {
                    "world_state": world_state.to_dict(),
                    "snapshot_metadata": metadata or {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                # Create snapshot model
                snapshot_model = WorldStateSnapshotModel(
                    world_state_id=uuid.UUID(world_state_id),
                    snapshot_name=snapshot_name,
                    snapshot_reason=f"Manual snapshot: {snapshot_name}",
                    world_version_at_snapshot=world_state.version,
                    snapshot_data=snapshot_data,
                    entity_count=len(world_state.entities),
                    data_size_bytes=len(json.dumps(snapshot_data).encode("utf-8")),
                )

                session.add(snapshot_model)
                await session.commit()

                self.logger.info(
                    "world_state_snapshot_created",
                    snapshot_name=snapshot_name,
                    world_state_id=world_state_id,
                )
                return str(snapshot_model.id)

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_snapshot_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to create snapshot: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_snapshot_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Unexpected error creating snapshot: {e}")

    async def restore_from_snapshot(
        self, world_state_id: str, snapshot_id: str
    ) -> WorldState:
        """Restore a WorldState aggregate from a snapshot.

        Args:
            world_state_id: The ID of the world state to restore to.
            snapshot_id: The ID of the snapshot to restore from.

        Returns:
            The restored WorldState.

        Raises:
            EntityNotFoundException: If snapshot or world state not found.
            RepositoryException: If restoration fails.
        """
        try:
            async with get_db_session() as session:
                snapshot_model = (
                    session.query(WorldStateSnapshotModel)
                    .filter(
                        and_(
                            WorldStateSnapshotModel.id == uuid.UUID(snapshot_id),
                            WorldStateSnapshotModel.world_state_id
                            == uuid.UUID(world_state_id),
                        )
                    )
                    .first()
                )

                if not snapshot_model:
                    raise EntityNotFoundException(
                        f"Snapshot {snapshot_id} not found for world state {world_state_id}"
                    )

                # Reconstruct world state from snapshot
                from .postgres_world_state_versioning import (
                    PostgresWorldStateVersioning,
                )

                versioning = PostgresWorldStateVersioning()
                snapshot_data = snapshot_model.snapshot_data["world_state"]
                restored_world_state = (
                    versioning._reconstruct_world_state_from_version_data(snapshot_data)
                )

                # Get current version for increment
                from .postgres_world_state_crud import PostgresWorldStateCrud

                crud = PostgresWorldStateCrud()
                current_world_state = await crud.get_by_id_or_raise(world_state_id)
                restored_world_state.version = current_world_state.version

                # Add restoration event
                from ...domain.events.world_events import WorldStateChanged

                restore_event = WorldStateChanged.snapshot_restored(
                    aggregate_id=world_state_id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_model.snapshot_name,
                )
                restored_world_state.raise_domain_event(restore_event)

                # Save the restored state
                return await crud.save(restored_world_state)

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                "restore_from_snapshot_database_error",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to restore from snapshot: {e}")
        except Exception as e:
            self.logger.error(
                "restore_from_snapshot_error", snapshot_id=snapshot_id, error=str(e)
            )
            raise RepositoryException(f"Unexpected error restoring from snapshot: {e}")

    async def list_snapshots(self, world_state_id: str) -> List[Dict[str, Any]]:
        """List all snapshots for a WorldState aggregate.

        Args:
            world_state_id: The ID of the world state.

        Returns:
            List of snapshot dictionaries with metadata.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                snapshots = (
                    session.query(WorldStateSnapshotModel)
                    .filter(
                        WorldStateSnapshotModel.world_state_id
                        == uuid.UUID(world_state_id)
                    )
                    .order_by(WorldStateSnapshotModel.created_at.desc())
                    .all()
                )

                return [
                    {
                        "id": str(snapshot.id),
                        "name": snapshot.snapshot_name,
                        "reason": snapshot.snapshot_reason,
                        "version_at_snapshot": snapshot.world_version_at_snapshot,
                        "entity_count": snapshot.entity_count,
                        "data_size_bytes": snapshot.data_size_bytes,
                        "created_at": snapshot.created_at.isoformat(),
                    }
                    for snapshot in snapshots
                ]

        except SQLAlchemyError as e:
            self.logger.error(
                "list_snapshots_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to list snapshots: {e}")
        except Exception as e:
            self.logger.error(
                "list_snapshots_error", world_state_id=world_state_id, error=str(e)
            )
            raise RepositoryException(f"Unexpected error listing snapshots: {e}")

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a WorldState snapshot.

        Args:
            snapshot_id: The ID of the snapshot to delete.

        Returns:
            True if deleted successfully, False if not found.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                snapshot = (
                    session.query(WorldStateSnapshotModel)
                    .filter(WorldStateSnapshotModel.id == uuid.UUID(snapshot_id))
                    .first()
                )

                if not snapshot:
                    return False

                await session.delete(snapshot)
                await session.commit()

                self.logger.info("snapshot_deleted", snapshot_id=snapshot_id)
                return True

        except SQLAlchemyError as e:
            self.logger.error(
                "delete_snapshot_database_error", snapshot_id=snapshot_id, error=str(e)
            )
            raise RepositoryException(f"Failed to delete snapshot: {e}")
        except Exception as e:
            self.logger.error(
                "delete_snapshot_error", snapshot_id=snapshot_id, error=str(e)
            )
            raise RepositoryException(f"Unexpected error deleting snapshot: {e}")

    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific snapshot.

        Args:
            snapshot_id: The ID of the snapshot.

        Returns:
            Snapshot details dictionary, or None if not found.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                snapshot = (
                    session.query(WorldStateSnapshotModel)
                    .filter(WorldStateSnapshotModel.id == uuid.UUID(snapshot_id))
                    .first()
                )

                if not snapshot:
                    return None

                return {
                    "id": str(snapshot.id),
                    "world_state_id": str(snapshot.world_state_id),
                    "name": snapshot.snapshot_name,
                    "reason": snapshot.snapshot_reason,
                    "version_at_snapshot": snapshot.world_version_at_snapshot,
                    "entity_count": snapshot.entity_count,
                    "data_size_bytes": snapshot.data_size_bytes,
                    "snapshot_data": snapshot.snapshot_data,
                    "created_at": snapshot.created_at.isoformat(),
                }

        except SQLAlchemyError as e:
            self.logger.error(
                "get_snapshot_by_id_database_error",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to get snapshot: {e}")
        except Exception as e:
            self.logger.error(
                "get_snapshot_by_id_error", snapshot_id=snapshot_id, error=str(e)
            )
            raise RepositoryException(f"Unexpected error getting snapshot: {e}")
