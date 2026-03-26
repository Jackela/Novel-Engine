"""Version management for world state.

This module provides the PostgresWorldStateVersioning class for managing
version history, rollback operations, and event sourcing support.
"""

import uuid
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
from .models import WorldStateVersionModel

logger = structlog.get_logger(__name__)


class PostgresWorldStateVersioning:
    """Handles version history and rollback operations for WorldState.

    This class encapsulates all versioning-related operations including
    history retrieval, version-specific queries, and rollback functionality.
    """

    def __init__(self) -> None:
        """Initialize the versioning handler."""
        self.logger = logger.bind(component=self.__class__.__name__)

    async def get_version(
        self, world_state_id: str, version: int
    ) -> Optional[WorldState]:
        """Retrieve a specific version of a WorldState aggregate.

        Args:
            world_state_id: The ID of the world state.
            version: The version number to retrieve.

        Returns:
            The WorldState at the specified version, or None if not found.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                version_model = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        and_(
                            WorldStateVersionModel.world_state_id
                            == uuid.UUID(world_state_id),
                            WorldStateVersionModel.version_number == version,
                        )
                    )
                    .first()
                )

                if not version_model:
                    return None

                # Reconstruct world state from version data
                result = self._reconstruct_world_state_from_version_data(
                    dict(version_model.version_data)
                    if version_model.version_data
                    else {}
                )
                return result

        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_version_retrieval_database_error",
                world_state_id=world_state_id,
                version=version,
                error=str(e),
            )
            raise RepositoryException(f"Failed to retrieve world state version: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_version_retrieval_error",
                world_state_id=world_state_id,
                version=version,
                error=str(e),
            )
            raise RepositoryException(
                f"Unexpected error retrieving world state version: {e}"
            )

    async def get_version_history(
        self, world_state_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get version history for a WorldState aggregate.

        Args:
            world_state_id: The ID of the world state.
            limit: Maximum number of versions to return.

        Returns:
            List of version history entries as dictionaries.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                versions = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        WorldStateVersionModel.world_state_id
                        == uuid.UUID(world_state_id)
                    )
                    .order_by(WorldStateVersionModel.version_number.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "version": version.version_number,
                        "previous_version": version.previous_version,
                        "change_reason": version.change_reason,
                        "change_summary": version.change_summary,
                        "changed_by": (
                            str(version.changed_by) if version.changed_by else None
                        ),
                        "created_at": version.created_at.isoformat(),
                        "entities_added": version.entities_added,
                        "entities_removed": version.entities_removed,
                        "entities_modified": version.entities_modified,
                        "environment_changed": version.environment_changed,
                    }
                    for version in versions
                ]

        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_version_history_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to retrieve version history: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_version_history_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(
                f"Unexpected error retrieving version history: {e}"
            )

    async def rollback_to_version(
        self, world_state_id: str, version: int
    ) -> WorldState:
        """Rollback a WorldState aggregate to a previous version.

        Args:
            world_state_id: The ID of the world state to rollback.
            version: The target version number.

        Returns:
            The WorldState after rollback.

        Raises:
            EntityNotFoundException: If target version or world state not found.
            RepositoryException: If rollback fails.
        """
        try:
            # Get the target version
            target_world_state = await self.get_version(world_state_id, version)
            if not target_world_state:
                raise EntityNotFoundException(
                    f"Version {version} not found for world state {world_state_id}"
                )

            # Get current world state
            from .postgres_world_state_crud import PostgresWorldStateCrud

            crud = PostgresWorldStateCrud()
            current_world_state = await crud.get_by_id_or_raise(world_state_id)

            # Create new version with rollback data
            target_world_state.version = (
                current_world_state.version
            )  # Will be incremented in save()

            # Add a domain event for the rollback
            # Note: world_events module not yet implemented
            # target_world_state.add_domain_event(...)  # type: ignore[attr-defined]

            # Save the rolled-back state
            return await crud.save(target_world_state)

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "world_state_rollback_error",
                world_state_id=world_state_id,
                version=version,
                error=str(e),
            )
            raise RepositoryException(f"Failed to rollback world state: {e}")

    async def get_events_since(
        self, world_state_id: str, since_version: int
    ) -> List[Dict[str, Any]]:
        """Get domain events for a world state since a specific version.

        Args:
            world_state_id: The ID of the world state.
            since_version: Get events after this version number.

        Returns:
            List of event data dictionaries.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                versions = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        and_(
                            WorldStateVersionModel.world_state_id
                            == uuid.UUID(world_state_id),
                            WorldStateVersionModel.version_number > since_version,
                        )
                    )
                    .order_by(WorldStateVersionModel.version_number.asc())
                    .all()
                )

                events: list[Any] = []
                for version in versions:
                    # Extract change information as events
                    event_data = {
                        "version": version.version_number,
                        "change_reason": version.change_reason,
                        "change_summary": version.change_summary,
                        "entities_added": version.entities_added,
                        "entities_removed": version.entities_removed,
                        "entities_modified": version.entities_modified,
                        "environment_changed": version.environment_changed,
                        "timestamp": version.created_at.isoformat(),
                        "changed_by": (
                            str(version.changed_by) if version.changed_by else None
                        ),
                    }
                    events.append(event_data)

                return events

        except SQLAlchemyError as e:
            self.logger.error(
                "get_events_since_database_error",
                world_state_id=world_state_id,
                since_version=since_version,
                error=str(e),
            )
            raise RepositoryException(f"Failed to get events since version: {e}")
        except Exception as e:
            self.logger.error(
                "get_events_since_error",
                world_state_id=world_state_id,
                since_version=since_version,
                error=str(e),
            )
            raise RepositoryException(
                f"Unexpected error getting events since version: {e}"
            )

    async def replay_events(
        self, world_state_id: str, to_version: Optional[int] = None
    ) -> Optional[WorldState]:
        """Reconstruct a WorldState aggregate by replaying domain events.

        Args:
            world_state_id: The ID of the world state.
            to_version: Optional target version. If None, returns latest version.

        Returns:
            The reconstructed WorldState.

        Raises:
            EntityNotFoundException: If world state not found.
            RepositoryException: If replay fails.
        """
        try:
            if to_version:
                # Replay to specific version
                return await self.get_version(world_state_id, to_version)
            else:
                # Replay to latest version
                from .postgres_world_state_crud import PostgresWorldStateCrud

                crud = PostgresWorldStateCrud()
                return await crud.get_by_id_or_raise(world_state_id)

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "replay_events_error", world_state_id=world_state_id, error=str(e)
            )
            raise RepositoryException(f"Failed to replay events: {e}")

    def _reconstruct_world_state_from_version_data(
        self, version_data: Dict[str, Any]
    ) -> WorldState:
        """Reconstruct a WorldState aggregate from version data.

        Args:
            version_data: Dictionary containing serialized world state data.

        Returns:
            The reconstructed WorldState aggregate.

        Raises:
            RepositoryException: If reconstruction fails.
        """
        try:
            # Import here to avoid circular imports
            from ...domain.aggregates.world_state import WorldState

            # Create world state with available fields
            world_state = WorldState(
                id=version_data.get("id", ""),
                story_id=version_data.get("story_id"),
                version=version_data.get("version", 1),
                calendar=version_data.get("calendar"),
                factions=version_data.get("factions", {}),
                locations=version_data.get("locations", {}),
                events=version_data.get("events", []),
                metadata=version_data.get("metadata", {}),
                is_deleted=version_data.get("is_deleted", False),
                created_at=version_data.get("created_at"),
                updated_at=version_data.get("updated_at"),
            )

            return world_state

        except Exception as e:
            self.logger.error("reconstruct_world_state_error", error=str(e))
            raise RepositoryException(
                f"Failed to reconstruct world state from version data: {e}"
            )

    async def cleanup_old_versions(
        self, world_state_id: str, keep_count: int = 50
    ) -> int:
        """Clean up old version history entries, keeping only the most recent.

        Args:
            world_state_id: The ID of the world state.
            keep_count: Number of recent versions to keep.

        Returns:
            Number of deleted versions.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                # Get count of versions
                version_count = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        WorldStateVersionModel.world_state_id
                        == uuid.UUID(world_state_id)
                    )
                    .count()
                )

                if version_count <= keep_count:
                    return 0

                # Delete old versions, keeping the latest keep_count
                old_versions = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        WorldStateVersionModel.world_state_id
                        == uuid.UUID(world_state_id)
                    )
                    .order_by(WorldStateVersionModel.version_number.desc())
                    .offset(keep_count)
                    .all()
                )

                deleted_count = len(old_versions)
                for version in old_versions:
                    await session.delete(version)

                await session.commit()

                self.logger.info(
                    "cleaned_up_old_versions",
                    world_state_id=world_state_id,
                    deleted_count=deleted_count,
                    kept_count=keep_count,
                )

                return deleted_count

        except SQLAlchemyError as e:
            self.logger.error(
                "cleanup_old_versions_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to cleanup old versions: {e}")
        except Exception as e:
            self.logger.error(
                "cleanup_old_versions_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Unexpected error cleaning up versions: {e}")
