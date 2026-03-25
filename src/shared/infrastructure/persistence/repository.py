"""Repository base classes for Novel Engine.

This module provides the repository pattern implementation,
enabling data access abstraction with full type safety.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from src.shared.domain.base.aggregate import AggregateRoot
from src.shared.infrastructure.persistence.database import Database, DatabaseConnection

T = TypeVar("T", bound=AggregateRoot)
K = TypeVar("K")


@runtime_checkable
class Repository(Protocol[T]):
    """Protocol defining repository interface.

    Repositories mediate between the domain and data mapping layers,
    acting like in-memory collections of domain objects.

    Type Parameters:
        T: The aggregate root type this repository manages.
    """

    async def get(self, id: K) -> T | None:
        """Get aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            Aggregate instance or None if not found.
        """
        ...

    async def add(self, aggregate: T) -> None:
        """Add aggregate to repository.

        Args:
            aggregate: Aggregate to add.
        """
        ...

    async def update(self, aggregate: T) -> None:
        """Update aggregate in repository.

        Args:
            aggregate: Aggregate to update.
        """
        ...

    async def delete(self, id: K) -> bool:
        """Delete aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def exists(self, id: K) -> bool:
        """Check if aggregate exists.

        Args:
            id: Aggregate identifier.

        Returns:
            True if exists, False otherwise.
        """
        ...


class BaseRepository(ABC, Generic[T, K]):
    """Abstract base class for all repositories.

    This class provides common functionality and enforces the
    repository pattern contract. Concrete implementations should
    override the abstract methods.

    Type Parameters:
        T: The aggregate root type this repository manages.
        K: The key type for lookups (typically UUID).

    Attributes:
        _db: Database instance for persistence operations.
        _connection: Optional database connection for transactions.

    Example:
        >>> class UserRepository(BaseRepository[User, UUID]):
        ...     async def get(self, id: UUID) -> User | None:
        ...         # Implementation
        ...         pass
    """

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self._db = db
        self._connection: DatabaseConnection | None = None

    @property
    def connection(self) -> DatabaseConnection:
        """Get database connection.

        Returns:
            Active database connection.

        Raises:
            RuntimeError: If no connection is available.
        """
        if self._connection:
            return self._connection
        raise RuntimeError("No connection available. Use within Unit of Work context.")

    def set_connection(self, connection: DatabaseConnection | None) -> None:
        """Set database connection for this repository.

        This is typically called by Unit of Work to provide
        a transaction-scoped connection.

        Args:
            connection: Database connection or None to clear.
        """
        self._connection = connection

    @abstractmethod
    async def get(self, id: K) -> T | None:
        """Get aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            Aggregate instance or None if not found.
        """
        ...

    @abstractmethod
    async def add(self, aggregate: T) -> None:
        """Add aggregate to repository.

        Args:
            aggregate: Aggregate to add.
        """
        ...

    @abstractmethod
    async def update(self, aggregate: T) -> None:
        """Update aggregate in repository.

        Args:
            aggregate: Aggregate to update.
        """
        ...

    @abstractmethod
    async def delete(self, id: K) -> bool:
        """Delete aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def exists(self, id: K) -> bool:
        """Check if aggregate exists.

        Default implementation that can be overridden for efficiency.

        Args:
            id: Aggregate identifier.

        Returns:
            True if exists, False otherwise.
        """
        result = await self.get(id)
        return result is not None

    @abstractmethod
    def _to_aggregate(self, row: dict[str, Any]) -> T:
        """Convert database row to aggregate.

        Args:
            row: Database row as dictionary.

        Returns:
            Aggregate instance.
        """
        ...

    @abstractmethod
    def _from_aggregate(self, aggregate: T) -> dict[str, Any]:
        """Convert aggregate to database row.

        Args:
            aggregate: Aggregate instance.

        Returns:
            Dictionary representing the database row.
        """
        ...


class InMemoryRepository(BaseRepository[T, K]):
    """In-memory repository implementation for testing.

    This implementation stores aggregates in memory and is useful
    for unit testing without database dependencies.

    Type Parameters:
        T: The aggregate root type this repository manages.
        K: The key type for lookups (typically UUID).

    Example:
        >>> repo = InMemoryRepository[User, UUID]()
        >>> await repo.add(user)
        >>> found = await repo.get(user.id)
    """

    def __init__(self) -> None:
        """Initialize in-memory repository."""
        # Bypass parent __init__ since we don't need a database
        self._data: dict[K, T] = {}
        self._connection = None

    async def get(self, id: K) -> T | None:
        """Get aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            Aggregate instance or None if not found.
        """
        return self._data.get(id)

    async def add(self, aggregate: T) -> None:
        """Add aggregate to repository.

        Args:
            aggregate: Aggregate to add.
        """
        key = self._get_key(aggregate)
        self._data[key] = aggregate

    async def update(self, aggregate: T) -> None:
        """Update aggregate in repository.

        Args:
            aggregate: Aggregate to update.
        """
        key = self._get_key(aggregate)
        if key in self._data:
            self._data[key] = aggregate

    async def delete(self, id: K) -> bool:
        """Delete aggregate by ID.

        Args:
            id: Aggregate identifier.

        Returns:
            True if deleted, False if not found.
        """
        if id in self._data:
            del self._data[id]
            return True
        return False

    async def exists(self, id: K) -> bool:
        """Check if aggregate exists.

        Args:
            id: Aggregate identifier.

        Returns:
            True if exists, False otherwise.
        """
        return id in self._data

    async def get_all(self) -> list[T]:
        """Get all aggregates.

        Returns:
            List of all aggregates.
        """
        return list(self._data.values())

    async def clear(self) -> None:
        """Clear all data."""
        self._data.clear()

    def _get_key(self, aggregate: T) -> K:
        """Get key from aggregate.

        Args:
            aggregate: Aggregate instance.

        Returns:
            Aggregate identifier.
        """
        return aggregate.id  # type: ignore

    def _to_aggregate(self, row: dict[str, Any]) -> T:
        """Not applicable for in-memory repository."""
        raise NotImplementedError("InMemoryRepository doesn't use row conversion")

    def _from_aggregate(self, aggregate: T) -> dict[str, Any]:
        """Not applicable for in-memory repository."""
        raise NotImplementedError("InMemoryRepository doesn't use row conversion")


# Common repository exception classes
class RepositoryException(Exception):
    """Base exception for repository operations."""

    pass


class AggregateNotFoundException(RepositoryException):
    """Exception raised when aggregate is not found."""

    def __init__(self, aggregate_type: str, id: Any) -> None:
        """Initialize exception.

        Args:
            aggregate_type: Type name of the aggregate.
            id: Identifier that was not found.
        """
        super().__init__(f"{aggregate_type} with id {id} not found")
        self.aggregate_type = aggregate_type
        self.id = id


class ConcurrentModificationException(RepositoryException):
    """Exception raised on concurrent modification conflict."""

    def __init__(
        self, aggregate_type: str, id: Any, expected: int, actual: int
    ) -> None:
        """Initialize exception.

        Args:
            aggregate_type: Type name of the aggregate.
            id: Identifier of the modified aggregate.
            expected: Expected version.
            actual: Actual version found.
        """
        super().__init__(
            f"Concurrent modification detected for {aggregate_type} {id}: "
            f"expected version {expected}, found {actual}"
        )
        self.aggregate_type = aggregate_type
        self.id = id
        self.expected = expected
        self.actual = actual
