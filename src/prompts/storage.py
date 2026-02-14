#!/usr/bin/env python3
"""
User Prompt Storage.

This module provides persistent storage for user-defined prompts,
including CRUD operations and optimization history tracking.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from .base import Language, StoryGenre

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path("data/user_prompts.db")


@dataclass
class UserPrompt:
    """
    Represents a user-defined prompt.

    Attributes:
        id: Unique identifier
        user_id: ID of the user who created this prompt
        name: Display name for the prompt
        content: The actual prompt content
        genre: Optional genre classification
        language: Language of the prompt
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_optimized: Whether the prompt has been optimized
        optimization_history: List of optimization iterations
        metadata: Additional metadata
    """

    id: str
    user_id: str
    name: str
    content: str
    genre: Optional[StoryGenre] = None
    language: Language = Language.ENGLISH
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_optimized: bool = False
    optimization_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "content": self.content,
            "genre": self.genre.value if self.genre else None,
            "language": self.language.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_optimized": self.is_optimized,
            "optimization_history": self.optimization_history,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPrompt":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            name=data["name"],
            content=data["content"],
            genre=StoryGenre(data["genre"]) if data.get("genre") else None,
            language=Language(data.get("language", "en")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            is_optimized=data.get("is_optimized", False),
            optimization_history=data.get("optimization_history", []),
            metadata=data.get("metadata", {}),
        )


class PromptStorage:
    """
    Persistent storage for user-defined prompts using SQLite.

    This class provides async CRUD operations for user prompts,
    with support for optimization history tracking.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the prompt storage.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_prompts (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    genre VARCHAR(50),
                    language VARCHAR(10) DEFAULT 'en',
                    is_optimized BOOLEAN DEFAULT FALSE,
                    optimization_history JSON,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_prompts_user_id
                ON user_prompts(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_prompts_genre
                ON user_prompts(genre)
            """)
            await db.commit()

        self._initialized = True
        logger.info(f"Prompt storage initialized at {self.db_path}")

    async def save(self, prompt: UserPrompt) -> str:
        """
        Save a user prompt.

        Args:
            prompt: The prompt to save

        Returns:
            The prompt ID
        """
        await self.initialize()

        # Generate ID if not provided
        if not prompt.id:
            prompt.id = str(uuid.uuid4())

        prompt.updated_at = datetime.now()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO user_prompts
                (id, user_id, name, content, genre, language, is_optimized,
                 optimization_history, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    prompt.id,
                    prompt.user_id,
                    prompt.name,
                    prompt.content,
                    prompt.genre.value if prompt.genre else None,
                    prompt.language.value,
                    prompt.is_optimized,
                    json.dumps(prompt.optimization_history),
                    json.dumps(prompt.metadata),
                    prompt.created_at.isoformat(),
                    prompt.updated_at.isoformat(),
                ),
            )
            await db.commit()

        logger.debug(f"Saved prompt: {prompt.id}")
        return prompt.id

    async def get(self, prompt_id: str) -> Optional[UserPrompt]:
        """
        Get a prompt by ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            The prompt if found, None otherwise
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_prompts WHERE id = ?", (prompt_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_prompt(dict(row))
        return None

    async def list_by_user(
        self,
        user_id: str,
        genre: Optional[StoryGenre] = None,
        language: Optional[Language] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UserPrompt]:
        """
        List prompts by user with optional filters.

        Args:
            user_id: The user ID to filter by
            genre: Optional genre filter
            language: Optional language filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching prompts
        """
        await self.initialize()

        query = "SELECT * FROM user_prompts WHERE user_id = ?"
        params: List[Any] = [user_id]

        if genre:
            query += " AND genre = ?"
            params.append(genre.value)

        if language:
            query += " AND language = ?"
            params.append(language.value)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        prompts = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    prompts.append(self._row_to_prompt(dict(row)))

        return prompts

    async def update(
        self,
        prompt_id: str,
        content: Optional[str] = None,
        name: Optional[str] = None,
        is_optimized: Optional[bool] = None,
        add_to_history: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update a prompt.

        Args:
            prompt_id: The prompt ID
            content: New content (optional)
            name: New name (optional)
            is_optimized: New optimization status (optional)
            add_to_history: Content to add to optimization history (optional)
            metadata: New metadata to merge (optional)

        Returns:
            True if updated, False if not found
        """
        await self.initialize()

        # First, get the existing prompt
        prompt = await self.get(prompt_id)
        if not prompt:
            return False

        # Apply updates
        if content is not None:
            prompt.content = content
        if name is not None:
            prompt.name = name
        if is_optimized is not None:
            prompt.is_optimized = is_optimized
        if add_to_history is not None:
            prompt.optimization_history.append(add_to_history)
        if metadata is not None:
            prompt.metadata.update(metadata)

        prompt.updated_at = datetime.now()

        # Save the updated prompt
        await self.save(prompt)
        return True

    async def delete(self, prompt_id: str) -> bool:
        """
        Delete a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            True if deleted, False if not found
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM user_prompts WHERE id = ?", (prompt_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count_by_user(self, user_id: str) -> int:
        """
        Count prompts for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of prompts
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM user_prompts WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> List[UserPrompt]:
        """
        Search prompts by name or content.

        Args:
            user_id: The user ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching prompts
        """
        await self.initialize()

        search_pattern = f"%{query}%"
        prompts = []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM user_prompts
                WHERE user_id = ? AND (name LIKE ? OR content LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (user_id, search_pattern, search_pattern, limit),
            ) as cursor:
                async for row in cursor:
                    prompts.append(self._row_to_prompt(dict(row)))

        return prompts

    def _row_to_prompt(self, row: Dict[str, Any]) -> UserPrompt:
        """Convert a database row to a UserPrompt object."""
        return UserPrompt(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            content=row["content"],
            genre=StoryGenre(row["genre"]) if row.get("genre") else None,
            language=Language(row.get("language", "en")),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            is_optimized=bool(row.get("is_optimized", False)),
            optimization_history=json.loads(row.get("optimization_history") or "[]"),
            metadata=json.loads(row.get("metadata") or "{}"),
        )


# Convenience function for creating a new user prompt
def create_user_prompt(
    user_id: str,
    name: str,
    content: str,
    genre: Optional[StoryGenre] = None,
    language: Language = Language.ENGLISH,
) -> UserPrompt:
    """
    Create a new UserPrompt with auto-generated ID.

    Args:
        user_id: The user's ID
        name: Display name for the prompt
        content: The prompt content
        genre: Optional genre classification
        language: Language of the prompt

    Returns:
        A new UserPrompt instance
    """
    return UserPrompt(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        content=content,
        genre=genre,
        language=language,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


__all__ = [
    "PromptStorage",
    "UserPrompt",
    "create_user_prompt",
]
