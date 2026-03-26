"""PostgreSQL implementation of KnowledgeRepositoryPort.

This module provides the PostgreSQL-based implementation of the
knowledge repository port interface using asyncpg for high-performance
async database operations.
"""

from uuid import UUID

import asyncpg

from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.domain.ports.knowledge_repository_port import (
    KnowledgeRepositoryPort,
)


class PostgresKnowledgeRepository(KnowledgeRepositoryPort):
    """PostgreSQL implementation of knowledge repository.

    Uses asyncpg for async database operations with connection pooling.

    Example:
        >>> repo = PostgresKnowledgeRepository(pool)
        ...     kb = await repo.get_by_id(kb_id)
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize repository with database connection pool.

        Args:
            pool: asyncpg connection pool.
        """
        self._pool = pool

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        """Get knowledge base by ID.

        Args:
            knowledge_base_id: Knowledge base UUID

        Returns:
            KnowledgeBase if found, None otherwise
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                FROM knowledge_bases
                WHERE id = $1
                """,
                knowledge_base_id,
            )

            if not row:
                return None

            return self._row_to_entity(row)

    async def get_by_name(self, name: str) -> KnowledgeBase | None:
        """Get knowledge base by name.

        Args:
            name: Knowledge base name

        Returns:
            KnowledgeBase if found, None otherwise
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                FROM knowledge_bases
                WHERE name = $1
                """,
                name,
            )

            if not row:
                return None

            return self._row_to_entity(row)

    async def save(self, knowledge_base: KnowledgeBase) -> None:
        """Save or update knowledge base.

        Uses UPSERT pattern with ON CONFLICT DO UPDATE to handle
        both insert and update operations efficiently.

        Args:
            knowledge_base: Knowledge base to save

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO knowledge_bases (
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    project_id = EXCLUDED.project_id,
                    embedding_model = EXCLUDED.embedding_model,
                    is_public = EXCLUDED.is_public,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata
                """,
                knowledge_base.id,
                knowledge_base.name,
                knowledge_base.description,
                knowledge_base.owner_id,
                knowledge_base.project_id,
                knowledge_base.embedding_model,
                knowledge_base.is_public,
                knowledge_base.created_at,
                knowledge_base.updated_at,
                knowledge_base.metadata,
            )

    async def delete(self, knowledge_base_id: UUID) -> bool:
        """Delete knowledge base.

        Args:
            knowledge_base_id: Knowledge base UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        async with self._pool.acquire() as connection:
            result: str = await connection.execute(
                "DELETE FROM knowledge_bases WHERE id = $1",
                knowledge_base_id,
            )
            # Result format: "DELETE n" where n is number of rows affected
            return bool(result != "DELETE 0")

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeBase]:
        """List all knowledge bases with pagination.

        Args:
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of knowledge bases

        Raises:
            ValueError: If limit or offset is negative
            asyncpg.PostgresError: If database operation fails
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                FROM knowledge_bases
                ORDER BY updated_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

            return [self._row_to_entity(row) for row in rows]

    async def count(self) -> int:
        """Get total count of knowledge bases.

        Returns:
            Total number of knowledge bases in the database.
        """
        async with self._pool.acquire() as connection:
            result = await connection.fetchval("SELECT COUNT(*) FROM knowledge_bases")
            return result or 0

    async def list_by_owner(
        self,
        owner_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeBase]:
        """List knowledge bases by owner.

        Args:
            owner_id: Owner identifier
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of knowledge bases belonging to the owner
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                FROM knowledge_bases
                WHERE owner_id = $1
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                owner_id,
                limit,
                offset,
            )

            return [self._row_to_entity(row) for row in rows]

    async def list_by_project(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeBase]:
        """List knowledge bases by project.

        Args:
            project_id: Project identifier
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of knowledge bases belonging to the project
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    id, name, description, owner_id, project_id,
                    embedding_model, is_public, created_at, updated_at, metadata
                FROM knowledge_bases
                WHERE project_id = $1
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                project_id,
                limit,
                offset,
            )

            return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: asyncpg.Record) -> KnowledgeBase:
        """Convert database row to domain entity.

        Args:
            row: Database record from asyncpg

        Returns:
            KnowledgeBase domain entity
        """
        return KnowledgeBase(
            id=row["id"],
            name=row["name"],
            owner_id=row["owner_id"],
            description=row["description"],
            project_id=row["project_id"],
            embedding_model=row["embedding_model"],
            is_public=row["is_public"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=dict(row["metadata"]) if row["metadata"] else {},
        )
