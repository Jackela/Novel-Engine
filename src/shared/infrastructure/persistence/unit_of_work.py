"""Unit of Work pattern implementation for Novel Engine.

This module implements the Unit of Work pattern to manage transactions
across multiple repositories and ensure data consistency.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Protocol, runtime_checkable

from src.shared.infrastructure.persistence.database import Database, DatabaseConnection
from src.shared.infrastructure.persistence.repository import BaseRepository


@runtime_checkable
class UnitOfWork(Protocol):
    """Protocol defining Unit of Work interface.

    Unit of Work maintains a list of objects affected by a business transaction
    and coordinates the writing out of changes and resolution of concurrency
    problems.
    """

    async def commit(self) -> None:
        """Commit all changes in the unit of work."""
        ...

    async def rollback(self) -> None:
        """Rollback all changes in the unit of work."""
        ...


class DatabaseUnitOfWork(UnitOfWork):
    """Database-backed Unit of Work implementation.

    This implementation coordinates transactions across multiple repositories,
    ensuring that all changes are committed or rolled back atomically.

    Example:
        >>> uow = DatabaseUnitOfWork(db)
        >>> async with uow:
        ...     user_repo = UserRepository(db)
        ...     uow.register_repository(user_repo)
        ...     await user_repo.add(user)
        ...     # Changes committed automatically on exit
    """

    def __init__(self, database: Database) -> None:
        """Initialize Unit of Work.

        Args:
            database: Database instance for transaction management.
        """
        self._db = database
        self._connection: DatabaseConnection | None = None
        self._repositories: list[BaseRepository[Any, Any]] = []
        self._committed = False
        self._rolled_back = False

    async def __aenter__(self) -> DatabaseUnitOfWork:
        """Enter async context manager.

        Returns:
            This Unit of Work instance.
        """
        await self._begin()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Commits if no exception occurred, otherwise rolls back.
        """
        if exc_type is None:
            if not self._rolled_back:
                await self.commit()
        else:
            await self.rollback()

    async def _begin(self) -> None:
        """Begin the unit of work.

        Acquires a database connection and prepares repositories.
        """
        # Get connection from pool
        context_manager: AbstractAsyncContextManager[DatabaseConnection] = (
            self._db.connection()
        )
        self._connection = await context_manager.__aenter__()

        # Register connection with all repositories
        for repo in self._repositories:
            repo.set_connection(self._connection)

    async def commit(self) -> None:
        """Commit all changes.

        Raises:
            RuntimeError: If already committed or rolled back.
        """
        if self._committed:
            raise RuntimeError("Unit of Work already committed")
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")

        self._committed = True
        # Release connection back to pool
        if self._connection:
            for repo in self._repositories:
                repo.set_connection(None)
            self._connection = None

    async def rollback(self) -> None:
        """Rollback all changes.

        Raises:
            RuntimeError: If already committed.
        """
        if self._committed:
            raise RuntimeError("Cannot rollback after commit")

        self._rolled_back = True
        # Release connection back to pool
        if self._connection:
            for repo in self._repositories:
                repo.set_connection(None)
            self._connection = None

    def register_repository(self, repository: BaseRepository[Any, Any]) -> None:
        """Register a repository with this unit of work.

        Repositories should be registered before entering the context.

        Args:
            repository: Repository to register.
        """
        self._repositories.append(repository)

    def register_repositories(self, *repositories: BaseRepository[Any, Any]) -> None:
        """Register multiple repositories with this unit of work.

        Args:
            *repositories: Repositories to register.
        """
        self._repositories.extend(repositories)

    @property
    def is_active(self) -> bool:
        """Check if unit of work is active.

        Returns:
            True if unit of work is active (has a connection).
        """
        return self._connection is not None


class TransactionalUnitOfWork(DatabaseUnitOfWork):
    """Transactional Unit of Work with automatic commit/rollback.

    This implementation uses database transactions for atomicity.

    Example:
        >>> uow = TransactionalUnitOfWork(db)
        >>> async with uow:
        ...     # All operations within this block are transactional
        ...     await user_repo.add(user)
        ...     await order_repo.add(order)
    """

    def __init__(self, database: Database) -> None:
        """Initialize transactional Unit of Work.

        Args:
            database: Database instance for transaction management.
        """
        super().__init__(database)
        self._transaction_context: Any = None

    async def _begin(self) -> None:
        """Begin the transaction."""
        # Get transaction from database
        self._transaction_context = self._db.transaction()
        self._connection = await self._transaction_context.__aenter__()

        # Register connection with all repositories
        for repo in self._repositories:
            repo.set_connection(self._connection)

    async def commit(self) -> None:
        """Commit the transaction."""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")

        # Transaction is committed automatically on context exit
        self._committed = True

        # Clean up repositories
        for repo in self._repositories:
            repo.set_connection(None)

        # Exit transaction context
        if self._transaction_context:
            await self._transaction_context.__aexit__(None, None, None)
            self._transaction_context = None
            self._connection = None

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if self._committed:
            raise RuntimeError("Cannot rollback after commit")

        self._rolled_back = True

        # Clean up repositories
        for repo in self._repositories:
            repo.set_connection(None)

        # Exit transaction context with exception to trigger rollback
        if self._transaction_context:
            try:
                raise TransactionRollbackException("Transaction rolled back")
            except TransactionRollbackException:
                await self._transaction_context.__aexit__(
                    TransactionRollbackException,
                    TransactionRollbackException("Transaction rolled back"),
                    None,
                )
            self._transaction_context = None
            self._connection = None


class TransactionRollbackException(Exception):
    """Exception used internally to trigger transaction rollback."""

    pass


@dataclass
class UnitOfWorkResult:
    """Result of a Unit of Work operation.

    Attributes:
        success: Whether the operation was successful.
        error: Error message if operation failed.
        data: Optional data from the operation.
    """

    success: bool
    error: str | None = None
    data: Any = None

    @classmethod
    def success_result(cls, data: Any = None) -> UnitOfWorkResult:
        """Create a successful result.

        Args:
            data: Optional result data.

        Returns:
            Successful result.
        """
        return cls(success=True, data=data)

    @classmethod
    def failure_result(cls, error: str) -> UnitOfWorkResult:
        """Create a failure result.

        Args:
            error: Error message.

        Returns:
            Failed result.
        """
        return cls(success=False, error=error)


class UnitOfWorkFactory:
    """Factory for creating Unit of Work instances."""

    def __init__(self, database: Database) -> None:
        """Initialize factory.

        Args:
            database: Database instance.
        """
        self._db = database

    def create(self, transactional: bool = True) -> DatabaseUnitOfWork:
        """Create a Unit of Work.

        Args:
            transactional: Whether to use transactions.

        Returns:
            Unit of Work instance.
        """
        if transactional:
            return TransactionalUnitOfWork(self._db)
        return DatabaseUnitOfWork(self._db)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[TransactionalUnitOfWork, None]:
        """Create and manage a transactional Unit of Work.

        Yields:
            TransactionalUnitOfWork: Transactional unit of work.

        Example:
            >>> async with uow_factory.transaction() as uow:
            ...     await repo.add(entity)
        """
        uow = TransactionalUnitOfWork(self._db)
        async with uow:
            yield uow


# Global factory instance (set during application initialization)
_unit_of_work_factory: UnitOfWorkFactory | None = None


def set_unit_of_work_factory(factory: UnitOfWorkFactory) -> None:
    """Set the global Unit of Work factory.

    Args:
        factory: Factory instance to use globally.
    """
    global _unit_of_work_factory
    _unit_of_work_factory = factory


def get_unit_of_work_factory() -> UnitOfWorkFactory:
    """Get the global Unit of Work factory.

    Returns:
        Global factory instance.

    Raises:
        RuntimeError: If factory has not been set.
    """
    if _unit_of_work_factory is None:
        raise RuntimeError(
            "UnitOfWorkFactory not initialized. Call set_unit_of_work_factory first."
        )
    return _unit_of_work_factory


def get_uow(transactional: bool = True) -> DatabaseUnitOfWork:
    """Get a Unit of Work from the global factory.

    Args:
        transactional: Whether to use transactions.

    Returns:
        Unit of Work instance.
    """
    return get_unit_of_work_factory().create(transactional)
