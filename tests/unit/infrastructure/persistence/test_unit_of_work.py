"""Tests for Unit of Work implementation."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any
from uuid import UUID, uuid4

from src.shared.infrastructure.persistence.unit_of_work import (
    DatabaseUnitOfWork,
    TransactionalUnitOfWork,
    TransactionRollbackException,
    UnitOfWorkResult,
    UnitOfWorkFactory,
    set_unit_of_work_factory,
    get_unit_of_work_factory,
    get_uow,
)
from src.shared.infrastructure.persistence.database import Database, DatabaseConnection
from src.shared.infrastructure.persistence.repository import (
    BaseRepository,
    InMemoryRepository,
)
from src.shared.domain.base.aggregate import AggregateRoot
from dataclasses import dataclass


@dataclass
class TestAggregate(AggregateRoot):
    """Test aggregate for UoW testing."""

    name: str = ""

    def validate_invariants(self) -> None:
        """Validate aggregate invariants."""
        pass


class TestRepository(BaseRepository[TestAggregate, UUID]):
    """Test repository."""

    async def get(self, id: UUID) -> TestAggregate | None:
        return None

    async def add(self, aggregate: TestAggregate) -> None:
        pass

    async def update(self, aggregate: TestAggregate) -> None:
        pass

    async def delete(self, id: UUID) -> bool:
        return True

    def _to_aggregate(self, row: dict[str, Any]) -> TestAggregate:
        return TestAggregate()

    def _from_aggregate(self, aggregate: TestAggregate) -> dict[str, Any]:
        return {}


class TestDatabaseUnitOfWork:
    """Test cases for DatabaseUnitOfWork."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock database."""
        db = MagicMock(spec=Database)
        return db

    @pytest.fixture
    def mock_conn(self) -> AsyncMock:
        """Create a mock connection."""
        conn = AsyncMock(spec=DatabaseConnection)
        return conn

    @pytest.fixture
    def uow(self, mock_db: MagicMock) -> DatabaseUnitOfWork:
        """Create a Unit of Work."""
        return DatabaseUnitOfWork(mock_db)

    @pytest.mark.asyncio
    async def test_initialization(
        self, uow: DatabaseUnitOfWork, mock_db: MagicMock
    ) -> None:
        """Test UoW initialization."""
        assert uow._db == mock_db
        assert uow._connection is None
        assert uow._repositories == []
        assert not uow._committed
        assert not uow._rolled_back

    @pytest.mark.asyncio
    async def test_register_repository(
        self, uow: DatabaseUnitOfWork, mock_db: MagicMock
    ) -> None:
        """Test registering a repository."""
        repo = TestRepository(mock_db)

        uow.register_repository(repo)

        assert repo in uow._repositories

    @pytest.mark.asyncio
    async def test_register_repositories(
        self, uow: DatabaseUnitOfWork, mock_db: MagicMock
    ) -> None:
        """Test registering multiple repositories."""
        repo1 = TestRepository(mock_db)
        repo2 = TestRepository(mock_db)

        uow.register_repositories(repo1, repo2)

        assert repo1 in uow._repositories
        assert repo2 in uow._repositories

    @pytest.mark.asyncio
    async def test_context_manager_enters(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test context manager enters correctly."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow as u:
            assert u == uow

    @pytest.mark.asyncio
    async def test_context_manager_commits_on_success(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test context manager commits when no exception."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow:
            pass

        assert uow._committed

    @pytest.mark.asyncio
    async def test_context_manager_rolls_back_on_exception(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test context manager rolls back on exception."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test error")

        assert uow._rolled_back

    @pytest.mark.asyncio
    async def test_commit_sets_connection_on_repositories(
        self, uow: DatabaseUnitOfWork, mock_db: MagicMock, mock_conn: AsyncMock
    ) -> None:
        """Test commit sets connection on repositories."""
        repo = TestRepository(mock_db)
        uow.register_repository(repo)
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow:
            assert repo._connection == mock_conn

        # After commit, connection should be cleared
        assert repo._connection is None

    @pytest.mark.asyncio
    async def test_commit_raises_if_already_committed(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test commit raises if already committed."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow:
            pass

        with pytest.raises(RuntimeError, match="already committed"):
            await uow.commit()

    @pytest.mark.asyncio
    async def test_commit_raises_if_rolled_back(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test commit raises if already rolled back."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test error")

        with pytest.raises(RuntimeError, match="Cannot commit after rollback"):
            await uow.commit()

    @pytest.mark.asyncio
    async def test_rollback_raises_if_already_committed(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test rollback raises if already committed."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow:
            pass

        with pytest.raises(RuntimeError, match="Cannot rollback after commit"):
            await uow.rollback()

    @pytest.mark.asyncio
    async def test_is_active_property(
        self, uow: DatabaseUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test is_active property."""
        uow._db.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        assert not uow.is_active

        async with uow:
            assert uow.is_active

        assert not uow.is_active


class TestTransactionalUnitOfWork:
    """Test cases for TransactionalUnitOfWork."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock database."""
        db = MagicMock(spec=Database)
        return db

    @pytest.fixture
    def mock_conn(self) -> AsyncMock:
        """Create a mock connection."""
        conn = AsyncMock(spec=DatabaseConnection)
        return conn

    @pytest.fixture
    def uow(self, mock_db: MagicMock) -> TransactionalUnitOfWork:
        """Create a transactional UoW."""
        return TransactionalUnitOfWork(mock_db)

    @pytest.mark.asyncio
    async def test_initialization(
        self, uow: TransactionalUnitOfWork, mock_db: MagicMock
    ) -> None:
        """Test transactional UoW initialization."""
        assert uow._db == mock_db
        assert uow._transaction_context is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager(
        self, uow: TransactionalUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test transactional context manager."""
        uow._db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow as u:
            assert u == uow

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(
        self, uow: TransactionalUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test transaction commits when no exception."""
        uow._db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

        async with uow:
            pass

        assert uow._committed
        assert uow._db.transaction.return_value.__aexit__.called

    @pytest.mark.asyncio
    async def test_transaction_rolls_back_on_exception(
        self, uow: TransactionalUnitOfWork, mock_conn: AsyncMock
    ) -> None:
        """Test transaction rolls back on exception."""
        uow._db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        uow._db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test error")

        assert uow._rolled_back


class TestUnitOfWorkResult:
    """Test cases for UnitOfWorkResult."""

    def test_success_result(self) -> None:
        """Test creating success result."""
        result = UnitOfWorkResult.success_result(data={"id": 1})

        assert result.success is True
        assert result.error is None
        assert result.data == {"id": 1}

    def test_success_result_without_data(self) -> None:
        """Test creating success result without data."""
        result = UnitOfWorkResult.success_result()

        assert result.success is True
        assert result.error is None
        assert result.data is None

    def test_failure_result(self) -> None:
        """Test creating failure result."""
        result = UnitOfWorkResult.failure_result("Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class TestUnitOfWorkFactory:
    """Test cases for UnitOfWorkFactory."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock database."""
        return MagicMock(spec=Database)

    @pytest.fixture
    def factory(self, mock_db: MagicMock) -> UnitOfWorkFactory:
        """Create a UoW factory."""
        return UnitOfWorkFactory(mock_db)

    def test_initialization(
        self, factory: UnitOfWorkFactory, mock_db: MagicMock
    ) -> None:
        """Test factory initialization."""
        assert factory._db == mock_db

    def test_create_transactional_uow(self, factory: UnitOfWorkFactory) -> None:
        """Test creating transactional UoW."""
        uow = factory.create(transactional=True)

        assert isinstance(uow, TransactionalUnitOfWork)

    def test_create_non_transactional_uow(self, factory: UnitOfWorkFactory) -> None:
        """Test creating non-transactional UoW."""
        uow = factory.create(transactional=False)

        assert isinstance(uow, DatabaseUnitOfWork)
        assert not isinstance(uow, TransactionalUnitOfWork)

    @pytest.mark.asyncio
    async def test_transaction_context_manager(
        self, factory: UnitOfWorkFactory
    ) -> None:
        """Test transaction context manager."""
        mock_conn = AsyncMock()
        factory._db.transaction.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        factory._db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

        async with factory.transaction() as uow:
            assert isinstance(uow, TransactionalUnitOfWork)


class TestGlobalUnitOfWorkFunctions:
    """Test cases for global UoW functions."""

    def test_set_and_get_factory(self) -> None:
        """Test setting and getting global factory."""
        mock_db = MagicMock(spec=Database)
        factory = UnitOfWorkFactory(mock_db)

        set_unit_of_work_factory(factory)

        retrieved = get_unit_of_work_factory()
        assert retrieved == factory

    def test_get_factory_raises_when_not_set(self) -> None:
        """Test get_factory raises when not initialized."""
        # Reset global state
        import src.shared.infrastructure.persistence.unit_of_work as uow_module

        uow_module._unit_of_work_factory = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_unit_of_work_factory()

    def test_get_uow(self) -> None:
        """Test get_uow convenience function."""
        mock_db = MagicMock(spec=Database)
        factory = UnitOfWorkFactory(mock_db)
        set_unit_of_work_factory(factory)

        uow = get_uow()

        assert isinstance(uow, TransactionalUnitOfWork)

    def test_get_uow_non_transactional(self) -> None:
        """Test get_uow with non-transactional."""
        mock_db = MagicMock(spec=Database)
        factory = UnitOfWorkFactory(mock_db)
        set_unit_of_work_factory(factory)

        uow = get_uow(transactional=False)

        assert isinstance(uow, DatabaseUnitOfWork)
        assert not isinstance(uow, TransactionalUnitOfWork)


class TestTransactionRollbackException:
    """Test cases for TransactionRollbackException."""

    def test_exception_message(self) -> None:
        """Test exception message."""
        exc = TransactionRollbackException("Transaction failed")

        assert str(exc) == "Transaction failed"

    def test_exception_is_exception(self) -> None:
        """Test TransactionRollbackException is an Exception."""
        exc = TransactionRollbackException("Test")

        assert isinstance(exc, Exception)
