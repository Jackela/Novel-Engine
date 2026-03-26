"""PostgreSQL repository implementations for knowledge context.

This module provides factory functions and exports for PostgreSQL-based
repository implementations.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

    from src.contexts.knowledge.domain.ports.document_repository_port import (
        DocumentRepositoryPort,
    )
    from src.contexts.knowledge.domain.ports.knowledge_repository_port import (
        KnowledgeRepositoryPort,
    )

from src.contexts.knowledge.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
    PostgresKnowledgeRepository,
)

__all__ = [
    "PostgresKnowledgeRepository",
    "PostgresDocumentRepository",
    "create_knowledge_repository",
    "create_document_repository",
]


async def create_knowledge_repository(
    db_pool: "asyncpg.Pool",
) -> "KnowledgeRepositoryPort":
    """Factory function to create a PostgreSQL knowledge repository.

    This factory function acquires a connection from the pool and
    returns a configured PostgresKnowledgeRepository instance.

    Note: The returned repository holds the acquired connection.
    Caller is responsible for proper connection management or use
    with context managers.

    Args:
        db_pool: asyncpg connection pool

    Returns:
        Configured KnowledgeRepositoryPort implementation

    Example:
        >>> from asyncpg import create_pool
        >>> pool = await create_pool(dsn="postgresql://...")
        >>> repo = await create_knowledge_repository(pool)
        >>> kb = await repo.get_by_id(kb_id)
    """
    conn = await db_pool.acquire()
    return PostgresKnowledgeRepository(conn)


async def create_document_repository(
    db_pool: "asyncpg.Pool",
) -> "DocumentRepositoryPort":
    """Factory function to create a PostgreSQL document repository.

    This factory function acquires a connection from the pool and
    returns a configured PostgresDocumentRepository instance.

    Note: The returned repository holds the acquired connection.
    Caller is responsible for proper connection management or use
    with context managers.

    Args:
        db_pool: asyncpg connection pool

    Returns:
        Configured DocumentRepositoryPort implementation

    Example:
        >>> from asyncpg import create_pool
        >>> pool = await create_pool(dsn="postgresql://...")
        >>> repo = await create_document_repository(pool)
        >>> docs = await repo.get_by_knowledge_base(kb_id)
    """
    conn = await db_pool.acquire()
    return PostgresDocumentRepository(conn)
