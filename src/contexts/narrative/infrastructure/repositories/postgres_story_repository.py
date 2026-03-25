"""PostgreSQL implementation of StoryRepositoryPort.

This module provides the PostgreSQL-based implementation of the
story repository port interface using asyncpg for high-performance
async database operations.
"""

from typing import Any
from uuid import UUID

import asyncpg

from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.entities.choice import Choice
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)


class PostgresStoryRepository(StoryRepositoryPort):
    """PostgreSQL implementation of story repository.

    Uses asyncpg for async database operations with connection pooling.

    Example:
        >>> async with db_pool.acquire() as conn:
        ...     repo = PostgresStoryRepository(conn)
        ...     story = await repo.get_by_id(story_id)
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg database connection.
        """
        self._connection = connection

    async def get_by_id(self, story_id: UUID) -> Story | None:
        """Get story by ID.

        Args:
            story_id: Story UUID

        Returns:
            Story if found, None otherwise
        """
        # Fetch story with chapters and scenes in a single query
        rows = await self._connection.fetch(
            """
            SELECT
                s.id as story_id,
                s.title,
                s.genre,
                s.author_id,
                s.status,
                s.current_chapter_id,
                s.target_audience,
                s.themes,
                s.created_at as story_created_at,
                s.updated_at as story_updated_at,
                s.metadata as story_metadata,
                c.id as chapter_id,
                c.chapter_number,
                c.title as chapter_title,
                c.summary as chapter_summary,
                c.created_at as chapter_created_at,
                c.updated_at as chapter_updated_at,
                c.metadata as chapter_metadata,
                sc.id as scene_id,
                sc.scene_number,
                sc.title as scene_title,
                sc.content as scene_content,
                sc.scene_type,
                sc.choices,
                sc.created_at as scene_created_at,
                sc.updated_at as scene_updated_at,
                sc.metadata as scene_metadata
            FROM stories s
            LEFT JOIN chapters c ON c.story_id = s.id
            LEFT JOIN scenes sc ON sc.chapter_id = c.id
            WHERE s.id = $1
            ORDER BY c.chapter_number, sc.scene_number
            """,
            story_id,
        )

        if not rows:
            return None

        return self._rows_to_story(rows)

    async def get_by_title(self, title: str) -> Story | None:
        """Get story by title.

        Args:
            title: Story title

        Returns:
            Story if found, None otherwise
        """
        # First get the story ID by title
        row = await self._connection.fetchrow(
            "SELECT id FROM stories WHERE title = $1",
            title,
        )

        if not row:
            return None

        # Use get_by_id to fetch complete story with chapters and scenes
        return await self.get_by_id(row["id"])

    async def save(self, story: Story) -> None:
        """Save or update story with all chapters and scenes.

        Uses UPSERT pattern for story and cascading save for chapters
        and scenes.

        Args:
            story: Story to save

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        async with self._connection.transaction():
            # Save story
            await self._connection.execute(
                """
                INSERT INTO stories (
                    id, title, genre, author_id, status, current_chapter_id,
                    target_audience, themes, created_at, updated_at, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    genre = EXCLUDED.genre,
                    status = EXCLUDED.status,
                    current_chapter_id = EXCLUDED.current_chapter_id,
                    target_audience = EXCLUDED.target_audience,
                    themes = EXCLUDED.themes,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata
                """,
                story.id,
                story.title,
                story.genre,
                story.author_id,
                story.status,
                story.current_chapter_id,
                story.target_audience,
                story.themes,
                story.created_at,
                story.updated_at,
                story.metadata,
            )

            # Save chapters
            for chapter in story.chapters:
                await self._save_chapter(chapter)

    async def _save_chapter(self, chapter: Chapter) -> None:
        """Save a chapter with its scenes."""
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

    async def delete(self, story_id: UUID) -> bool:
        """Delete story and all related chapters and scenes.

        Args:
            story_id: Story UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        result: str = await self._connection.execute(
            "DELETE FROM stories WHERE id = $1",
            story_id,
        )
        # Result format: "DELETE n" where n is number of rows affected
        return bool(result and result != "DELETE 0")

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Story]:
        """List all stories with pagination.

        Args:
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of stories

        Raises:
            ValueError: If limit or offset is negative
            asyncpg.PostgresError: If database operation fails
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        # Get all story IDs first
        rows = await self._connection.fetch(
            """
            SELECT id FROM stories
            ORDER BY updated_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )

        # Fetch full story for each ID
        stories = []
        for row in rows:
            story = await self.get_by_id(row["id"])
            if story:
                stories.append(story)

        return stories

    async def list_by_author(self, author_id: str, limit: int = 100) -> list[Story]:
        """List stories by author.

        Args:
            author_id: Author identifier
            limit: Maximum number of results (default: 100)

        Returns:
            List of stories by the author
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")

        # Get story IDs by author
        rows = await self._connection.fetch(
            """
            SELECT id FROM stories
            WHERE author_id = $1
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            author_id,
            limit,
        )

        # Fetch full story for each ID
        stories = []
        for row in rows:
            story = await self.get_by_id(row["id"])
            if story:
                stories.append(story)

        return stories

    def _rows_to_story(self, rows: list[asyncpg.Record]) -> Story:
        """Convert database rows to Story aggregate.

        Args:
            rows: Database records containing story, chapter, and scene data

        Returns:
            Story domain aggregate
        """
        if not rows:
            raise ValueError("No rows provided")

        first_row = rows[0]

        # Build chapters and scenes from rows
        chapters: dict[str, Chapter] = {}
        for row in rows:
            chapter_id = row.get("chapter_id")
            if chapter_id and str(chapter_id) not in chapters:
                chapter = Chapter(  # type: ignore[abstract]
                    id=chapter_id,
                    story_id=str(first_row["story_id"]),
                    chapter_number=row["chapter_number"],
                    title=row["chapter_title"],
                    summary=row["chapter_summary"],
                    scenes=[],
                    metadata=dict(row["chapter_metadata"])
                    if row["chapter_metadata"]
                    else {},
                    created_at=row["chapter_created_at"],
                    updated_at=row["chapter_updated_at"],
                )
                chapters[str(chapter_id)] = chapter

            # Add scene to chapter
            scene_id = row.get("scene_id")
            if scene_id and chapter_id:
                chapter_obj = chapters.get(str(chapter_id))
                if chapter_obj:
                    # Check if scene already added
                    existing_scene = next(
                        (s for s in chapter_obj.scenes if str(s.id) == str(scene_id)),
                        None,
                    )
                    if not existing_scene:
                        choices_data = row["choices"] or []
                        choices = [self._dict_to_choice(c) for c in choices_data]

                        scene = Scene(  # type: ignore[abstract]
                            id=scene_id,
                            chapter_id=str(chapter_id),
                            scene_number=row["scene_number"],
                            title=row["scene_title"],
                            content=row["scene_content"],
                            scene_type=row["scene_type"],
                            choices=choices,
                            metadata=dict(row["scene_metadata"])
                            if row["scene_metadata"]
                            else {},
                            created_at=row["scene_created_at"],
                            updated_at=row["scene_updated_at"],
                        )
                        chapter_obj.scenes.append(scene)

        return Story(
            id=first_row["story_id"],
            title=first_row["title"],
            genre=first_row["genre"],
            author_id=first_row["author_id"],
            status=first_row["status"],
            current_chapter_id=first_row["current_chapter_id"],
            target_audience=first_row["target_audience"],
            themes=list(first_row["themes"]) if first_row["themes"] else [],
            chapters=list(chapters.values()),
            metadata=dict(first_row["story_metadata"])
            if first_row["story_metadata"]
            else {},
            created_at=first_row["story_created_at"],
            updated_at=first_row["story_updated_at"],
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
