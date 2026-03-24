"""Database session manager.

This module provides session management for database operations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from src.shared.infrastructure.persistence.connection_pool import (
    DatabaseConnectionPool,
)


class DatabaseSessionManager:
    """Database session manager.

    This class manages database sessions and provides
    transactional context managers.
    """

    def __init__(self, pool: DatabaseConnectionPool):
        """Initialize session manager.

        Args:
            pool: Database connection pool.
        """
        self._pool = pool

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database session.

        Yields:
            A database connection.
        """
        conn = await self._pool.acquire()
        try:
            yield conn
        finally:
            await self._pool.release(conn)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database transaction.

        Yields:
            A database connection within a transaction.
        """
        conn = await self._pool.acquire()
        transaction = conn.transaction()
        await transaction.start()
        try:
            yield conn
            await transaction.commit()
        except Exception:
            await transaction.rollback()
            raise
        finally:
            await self._pool.release(conn)
