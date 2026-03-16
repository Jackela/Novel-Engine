"""Tests for repository base classes."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from src.shared.domain.base.aggregate import AggregateRoot
from src.shared.infrastructure.persistence.repository import (
    BaseRepository,
    InMemoryRepository,
    Repository,
    AggregateNotFoundException,
    ConcurrentModificationException,
    RepositoryException,
)
from src.shared.infrastructure.persistence.database import Database, DatabaseConnection


@dataclass
class TestAggregate(AggregateRoot):
    """Test aggregate for repository testing."""

    name: str = ""
    email: str = ""

    def validate_invariants(self) -> None:
        """Validate aggregate invariants."""
        if not self.name:
            raise ValueError("Name is required")


class TestRepository(BaseRepository[TestAggregate, UUID]):
    """Test repository implementation."""

    async def get(self, id: UUID) -> TestAggregate | None:
        """Get aggregate by ID."""
        row = await self.connection.fetchrow(
            "SELECT * FROM test_aggregates WHERE id = $1", id
        )
        return self._to_aggregate(row) if row else None

    async def add(self, aggregate: TestAggregate) -> None:
        """Add aggregate."""
        row = self._from_aggregate(aggregate)
        await self.connection.execute(
            "INSERT INTO test_aggregates (id, name, email) VALUES ($1, $2, $3)",
            row["id"],
            row["name"],
            row["email"],
        )

    async def update(self, aggregate: TestAggregate) -> None:
        """Update aggregate."""
        row = self._from_aggregate(aggregate)
        await self.connection.execute(
            "UPDATE test_aggregates SET name = $1, email = $2 WHERE id = $3",
            row["name"],
            row["email"],
            row["id"],
        )

    async def delete(self, id: UUID) -> bool:
        """Delete aggregate."""
        result = await self.connection.execute(
            "DELETE FROM test_aggregates WHERE id = $1", id
        )
        return "DELETE 1" in result

    def _to_aggregate(self, row: dict[str, Any]) -> TestAggregate:
        """Convert row to aggregate."""
        return TestAggregate(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row.get("created_at", datetime.utcnow()),
            updated_at=row.get("updated_at", datetime.utcnow()),
        )

    def _from_aggregate(self, aggregate: TestAggregate) -> dict[str, Any]:
        """Convert aggregate to row."""
        return {
            "id": aggregate.id,
            "name": aggregate.name,
            "email": aggregate.email,
        }


class TestBaseRepository:
    """Test cases for BaseRepository."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock database."""
        return MagicMock(spec=Database)

    @pytest.fixture
    def mock_conn(self) -> AsyncMock:
        """Create a mock connection."""
        conn = AsyncMock(spec=DatabaseConnection)
        return conn

    @pytest.fixture
    def repo(self, mock_db: MagicMock) -> TestRepository:
        """Create a test repository."""
        return TestRepository(mock_db)

    def test_initialization(self, repo: TestRepository, mock_db: MagicMock) -> None:
        """Test repository initialization."""
        assert repo._db == mock_db
        assert repo._connection is None

    def test_connection_property_raises_without_connection(
        self, repo: TestRepository
    ) -> None:
        """Test connection property raises when no connection set."""
        with pytest.raises(RuntimeError, match="No connection available"):
            _ = repo.connection

    def test_connection_property_returns_connection(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test connection property returns set connection."""
        repo.set_connection(mock_conn)

        assert repo.connection == mock_conn

    def test_set_connection(self, repo: TestRepository, mock_conn: AsyncMock) -> None:
        """Test setting connection."""
        repo.set_connection(mock_conn)

        assert repo._connection == mock_conn

    def test_set_connection_to_none(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test clearing connection."""
        repo.set_connection(mock_conn)
        repo.set_connection(None)

        assert repo._connection is None

    @pytest.mark.asyncio
    async def test_get_returns_aggregate(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test get returns aggregate when found."""
        aggregate_id = uuid4()
        row = {
            "id": aggregate_id,
            "name": "Test",
            "email": "test@example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_conn.fetchrow.return_value = row
        repo.set_connection(mock_conn)

        result = await repo.get(aggregate_id)

        assert result is not None
        assert result.id == aggregate_id
        assert result.name == "Test"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test get returns None when aggregate not found."""
        aggregate_id = uuid4()
        mock_conn.fetchrow.return_value = None
        repo.set_connection(mock_conn)

        result = await repo.get(aggregate_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test exists returns True when aggregate found."""
        aggregate_id = uuid4()
        row = {
            "id": aggregate_id,
            "name": "Test",
            "email": "test@example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_conn.fetchrow.return_value = row
        repo.set_connection(mock_conn)

        result = await repo.exists(aggregate_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test exists returns False when aggregate not found."""
        aggregate_id = uuid4()
        mock_conn.fetchrow.return_value = None
        repo.set_connection(mock_conn)

        result = await repo.exists(aggregate_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_add_inserts_aggregate(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test add inserts aggregate."""
        aggregate = TestAggregate(name="Test", email="test@example.com")
        repo.set_connection(mock_conn)

        await repo.add(aggregate)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_update_updates_aggregate(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test update modifies aggregate."""
        aggregate = TestAggregate(name="Updated", email="updated@example.com")
        repo.set_connection(mock_conn)

        await repo.update(aggregate)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "UPDATE" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test delete returns True when aggregate deleted."""
        aggregate_id = uuid4()
        mock_conn.execute.return_value = "DELETE 1"
        repo.set_connection(mock_conn)

        result = await repo.delete(aggregate_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, repo: TestRepository, mock_conn: AsyncMock
    ) -> None:
        """Test delete returns False when aggregate not found."""
        aggregate_id = uuid4()
        mock_conn.execute.return_value = "DELETE 0"
        repo.set_connection(mock_conn)

        result = await repo.delete(aggregate_id)

        assert result is False


class TestInMemoryRepository:
    """Test cases for InMemoryRepository."""

    @pytest.fixture
    def repo(self) -> InMemoryRepository[TestAggregate, UUID]:
        """Create an in-memory repository."""
        return InMemoryRepository[TestAggregate, UUID]()

    @pytest.fixture
    def aggregate(self) -> TestAggregate:
        """Create a test aggregate."""
        return TestAggregate(name="Test", email="test@example.com")

    @pytest.mark.asyncio
    async def test_add_stores_aggregate(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test add stores aggregate in memory."""
        await repo.add(aggregate)

        assert aggregate.id in repo._data

    @pytest.mark.asyncio
    async def test_get_retrieves_aggregate(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test get retrieves stored aggregate."""
        await repo.add(aggregate)

        result = await repo.get(aggregate.id)

        assert result == aggregate

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, repo: InMemoryRepository) -> None:
        """Test get returns None for missing aggregate."""
        result = await repo.get(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update_modifies_aggregate(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test update modifies stored aggregate."""
        await repo.add(aggregate)
        aggregate.name = "Updated"

        await repo.update(aggregate)

        stored = await repo.get(aggregate.id)
        assert stored.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_removes_aggregate(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test delete removes aggregate."""
        await repo.add(aggregate)

        result = await repo.delete(aggregate.id)

        assert result is True
        assert aggregate.id not in repo._data

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(
        self, repo: InMemoryRepository
    ) -> None:
        """Test delete returns False for missing aggregate."""
        result = await repo.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test exists returns True for existing aggregate."""
        await repo.add(aggregate)

        result = await repo.exists(aggregate.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing(
        self, repo: InMemoryRepository
    ) -> None:
        """Test exists returns False for missing aggregate."""
        result = await repo.exists(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_returns_all_aggregates(
        self, repo: InMemoryRepository
    ) -> None:
        """Test get_all returns all stored aggregates."""
        agg1 = TestAggregate(name="Test1")
        agg2 = TestAggregate(name="Test2")
        await repo.add(agg1)
        await repo.add(agg2)

        result = await repo.get_all()

        assert len(result) == 2
        assert agg1 in result
        assert agg2 in result

    @pytest.mark.asyncio
    async def test_clear_removes_all_aggregates(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test clear removes all aggregates."""
        await repo.add(aggregate)

        await repo.clear()

        assert len(repo._data) == 0

    def test_no_database_required(self) -> None:
        """Test InMemoryRepository doesn't require database."""
        repo = InMemoryRepository[TestAggregate, UUID]()

        # Should not raise
        assert repo._connection is None
        assert repo._data == {}

    @pytest.mark.asyncio
    async def test_update_nonexistent_aggregate(
        self, repo: InMemoryRepository, aggregate: TestAggregate
    ) -> None:
        """Test update doesn't fail for non-existent aggregate."""
        # Should not raise, just does nothing
        await repo.update(aggregate)

        assert aggregate.id not in repo._data


class TestRepositoryExceptions:
    """Test cases for repository exceptions."""

    def test_repository_exception_base(self) -> None:
        """Test RepositoryException base class."""
        exc = RepositoryException("Test error")

        assert str(exc) == "Test error"

    def test_aggregate_not_found_exception(self) -> None:
        """Test AggregateNotFoundException."""
        exc = AggregateNotFoundException("User", uuid4())

        assert "User" in str(exc)
        assert exc.aggregate_type == "User"
        assert exc.id is not None

    def test_concurrent_modification_exception(self) -> None:
        """Test ConcurrentModificationException."""
        agg_id = uuid4()
        exc = ConcurrentModificationException("User", agg_id, 5, 8)

        assert "User" in str(exc)
        assert "5" in str(exc)
        assert "8" in str(exc)
        assert exc.aggregate_type == "User"
        assert exc.id == agg_id
        assert exc.expected == 5
        assert exc.actual == 8

    def test_exception_inheritance(self) -> None:
        """Test exception inheritance."""
        assert issubclass(AggregateNotFoundException, RepositoryException)
        assert issubclass(ConcurrentModificationException, RepositoryException)


class TestRepositoryProtocol:
    """Test cases for Repository protocol."""

    def test_repository_protocol_is_runtime_checkable(self) -> None:
        """Test that Repository protocol can be used with isinstance."""
        from typing import runtime_checkable

        # Repository should be runtime checkable
        assert hasattr(Repository, "__subclasshook__")

    @pytest.mark.asyncio
    async def test_inmemory_repository_implements_protocol(self) -> None:
        """Test InMemoryRepository implements Repository protocol."""
        repo = InMemoryRepository[TestAggregate, UUID]()

        # Should satisfy the protocol
        assert hasattr(repo, "get")
        assert hasattr(repo, "add")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "exists")
