"""PostgreSQL implementation of DocumentRepositoryPort.

This module provides the PostgreSQL-based implementation of the
document repository port interface using asyncpg for high-performance
async database operations.
"""

from uuid import UUID

import asyncpg

from src.contexts.knowledge.domain.entities.document import Document
from src.contexts.knowledge.domain.ports.document_repository_port import (
    DocumentRepositoryPort,
)


class PostgresDocumentRepository(DocumentRepositoryPort):
    """PostgreSQL implementation of document repository.

    Uses asyncpg for async database operations with connection pooling.

    Example:
        >>> async with db_pool.acquire() as conn:
        ...     repo = PostgresDocumentRepository(conn)
        ...     docs = await repo.get_by_knowledge_base(kb_id)
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg database connection.
        """
        self._connection = connection

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document if found, None otherwise
        """
        row = await self._connection.fetchrow(
            """
            SELECT
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            FROM documents
            WHERE id = $1
            """,
            document_id,
        )

        if not row:
            return None

        return self._row_to_entity(row)

    async def get_by_knowledge_base(self, kb_id: UUID) -> list[Document]:
        """Get all documents in a knowledge base.

        Args:
            kb_id: Knowledge base UUID

        Returns:
            List of documents belonging to the knowledge base
        """
        rows = await self._connection.fetch(
            """
            SELECT
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            FROM documents
            WHERE knowledge_base_id = $1
            ORDER BY created_at DESC
            """,
            kb_id,
        )

        return [self._row_to_entity(row) for row in rows]

    async def get_by_knowledge_base_paginated(
        self,
        kb_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """Get documents in a knowledge base with pagination.

        Args:
            kb_id: Knowledge base UUID
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of documents belonging to the knowledge base

        Raises:
            ValueError: If limit or offset is negative
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        rows = await self._connection.fetch(
            """
            SELECT
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            FROM documents
            WHERE knowledge_base_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            kb_id,
            limit,
            offset,
        )

        return [self._row_to_entity(row) for row in rows]

    async def save(self, document: Document) -> None:
        """Save or update document.

        Uses UPSERT pattern with ON CONFLICT DO UPDATE to handle
        both insert and update operations efficiently.

        Args:
            document: Document to save

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        await self._connection.execute(
            """
            INSERT INTO documents (
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                content_type = EXCLUDED.content_type,
                source = EXCLUDED.source,
                tags = EXCLUDED.tags,
                chunks = EXCLUDED.chunks,
                embedding = EXCLUDED.embedding,
                is_indexed = EXCLUDED.is_indexed,
                indexed_at = EXCLUDED.indexed_at,
                chunk_count = EXCLUDED.chunk_count,
                word_count = EXCLUDED.word_count,
                updated_at = EXCLUDED.updated_at,
                metadata = EXCLUDED.metadata
            """,
            document.id,
            document.knowledge_base_id,
            document.title,
            document.content,
            document.content_type,
            document.source,
            document.tags,
            document.chunks,
            document.embedding,
            document.is_indexed,
            document.indexed_at,
            document.chunk_count,
            document.word_count,
            document.created_at,
            document.updated_at,
            document.metadata,
        )

    async def delete(self, document_id: UUID) -> bool:
        """Delete document.

        Args:
            document_id: Document UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If database operation fails
        """
        result: str = await self._connection.execute(
            "DELETE FROM documents WHERE id = $1",
            document_id,
        )
        return bool(result != "DELETE 0")

    async def delete_by_knowledge_base(self, kb_id: UUID) -> int:
        """Delete all documents in a knowledge base.

        Args:
            kb_id: Knowledge base UUID

        Returns:
            Number of documents deleted
        """
        result = await self._connection.execute(
            "DELETE FROM documents WHERE knowledge_base_id = $1",
            kb_id,
        )
        # Parse "DELETE n" to get count
        if result.startswith("DELETE "):
            return int(result.split(" ")[1])
        return 0

    async def count_by_knowledge_base(self, kb_id: UUID) -> int:
        """Count documents in a knowledge base.

        Args:
            kb_id: Knowledge base UUID

        Returns:
            Number of documents in the knowledge base
        """
        result = await self._connection.fetchval(
            "SELECT COUNT(*) FROM documents WHERE knowledge_base_id = $1",
            kb_id,
        )
        return result or 0

    async def search_by_tags(
        self,
        kb_id: UUID,
        tags: list[str],
    ) -> list[Document]:
        """Search documents by tags within a knowledge base.

        Args:
            kb_id: Knowledge base UUID
            tags: List of tags to search for

        Returns:
            List of documents that have any of the specified tags
        """
        if not tags:
            return []

        rows = await self._connection.fetch(
            """
            SELECT
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            FROM documents
            WHERE knowledge_base_id = $1
              AND tags && $2::text[]
            ORDER BY created_at DESC
            """,
            kb_id,
            tags,
        )

        return [self._row_to_entity(row) for row in rows]

    async def search_by_title(
        self,
        kb_id: UUID,
        title_query: str,
        limit: int = 20,
    ) -> list[Document]:
        """Search documents by title (case-insensitive partial match).

        Args:
            kb_id: Knowledge base UUID
            title_query: Search query for title
            limit: Maximum number of results (default: 20)

        Returns:
            List of documents matching the title query
        """
        rows = await self._connection.fetch(
            """
            SELECT
                id, knowledge_base_id, title, content, content_type,
                source, tags, chunks, embedding, is_indexed, indexed_at,
                chunk_count, word_count, created_at, updated_at, metadata
            FROM documents
            WHERE knowledge_base_id = $1
              AND title ILIKE $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            kb_id,
            f"%{title_query}%",
            limit,
        )

        return [self._row_to_entity(row) for row in rows]

    async def update_indexed_status(
        self,
        document_id: UUID,
        is_indexed: bool,
        embedding: list[float] | None = None,
    ) -> None:
        """Update document indexing status and optional embedding.

        Args:
            document_id: Document UUID
            is_indexed: Whether document is indexed
            embedding: Optional vector embedding for the document
        """
        from datetime import datetime

        indexed_at = datetime.utcnow() if is_indexed else None

        await self._connection.execute(
            """
            UPDATE documents
            SET is_indexed = $1,
                indexed_at = $2,
                embedding = $3,
                updated_at = NOW()
            WHERE id = $4
            """,
            is_indexed,
            indexed_at,
            embedding,
            document_id,
        )

    def _row_to_entity(self, row: asyncpg.Record) -> Document:
        """Convert database row to domain entity.

        Args:
            row: Database record from asyncpg

        Returns:
            Document domain entity
        """
        # Convert embedding from text array to float list if present
        embedding = None
        if row["embedding"]:
            try:
                embedding = [float(x) for x in row["embedding"]]
            except (ValueError, TypeError):
                # Handle cases where embedding might be stored differently
                embedding = row["embedding"]

        return Document(
            id=row["id"],
            knowledge_base_id=str(row["knowledge_base_id"]),
            title=row["title"],
            content=row["content"],
            content_type=row["content_type"],
            source=row["source"],
            tags=list(row["tags"]) if row["tags"] else [],
            chunks=list(row["chunks"]) if row["chunks"] else [],
            embedding=embedding,
            is_indexed=row["is_indexed"],
            indexed_at=row["indexed_at"],
            chunk_count=row["chunk_count"],
            word_count=row["word_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=dict(row["metadata"]) if row["metadata"] else {},
        )
