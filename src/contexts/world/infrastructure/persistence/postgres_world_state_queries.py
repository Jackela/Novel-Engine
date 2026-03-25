"""Query operations for world state.

This module provides the PostgresWorldStateQueries class for complex
queries and searches on WorldState aggregates.
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
from ...domain.value_objects.coordinates import Coordinates
from .models import WorldStateModel

logger = structlog.get_logger(__name__)


class PostgresWorldStateQueries:
    """Handles complex queries and searches for WorldState.

    This class encapsulates all query operations including pagination,
    filtering, searching, and entity-specific queries.
    """

    def __init__(self) -> None:
        """Initialize the queries handler."""
        self.logger = logger.bind(component=self.__class__.__name__)

    async def get_all(self, offset: int = 0, limit: int = 100) -> List[WorldState]:
        """Retrieve all WorldState aggregates with pagination.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of WorldState aggregates.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                models = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.is_deleted.is_(False))
                    .order_by(WorldStateModel.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                return [
                    model.to_domain_aggregate()
                    for model in models
                    if model.to_domain_aggregate() is not None
                ]

        except SQLAlchemyError as e:
            self.logger.error("all_world_states_retrieval_database_error", error=str(e))
            raise RepositoryException(f"Failed to retrieve world states: {e}")
        except Exception as e:
            self.logger.error("all_world_states_retrieval_error", error=str(e))
            raise RepositoryException(f"Unexpected error retrieving world states: {e}")

    async def find_by_name(self, name: str) -> Optional[WorldState]:
        """Find a WorldState aggregate by its name.

        Args:
            name: The name to search for.

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
                            WorldStateModel.name == name,
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
                "world_state_find_by_name_database_error", name=name, error=str(e)
            )
            raise RepositoryException(f"Failed to find world state by name: {e}")
        except Exception as e:
            self.logger.error("world_state_find_by_name_error", name=name, error=str(e))
            raise RepositoryException(
                f"Unexpected error finding world state by name: {e}"
            )

    async def find_by_criteria(
        self, criteria: Dict[str, Any], offset: int = 0, limit: int = 100
    ) -> List[WorldState]:
        """Find WorldState aggregates matching specific criteria.

        Supported criteria:
        - name: Partial match (case-insensitive)
        - status: Exact match
        - description: Partial match (case-insensitive)
        - max_entities: Greater than or equal
        - created_after: Created after datetime
        - created_before: Created before datetime
        - version: Exact match

        Args:
            criteria: Dictionary of filter criteria.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of WorldState aggregates matching criteria.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                query = session.query(WorldStateModel).filter(
                    WorldStateModel.is_deleted.is_(False)
                )

                # Apply criteria filters
                for key, value in criteria.items():
                    if key == "name":
                        query = query.filter(WorldStateModel.name.ilike(f"%{value}%"))
                    elif key == "status":
                        query = query.filter(WorldStateModel.status == value)
                    elif key == "description":
                        query = query.filter(
                            WorldStateModel.description.ilike(f"%{value}%")
                        )
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
                return [
                    model.to_domain_aggregate()
                    for model in models
                    if model.to_domain_aggregate() is not None
                ]

        except SQLAlchemyError as e:
            self.logger.error(
                "find_world_states_by_criteria_database_error", error=str(e)
            )
            raise RepositoryException(f"Failed to find world states by criteria: {e}")
        except Exception as e:
            self.logger.error("find_world_states_by_criteria_error", error=str(e))
            raise RepositoryException(
                f"Unexpected error finding world states by criteria: {e}"
            )

    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """Count WorldState aggregates matching optional criteria.

        Args:
            criteria: Optional dictionary of filter criteria.

        Returns:
            Number of matching WorldState aggregates.

        Raises:
            RepositoryException: If database error occurs.
        """
        try:
            async with get_db_session() as session:
                query = session.query(WorldStateModel).filter(
                    WorldStateModel.is_deleted.is_(False)
                )

                if criteria:
                    # Apply same criteria logic as find_by_criteria
                    for key, value in criteria.items():
                        if key == "name":
                            query = query.filter(
                                WorldStateModel.name.ilike(f"%{value}%")
                            )
                        elif key == "status":
                            query = query.filter(WorldStateModel.status == value)
                        # Add other criteria as needed

                count_result: int = query.count()
                return count_result

        except SQLAlchemyError as e:
            self.logger.error("count_world_states_database_error", error=str(e))
            raise RepositoryException(f"Failed to count world states: {e}")
        except Exception as e:
            self.logger.error("count_world_states_error", error=str(e))
            raise RepositoryException(f"Unexpected error counting world states: {e}")

    async def find_entities_by_type(
        self, world_state_id: str, entity_type: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find entities within a world state by their type.

        Args:
            world_state_id: The ID of the world state to search in.
            entity_type: The type of entities to find.
            offset: Number of entities to skip.
            limit: Maximum number of entities to return.

        Returns:
            List of entity dictionaries matching the type.

        Raises:
            EntityNotFoundException: If world state not found.
            RepositoryException: If query fails.
        """
        from .postgres_world_state_crud import PostgresWorldStateCrud

        try:
            crud = PostgresWorldStateCrud()
            world_state = await crud.get_by_id_or_raise(world_state_id)

            # Filter entities by type
            matching_entities: list[Any] = []
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
            self.logger.error(
                "find_entities_by_type_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find entities by type: {e}")

    async def find_entities_in_area(
        self,
        world_state_id: str,
        center: Coordinates,
        radius: float,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find entities within a specific geographical area.

        Args:
            world_state_id: The ID of the world state to search in.
            center: Center coordinates of the search area.
            radius: Search radius.
            entity_types: Optional list of entity types to filter by.

        Returns:
            List of entity dictionaries within the area, sorted by distance.

        Raises:
            EntityNotFoundException: If world state not found.
            RepositoryException: If query fails.
        """
        from .postgres_world_state_crud import PostgresWorldStateCrud

        try:
            crud = PostgresWorldStateCrud()
            world_state = await crud.get_by_id_or_raise(world_state_id)

            # Filter entities within radius
            matching_entities: list[Any] = []
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
            self.logger.error(
                "find_entities_in_area_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find entities in area: {e}")

    async def find_entities_by_coordinates(
        self, world_state_id: str, coordinates: Coordinates, tolerance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Find entities at specific coordinates (with optional tolerance).

        Args:
            world_state_id: The ID of the world state to search in.
            coordinates: Target coordinates.
            tolerance: Distance tolerance for matching.

        Returns:
            List of entity dictionaries at/near the coordinates, sorted by distance.

        Raises:
            EntityNotFoundException: If world state not found.
            RepositoryException: If query fails.
        """
        from .postgres_world_state_crud import PostgresWorldStateCrud

        try:
            crud = PostgresWorldStateCrud()
            world_state = await crud.get_by_id_or_raise(world_state_id)

            matching_entities: list[Any] = []
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
                "find_entities_by_coordinates_error",
                world_state_id=world_state_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find entities by coordinates: {e}")

    async def get_statistics(
        self, world_state_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get storage statistics for world states."""
        from .models import WorldStateSnapshotModel, WorldStateVersionModel

        try:
            async with get_db_session() as session:
                if world_state_id:
                    model = (
                        session.query(WorldStateModel)
                        .filter(WorldStateModel.id == uuid.UUID(world_state_id))
                        .first()
                    )

                    if not model:
                        raise EntityNotFoundException(
                            f"World state {world_state_id} not found"
                        )

                    version_count = (
                        session.query(WorldStateVersionModel)
                        .filter(
                            WorldStateVersionModel.world_state_id
                            == uuid.UUID(world_state_id)
                        )
                        .count()
                    )

                    snapshot_count = (
                        session.query(WorldStateSnapshotModel)
                        .filter(
                            WorldStateSnapshotModel.world_state_id
                            == uuid.UUID(world_state_id)
                        )
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
                    total_worlds = (
                        session.query(WorldStateModel)
                        .filter(WorldStateModel.is_deleted.is_(False))
                        .count()
                    )

                    total_entities = 0
                    active_worlds = (
                        session.query(WorldStateModel)
                        .filter(
                            and_(
                                WorldStateModel.is_deleted.is_(False),
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
                        "average_entities_per_world": total_entities
                        / max(len(active_worlds), 1),
                    }

        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            self.logger.error("get_statistics_database_error", error=str(e))
            raise RepositoryException(f"Failed to get statistics: {e}")
        except Exception as e:
            self.logger.error("get_statistics_error", error=str(e))
            raise RepositoryException(f"Unexpected error getting statistics: {e}")
