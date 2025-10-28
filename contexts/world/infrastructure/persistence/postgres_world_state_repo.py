#!/usr/bin/env python3
"""
PostgreSQL World State Repository Implementation

Concrete implementation of IWorldStateRepository using PostgreSQL with SQLAlchemy.
This implementation provides full repository functionality including CRUD operations,
spatial queries, versioning, snapshots, and reliable event publishing.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core_platform.messaging.outbox import publish_event_transactionally
from core_platform.persistence.database import get_db_session
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...domain.aggregates.world_state import WorldState
from ...domain.repositories.world_state_repo import (
    ConcurrencyException,
    EntityNotFoundException,
    IWorldStateRepository,
    RepositoryException,
)
from ...domain.value_objects.coordinates import Coordinates
from .models import WorldStateModel, WorldStateSnapshotModel, WorldStateVersionModel

logger = logging.getLogger(__name__)


class PostgresWorldStateRepository(IWorldStateRepository):
    """
    PostgreSQL implementation of IWorldStateRepository.

    This implementation provides:
    - Full CRUD operations with transaction support
    - Optimistic concurrency control using versioning
    - Spatial queries for entity location searches
    - Version history tracking and rollback capabilities
    - Snapshot creation and restoration
    - Reliable domain event publishing via Outbox pattern
    - Performance optimization through spatial indexing
    """

    def __init__(self):
        """Initialize the repository."""
        self.logger = logger.getChild(self.__class__.__name__)

    # Basic CRUD Operations

    async def save(self, world_state: WorldState) -> WorldState:
        """
        Save a WorldState aggregate to PostgreSQL storage.

        Handles both create and update operations with optimistic concurrency control.
        Domain events are published reliably using the Outbox pattern.
        """
        try:
            with get_db_session() as session:
                # Check if this is an update or create
                existing_model = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.id == uuid.UUID(world_state.id))
                    .first()
                )

                if existing_model:
                    # Update operation - check version for optimistic concurrency
                    if existing_model.version != world_state.version:
                        raise ConcurrencyException(
                            f"Version conflict for world state {world_state.id}",
                            expected_version=world_state.version,
                            actual_version=existing_model.version,
                        )

                    # Increment version for the update
                    world_state.version += 1

                    # Create version history entry
                    await self._create_version_entry(session, world_state, existing_model)

                    # Update existing model
                    existing_model.update_from_domain_aggregate(world_state)
                    model_to_save = existing_model

                    self.logger.info(
                        f"Updated world state {world_state.id} to version {world_state.version}"
                    )

                else:
                    # Create operation
                    world_state.version = 1
                    model_to_save = WorldStateModel.from_domain_aggregate(world_state)
                    session.add(model_to_save)

                    # Create initial version entry
                    await self._create_version_entry(session, world_state, None)

                    self.logger.info(f"Created new world state {world_state.id}")

                # Validate the model before saving
                validation_errors = model_to_save.validate()
                if validation_errors:
                    raise RepositoryException(f"Validation failed: {'; '.join(validation_errors)}")

                # Publish domain events within the same transaction
                domain_events = world_state.get_domain_events()
                for event in domain_events:
                    await publish_event_transactionally(session, event)

                # Clear events from aggregate (they're now persisted)
                world_state.clear_domain_events()

                # Commit transaction (includes outbox events)
                session.commit()

                # Return the saved aggregate with updated version
                return model_to_save.to_domain_aggregate()

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error saving world state {world_state.id}: {e}")
            raise RepositoryException(f"Failed to save world state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error saving world state {world_state.id}: {e}")
            raise RepositoryException(f"Unexpected error saving world state: {e}")

    async def get_by_id(self, world_state_id: str) -> Optional[WorldState]:
        """Retrieve a WorldState aggregate by its unique identifier."""
        try:
            with get_db_session() as session:
                model = (
                    session.query(WorldStateModel)
                    .filter(
                        and_(
                            WorldStateModel.id == uuid.UUID(world_state_id),
                            WorldStateModel.is_deleted is False,
                        )
                    )
                    .first()
                )

                if model:
                    return model.to_domain_aggregate()
                return None

        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving world state {world_state_id}: {e}")
            raise RepositoryException(f"Failed to retrieve world state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving world state {world_state_id}: {e}")
            raise RepositoryException(f"Unexpected error retrieving world state: {e}")

    async def get_by_id_or_raise(self, world_state_id: str) -> WorldState:
        """Retrieve a WorldState aggregate by ID or raise exception if not found."""
        world_state = await self.get_by_id(world_state_id)
        if world_state is None:
            raise EntityNotFoundException(f"World state with ID {world_state_id} not found")
        return world_state

    async def delete(self, world_state_id: str) -> bool:
        """Delete a WorldState aggregate using soft delete."""
        try:
            with get_db_session() as session:
                model = (
                    session.query(WorldStateModel)
                    .filter(
                        and_(
                            WorldStateModel.id == uuid.UUID(world_state_id),
                            WorldStateModel.is_deleted is False,
                        )
                    )
                    .first()
                )

                if not model:
                    return False

                # Soft delete
                model.soft_delete()
                session.commit()

                self.logger.info(f"Soft deleted world state {world_state_id}")
                return True

        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting world state {world_state_id}: {e}")
            raise RepositoryException(f"Failed to delete world state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error deleting world state {world_state_id}: {e}")
            raise RepositoryException(f"Unexpected error deleting world state: {e}")

    async def exists(self, world_state_id: str) -> bool:
        """Check if a WorldState aggregate exists in storage."""
        try:
            with get_db_session() as session:
                count = (
                    session.query(WorldStateModel)
                    .filter(
                        and_(
                            WorldStateModel.id == uuid.UUID(world_state_id),
                            WorldStateModel.is_deleted is False,
                        )
                    )
                    .count()
                )
                return count > 0

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error checking existence of world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to check world state existence: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error checking existence of world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error checking world state existence: {e}")

    # Query Operations

    async def get_all(self, offset: int = 0, limit: int = 100) -> List[WorldState]:
        """Retrieve all WorldState aggregates with pagination."""
        try:
            with get_db_session() as session:
                models = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.is_deleted is False)
                    .order_by(WorldStateModel.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                return [model.to_domain_aggregate() for model in models]

        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving all world states: {e}")
            raise RepositoryException(f"Failed to retrieve world states: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving all world states: {e}")
            raise RepositoryException(f"Unexpected error retrieving world states: {e}")

    async def find_by_name(self, name: str) -> Optional[WorldState]:
        """Find a WorldState aggregate by its name."""
        try:
            with get_db_session() as session:
                model = (
                    session.query(WorldStateModel)
                    .filter(
                        and_(
                            WorldStateModel.name == name,
                            WorldStateModel.is_deleted is False,
                        )
                    )
                    .first()
                )

                if model:
                    return model.to_domain_aggregate()
                return None

        except SQLAlchemyError as e:
            self.logger.error(f"Database error finding world state by name '{name}': {e}")
            raise RepositoryException(f"Failed to find world state by name: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error finding world state by name '{name}': {e}")
            raise RepositoryException(f"Unexpected error finding world state by name: {e}")

    async def find_by_criteria(
        self, criteria: Dict[str, Any], offset: int = 0, limit: int = 100
    ) -> List[WorldState]:
        """Find WorldState aggregates matching specific criteria."""
        try:
            with get_db_session() as session:
                query = session.query(WorldStateModel).filter(WorldStateModel.is_deleted is False)

                # Apply criteria filters
                for key, value in criteria.items():
                    if key == "name":
                        query = query.filter(WorldStateModel.name.ilike(f"%{value}%"))
                    elif key == "status":
                        query = query.filter(WorldStateModel.status == value)
                    elif key == "description":
                        query = query.filter(WorldStateModel.description.ilike(f"%{value}%"))
                    elif key == "max_entities":
                        query = query.filter(WorldStateModel.max_entities >= value)
                    elif key == "created_after":
                        query = query.filter(WorldStateModel.created_at >= value)
                    elif key == "created_before":
                        query = query.filter(WorldStateModel.created_at <= value)
                    elif key == "version":
                        query = query.filter(WorldStateModel.version == value)
                    # Add more criteria as needed

                models = (
                    query.order_by(WorldStateModel.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )
                return [model.to_domain_aggregate() for model in models]

        except SQLAlchemyError as e:
            self.logger.error(f"Database error finding world states by criteria: {e}")
            raise RepositoryException(f"Failed to find world states by criteria: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error finding world states by criteria: {e}")
            raise RepositoryException(f"Unexpected error finding world states by criteria: {e}")

    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """Count WorldState aggregates matching optional criteria."""
        try:
            with get_db_session() as session:
                query = session.query(WorldStateModel).filter(WorldStateModel.is_deleted is False)

                if criteria:
                    # Apply same criteria logic as find_by_criteria
                    for key, value in criteria.items():
                        if key == "name":
                            query = query.filter(WorldStateModel.name.ilike(f"%{value}%"))
                        elif key == "status":
                            query = query.filter(WorldStateModel.status == value)
                        # Add other criteria as needed

                return query.count()

        except SQLAlchemyError as e:
            self.logger.error(f"Database error counting world states: {e}")
            raise RepositoryException(f"Failed to count world states: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error counting world states: {e}")
            raise RepositoryException(f"Unexpected error counting world states: {e}")

    # Entity-specific Operations

    async def find_entities_by_type(
        self, world_state_id: str, entity_type: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find entities within a world state by their type."""
        try:
            world_state = await self.get_by_id_or_raise(world_state_id)

            # Filter entities by type
            matching_entities = []
            count = 0

            for entity_id, entity in world_state.entities.items():
                if entity.entity_type.value == entity_type:
                    if count >= offset:
                        matching_entities.append(entity.to_dict())
                    count += 1

                    if len(matching_entities) >= limit:
                        break

            return matching_entities

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error finding entities by type in world {world_state_id}: {e}")
            raise RepositoryException(f"Failed to find entities by type: {e}")

    async def find_entities_in_area(
        self,
        world_state_id: str,
        center: Coordinates,
        radius: float,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find entities within a specific geographical area."""
        try:
            world_state = await self.get_by_id_or_raise(world_state_id)

            # Filter entities within radius
            matching_entities = []

            for entity_id, entity in world_state.entities.items():
                # Calculate distance from center
                distance = entity.coordinates.distance_to(center)

                if distance <= radius:
                    # Apply entity type filter if specified
                    if entity_types is None or entity.entity_type.value in entity_types:
                        entity_dict = entity.to_dict()
                        entity_dict["distance_from_center"] = distance
                        matching_entities.append(entity_dict)

            # Sort by distance
            matching_entities.sort(key=lambda x: x["distance_from_center"])
            return matching_entities

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error finding entities in area for world {world_state_id}: {e}")
            raise RepositoryException(f"Failed to find entities in area: {e}")

    async def find_entities_by_coordinates(
        self, world_state_id: str, coordinates: Coordinates, tolerance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Find entities at specific coordinates (with optional tolerance)."""
        try:
            world_state = await self.get_by_id_or_raise(world_state_id)

            matching_entities = []

            for entity_id, entity in world_state.entities.items():
                distance = entity.coordinates.distance_to(coordinates)

                if distance <= tolerance:
                    entity_dict = entity.to_dict()
                    entity_dict["distance_from_target"] = distance
                    matching_entities.append(entity_dict)

            # Sort by distance
            matching_entities.sort(key=lambda x: x["distance_from_target"])
            return matching_entities

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                f"Error finding entities by coordinates for world {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to find entities by coordinates: {e}")

    # Versioning and History Operations

    async def get_version(self, world_state_id: str, version: int) -> Optional[WorldState]:
        """Retrieve a specific version of a WorldState aggregate."""
        try:
            with get_db_session() as session:
                version_model = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        and_(
                            WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id),
                            WorldStateVersionModel.version_number == version,
                        )
                    )
                    .first()
                )

                if not version_model:
                    return None

                # Reconstruct world state from version data
                return self._reconstruct_world_state_from_version_data(version_model.version_data)

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error retrieving version {version} of world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to retrieve world state version: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving version {version} of world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error retrieving world state version: {e}")

    async def get_version_history(
        self, world_state_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get version history for a WorldState aggregate."""
        try:
            with get_db_session() as session:
                versions = (
                    session.query(WorldStateVersionModel)
                    .filter(WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id))
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
                        "changed_by": (str(version.changed_by) if version.changed_by else None),
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
                f"Database error retrieving version history for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to retrieve version history: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving version history for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error retrieving version history: {e}")

    async def rollback_to_version(self, world_state_id: str, version: int) -> WorldState:
        """Rollback a WorldState aggregate to a previous version."""
        try:
            # Get the target version
            target_world_state = await self.get_version(world_state_id, version)
            if not target_world_state:
                raise EntityNotFoundException(
                    f"Version {version} not found for world state {world_state_id}"
                )

            # Get current world state
            current_world_state = await self.get_by_id_or_raise(world_state_id)

            # Create new version with rollback data
            target_world_state.version = (
                current_world_state.version
            )  # Will be incremented in save()

            # Add a domain event for the rollback
            from ...domain.events.world_events import WorldStateChanged

            rollback_event = WorldStateChanged.rollback_performed(
                aggregate_id=world_state_id,
                rollback_to_version=version,
                previous_version=current_world_state.version,
            )
            target_world_state.raise_domain_event(rollback_event)

            # Save the rolled-back state
            return await self.save(target_world_state)

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                f"Error rolling back world state {world_state_id} to version {version}: {e}"
            )
            raise RepositoryException(f"Failed to rollback world state: {e}")

    # Snapshot and Backup Operations

    async def create_snapshot(
        self,
        world_state_id: str,
        snapshot_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a named snapshot of a WorldState aggregate."""
        try:
            world_state = await self.get_by_id_or_raise(world_state_id)

            with get_db_session() as session:
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
                session.commit()

                self.logger.info(
                    f"Created snapshot '{snapshot_name}' for world state {world_state_id}"
                )
                return str(snapshot_model.id)

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error creating snapshot for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to create snapshot: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating snapshot for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error creating snapshot: {e}")

    async def restore_from_snapshot(self, world_state_id: str, snapshot_id: str) -> WorldState:
        """Restore a WorldState aggregate from a snapshot."""
        try:
            with get_db_session() as session:
                snapshot_model = (
                    session.query(WorldStateSnapshotModel)
                    .filter(
                        and_(
                            WorldStateSnapshotModel.id == uuid.UUID(snapshot_id),
                            WorldStateSnapshotModel.world_state_id == uuid.UUID(world_state_id),
                        )
                    )
                    .first()
                )

                if not snapshot_model:
                    raise EntityNotFoundException(
                        f"Snapshot {snapshot_id} not found for world state {world_state_id}"
                    )

                # Reconstruct world state from snapshot
                snapshot_data = snapshot_model.snapshot_data["world_state"]
                restored_world_state = self._reconstruct_world_state_from_version_data(
                    snapshot_data
                )

                # Get current version for increment
                current_world_state = await self.get_by_id_or_raise(world_state_id)
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
                return await self.save(restored_world_state)

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error restoring from snapshot {snapshot_id}: {e}")
            raise RepositoryException(f"Failed to restore from snapshot: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error restoring from snapshot {snapshot_id}: {e}")
            raise RepositoryException(f"Unexpected error restoring from snapshot: {e}")

    async def list_snapshots(self, world_state_id: str) -> List[Dict[str, Any]]:
        """List all snapshots for a WorldState aggregate."""
        try:
            with get_db_session() as session:
                snapshots = (
                    session.query(WorldStateSnapshotModel)
                    .filter(WorldStateSnapshotModel.world_state_id == uuid.UUID(world_state_id))
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
                f"Database error listing snapshots for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to list snapshots: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error listing snapshots for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error listing snapshots: {e}")

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a WorldState snapshot."""
        try:
            with get_db_session() as session:
                snapshot = (
                    session.query(WorldStateSnapshotModel)
                    .filter(WorldStateSnapshotModel.id == uuid.UUID(snapshot_id))
                    .first()
                )

                if not snapshot:
                    return False

                session.delete(snapshot)
                session.commit()

                self.logger.info(f"Deleted snapshot {snapshot_id}")
                return True

        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting snapshot {snapshot_id}: {e}")
            raise RepositoryException(f"Failed to delete snapshot: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error deleting snapshot {snapshot_id}: {e}")
            raise RepositoryException(f"Unexpected error deleting snapshot: {e}")

    # Batch Operations

    async def save_batch(self, world_states: List[WorldState]) -> List[WorldState]:
        """Save multiple WorldState aggregates in a single transaction."""
        if not world_states:
            return []

        try:
            with get_db_session() as session:
                saved_states = []

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
                                actual_version=existing_model.version,
                            )

                        world_state.version += 1
                        await self._create_version_entry(session, world_state, existing_model)
                        existing_model.update_from_domain_aggregate(world_state)
                        model_to_save = existing_model
                    else:
                        # Create new
                        world_state.version = 1
                        model_to_save = WorldStateModel.from_domain_aggregate(world_state)
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

                session.commit()
                self.logger.info(f"Batch saved {len(saved_states)} world states")
                return saved_states

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in batch save: {e}")
            raise RepositoryException(f"Failed to batch save world states: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in batch save: {e}")
            raise RepositoryException(f"Unexpected error in batch save: {e}")

    async def delete_batch(self, world_state_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple WorldState aggregates in a single transaction."""
        if not world_state_ids:
            return {}

        results = {}

        try:
            with get_db_session() as session:
                for world_state_id in world_state_ids:
                    model = (
                        session.query(WorldStateModel)
                        .filter(
                            and_(
                                WorldStateModel.id == uuid.UUID(world_state_id),
                                WorldStateModel.is_deleted is False,
                            )
                        )
                        .first()
                    )

                    if model:
                        model.soft_delete()
                        results[world_state_id] = True
                    else:
                        results[world_state_id] = False

                session.commit()
                self.logger.info(f"Batch deleted {sum(results.values())} world states")
                return results

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in batch delete: {e}")
            raise RepositoryException(f"Failed to batch delete world states: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in batch delete: {e}")
            raise RepositoryException(f"Unexpected error in batch delete: {e}")

    # Performance and Optimization

    async def optimize_storage(self, world_state_id: str) -> Dict[str, Any]:
        """Optimize storage for a WorldState aggregate."""
        try:
            with get_db_session() as session:
                # Get current world state
                model = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.id == uuid.UUID(world_state_id))
                    .first()
                )

                if not model:
                    raise EntityNotFoundException(f"World state {world_state_id} not found")

                optimization_results = {
                    "world_state_id": world_state_id,
                    "optimizations_performed": [],
                    "space_saved_bytes": 0,
                    "processing_time_ms": 0,
                }

                start_time = datetime.now()

                # Optimization 1: Clean up old version history (keep last 50 versions)
                version_count = (
                    session.query(WorldStateVersionModel)
                    .filter(WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id))
                    .count()
                )

                if version_count > 50:
                    # Delete old versions, keeping the latest 50
                    old_versions = (
                        session.query(WorldStateVersionModel)
                        .filter(WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id))
                        .order_by(WorldStateVersionModel.version_number.desc())
                        .offset(50)
                    )

                    deleted_count = old_versions.count()
                    for version in old_versions:
                        session.delete(version)

                    optimization_results["optimizations_performed"].append(
                        f"Cleaned {deleted_count} old versions"
                    )

                # Optimization 2: Rebuild spatial index for better performance
                world_state = model.to_domain_aggregate()
                world_state.rebuild_spatial_index()
                model.update_from_domain_aggregate(world_state)
                optimization_results["optimizations_performed"].append("Rebuilt spatial index")

                session.commit()

                end_time = datetime.now()
                optimization_results["processing_time_ms"] = int(
                    (end_time - start_time).total_seconds() * 1000
                )

                self.logger.info(f"Optimized storage for world state {world_state_id}")
                return optimization_results

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error optimizing storage for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to optimize storage: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error optimizing storage for world state {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error optimizing storage: {e}")

    async def get_statistics(self, world_state_id: Optional[str] = None) -> Dict[str, Any]:
        """Get storage statistics for world states."""
        try:
            with get_db_session() as session:
                if world_state_id:
                    # Statistics for specific world state
                    model = (
                        session.query(WorldStateModel)
                        .filter(WorldStateModel.id == uuid.UUID(world_state_id))
                        .first()
                    )

                    if not model:
                        raise EntityNotFoundException(f"World state {world_state_id} not found")

                    version_count = (
                        session.query(WorldStateVersionModel)
                        .filter(WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id))
                        .count()
                    )

                    snapshot_count = (
                        session.query(WorldStateSnapshotModel)
                        .filter(WorldStateSnapshotModel.world_state_id == uuid.UUID(world_state_id))
                        .count()
                    )

                    return {
                        "world_state_id": world_state_id,
                        "entity_count": model.get_entity_count(),
                        "version_count": version_count,
                        "snapshot_count": snapshot_count,
                        "current_version": model.version,
                        "status": model.status,
                        "entity_types_summary": model.get_entity_types_summary(),
                        "created_at": model.created_at.isoformat(),
                        "updated_at": model.updated_at.isoformat(),
                    }

                else:
                    # Global statistics
                    total_worlds = (
                        session.query(WorldStateModel)
                        .filter(WorldStateModel.is_deleted is False)
                        .count()
                    )

                    total_entities = 0
                    active_worlds = (
                        session.query(WorldStateModel)
                        .filter(
                            and_(
                                WorldStateModel.is_deleted is False,
                                WorldStateModel.status == "active",
                            )
                        )
                        .all()
                    )

                    for world in active_worlds:
                        total_entities += world.get_entity_count()

                    total_versions = session.query(WorldStateVersionModel).count()
                    total_snapshots = session.query(WorldStateSnapshotModel).count()

                    return {
                        "total_world_states": total_worlds,
                        "active_world_states": len(active_worlds),
                        "total_entities": total_entities,
                        "total_versions": total_versions,
                        "total_snapshots": total_snapshots,
                        "average_entities_per_world": total_entities / max(len(active_worlds), 1),
                    }

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting statistics: {e}")
            raise RepositoryException(f"Failed to get statistics: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting statistics: {e}")
            raise RepositoryException(f"Unexpected error getting statistics: {e}")

    # Event Sourcing Support

    async def get_events_since(
        self, world_state_id: str, since_version: int
    ) -> List[Dict[str, Any]]:
        """Get domain events for a world state since a specific version."""
        try:
            with get_db_session() as session:
                versions = (
                    session.query(WorldStateVersionModel)
                    .filter(
                        and_(
                            WorldStateVersionModel.world_state_id == uuid.UUID(world_state_id),
                            WorldStateVersionModel.version_number > since_version,
                        )
                    )
                    .order_by(WorldStateVersionModel.version_number.asc())
                    .all()
                )

                events = []
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
                        "changed_by": (str(version.changed_by) if version.changed_by else None),
                    }
                    events.append(event_data)

                return events

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error getting events since version {since_version} for world {world_state_id}: {e}"
            )
            raise RepositoryException(f"Failed to get events since version: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error getting events since version {since_version} for world {world_state_id}: {e}"
            )
            raise RepositoryException(f"Unexpected error getting events since version: {e}")

    async def replay_events(
        self, world_state_id: str, to_version: Optional[int] = None
    ) -> WorldState:
        """Reconstruct a WorldState aggregate by replaying domain events."""
        try:
            if to_version:
                # Replay to specific version
                return await self.get_version(world_state_id, to_version)
            else:
                # Replay to latest version
                return await self.get_by_id_or_raise(world_state_id)

        except EntityNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error replaying events for world state {world_state_id}: {e}")
            raise RepositoryException(f"Failed to replay events: {e}")

    # Private Helper Methods

    async def _create_version_entry(
        self,
        session: Session,
        world_state: WorldState,
        previous_model: Optional[WorldStateModel],
    ) -> None:
        """Create a version history entry for the world state."""
        try:
            # Calculate change statistics
            entities_added = 0
            entities_removed = 0
            entities_modified = 0
            environment_changed = False

            if previous_model:
                previous_world_state = previous_model.to_domain_aggregate()

                # Count entity changes
                current_entity_ids = set(world_state.entities.keys())
                previous_entity_ids = set(previous_world_state.entities.keys())

                entities_added = len(current_entity_ids - previous_entity_ids)
                entities_removed = len(previous_entity_ids - current_entity_ids)

                # Count modified entities
                common_entities = current_entity_ids & previous_entity_ids
                for entity_id in common_entities:
                    current_entity = world_state.entities[entity_id]
                    previous_entity = previous_world_state.entities[entity_id]

                    if current_entity.to_dict() != previous_entity.to_dict():
                        entities_modified += 1

                # Check environment changes
                environment_changed = world_state.environment != previous_world_state.environment

            version_model = WorldStateVersionModel(
                world_state_id=uuid.UUID(world_state.id),
                version_number=world_state.version,
                previous_version=previous_model.version if previous_model else None,
                change_reason="World state update",
                change_summary=f"Version {world_state.version} update",
                version_data=world_state.to_dict(),
                entities_added=entities_added,
                entities_removed=entities_removed,
                entities_modified=entities_modified,
                environment_changed=environment_changed,
            )

            session.add(version_model)

        except Exception as e:
            self.logger.error(f"Error creating version entry for world state {world_state.id}: {e}")
            raise

    def _reconstruct_world_state_from_version_data(
        self, version_data: Dict[str, Any]
    ) -> WorldState:
        """Reconstruct a WorldState aggregate from version data."""
        try:
            # Import here to avoid circular imports
            from ...domain.aggregates.world_state import (
                EntityType,
                WorldEntity,
                WorldState,
                WorldStatus,
            )
            from ...domain.value_objects.coordinates import Coordinates

            # Parse entities
            domain_entities = {}
            if version_data.get("entities"):
                for entity_id, entity_data in version_data["entities"].items():
                    if entity_data:
                        coordinates = Coordinates.from_dict(entity_data["coordinates"])
                        entity_type = EntityType(entity_data["entity_type"])

                        world_entity = WorldEntity(
                            id=entity_data["id"],
                            entity_type=entity_type,
                            name=entity_data["name"],
                            coordinates=coordinates,
                            properties=entity_data.get("properties", {}),
                            metadata=entity_data.get("metadata", {}),
                            created_at=(
                                datetime.fromisoformat(entity_data["created_at"])
                                if entity_data.get("created_at")
                                else datetime.now()
                            ),
                            updated_at=(
                                datetime.fromisoformat(entity_data["updated_at"])
                                if entity_data.get("updated_at")
                                else datetime.now()
                            ),
                        )
                        domain_entities[entity_id] = world_entity

            # Create world state
            world_state = WorldState(
                id=version_data["id"],
                name=version_data["name"],
                description=version_data.get("description"),
                status=WorldStatus(version_data["status"]),
                world_time=(
                    datetime.fromisoformat(version_data["world_time"])
                    if isinstance(version_data["world_time"], str)
                    else version_data["world_time"]
                ),
                entities=domain_entities,
                environment=version_data.get("environment", {}),
                spatial_index=version_data.get("spatial_index", {}),
                metadata=version_data.get("metadata", {}),
                max_entities=version_data.get("max_entities", 10000),
                spatial_grid_size=version_data.get("spatial_grid_size", 100.0),
                created_at=(
                    datetime.fromisoformat(version_data["created_at"])
                    if isinstance(version_data["created_at"], str)
                    else version_data["created_at"]
                ),
                updated_at=(
                    datetime.fromisoformat(version_data["updated_at"])
                    if isinstance(version_data["updated_at"], str)
                    else version_data["updated_at"]
                ),
                version=version_data["version"],
            )

            return world_state

        except Exception as e:
            self.logger.error(f"Error reconstructing world state from version data: {e}")
            raise RepositoryException(f"Failed to reconstruct world state from version data: {e}")
