"""Main repository facade combining all world state operations."""

from typing import Any, Dict, List, Optional

from ...domain.aggregates.world_state import WorldState
from ...domain.ports import WorldStateRepositoryPort
from ...domain.value_objects.coordinates import Coordinates
from .postgres_world_state_batch import PostgresWorldStateBatch
from .postgres_world_state_crud import PostgresWorldStateCrud
from .postgres_world_state_queries import PostgresWorldStateQueries
from .postgres_world_state_snapshots import PostgresWorldStateSnapshots
from .postgres_world_state_versioning import PostgresWorldStateVersioning

__all__ = [
    "PostgresWorldStateRepository",
    "PostgresWorldStateCrud",
    "PostgresWorldStateQueries",
    "PostgresWorldStateVersioning",
    "PostgresWorldStateSnapshots",
    "PostgresWorldStateBatch",
]


class PostgresWorldStateRepository(WorldStateRepositoryPort):
    """Facade providing unified access to all world state operations."""

    def __init__(self) -> None:
        self._crud = PostgresWorldStateCrud()
        self._queries = PostgresWorldStateQueries()
        self._versioning = PostgresWorldStateVersioning()
        self._snapshots = PostgresWorldStateSnapshots()
        self._batch = PostgresWorldStateBatch()

    async def save(self, world_state: WorldState) -> WorldState:
        return await self._crud.save(world_state)

    async def get_by_id(self, world_state_id: str) -> Optional[WorldState]:
        return await self._crud.get_by_id(world_state_id)

    async def get_by_id_or_raise(self, world_state_id: str) -> WorldState:
        return await self._crud.get_by_id_or_raise(world_state_id)

    async def delete(self, world_state_id: str) -> bool:
        return await self._crud.delete(world_state_id)

    async def exists(self, world_state_id: str) -> bool:
        return await self._crud.exists(world_state_id)

    async def get_all(self, offset: int = 0, limit: int = 100) -> List[WorldState]:
        return await self._queries.get_all(offset=offset, limit=limit)

    async def find_by_name(self, name: str) -> Optional[WorldState]:
        return await self._queries.find_by_name(name)

    async def find_by_criteria(
        self, criteria: Dict[str, Any], offset: int = 0, limit: int = 100
    ) -> List[WorldState]:
        return await self._queries.find_by_criteria(
            criteria, offset=offset, limit=limit
        )

    async def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        return await self._queries.count(criteria)

    async def find_entities_by_type(
        self, world_state_id: str, entity_type: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self._queries.find_entities_by_type(
            world_state_id, entity_type, offset=offset, limit=limit
        )

    async def find_entities_in_area(
        self,
        world_state_id: str,
        center: Coordinates,
        radius: float,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return await self._queries.find_entities_in_area(
            world_state_id, center, radius, entity_types
        )

    async def find_entities_by_coordinates(
        self, world_state_id: str, coordinates: Coordinates, tolerance: float = 0.0
    ) -> List[Dict[str, Any]]:
        return await self._queries.find_entities_by_coordinates(
            world_state_id, coordinates, tolerance
        )

    async def get_version(
        self, world_state_id: str, version: int
    ) -> Optional[WorldState]:
        return await self._versioning.get_version(world_state_id, version)

    async def get_version_history(
        self, world_state_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return await self._versioning.get_version_history(world_state_id, limit)

    async def rollback_to_version(
        self, world_state_id: str, version: int
    ) -> WorldState:
        return await self._versioning.rollback_to_version(world_state_id, version)

    async def get_events_since(
        self, world_state_id: str, since_version: int
    ) -> List[Dict[str, Any]]:
        return await self._versioning.get_events_since(world_state_id, since_version)

    async def replay_events(
        self, world_state_id: str, to_version: Optional[int] = None
    ) -> Optional[WorldState]:
        return await self._versioning.replay_events(world_state_id, to_version)

    async def create_snapshot(
        self,
        world_state_id: str,
        snapshot_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return await self._snapshots.create_snapshot(
            world_state_id, snapshot_name, metadata
        )

    async def restore_from_snapshot(
        self, world_state_id: str, snapshot_id: str
    ) -> WorldState:
        return await self._snapshots.restore_from_snapshot(world_state_id, snapshot_id)

    async def list_snapshots(self, world_state_id: str) -> List[Dict[str, Any]]:
        return await self._snapshots.list_snapshots(world_state_id)

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        return await self._snapshots.delete_snapshot(snapshot_id)

    async def save_batch(self, world_states: List[WorldState]) -> List[WorldState]:
        return await self._batch.save_batch(world_states)

    async def delete_batch(self, world_state_ids: List[str]) -> Dict[str, bool]:
        return await self._batch.delete_batch(world_state_ids)

    async def batch_create(self, world_states: List[WorldState]) -> List[str]:
        return await self._batch.batch_create(world_states)

    async def batch_update(self, world_states: List[WorldState]) -> None:
        await self._batch.batch_update(world_states)

    async def optimize_storage(self, world_state_id: str) -> Dict[str, Any]:
        import uuid as uuid_mod
        from datetime import datetime

        from sqlalchemy.exc import SQLAlchemyError

        from core_platform.persistence.database import get_db_session

        from ...domain.repositories.world_state_repo import (
            EntityNotFoundException,
            RepositoryException,
        )
        from .models import WorldStateModel

        try:
            async with get_db_session() as session:
                model = (
                    session.query(WorldStateModel)
                    .filter(WorldStateModel.id == uuid_mod.UUID(world_state_id))
                    .first()
                )
                if not model:
                    raise EntityNotFoundException(
                        f"World state {world_state_id} not found"
                    )
                start_time = datetime.now()
                deleted = await self._versioning.cleanup_old_versions(
                    world_state_id, 50
                )
                world_state = model.to_domain_aggregate()
                world_state.rebuild_spatial_index()
                model.update_from_domain_aggregate(world_state)
                await session.commit()
                return {
                    "world_state_id": world_state_id,
                    "optimizations_performed": [
                        f"Cleaned {deleted} old versions",
                        "Rebuilt spatial index",
                    ],
                    "space_saved_bytes": 0,
                    "processing_time_ms": int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    ),
                }
        except EntityNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to optimize storage: {e}")
        except Exception as e:
            raise RepositoryException(f"Unexpected error optimizing storage: {e}")

    async def get_statistics(
        self, world_state_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._queries.get_statistics(world_state_id)
