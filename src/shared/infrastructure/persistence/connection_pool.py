"""Database connection pool management.

This module provides connection pool management for database connections.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg


class DatabaseConnectionPool:
    """Database connection pool wrapper.

    This class wraps asyncpg's connection pool and provides
    a simple interface for acquiring and releasing connections.
    """

    def __init__(
        self,
        database_url: str,
        max_connections: int = 20,
    ):
        """Initialize connection pool.

        Args:
            database_url: Database connection URL.
            max_connections: Maximum number of connections in the pool.
        """
        self._database_url = database_url
        self._max_connections = max_connections
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the underlying connection pool.

        Returns:
            The asyncpg connection pool.

        Raises:
            RuntimeError: If pool is not initialized.
        """
        if self._pool is None:
            raise RuntimeError("Connection pool is not initialized")
        return self._pool

    async def initialize(self) -> None:
        """Initialize the connection pool.

        This method creates the connection pool.
        """
        self._pool = await asyncpg.create_pool(
            self._database_url,
            max_size=self._max_connections,
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool.

        Yields:
            A database connection.
        """
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
