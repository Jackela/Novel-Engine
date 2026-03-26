"""Basic CRUD operations for world state.

This module provides the PostgresWorldStateCrud class for basic
create, read, update, and delete operations on WorldState aggregates.
"""

import uuid
from typing import Any, Optional

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


class PostgresWorldStateCrud:
    """Handles create, read, update, delete operations for WorldState.

    This class encapsulates all basic CRUD operations with optimistic
    concurrency control and transaction support.
    """

    def __init__(self) -> None:
        """Initialize the CRUD operations handler."""
        self.logger = logger.bind(component=self.__class__.__name__)

    async def save(self, world_state: WorldState) -> WorldState:
        """Save a WorldState aggregate to PostgreSQL storage.

        Handles both create and update operations with optimistic concurrency control.
        Domain events are published reliably using the Outbox pattern.

        Args:
            world_state: The WorldState aggregate to save.

        Returns:
            The saved WorldState aggregate with updated version.

        Raises:
            ConcurrencyException: If version conflict detected.
            RepositoryException: If database or validation error occurs.
        """
        try:
            async with get_db_session() as session:
                # Check if this is an update or create
                existing_model = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.id == uuid.UUID(world_state.id))
                    .first()
                )

                if existing_model:
                    # Update operation - check version for optimistic concurrency
                    if int(existing_model.version) != world_state.version:
                        raise ConcurrencyException(
                            f"Version conflict for world state {world_state.id}",
                            expected_version=world_state.version,
                            actual_version=int(existing_model.version),
                        )

                    # Increment version for the update
                    world_state.version += 1

                    # Create version history entry
                    await self._create_version_entry(
                        session, world_state, existing_model
                    )

                    # Update existing model
                    existing_model.update_from_domain_aggregate(world_state)
                    model_to_save = existing_model

                    self.logger.info(
                        "world_state_updated",
                        world_state_id=world_state.id,
                        version=world_state.version,
                    )

                else:
                    # Create operation
                    world_state.version = 1
                    model_to_save = WorldStateModel.from_domain_aggregate(world_state)
                    session.add(model_to_save)

                    # Create initial version entry
                    await self._create_version_entry(session, world_state, None)

                    self.logger.info(
                        "world_state_created", world_state_id=world_state.id
                    )

                # Validate the model before saving
                validation_errors = model_to_save.validate()
                if validation_errors:
                    raise RepositoryException(
                        f"Validation failed: {'; '.join(validation_errors)}"
                    )

                # Publish domain events within the same transaction
                domain_events = world_state.get_domain_events()
                for event in domain_events:
                    await publish_event_transactionally(session, event)

                # Clear events from aggregate (they're now persisted)
                world_state.clear_domain_events()

                # Commit transaction (includes outbox events)
                await session.commit()

                # Return the saved aggregate with updated version
                result = model_to_save.to_domain_aggregate()
                if result is None:
                    raise RepositoryException(
                        "Failed to convert saved model to domain aggregate"
                    )
                return result  # type: ignore[no-any-return]

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_save_database_error",
                world_state_id=world_state.id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to save world state: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_save_error", world_state_id=world_state.id, error=str(e)
            )
            raise RepositoryException(f"Unexpected error saving world state: {e}")

    async def get_by_id(self, world_state_id: str) -> Optional[WorldState]:
        """Retrieve a WorldState aggregate by its unique identifier.

        Args:
            world_state_id: The unique identifier of the world state.

        Returns:
            The WorldState aggregate if found, None otherwise.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
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
                    result = model.to_domain_aggregate()
                    return result  # type: ignore[no-any-return]
                return None

        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_retrieval_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to retrieve world state: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_retrieval_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Unexpected error retrieving world state: {e}")

    async def get_by_id_or_raise(self, world_state_id: str) -> WorldState:
        """Retrieve a WorldState aggregate by ID or raise exception if not found.

        Args:
            world_state_id: The unique identifier of the world state.

        Returns:
            The WorldState aggregate.

        Raises:
            EntityNotFoundException: If world state not found.
        """
        from ...domain.repositories.world_state_repo import EntityNotFoundException

        world_state = await self.get_by_id(world_state_id)
        if world_state is None:
            raise EntityNotFoundException(
                f"World state with ID {world_state_id} not found"
            )
        return world_state

    async def delete(self, world_state_id: str) -> bool:
        """Delete a WorldState aggregate using soft delete.

        Args:
            world_state_id: The unique identifier of the world state to delete.

        Returns:
            True if deleted successfully, False if not found.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
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

                if not model:
                    return False

                # Soft delete
                model.soft_delete()
                await session.commit()

                self.logger.info(
                    "world_state_soft_deleted", world_state_id=world_state_id
                )
                return True

        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_deletion_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to delete world state: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_deletion_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Unexpected error deleting world state: {e}")

    async def exists(self, world_state_id: str) -> bool:
        """Check if a WorldState aggregate exists in storage.

        Args:
            world_state_id: The unique identifier to check.

        Returns:
            True if exists, False otherwise.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                count = (
                    session.query(WorldStateModel)
                    .filter(
                        and_(
                            WorldStateModel.id == uuid.UUID(world_state_id),
                            WorldStateModel.is_deleted.is_(False),
                        )
                    )
                    .count()
                )
                return count > 0  # type: ignore[no-any-return]

        except SQLAlchemyError as e:
            self.logger.error(
                "world_state_existence_check_database_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to check world state existence: {e}")
        except Exception as e:
            self.logger.error(
                "world_state_existence_check_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(
                f"Unexpected error checking world state existence: {e}"
            )

    async def _create_version_entry(
        self,
        session: Any,
        world_state: WorldState,
        previous_model: Optional[WorldStateModel],
    ) -> None:
        """Create a version history entry for the world state.

        This is a helper method used internally by save().

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
