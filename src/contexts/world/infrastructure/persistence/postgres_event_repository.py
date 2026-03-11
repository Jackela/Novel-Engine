# mypy: ignore-errors

#!/usr/bin/env python3
"""PostgreSQL Event Repository Implementation.

This module provides a PostgreSQL implementation of EventRepository
using asyncpg for async database operations.

Hexagonal Architecture:
- Infrastructure adapter implementing the domain port (EventRepository)
- Depends on asyncpg.Pool for database connectivity
- Maps between database rows and HistoryEvent domain entities
"""

from typing import Any, List, Optional
from uuid import UUID

import asyncpg
import structlog

from src.contexts.world.domain.entities.history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.ports.event_repository import EventRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

logger = structlog.get_logger()


class PostgreSQLEventRepository(EventRepository):
    """PostgreSQL implementation of EventRepository.

    Stores and retrieves HistoryEvent entities from PostgreSQL database.
    Uses asyncpg for async database operations with connection pooling.

    Attributes:
        _pool: asyncpg connection pool for database access

    Example:
        >>> pool = await asyncpg.create_pool(dsn="postgresql://...")
        >>> repo = PostgreSQLEventRepository(pool)
        >>> event = await repo.get_by_id("event-uuid")
    """

    def __init__(self, connection_pool: asyncpg.Pool) -> None:
        """Initialize the repository with a connection pool.

        Args:
            connection_pool: asyncpg.Pool for database connections
        """
        self._pool = connection_pool
        logger.debug("postgres_event_repository_initialized")

    async def get_by_id(self, event_id: str) -> Optional[HistoryEvent]:
        """Retrieve a specific event by its ID.

        Args:
            event_id: Unique identifier for the event

        Returns:
            HistoryEvent if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM history_events WHERE id = $1", UUID(event_id)
            )
            return self._row_to_entity(row) if row else None

    async def get_by_world_id(
        self, world_id: str, limit: int = 100, offset: int = 0
    ) -> List[HistoryEvent]:
        """Retrieve all events for a specific world with pagination.

        Since HistoryEvent doesn't have a direct world_id field, we use
        location_ids as a proxy - events are associated with worlds through
        their locations.

        Args:
            world_id: ID of the world (used as location_id proxy)
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of HistoryEvent objects, sorted by narrative_importance desc
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM history_events
                WHERE $1 = ANY(location_ids)
                ORDER BY narrative_importance DESC, name ASC
                LIMIT $2 OFFSET $3
                """,
                UUID(world_id),
                limit,
                offset,
            )
            return [self._row_to_entity(row) for row in rows]

    async def save(self, event: HistoryEvent) -> HistoryEvent:
        """Persist a history event.

        Uses UPSERT (INSERT ... ON CONFLICT) to handle both create and update.

        Args:
            event: The HistoryEvent to persist

        Returns:
            The saved HistoryEvent
        """
        structured_date_dict = None
        if event.structured_date:
            structured_date_dict = event.structured_date.to_dict()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO history_events (
                    id, name, description, event_type, significance, outcome,
                    date_description, duration_description, location_ids, faction_ids,
                    key_figures, causes, consequences, preceding_event_ids,
                    following_event_ids, related_event_ids, is_secret, sources,
                    narrative_importance, impact_scope, affected_faction_ids,
                    affected_location_ids, structured_date, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                         $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    event_type = EXCLUDED.event_type,
                    significance = EXCLUDED.significance,
                    outcome = EXCLUDED.outcome,
                    date_description = EXCLUDED.date_description,
                    duration_description = EXCLUDED.duration_description,
                    location_ids = EXCLUDED.location_ids,
                    faction_ids = EXCLUDED.faction_ids,
                    key_figures = EXCLUDED.key_figures,
                    causes = EXCLUDED.causes,
                    consequences = EXCLUDED.consequences,
                    preceding_event_ids = EXCLUDED.preceding_event_ids,
                    following_event_ids = EXCLUDED.following_event_ids,
                    related_event_ids = EXCLUDED.related_event_ids,
                    is_secret = EXCLUDED.is_secret,
                    sources = EXCLUDED.sources,
                    narrative_importance = EXCLUDED.narrative_importance,
                    impact_scope = EXCLUDED.impact_scope,
                    affected_faction_ids = EXCLUDED.affected_faction_ids,
                    affected_location_ids = EXCLUDED.affected_location_ids,
                    structured_date = EXCLUDED.structured_date,
                    updated_at = NOW()
                """,
                UUID(event.id),
                event.name,
                event.description,
                event.event_type.value,
                event.significance.value,
                event.outcome.value,
                event.date_description,
                event.duration_description,
                [UUID(lid) for lid in event.location_ids] if event.location_ids else [],
                [UUID(fid) for fid in event.faction_ids] if event.faction_ids else [],
                event.key_figures,
                event.causes,
                event.consequences,
                (
                    [UUID(eid) for eid in event.preceding_event_ids]
                    if event.preceding_event_ids
                    else []
                ),
                (
                    [UUID(eid) for eid in event.following_event_ids]
                    if event.following_event_ids
                    else []
                ),
                (
                    [UUID(eid) for eid in event.related_event_ids]
                    if event.related_event_ids
                    else []
                ),
                event.is_secret,
                event.sources,
                event.narrative_importance,
                event.impact_scope.value if event.impact_scope else None,
                (
                    [UUID(fid) for fid in event.affected_faction_ids]
                    if event.affected_faction_ids
                    else []
                ),
                (
                    [UUID(lid) for lid in event.affected_location_ids]
                    if event.affected_location_ids
                    else []
                ),
                structured_date_dict,
                event.created_at,
                event.updated_at,
            )

            logger.debug(
                "event_saved",
                event_id=event.id,
                event_name=event.name,
                event_type=event.event_type.value,
            )
            return event

    async def save_all(self, events: List[HistoryEvent]) -> List[HistoryEvent]:
        """Persist multiple history events in a single transaction.

        Args:
            events: List of HistoryEvent objects to persist

        Returns:
            List of saved HistoryEvent objects
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                saved_events: list[Any] = []
                for event in events:
                    await self.save(event)
                    saved_events.append(event)

                logger.info(
                    "events_batch_saved",
                    count=len(saved_events),
                )
                return saved_events

    async def delete(self, event_id: str) -> bool:
        """Remove an event from the repository.

        Args:
            event_id: Unique identifier for the event

        Returns:
            True if event was deleted, False if it didn't exist
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM history_events WHERE id = $1", UUID(event_id)
            )
            # result is like "DELETE 1" or "DELETE 0"
            deleted = result != "DELETE 0"

            if deleted:
                logger.debug("event_deleted", event_id=event_id)
            return deleted

    async def get_by_location_id(self, location_id: str) -> List[HistoryEvent]:
        """Retrieve all events that occurred at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of HistoryEvent objects associated with the location
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM history_events
                WHERE $1 = ANY(location_ids)
                ORDER BY narrative_importance DESC, name ASC
                """,
                UUID(location_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def get_by_faction_id(self, faction_id: str) -> List[HistoryEvent]:
        """Retrieve all events involving a specific faction.

        Args:
            faction_id: ID of the faction

        Returns:
            List of HistoryEvent objects where the faction was involved
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM history_events
                WHERE $1 = ANY(faction_ids)
                ORDER BY narrative_importance DESC, name ASC
                """,
                UUID(faction_id),
            )
            return [self._row_to_entity(row) for row in rows]

    async def clear(self) -> None:
        """Clear all events from the repository.

        This is a utility method primarily used for testing.
        """
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM history_events")
            logger.debug("all_events_cleared")

    def _row_to_entity(self, row: asyncpg.Record) -> HistoryEvent:
        """Convert a database row to a HistoryEvent entity.

        Args:
            row: asyncpg Record from database query

        Returns:
            HistoryEvent domain entity
        """
        # Parse structured_date from JSONB
        structured_date = None
        if row["structured_date"]:
            structured_date = WorldCalendar.from_dict(row["structured_date"])

        # Parse impact_scope enum
        impact_scope = None
        if row["impact_scope"]:
            impact_scope = ImpactScope(row["impact_scope"])

        # Convert UUID arrays to string lists
        location_ids = (
            [str(lid) for lid in row["location_ids"]] if row["location_ids"] else []
        )
        faction_ids = (
            [str(fid) for fid in row["faction_ids"]] if row["faction_ids"] else []
        )
        preceding_event_ids = (
            [str(eid) for eid in row["preceding_event_ids"]]
            if row["preceding_event_ids"]
            else []
        )
        following_event_ids = (
            [str(eid) for eid in row["following_event_ids"]]
            if row["following_event_ids"]
            else []
        )
        related_event_ids = (
            [str(eid) for eid in row["related_event_ids"]]
            if row["related_event_ids"]
            else []
        )
        affected_faction_ids = (
            [str(fid) for fid in row["affected_faction_ids"]]
            if row["affected_faction_ids"]
            else []
        )
        affected_location_ids = (
            [str(lid) for lid in row["affected_location_ids"]]
            if row["affected_location_ids"]
            else []
        )

        return HistoryEvent(
            id=str(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            event_type=EventType(row["event_type"]),
            significance=EventSignificance(row["significance"]),
            outcome=EventOutcome(row["outcome"]),
            date_description=row["date_description"],
            duration_description=row["duration_description"],
            location_ids=location_ids,
            faction_ids=faction_ids,
            key_figures=list(row["key_figures"]) if row["key_figures"] else [],
            causes=list(row["causes"]) if row["causes"] else [],
            consequences=list(row["consequences"]) if row["consequences"] else [],
            preceding_event_ids=preceding_event_ids,
            following_event_ids=following_event_ids,
            related_event_ids=related_event_ids,
            is_secret=row["is_secret"],
            sources=list(row["sources"]) if row["sources"] else [],
            narrative_importance=row["narrative_importance"],
            impact_scope=impact_scope,
            affected_faction_ids=affected_faction_ids if affected_faction_ids else None,
            affected_location_ids=(
                affected_location_ids if affected_location_ids else None
            ),
            structured_date=structured_date,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=1,  # Version tracking can be enhanced later
        )
