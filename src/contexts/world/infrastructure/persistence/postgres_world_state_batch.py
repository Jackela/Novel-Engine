"""Batch operations for world state.

This module provides the PostgresWorldStateBatch class for managing
batch create, update, and delete operations on WorldState aggregates.
"""

import uuid
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from core_platform.messaging.outbox import publish_event_transactionally
from core_platform.persistence.database import get_db_session

from ...domain.aggregates.world_state import WorldState
from ...domain.repositories.world_state_repo import (
    ConcurrencyException,
    RepositoryException,
)
from .models import WorldStateModel

logger = structlog.get_logger(__name__)


class PostgresWorldStateBatch:
    """Handles batch operations for WorldState.

    This class encapsulates all batch operations including bulk create,
    update, and delete with transaction support.
    """

    def __init__(self) -> None:
        """Initialize the batch operations handler."""
        self.logger = logger.bind(component=self.__class__.__name__)

    async def save_batch(self, world_states: List[WorldState]) -> List[WorldState]:
        """Save multiple WorldState aggregates in a single transaction.

        Args:
            world_states: List of WorldState aggregates to save.

        Returns:
            List of saved WorldState aggregates.

        Raises:
            ConcurrencyException: If version conflict detected.
            RepositoryException: If database or validation error occurs.
        """
        if not world_states:
            return []

        try:
            async with get_db_session() as session:
                saved_states: list[Any] = []
                for world_state in world_states:
                    # Similar logic to save() but within the same transaction
                    existing_model = (
                        session.query(WorldStateModel)
                        .filter(WorldStateModel.id == uuid.UUID(world_state.id))
                        .first()
                    )

                    if existing_model:
                        # Update existing
                        if existing_model.version != world_state.version:
                            raise ConcurrencyException(
                                f"Version conflict for world state {world_state.id}",
                                expected_version=world_state.version,
                                actual_version=int(existing_model.version),
                            )

                        world_state.version += 1
                        await self._create_version_entry(
                            session, world_state, existing_model
                        )
                        existing_model.update_from_domain_aggregate(world_state)
                        model_to_save = existing_model
                    else:
                        # Create new
                        world_state.version = 1
                        model_to_save = WorldStateModel.from_domain_aggregate(
                            world_state
                        )
                        session.add(model_to_save)
                        await self._create_version_entry(session, world_state, None)

                    # Validate
                    validation_errors = model_to_save.validate()
                    if validation_errors:
                        raise RepositoryException(
                            f"Validation failed for {world_state.id}: {'; '.join(validation_errors)}"
                        )

                    # Publish events
                    for event in world_state.get_domain_events():
                        await publish_event_transactionally(session, event)

                    world_state.clear_domain_events()
                    saved_states.append(model_to_save.to_domain_aggregate())

                await session.commit()
                self.logger.info("batch_saved_world_states", count=len(saved_states))
                return saved_states

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error("batch_save_database_error", error=str(e))
            raise RepositoryException(f"Failed to batch save world states: {e}")
        except Exception as e:
            self.logger.error("batch_save_error", error=str(e))
            raise RepositoryException(f"Unexpected error in batch save: {e}")

    async def delete_batch(self, world_state_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple WorldState aggregates in a single transaction.

        Args:
            world_state_ids: List of world state IDs to delete.

        Returns:
            Dictionary mapping world state IDs to success status.

        Raises:
            RepositoryException: If database error occurs.
        """
        if not world_state_ids:
            return {}

        results: dict[Any, Any] = {}
        try:
            async with get_db_session() as session:
                for world_state_id in world_state_ids:
                    model = (
                        session.query(WorldStateModel)
                        .filter(
                            and_(
                                WorldStateModel.id == uuid.UUID(world_state_id),
                                WorldStateModel.is_deleted.is_(False),
                            )
                        )
                        .first()
                    )

                    if model:
                        model.soft_delete()
                        results[world_state_id] = True
                    else:
                        results[world_state_id] = False

                await session.commit()
                self.logger.info(
                    "batch_deleted_world_states", count=sum(results.values())
                )
                return results

        except SQLAlchemyError as e:
            self.logger.error("batch_delete_database_error", error=str(e))
            raise RepositoryException(f"Failed to batch delete world states: {e}")
        except Exception as e:
            self.logger.error("batch_delete_error", error=str(e))
            raise RepositoryException(f"Unexpected error in batch delete: {e}")

    async def batch_create(self, world_states: List[WorldState]) -> List[str]:
        """Create multiple new WorldState aggregates.

        Args:
            world_states: List of WorldState aggregates to create.

        Returns:
            List of created world state IDs.

        Raises:
            RepositoryException: If database or validation error occurs.
        """
        if not world_states:
            return []

        try:
            async with get_db_session() as session:
                created_ids: list[str] = []
                for world_state in world_states:
                    # Ensure new entity
                    world_state.version = 1
                    model = WorldStateModel.from_domain_aggregate(world_state)
                    session.add(model)

                    # Create initial version entry
                    await self._create_version_entry(session, world_state, None)

                    # Validate
                    validation_errors = model.validate()
                    if validation_errors:
                        raise RepositoryException(
                            f"Validation failed for {world_state.id}: {'; '.join(validation_errors)}"
                        )

                    # Publish events
                    for event in world_state.get_domain_events():
                        await publish_event_transactionally(session, event)

                    world_state.clear_domain_events()
                    created_ids.append(world_state.id)

                await session.commit()
                self.logger.info("batch_created_world_states", count=len(created_ids))
                return created_ids

        except SQLAlchemyError as e:
            self.logger.error("batch_create_database_error", error=str(e))
            raise RepositoryException(f"Failed to batch create world states: {e}")
        except Exception as e:
            self.logger.error("batch_create_error", error=str(e))
            raise RepositoryException(f"Unexpected error in batch create: {e}")

    async def batch_update(self, world_states: List[WorldState]) -> None:
        """Update multiple existing WorldState aggregates.

        Args:
            world_states: List of WorldState aggregates to update.

        Raises:
            ConcurrencyException: If version conflict detected.
            EntityNotFoundException: If any world state not found.
            RepositoryException: If database or validation error occurs.
        """
        if not world_states:
            return

        from ...domain.repositories.world_state_repo import EntityNotFoundException

        try:
            async with get_db_session() as session:
                for world_state in world_states:
                    existing_model = (
                        session.query(WorldStateModel)
                        .filter(
                            and_(
                                WorldStateModel.id == uuid.UUID(world_state.id),
                                WorldStateModel.is_deleted.is_(False),
                            )
                        )
                        .first()
                    )

                    if not existing_model:
                        raise EntityNotFoundException(
                            f"World state {world_state.id} not found"
                        )

                    # Check version for optimistic concurrency
                    if existing_model.version != world_state.version:
                        raise ConcurrencyException(
                            f"Version conflict for world state {world_state.id}",
                            expected_version=world_state.version,
                            actual_version=int(existing_model.version),
                        )

                    world_state.version += 1
                    await self._create_version_entry(
                        session, world_state, existing_model
                    )
                    existing_model.update_from_domain_aggregate(world_state)

                    # Validate
                    validation_errors = existing_model.validate()
                    if validation_errors:
                        raise RepositoryException(
                            f"Validation failed for {world_state.id}: {'; '.join(validation_errors)}"
                        )

                    # Publish events
                    for event in world_state.get_domain_events():
                        await publish_event_transactionally(session, event)

                    world_state.clear_domain_events()

                await session.commit()
                self.logger.info("batch_updated_world_states", count=len(world_states))

        except (ConcurrencyException, EntityNotFoundException):
            raise
        except SQLAlchemyError as e:
            self.logger.error("batch_update_database_error", error=str(e))
            raise RepositoryException(f"Failed to batch update world states: {e}")
        except Exception as e:
            self.logger.error("batch_update_error", error=str(e))
            raise RepositoryException(f"Unexpected error in batch update: {e}")

    async def _create_version_entry(
        self,
        session: Any,
        world_state: WorldState,
        previous_model: Optional[WorldStateModel],
    ) -> None:
        """Create a version history entry for the world state.

        This is a helper method used internally by batch operations.

        Args:
            session: The database session.
            world_state: The current world state.
            previous_model: The previous model state (None for new entities).
        """
        from .models import WorldStateVersionModel

        try:
            # Simplified version entry creation
            # Note: entities and environment tracking not yet implemented
            version_model = WorldStateVersionModel(
                world_state_id=world_state.id,
                version_number=world_state.version,
                previous_version=previous_model.version if previous_model else None,
                change_reason="World state update",
                change_summary=f"Version {world_state.version} update",
                version_data={},  # Simplified - no to_dict method available
                entities_added=0,
                entities_removed=0,
                entities_modified=0,
                environment_changed=False,
            )

            session.add(version_model)

        except Exception as e:
            self.logger.error(
                "create_version_entry_error",
                world_state_id=world_state.id,
                error=str(e),
            )
            raise
