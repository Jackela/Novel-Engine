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
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database transaction.

        Yields:
            A database connection within a transaction.
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn
