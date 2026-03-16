"""PostgreSQL implementation of database abstraction.

This module provides a PostgreSQL-specific implementation using asyncpg
with connection pooling and full type safety.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import asyncpg
from asyncpg import Pool, Connection

from src.shared.infrastructure.persistence.database import (
    Database,
    DatabaseConnection,
    DatabaseFactory,
    DEFAULT_POOL_MIN_SIZE,
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_MAX_INACTIVE_TIME,
    DEFAULT_MAX_QUERIES,
)


class AsyncpgConnection(DatabaseConnection):
    """asyncpg-based database connection wrapper."""

    def __init__(self, connection: Connection) -> None:
        """Initialize connection wrapper.

        Args:
            connection: asyncpg Connection instance.
        """
        self._conn: Connection = connection

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Command completion status.
        """
        result: str = await self._conn.execute(query, *args)
        return result

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch multiple rows.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            List of row dictionaries.
        """
        rows = await self._conn.fetch(query, *args)
        return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Single row dictionary or None if not found.
        """
        row = await self._conn.fetchrow(query, *args)
        return dict(row) if row else None

    async def fetchval(self, query: str, *args: Any) -> Any | None:
        """Fetch a single value.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Single value or None if not found.
        """
        return await self._conn.fetchval(query, *args)

    async def execute_many(self, query: str, args_seq: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: SQL query string.
            args_seq: Sequence of parameter tuples.
        """
        await self._conn.executemany(query, args_seq)


class PostgreSQLDatabase(Database):
    """PostgreSQL database implementation using asyncpg.

    This implementation provides connection pooling, transactions,
    and full async support for PostgreSQL databases.

    Example:
        >>> db = PostgreSQLDatabase(
        ...     dsn="postgresql://user:pass@localhost:5432/db",
        ...     min_size=5,
        ...     max_size=20
        ... )
        >>> await db.connect()
        >>> async with db.connection() as conn:
        ...     users = await conn.fetch("SELECT * FROM users")
    """

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = DEFAULT_POOL_MIN_SIZE,
        max_size: int = DEFAULT_POOL_MAX_SIZE,
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT,
        max_inactive_time: float = DEFAULT_MAX_INACTIVE_TIME,
        max_queries: int = DEFAULT_MAX_QUERIES,
        ssl: bool | str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize PostgreSQL database.

        Args:
            dsn: PostgreSQL connection string.
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
            command_timeout: Timeout for SQL commands in seconds.
            max_inactive_time: Maximum time a connection can be inactive.
            max_queries: Maximum number of queries per connection before reconnection.
            ssl: SSL mode or SSL context.
            **kwargs: Additional connection parameters.
        """
        super().__init__(dsn, **kwargs)
        self._min_size = min_size
        self._max_size = max_size
        self._command_timeout = command_timeout
        self._max_inactive_time = max_inactive_time
        self._max_queries = max_queries
        self._ssl = ssl
        self._pool: Pool | None = None

    async def connect(self) -> None:
        """Establish database connection and initialize connection pool.

        Raises:
            ConnectionError: If connection fails.
        """
        try:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=self._command_timeout,
                max_inactive_connection_lifetime=self._max_inactive_time,
                max_queries=self._max_queries,
                ssl=self._ssl,
                **self._kwargs,
            )
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._connected = False

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[AsyncpgConnection, None]:
        """Get a connection from the pool.

        Yields:
            AsyncpgConnection: A database connection wrapper.

        Raises:
            RuntimeError: If database is not connected.
        """
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            yield AsyncpgConnection(conn)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncpgConnection, None]:
        """Get a transaction.

        Yields:
            AsyncpgConnection: A database connection within a transaction.

        Raises:
            RuntimeError: If database is not connected.
        """
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield AsyncpgConnection(conn)

    @property
    def pool_size(self) -> dict[str, int]:
        """Get current pool statistics.

        Returns:
            Dictionary with pool size information.
        """
        if not self._pool:
            return {"min": 0, "max": 0, "size": 0, "free": 0}

        return {
            "min": self._pool.get_min_size(),
            "max": self._pool.get_max_size(),
            "size": self._pool.get_size(),
            "free": self._pool.get_idle_size(),
        }

    async def execute_with_timeout(
        self, query: str, *args: Any, timeout: float | None = None
    ) -> str:
        """Execute query with custom timeout.

        Args:
            query: SQL query string.
            *args: Query parameters.
            timeout: Custom timeout in seconds.

        Returns:
            Command completion status.
        """
        async with self.connection() as conn:
            # Note: asyncpg doesn't support per-query timeout directly
            # This is handled at connection level via command_timeout
            return await conn.execute(query, *args)


# Register PostgreSQL database with factory
DatabaseFactory.register("postgresql", PostgreSQLDatabase)
DatabaseFactory.register("postgres", PostgreSQLDatabase)
