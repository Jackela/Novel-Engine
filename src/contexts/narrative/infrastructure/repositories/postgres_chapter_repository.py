"""PostgreSQL implementation of ChapterRepositoryPort.

This module provides the PostgreSQL-based implementation of the
chapter repository port interface using asyncpg for high-performance
async database operations.
"""

from typing import Any
from uuid import UUID

import asyncpg

from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.entities.choice import Choice
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.ports.chapter_repository_port import (
    ChapterRepositoryPort,
)


class PostgresChapterRepository(ChapterRepositoryPort):
    """PostgreSQL implementation of chapter repository.

    Uses asyncpg for async database operations with connection pooling.

    Example:
        >>> async with db_pool.acquire() as conn:
        ...     repo = PostgresChapterRepository(conn)
        ...     chapter = await repo.get_by_id(chapter_id)
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg database connection.
        """
        self._connection = connection

    async def get_by_id(self, chapter_id: UUID) -> Chapter | None:
        """Get chapter by ID with all its scenes.

        Args:
            chapter_id: Chapter UUID

        Returns:
            Chapter if found, None otherwise
        """
        # Fetch chapter with scenes in a single query
        rows = await self._connection.fetch(
            """
            SELECT
                c.id as chapter_id,
                c.story_id,
                c.chapter_number,
                c.title as chapter_title,
                c.summary,
                c.created_at as chapter_created_at,
                c.updated_at as chapter_updated_at,
                c.metadata as chapter_metadata,
                s.id as scene_id,
                s.scene_number,
                s.title as scene_title,
                s.content,
                s.scene_type,
                s.choices,
                s.created_at as scene_created_at,
                s.updated_at as scene_updated_at,
                s.metadata as scene_metadata
            FROM chapters c
            LEFT JOIN scenes s ON s.chapter_id = c.id
            WHERE c.id = $1
            ORDER BY s.scene_number
            """,
            chapter_id,
        )

        if not rows:
            return None

        return self._rows_to_chapter(rows)

    async def get_by_story(self, story_id: UUID) -> list[Chapter]:
        """Get chapters by story ID.

        Args:
            story_id: Story UUID

        Returns:
            List of chapters belonging to the story, ordered by chapter_number
        """
        # Fetch all chapter IDs for the story
        rows = await self._connection.fetch(
            """
            SELECT id FROM chapters
            WHERE story_id = $1
            ORDER BY chapter_number
            """,
            story_id,
        )

        # Fetch full chapter for each ID
        chapters = []
        for row in rows:
            chapter = await self.get_by_id(row["id"])
            if chapter:
                chapters.append(chapter)

        return chapters

    async def save(self, chapter: Chapter) -> None:
        """Save or update chapter with all its scenes.

        Uses UPSERT pattern for chapter and cascading save for scenes.

        Args:
            chapter: Chapter to save

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        async with self._connection.transaction():
            # Save chapter
            await self._connection.execute(
                """
                INSERT INTO chapters (
                    id, story_id, chapter_number, title, summary,
                    created_at, updated_at, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO UPDATE SET
                    chapter_number = EXCLUDED.chapter_number,
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata
                """,
                chapter.id,
                UUID(chapter.story_id),
                chapter.chapter_number,
                chapter.title,
                chapter.summary,
                chapter.created_at,
                chapter.updated_at,
                chapter.metadata,
            )

            # Save scenes
            for scene in chapter.scenes:
                await self._save_scene(scene)

    async def _save_scene(self, scene: Scene) -> None:
        """Save a scene with its choices."""
        await self._connection.execute(
            """
            INSERT INTO scenes (
                id, chapter_id, scene_number, title, content,
                scene_type, choices, created_at, updated_at, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO UPDATE SET
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

    async def delete(self, chapter_id: UUID) -> bool:
        """Delete chapter and all related scenes.

        Args:
            chapter_id: Chapter UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        result: str = await self._connection.execute(
            "DELETE FROM chapters WHERE id = $1",
            chapter_id,
        )
        # Result format: "DELETE n" where n is number of rows affected
        return bool(result and result != "DELETE 0")

    async def reorder_chapters(self, story_id: UUID, chapter_order: list[UUID]) -> None:
        """Reorder chapters in a story.

        Updates the chapter_number field for all chapters in the story
        based on the provided order.

        Args:
            story_id: Story UUID
            chapter_order: List of chapter IDs in desired order

        Raises:
            ValueError: If chapter_order is empty or contains invalid IDs
            asyncpg.PostgresError: If database operation fails
        """
        if not chapter_order:
            raise ValueError("Chapter order cannot be empty")

        async with self._connection.transaction():
            # Update each chapter's number based on its position in the order list
            for new_number, chapter_id in enumerate(chapter_order, 1):
                result = await self._connection.execute(
                    """
                    UPDATE chapters
                    SET chapter_number = $1, updated_at = NOW()
                    WHERE id = $2 AND story_id = $3
                    """,
                    new_number,
                    chapter_id,
                    story_id,
                )

                # Check if the chapter was actually updated
                if result == "UPDATE 0":
                    raise ValueError(
                        f"Chapter {chapter_id} not found or does not "
                        f"belong to story {story_id}"
                    )

    async def count_by_story(self, story_id: UUID) -> int:
        """Get total count of chapters in a story.

        Args:
            story_id: Story UUID

        Returns:
            Total number of chapters in the story
        """
        result = await self._connection.fetchval(
            "SELECT COUNT(*) FROM chapters WHERE story_id = $1",
            story_id,
        )
        return result or 0

    async def get_chapter_numbers(self, story_id: UUID) -> list[int]:
        """Get all chapter numbers for a story.

        Args:
            story_id: Story UUID

        Returns:
            List of chapter numbers in order
        """
        rows = await self._connection.fetch(
            """
            SELECT chapter_number FROM chapters
            WHERE story_id = $1
            ORDER BY chapter_number
            """,
            story_id,
        )
        return [row["chapter_number"] for row in rows]

    def _rows_to_chapter(self, rows: list[asyncpg.Record]) -> Chapter:
        """Convert database rows to Chapter entity.

        Args:
            rows: Database records containing chapter and scene data

        Returns:
            Chapter domain entity
        """
        if not rows:
            raise ValueError("No rows provided")

        first_row = rows[0]

        # Build scenes from rows
        scenes = []
        seen_scene_ids: set[str] = set()

        for row in rows:
            scene_id = row.get("scene_id")
            if scene_id and str(scene_id) not in seen_scene_ids:
                seen_scene_ids.add(str(scene_id))
                choices_data = row["choices"] or []
                choices = [self._dict_to_choice(c) for c in choices_data]

                scene = Scene(
                    id=scene_id,
                    chapter_id=str(first_row["chapter_id"]),
                    scene_number=row["scene_number"],
                    title=row["scene_title"],
                    content=row["content"],
                    scene_type=row["scene_type"],
                    choices=choices,
                    metadata=dict(row["scene_metadata"])
                    if row["scene_metadata"]
                    else {},
                    created_at=row["scene_created_at"],
                    updated_at=row["scene_updated_at"],
                )
                scenes.append(scene)

        return Chapter(
            id=first_row["chapter_id"],
            story_id=str(first_row["story_id"]),
            chapter_number=first_row["chapter_number"],
            title=first_row["chapter_title"],
            summary=first_row["summary"],
            scenes=scenes,
            metadata=dict(first_row["chapter_metadata"])
            if first_row["chapter_metadata"]
            else {},
            created_at=first_row["chapter_created_at"],
            updated_at=first_row["chapter_updated_at"],
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
