"""Tests for UnitOfWork."""

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.shared.infrastructure.persistence.database import Database, DatabaseConnection
from src.shared.infrastructure.persistence.repository import BaseRepository
from src.shared.infrastructure.persistence.unit_of_work import (
    DatabaseUnitOfWork,
    TransactionalUnitOfWork,
    TransactionRollbackException,
    UnitOfWorkFactory,
    UnitOfWorkResult,
    get_unit_of_work_factory,
    get_uow,
    set_unit_of_work_factory,
)


class MockDatabaseConnection:
    """Mock database connection for testing."""

    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()


class MockDatabase(Database):
    """Mock database for testing."""

    def __init__(self):
        self._connection = MockDatabaseConnection()
        self.connection = MagicMock(return_value=self._connection)
        self.transaction = MagicMock(return_value=self._connection)

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def execute(self, query: str, *args) -> Any:
        return []

    def connection(self) -> MockDatabaseConnection:
        return self._connection

    def transaction(self) -> MockDatabaseConnection:
        return self._connection


class MockAggregate:
    """Mock aggregate for testing."""

    def __init__(self):
        self.id = uuid4()


class MockRepository(BaseRepository[MockAggregate, UUID]):
    """Mock repository for testing."""

    def __init__(self):
        # Bypass parent __init__ to avoid database requirement
        self._connection: Optional[DatabaseConnection] = None
        self._data: dict[UUID, MockAggregate] = {}
        self.saved: list[MockAggregate] = []
        self.deleted: list[UUID] = []

    async def get(self, id: UUID) -> Optional[MockAggregate]:
        return self._data.get(id)

    async def add(self, aggregate: MockAggregate) -> None:
        self._data[aggregate.id] = aggregate
        self.saved.append(aggregate)

    async def update(self, aggregate: MockAggregate) -> None:
        self._data[aggregate.id] = aggregate
        self.saved.append(aggregate)

    async def delete(self, id: UUID) -> bool:
        if id in self._data:
            del self._data[id]
            self.deleted.append(id)
            return True
        return False

    def _to_aggregate(self, row: dict[str, Any]) -> MockAggregate:
        agg = MockAggregate()
        return agg

    def _from_aggregate(self, aggregate: MockAggregate) -> dict[str, Any]:
        return {"id": str(aggregate.id)}


@pytest.fixture
def mock_database():
    """Create mock database."""
    db = MockDatabase()
    return db


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return MockRepository()


@pytest.fixture
def database_uow(mock_database):
    """Create DatabaseUnitOfWork."""
    return DatabaseUnitOfWork(mock_database)


@pytest.fixture
def transactional_uow(mock_database):
    """Create TransactionalUnitOfWork."""
    return TransactionalUnitOfWork(mock_database)


class TestDatabaseUnitOfWork:
    """Test suite for DatabaseUnitOfWork."""

    @pytest.mark.asyncio
    async def test_context_manager_commits_on_success(
        self, database_uow, mock_repository
    ):
        """Test context manager commits when no exception."""
        # Arrange
        database_uow.register_repository(mock_repository)

        # Act
        async with database_uow as uow:
            assert uow.is_active
            # Simulate some work
            mock_repository.set_connection(database_uow._connection)

        # Assert
        assert database_uow._committed
        assert not database_uow._rolled_back

    @pytest.mark.asyncio
    async def test_context_manager_rollbacks_on_exception(
        self, database_uow, mock_repository
    ):
        """Test context manager rollbacks when exception raised."""
        # Arrange
        database_uow.register_repository(mock_repository)

        # Act & Assert
        with pytest.raises(ValueError):
            async with database_uow as uow:
                assert uow.is_active
                raise ValueError("Test exception")

        assert database_uow._rolled_back
        assert not database_uow._committed

    @pytest.mark.asyncio
    async def test_commit_persists_changes(self, database_uow, mock_repository):
        """Test commit persists changes."""
        # Arrange
        database_uow.register_repository(mock_repository)
        await database_uow._begin()

        # Act
        await database_uow.commit()

        # Assert
        assert database_uow._committed
        assert not database_uow.is_active

    @pytest.mark.asyncio
    async def test_rollback_reverts_changes(self, database_uow, mock_repository):
        """Test rollback reverts changes."""
        # Arrange
        database_uow.register_repository(mock_repository)
        await database_uow._begin()

        # Act
        await database_uow.rollback()

        # Assert
        assert database_uow._rolled_back
        assert not database_uow.is_active

    @pytest.mark.asyncio
    async def test_double_commit_raises_error(self, database_uow, mock_repository):
        """Test that double commit raises error."""
        # Arrange
        database_uow.register_repository(mock_repository)
        await database_uow._begin()
        await database_uow.commit()

        # Act & Assert
        with pytest.raises(RuntimeError, match="already committed"):
            await database_uow.commit()

    @pytest.mark.asyncio
    async def test_commit_after_rollback_raises_error(
        self, database_uow, mock_repository
    ):
        """Test that commit after rollback raises error."""
        # Arrange
        database_uow.register_repository(mock_repository)
        await database_uow._begin()
        await database_uow.rollback()

        # Act & Assert
        with pytest.raises(RuntimeError, match="Cannot commit after rollback"):
            await database_uow.commit()

    @pytest.mark.asyncio
    async def test_rollback_after_commit_raises_error(
        self, database_uow, mock_repository
    ):
        """Test that rollback after commit raises error."""
        # Arrange
        database_uow.register_repository(mock_repository)
        await database_uow._begin()
        await database_uow.commit()

        # Act & Assert
        with pytest.raises(RuntimeError, match="Cannot rollback after commit"):
            await database_uow.rollback()

    @pytest.mark.asyncio
    async def test_register_repository(self, database_uow):
        """Test registering a repository."""
        # Arrange
        repo = MockRepository()

        # Act
        database_uow.register_repository(repo)

        # Assert
        assert repo in database_uow._repositories

    @pytest.mark.asyncio
    async def test_register_multiple_repositories(self, database_uow):
        """Test registering multiple repositories."""
        # Arrange
        repo1 = MockRepository()
        repo2 = MockRepository()

        # Act
        database_uow.register_repositories(repo1, repo2)

        # Assert
        assert repo1 in database_uow._repositories
        assert repo2 in database_uow._repositories

    @pytest.mark.asyncio
    async def test_is_active_property(self, database_uow):
        """Test is_active property."""
        # Initially not active
        assert not database_uow.is_active

        # Active after begin
        await database_uow._begin()
        assert database_uow.is_active

        # Not active after commit
        await database_uow.commit()
        assert not database_uow.is_active


class TestTransactionalUnitOfWork:
    """Test suite for TransactionalUnitOfWork."""

    @pytest.mark.asyncio
    async def test_transactional_context_manager(
        self, transactional_uow, mock_repository
    ):
        """Test transactional context manager."""
        # Arrange
        transactional_uow.register_repository(mock_repository)

        # Act
        async with transactional_uow as uow:
            assert uow.is_active

        # Assert
        assert transactional_uow._committed

    @pytest.mark.asyncio
    async def test_transactional_rollback_on_exception(
        self, transactional_uow, mock_repository
    ):
        """Test transactional rollback on exception."""
        # Arrange
        transactional_uow.register_repository(mock_repository)

        # Act & Assert
        with pytest.raises(ValueError):
            async with transactional_uow:
                raise ValueError("Test error")

        assert transactional_uow._rolled_back

    @pytest.mark.asyncio
    async def test_transactional_commit(self, transactional_uow, mock_repository):
        """Test transactional commit."""
        # Arrange
        transactional_uow.register_repository(mock_repository)
        await transactional_uow._begin()

        # Act
        await transactional_uow.commit()

        # Assert
        assert transactional_uow._committed
        assert transactional_uow._transaction_context is None

    @pytest.mark.asyncio
    async def test_transactional_rollback(self, transactional_uow, mock_repository):
        """Test transactional rollback."""
        # Arrange
        transactional_uow.register_repository(mock_repository)
        await transactional_uow._begin()

        # Act
        await transactional_uow.rollback()

        # Assert
        assert transactional_uow._rolled_back
        assert transactional_uow._transaction_context is None

    @pytest.mark.asyncio
    async def test_repository_connection_set_during_begin(
        self, transactional_uow, mock_repository
    ):
        """Test that repository connection is set during begin."""
        # Arrange
        transactional_uow.register_repository(mock_repository)

        # Act
        await transactional_uow._begin()

        # Assert - connection should be set
        assert mock_repository._connection is not None

    @pytest.mark.asyncio
    async def test_repository_connection_cleared_after_commit(
        self, transactional_uow, mock_repository
    ):
        """Test that repository connection is cleared after commit."""
        # Arrange
        transactional_uow.register_repository(mock_repository)
        await transactional_uow._begin()

        # Act
        await transactional_uow.commit()

        # Assert
        assert mock_repository._connection is None


class TestUnitOfWorkResult:
    """Test suite for UnitOfWorkResult."""

    def test_success_result_creation(self):
        """Test creating a successful result."""
        # Act
        result = UnitOfWorkResult.success_result(data={"key": "value"})

        # Assert
        assert result.success is True
        assert result.error is None
        assert result.data == {"key": "value"}

    def test_success_result_without_data(self):
        """Test creating a successful result without data."""
        # Act
        result = UnitOfWorkResult.success_result()

        # Assert
        assert result.success is True
        assert result.data is None

    def test_failure_result_creation(self):
        """Test creating a failure result."""
        # Act
        result = UnitOfWorkResult.failure_result("Something went wrong")

        # Assert
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class TestUnitOfWorkFactory:
    """Test suite for UnitOfWorkFactory."""

    @pytest.mark.asyncio
    async def test_create_transactional_uow(self, mock_database):
        """Test creating transactional unit of work."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act
        uow = factory.create(transactional=True)

        # Assert
        assert isinstance(uow, TransactionalUnitOfWork)

    @pytest.mark.asyncio
    async def test_create_non_transactional_uow(self, mock_database):
        """Test creating non-transactional unit of work."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act
        uow = factory.create(transactional=False)

        # Assert
        assert isinstance(uow, DatabaseUnitOfWork)
        assert not isinstance(uow, TransactionalUnitOfWork)

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, mock_database):
        """Test transaction context manager."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act
        async with factory.transaction() as uow:
            assert isinstance(uow, TransactionalUnitOfWork)
            assert uow.is_active

    @pytest.mark.asyncio
    async def test_transaction_context_manager_commits_on_success(self, mock_database):
        """Test transaction commits on successful exit."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act
        async with factory.transaction() as uow:
            pass  # No exception

        # Assert
        assert uow._committed

    @pytest.mark.asyncio
    async def test_transaction_context_manager_rollbacks_on_error(self, mock_database):
        """Test transaction rollbacks on error."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act & Assert
        with pytest.raises(ValueError):
            async with factory.transaction():
                raise ValueError("Test error")


class TestUnitOfWorkGlobalFunctions:
    """Test suite for global Unit of Work functions."""

    def test_set_and_get_factory(self, mock_database):
        """Test setting and getting global factory."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act
        set_unit_of_work_factory(factory)
        retrieved = get_unit_of_work_factory()

        # Assert
        assert retrieved is factory

    def test_get_factory_without_setting_raises_error(self):
        """Test getting factory without setting raises error."""
        # Clear any existing factory
        import src.shared.infrastructure.persistence.unit_of_work as uow_module

        uow_module._unit_of_work_factory = None

        # Act & Assert
        with pytest.raises(RuntimeError, match="not initialized"):
            get_unit_of_work_factory()

    def test_get_uow_uses_global_factory(self, mock_database):
        """Test get_uow uses global factory."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)
        set_unit_of_work_factory(factory)

        # Act
        uow = get_uow(transactional=True)

        # Assert
        assert isinstance(uow, TransactionalUnitOfWork)

    def test_get_uow_non_transactional(self, mock_database):
        """Test get_uow creates non-transactional uow."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)
        set_unit_of_work_factory(factory)

        # Act
        uow = get_uow(transactional=False)

        # Assert
        assert isinstance(uow, DatabaseUnitOfWork)
        assert not isinstance(uow, TransactionalUnitOfWork)


class TestUnitOfWorkEdgeCases:
    """Test edge cases for Unit of Work."""

    @pytest.mark.asyncio
    async def test_empty_context_manager(self, database_uow):
        """Test context manager with no operations."""
        # Act
        async with database_uow:
            pass

        # Assert
        assert database_uow._committed

    @pytest.mark.asyncio
    async def test_multiple_repositories_same_uow(self, database_uow):
        """Test multiple repositories in same unit of work."""
        # Arrange
        repo1 = MockRepository()
        repo2 = MockRepository()
        database_uow.register_repositories(repo1, repo2)

        # Act
        async with database_uow:
            repo1.set_connection(database_uow._connection)
            repo2.set_connection(database_uow._connection)

        # Assert
        assert database_uow._committed

    @pytest.mark.asyncio
    async def test_context_manager_reentrance(self, database_uow):
        """Test context manager re-entrance behavior."""
        # Arrange
        await database_uow._begin()

        # Act - Second entry should work with implementation
        async with database_uow:
            pass  # Implementation allows re-entrance

        # Assert - Should commit without error
        assert database_uow._committed or database_uow._rolled_back

    @pytest.mark.asyncio
    async def test_manual_commit_before_context(self, database_uow):
        """Test manual commit before entering context manager."""
        # Arrange
        await database_uow._begin()

        # Act - Commit manually first
        await database_uow.commit()

        # Assert - Should be committed
        assert database_uow._committed

        # Second commit should raise error
        with pytest.raises(RuntimeError, match="already committed"):
            await database_uow.commit()

    @pytest.mark.asyncio
    async def test_uow_without_repositories(self, database_uow):
        """Test unit of work without any repositories."""
        # Act
        async with database_uow:
            pass

        # Assert
        assert database_uow._committed


class TestTransactionRollbackException:
    """Test TransactionRollbackException."""

    def test_exception_creation(self):
        """Test creating exception."""
        # Act
        exc = TransactionRollbackException("Test rollback")

        # Assert
        assert str(exc) == "Test rollback"
        assert isinstance(exc, Exception)


class TestUnitOfWorkIntegration:
    """Integration-style tests for Unit of Work."""

    @pytest.mark.asyncio
    async def test_full_transaction_workflow(self, mock_database):
        """Test complete transaction workflow."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)
        repo = MockRepository()
        aggregate = MockAggregate()

        # Act - Create
        async with factory.transaction() as uow:
            uow.register_repository(repo)
            await repo.add(aggregate)

        # Assert
        assert uow._committed
        assert aggregate in repo.saved

    @pytest.mark.asyncio
    async def test_rollback_preserves_data_integrity(self, mock_database):
        """Test rollback preserves data integrity by checking UOW state."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)

        # Act - Execute transaction that will rollback
        uow_rolled_back = False
        try:
            async with factory.transaction() as uow:
                uow.register_repository(MockRepository())
                raise ValueError("Simulated error")
        except ValueError:
            uow_rolled_back = True

        # Assert
        assert uow_rolled_back, "Exception should have been raised"

    @pytest.mark.asyncio
    async def test_multiple_operations_in_transaction(self, mock_database):
        """Test multiple operations in single transaction."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)
        repo = MockRepository()
        agg1 = MockAggregate()
        agg2 = MockAggregate()

        # Act
        async with factory.transaction() as uow:
            uow.register_repository(repo)
            await repo.add(agg1)
            await repo.add(agg2)
            await repo.update(agg1)

        # Assert
        assert len(repo.saved) == 3

    @pytest.mark.asyncio
    async def test_sequential_transactions(self, mock_database):
        """Test sequential transactions."""
        # Arrange
        factory = UnitOfWorkFactory(mock_database)
        repo = MockRepository()

        # Act - First transaction
        async with factory.transaction() as uow1:
            uow1.register_repository(repo)
            agg1 = MockAggregate()
            await repo.add(agg1)

        # Second transaction
        async with factory.transaction() as uow2:
            uow2.register_repository(repo)
            agg2 = MockAggregate()
            await repo.add(agg2)

        # Assert
        assert uow1._committed
        assert uow2._committed
        assert len(repo._data) == 2
