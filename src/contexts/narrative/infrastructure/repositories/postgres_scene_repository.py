"""PostgreSQL implementation of SceneRepositoryPort.

This module provides the PostgreSQL-based implementation of the
scene repository port interface using asyncpg for high-performance
async database operations.
"""

from typing import Any
from uuid import UUID

import asyncpg

from src.contexts.narrative.domain.entities.choice import Choice
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.ports.scene_repository_port import (
    SceneRepositoryPort,
)


class PostgresSceneRepository(SceneRepositoryPort):
    """PostgreSQL implementation of scene repository.

    Uses asyncpg for async database operations with connection pooling.

    Example:
        >>> async with db_pool.acquire() as conn:
        ...     repo = PostgresSceneRepository(conn)
        ...     scene = await repo.get_by_id(scene_id)
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg database connection.
        """
        self._connection = connection

    async def get_by_id(self, scene_id: UUID) -> Scene | None:
        """Get scene by ID.

        Args:
            scene_id: Scene UUID

        Returns:
            Scene if found, None otherwise
        """
        row = await self._connection.fetchrow(
            """
            SELECT
                id, chapter_id, scene_number, title, content,
                scene_type, choices, created_at, updated_at, metadata
            FROM scenes
            WHERE id = $1
            """,
            scene_id,
        )

        if not row:
            return None

        return self._row_to_scene(row)

    async def get_by_chapter(self, chapter_id: UUID) -> list[Scene]:
        """Get scenes by chapter ID.

        Args:
            chapter_id: Chapter UUID

        Returns:
            List of scenes belonging to the chapter, ordered by scene_number
        """
        rows = await self._connection.fetch(
            """
            SELECT
                id, chapter_id, scene_number, title, content,
                scene_type, choices, created_at, updated_at, metadata
            FROM scenes
            WHERE chapter_id = $1
            ORDER BY scene_number
            """,
            chapter_id,
        )

        return [self._row_to_scene(row) for row in rows]

    async def save(self, scene: Scene) -> None:
        """Save or update scene.

        Uses UPSERT pattern to handle both insert and update operations.

        Args:
            scene: Scene to save

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        await self._connection.execute(
            """
            INSERT INTO scenes (
                id, chapter_id, scene_number, title, content,
                scene_type, choices, created_at, updated_at, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO UPDATE SET
                chapter_id = EXCLUDED.chapter_id,
                scene_number = EXCLUDED.scene_number,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                scene_type = EXCLUDED.scene_type,
                choices = EXCLUDED.choices,
                updated_at = EXCLUDED.updated_at,
                metadata = EXCLUDED.metadata
            """,
            scene.id,
            UUID(scene.chapter_id),
            scene.scene_number,
            scene.title,
            scene.content,
            scene.scene_type,
            [c.to_dict() for c in scene.choices],
            scene.created_at,
            scene.updated_at,
            scene.metadata,
        )

    async def delete(self, scene_id: UUID) -> bool:
        """Delete scene.

        Args:
            scene_id: Scene UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        result: str = await self._connection.execute(
            "DELETE FROM scenes WHERE id = $1",
            scene_id,
        )
        # Result format: "DELETE n" where n is number of rows affected
        return bool(result and result != "DELETE 0")

    async def count_by_chapter(self, chapter_id: UUID) -> int:
        """Get total count of scenes in a chapter.

        Args:
            chapter_id: Chapter UUID

        Returns:
            Total number of scenes in the chapter
        """
        result = await self._connection.fetchval(
            "SELECT COUNT(*) FROM scenes WHERE chapter_id = $1",
            chapter_id,
        )
        return result or 0

    async def get_max_scene_number(self, chapter_id: UUID) -> int:
        """Get the maximum scene number in a chapter.

        Args:
            chapter_id: Chapter UUID

        Returns:
            Maximum scene number, or 0 if chapter has no scenes
        """
        result = await self._connection.fetchval(
            "SELECT MAX(scene_number) FROM scenes WHERE chapter_id = $1",
            chapter_id,
        )
        return result or 0

    async def reorder_scenes(self, chapter_id: UUID, new_order: list[UUID]) -> None:
        """Reorder scenes within a chapter.

        Updates the scene_number field for all scenes in the chapter
        based on the provided order.

        Args:
            chapter_id: Chapter UUID
            new_order: List of scene IDs in desired order

        Raises:
            ValueError: If new_order is empty or contains invalid IDs
            asyncpg.PostgresError: If database operation fails
        """
        if not new_order:
            raise ValueError("Scene order cannot be empty")

        async with self._connection.transaction():
            # Update each scene's number based on its position in the order list
            for new_number, scene_id in enumerate(new_order, 1):
                result = await self._connection.execute(
                    """
                    UPDATE scenes
                    SET scene_number = $1, updated_at = NOW()
                    WHERE id = $2 AND chapter_id = $3
                    """,
                    new_number,
                    scene_id,
                    chapter_id,
                )

                # Check if the scene was actually updated
                if result == "UPDATE 0":
                    raise ValueError(
                        f"Scene {scene_id} not found or does not "
                        f"belong to chapter {chapter_id}"
                    )

    async def search_by_content(
        self,
        chapter_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[Scene]:
        """Search scenes by content within a chapter.

        Args:
            chapter_id: Chapter UUID
            query: Search query string
            limit: Maximum number of results (default: 10)

        Returns:
            List of scenes matching the search query
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")

        rows = await self._connection.fetch(
            """
            SELECT
                id, chapter_id, scene_number, title, content,
                scene_type, choices, created_at, updated_at, metadata
            FROM scenes
            WHERE chapter_id = $1 AND content ILIKE $2
            ORDER BY scene_number
            LIMIT $3
            """,
            chapter_id,
            f"%{query}%",
            limit,
        )

        return [self._row_to_scene(row) for row in rows]

    def _row_to_scene(self, row: asyncpg.Record) -> Scene:
        """Convert database row to Scene entity.

        Args:
            row: Database record from asyncpg

        Returns:
            Scene domain entity
        """
        choices_data = row["choices"] or []
        choices = [self._dict_to_choice(c) for c in choices_data]

        return Scene(
            id=row["id"],
            chapter_id=str(row["chapter_id"]),
            scene_number=row["scene_number"],
            title=row["title"],
            content=row["content"],
            scene_type=row["scene_type"],
            choices=choices,
            metadata=dict(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _dict_to_choice(self, data: dict[str, Any]) -> Choice:
        """Convert dictionary to Choice entity."""
        from uuid import uuid4

        return Choice(
            id=UUID(data.get("id", str(uuid4()))),
            scene_id=data.get("scene_id", ""),
            text=data.get("text", ""),
            next_scene_id=data.get("next_scene_id"),
            conditions=data.get("conditions", {}),
            consequences=data.get("consequences", {}),
            order=data.get("order", 0),
            is_hidden=data.get("is_hidden", False),
            metadata=data.get("metadata", {}),
        )
