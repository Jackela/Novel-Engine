"""Database abstraction layer for Novel Engine.

This module defines abstract interfaces for database operations,
enabling different database backends while maintaining type safety.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class DatabaseConnection(Protocol):
    """Protocol defining database connection interface."""

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Command completion status.
        """
        ...

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch multiple rows.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            List of row dictionaries.
        """
        ...

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Single row dictionary or None if not found.
        """
        ...

    async def fetchval(self, query: str, *args: Any) -> Any | None:
        """Fetch a single value.

        Args:
            query: SQL query string.
            *args: Query parameters.

        Returns:
            Single value or None if not found.
        """
        ...

    async def execute_many(self, query: str, args_seq: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: SQL query string.
            args_seq: Sequence of parameter tuples.
        """
        ...


class DatabaseTransaction(Protocol):
    """Protocol defining database transaction interface."""

    async def commit(self) -> None:
        """Commit the transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...


class Database(ABC):
    """Abstract base class for database implementations.

    This class defines the interface that all database implementations
    must follow, ensuring consistent behavior across different backends.

    Example:
        >>> db = PostgreSQLDatabase(dsn="postgresql://localhost/db")
        >>> await db.connect()
        >>> async with db.connection() as conn:
        ...     rows = await conn.fetch("SELECT * FROM users")
    """

    def __init__(self, dsn: str, **kwargs: Any) -> None:
        """Initialize database.

        Args:
            dsn: Database connection string.
            **kwargs: Additional connection parameters.
        """
        self._dsn = dsn
        self._kwargs = kwargs
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if database is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection.

        This method should initialize the connection pool.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection.

        This method should close the connection pool.
        """
        ...

    @abstractmethod
    def connection(self) -> AbstractAsyncContextManager[DatabaseConnection]:
        """Get a connection from the pool.

        Returns:
            An async context manager yielding a database connection.

        Example:
            >>> async with db.connection() as conn:
            ...     await conn.execute("INSERT INTO users (name) VALUES ($1)", "John")
        """
        ...

    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[DatabaseConnection]:
        """Get a transaction.

        Returns:
            An async context manager yielding a database connection within a transaction.

        Example:
            >>> async with db.transaction() as conn:
            ...     await conn.execute("INSERT INTO users (name) VALUES ($1)", "John")
            ...     await conn.execute("INSERT INTO profiles (user_id) VALUES ($1)", user_id)
        """
        ...

    async def health_check(self) -> bool:
        """Check database health.

        Returns:
            True if database is healthy, False otherwise.
        """
        try:
            async with self.connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except (ConnectionError, TimeoutError, OSError):
            return False


class DatabaseFactory:
    """Factory for creating database instances."""

    _registry: dict[str, type[Database]] = {}

    @classmethod
    def register(cls, backend: str, database_class: type[Database]) -> None:
        """Register a database implementation.

        Args:
            backend: Backend identifier (e.g., 'postgresql').
            database_class: Database implementation class.
        """
        cls._registry[backend] = database_class

    @classmethod
    def create(cls, backend: str, dsn: str, **kwargs: Any) -> Database:
        """Create a database instance.

        Args:
            backend: Backend identifier.
            dsn: Database connection string.
            **kwargs: Additional connection parameters.

        Returns:
            Database instance.

        Raises:
            ValueError: If backend is not registered.
        """
        if backend not in cls._registry:
            raise ValueError(f"Unknown database backend: {backend}")

        database_class = cls._registry[backend]
        return database_class(dsn, **kwargs)


# Connection pool configuration defaults
DEFAULT_POOL_MIN_SIZE = 5
DEFAULT_POOL_MAX_SIZE = 20
DEFAULT_COMMAND_TIMEOUT = 60.0
DEFAULT_MAX_INACTIVE_TIME = 300.0
DEFAULT_MAX_QUERIES = 50000
