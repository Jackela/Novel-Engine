#!/usr/bin/env python3
"""PostgreSQL Rumor Repository Implementation.

This module provides a PostgreSQL implementation of RumorRepository
using asyncpg for async database operations.

Hexagonal Architecture:
- Infrastructure adapter implementing the domain port (RumorRepository)
- Depends on asyncpg.Pool for database connectivity
- Maps between database rows and Rumor domain entities
"""

from typing import List, Optional, Set
from uuid import UUID

import asyncpg
import structlog

from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin
from src.contexts.world.domain.ports.rumor_repository import RumorRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

logger = structlog.get_logger()


class PostgreSQLRumorRepository(RumorRepository):
    """PostgreSQL implementation of RumorRepository.

    Stores and retrieves Rumor entities from PostgreSQL database.
    Uses asyncpg for async database operations with connection pooling.

    Attributes:
        _pool: asyncpg connection pool for database access

    Example:
        >>> pool = await asyncpg.create_pool(dsn="postgresql://...")
        >>> repo = PostgreSQLRumorRepository(pool)
        >>> rumors = await repo.get_active_rumors("world-uuid")
    """

    def __init__(self, connection_pool: asyncpg.Pool) -> None:
        """Initialize the repository with a connection pool.

        Args:
            connection_pool: asyncpg.Pool for database connections
        """
        self._pool = connection_pool
        logger.debug("postgres_rumor_repository_initialized")

    async def get_by_id(self, rumor_id: str) -> Optional[Rumor]:
        """Retrieve a specific rumor by its ID.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            Rumor if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM rumors WHERE id = $1", UUID(rumor_id)
            )
            return self._row_to_entity(row) if row else None

    async def get_active_rumors(self, world_id: str) -> List[Rumor]:
        """Retrieve all active rumors for a world (truth_value > 0).

        Since Rumor doesn't have a direct world_id field, we use
        origin_location_id as a proxy for world identification.

        Args:
            world_id: ID of the world (used as location_id proxy)

        Returns:
            List of active Rumor objects (truth_value > 0)
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM rumors
                WHERE origin_location_id = $1 AND truth_value > 0
                ORDER BY truth_value DESC, spread_count DESC
                """,
                UUID(world_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def get_by_world_id(self, world_id: str) -> List[Rumor]:
        """Retrieve all rumors for a specific world (including dead ones).

        Args:
            world_id: ID of the world (used as location_id proxy)

        Returns:
            List of all Rumor objects in the world
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM rumors
                WHERE origin_location_id = $1
                ORDER BY truth_value DESC
                """,
                UUID(world_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def save(self, rumor: Rumor) -> Rumor:
        """Persist a rumor.

        Uses UPSERT (INSERT ... ON CONFLICT) to handle both create and update.

        Args:
            rumor: The Rumor to persist

        Returns:
            The saved Rumor
        """
        created_date_dict = None
        if rumor.created_date:
            created_date_dict = rumor.created_date.to_dict()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO rumors (
                    id, content, truth_value, origin_type, source_event_id,
                    origin_location_id, current_locations, created_date,
                    spread_count, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    truth_value = EXCLUDED.truth_value,
                    origin_type = EXCLUDED.origin_type,
                    source_event_id = EXCLUDED.source_event_id,
                    origin_location_id = EXCLUDED.origin_location_id,
                    current_locations = EXCLUDED.current_locations,
                    created_date = EXCLUDED.created_date,
                    spread_count = EXCLUDED.spread_count
                """,
                UUID(rumor.rumor_id),
                rumor.content,
                rumor.truth_value,
                rumor.origin_type.value,
                UUID(rumor.source_event_id) if rumor.source_event_id else None,
                UUID(rumor.origin_location_id),
                (
                    [UUID(lid) for lid in rumor.current_locations]
                    if rumor.current_locations
                    else []
                ),
                created_date_dict,
                rumor.spread_count,
            )

            logger.debug(
                "rumor_saved",
                rumor_id=rumor.rumor_id,
                truth_value=rumor.truth_value,
                spread_count=rumor.spread_count,
            )
            return rumor

    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        """Persist multiple rumors in a single transaction.

        This is more efficient than calling save() multiple times,
        especially for database implementations that can batch inserts.

        Args:
            rumors: List of Rumor objects to persist

        Returns:
            List of saved Rumor objects
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                saved_rumors: list[Any] = []
                for rumor in rumors:
                    await self.save(rumor)
                    saved_rumors.append(rumor)

                logger.info(
                    "rumors_batch_saved",
                    count=len(saved_rumors),
                )
                return saved_rumors

    async def delete(self, rumor_id: str) -> bool:
        """Remove a rumor from the repository.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            True if rumor was deleted, False if it didn't exist
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM rumors WHERE id = $1", UUID(rumor_id)
            )
            deleted = result != "DELETE 0"

            if deleted:
                logger.debug("rumor_deleted", rumor_id=rumor_id)
            return deleted

    async def get_by_location_id(self, location_id: str) -> List[Rumor]:
        """Retrieve all rumors currently at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of Rumor objects that have spread to this location
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM rumors
                WHERE $1 = ANY(current_locations)
                ORDER BY truth_value DESC
                """,
                UUID(location_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def get_by_event_id(self, event_id: str) -> List[Rumor]:
        """Retrieve all rumors originating from a specific event.

        Args:
            event_id: ID of the source event

        Returns:
            List of Rumor objects that originated from this event
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM rumors
                WHERE source_event_id = $1
                ORDER BY truth_value DESC
                """,
                UUID(event_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def clear(self) -> None:
        """Clear all rumors from the repository.

        This is a utility method primarily used for testing.
        """
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM rumors")
            logger.debug("all_rumors_cleared")

    def _row_to_entity(self, row: asyncpg.Record) -> Rumor:
        """Convert a database row to a Rumor entity.

        Args:
            row: asyncpg Record from database query

        Returns:
            Rumor domain entity
        """
        # Parse created_date from JSONB
        created_date = None
        if row["created_date"]:
            created_date = WorldCalendar.from_dict(row["created_date"])

        # Convert current_locations UUID array to string set
        current_locations: Set[str] = set()
        if row["current_locations"]:
            current_locations = {str(lid) for lid in row["current_locations"]}

        return Rumor(
            rumor_id=str(row["id"]),
            content=row["content"],
            truth_value=row["truth_value"],
            origin_type=RumorOrigin(row["origin_type"]),
            source_event_id=(
                str(row["source_event_id"]) if row["source_event_id"] else None
            ),
            origin_location_id=str(row["origin_location_id"]),
            current_locations=current_locations,
            created_date=created_date,
            spread_count=row["spread_count"],
        )
