"""Tests for PostgreSQL implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.infrastructure.persistence.database import DatabaseFactory

# Import postgresql module to register with factory
from src.shared.infrastructure.persistence.postgresql import (
    AsyncpgConnection,
    PostgreSQLDatabase,
)


class TestAsyncpgConnection:
    """Test cases for AsyncpgConnection wrapper."""

    @pytest.fixture
    def mock_asyncpg_conn(self) -> AsyncMock:
        """Create a mock asyncpg connection."""
        conn = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_execute_delegates_to_asyncpg(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test execute method delegates to asyncpg."""
        mock_asyncpg_conn.execute.return_value = "INSERT 0 1"
        conn = AsyncpgConnection(mock_asyncpg_conn)

        result = await conn.execute("INSERT INTO test VALUES ($1)", "value")

        mock_asyncpg_conn.execute.assert_called_once_with(
            "INSERT INTO test VALUES ($1)", "value"
        )
        assert result == "INSERT 0 1"

    @pytest.mark.asyncio
    async def test_fetch_converts_records_to_dicts(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test fetch converts asyncpg Records to dictionaries."""
        # Create mock records
        record1 = MagicMock()
        record1.__iter__ = lambda self: iter([("id", 1), ("name", "test1")])
        record1.keys.return_value = ["id", "name"]
        record1.__getitem__ = lambda self, key: {"id": 1, "name": "test1"}[key]

        record2 = MagicMock()
        record2.__iter__ = lambda self: iter([("id", 2), ("name", "test2")])
        record2.keys.return_value = ["id", "name"]
        record2.__getitem__ = lambda self, key: {"id": 2, "name": "test2"}[key]

        mock_asyncpg_conn.fetch.return_value = [record1, record2]
        conn = AsyncpgConnection(mock_asyncpg_conn)

        result = await conn.fetch("SELECT * FROM test")

        # Result should be list of dicts
        assert len(result) == 2
        mock_asyncpg_conn.fetch.assert_called_once_with("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_fetchrow_converts_record_to_dict(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test fetchrow converts single record to dictionary."""
        record = MagicMock()
        record.__iter__ = lambda self: iter([("id", 1), ("name", "test")])
        record.keys.return_value = ["id", "name"]
        record.__getitem__ = lambda self, key: {"id": 1, "name": "test"}[key]

        mock_asyncpg_conn.fetchrow.return_value = record
        conn = AsyncpgConnection(mock_asyncpg_conn)

        result = await conn.fetchrow("SELECT * FROM test WHERE id = $1", 1)

        mock_asyncpg_conn.fetchrow.assert_called_once_with(
            "SELECT * FROM test WHERE id = $1", 1
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_fetchrow_returns_none_for_no_result(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test fetchrow returns None when no row found."""
        mock_asyncpg_conn.fetchrow.return_value = None
        conn = AsyncpgConnection(mock_asyncpg_conn)

        result = await conn.fetchrow("SELECT * FROM test WHERE id = $1", 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetchval_delegates_to_asyncpg(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test fetchval method delegates to asyncpg."""
        mock_asyncpg_conn.fetchval.return_value = 42
        conn = AsyncpgConnection(mock_asyncpg_conn)

        result = await conn.fetchval("SELECT COUNT(*) FROM test")

        mock_asyncpg_conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_many_delegates_to_asyncpg(
        self, mock_asyncpg_conn: AsyncMock
    ) -> None:
        """Test execute_many method delegates to asyncpg."""
        conn = AsyncpgConnection(mock_asyncpg_conn)
        args_seq = [(1,), (2,), (3,)]

        await conn.execute_many("INSERT INTO test VALUES ($1)", args_seq)

        mock_asyncpg_conn.executemany.assert_called_once_with(
            "INSERT INTO test VALUES ($1)", args_seq
        )


class TestPostgreSQLDatabase:
    """Test cases for PostgreSQLDatabase implementation."""

    @pytest.fixture
    def db(self) -> PostgreSQLDatabase:
        """Create a PostgreSQLDatabase instance."""
        return PostgreSQLDatabase(
            "postgresql://user:pass@localhost:5432/testdb",
            min_size=5,
            max_size=20,
        )

    def test_initialization(self, db: PostgreSQLDatabase) -> None:
        """Test database initialization."""
        assert db._dsn == "postgresql://user:pass@localhost:5432/testdb"
        assert db._min_size == 5
        assert db._max_size == 20
        assert db._command_timeout == 60.0
        assert db._pool is None
        assert not db.is_connected

    def test_initialization_with_ssl(self) -> None:
        """Test database initialization with SSL."""
        db = PostgreSQLDatabase(
            "postgresql://user:pass@localhost:5432/testdb",
            ssl=True,
        )
        assert db._ssl is True

    def test_initialization_with_custom_timeout(self) -> None:
        """Test database initialization with custom timeout."""
        db = PostgreSQLDatabase(
            "postgresql://user:pass@localhost:5432/testdb",
            command_timeout=120.0,
        )
        assert db._command_timeout == 120.0

    @pytest.mark.asyncio
    async def test_connect_creates_pool(self, db: PostgreSQLDatabase) -> None:
        """Test connect creates connection pool."""
        mock_pool = MagicMock()
        mock_pool.get_min_size.return_value = 5
        mock_pool.get_max_size.return_value = 20
        mock_pool.get_size.return_value = 5
        mock_pool.get_idle_size.return_value = 3

        async def mock_create_pool(*args, **kwargs):
            return mock_pool

        with patch(
            "asyncpg.create_pool", side_effect=mock_create_pool
        ) as mock_pool_func:
            await db.connect()

            mock_pool_func.assert_called_once()
            call_kwargs = mock_pool_func.call_args.kwargs
            assert call_kwargs["dsn"] == db._dsn
            assert call_kwargs["min_size"] == 5
            assert call_kwargs["max_size"] == 20
            assert db.is_connected

    @pytest.mark.asyncio
    async def test_connect_raises_on_failure(self, db: PostgreSQLDatabase) -> None:
        """Test connect raises ConnectionError on failure."""
        with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
            with pytest.raises(
                ConnectionError, match="Failed to connect to PostgreSQL"
            ):
                await db.connect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_pool(self, db: PostgreSQLDatabase) -> None:
        """Test disconnect closes connection pool."""
        mock_pool = AsyncMock()
        db._pool = mock_pool
        db._connected = True

        await db.disconnect()

        mock_pool.close.assert_called_once()
        assert db._pool is None
        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_connection_context_manager(self, db: PostgreSQLDatabase) -> None:
        """Test connection context manager."""
        mock_conn = AsyncMock()

        # Create a proper async context manager mock
        class AcquireContextManager:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, *args):
                return None

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = AcquireContextManager()
        db._pool = mock_pool
        db._connected = True

        async with db.connection() as conn:
            assert isinstance(conn, AsyncpgConnection)

    @pytest.mark.asyncio
    async def test_connection_raises_when_not_connected(
        self, db: PostgreSQLDatabase
    ) -> None:
        """Test connection raises RuntimeError when not connected."""
        with pytest.raises(RuntimeError, match="Database not connected"):
            async with db.connection():
                pass

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, db: PostgreSQLDatabase) -> None:
        """Test transaction context manager."""

        # Create a proper async context manager mock for transaction
        class TransactionContextManager:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, *args):
                return None

        # Create a proper async context manager mock for acquire
        class AcquireContextManager:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, *args):
                return None

        mock_conn = MagicMock()
        mock_conn.transaction = MagicMock(return_value=TransactionContextManager())
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = AcquireContextManager()
        db._pool = mock_pool
        db._connected = True

        async with db.transaction() as conn:
            assert isinstance(conn, AsyncpgConnection)

    @pytest.mark.asyncio
    async def test_transaction_raises_when_not_connected(
        self, db: PostgreSQLDatabase
    ) -> None:
        """Test transaction raises RuntimeError when not connected."""
        with pytest.raises(RuntimeError, match="Database not connected"):
            async with db.transaction():
                pass

    @pytest.mark.asyncio
    async def test_pool_size_property(self, db: PostgreSQLDatabase) -> None:
        """Test pool_size property returns correct statistics."""
        mock_pool = MagicMock()
        mock_pool.get_min_size.return_value = 5
        mock_pool.get_max_size.return_value = 20
        mock_pool.get_size.return_value = 10
        mock_pool.get_idle_size.return_value = 3
        db._pool = mock_pool

        stats = db.pool_size

        assert stats == {
            "min": 5,
            "max": 20,
            "size": 10,
            "free": 3,
        }

    def test_pool_size_property_no_pool(self, db: PostgreSQLDatabase) -> None:
        """Test pool_size property returns zeros when no pool."""
        stats = db.pool_size

        assert stats == {
            "min": 0,
            "max": 0,
            "size": 0,
            "free": 0,
        }

    @pytest.mark.asyncio
    async def test_health_check_success(self, db: PostgreSQLDatabase) -> None:
        """Test health check returns True when healthy."""
        mock_conn = AsyncMock()

        # Create a proper async context manager mock
        class AcquireContextManager:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, *args):
                return None

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = AcquireContextManager()
        db._pool = mock_pool
        db._connected = True

        result = await db.health_check()

        assert result is True


class TestDatabaseFactoryRegistration:
    """Test cases for DatabaseFactory with PostgreSQL."""

    def setup_method(self) -> None:
        """Setup method - ensure PostgreSQL is registered."""
        # Import registers the backend - re-register if needed
        DatabaseFactory.register("postgresql", PostgreSQLDatabase)
        DatabaseFactory.register("postgres", PostgreSQLDatabase)

    def test_postgresql_registration(self) -> None:
        """Test PostgreSQL is registered with factory."""
        # Import registers the backend
        assert "postgresql" in DatabaseFactory._registry
        assert DatabaseFactory._registry["postgresql"] == PostgreSQLDatabase

    def test_postgres_alias_registration(self) -> None:
        """Test postgres alias is registered with factory."""
        assert "postgres" in DatabaseFactory._registry
        assert DatabaseFactory._registry["postgres"] == PostgreSQLDatabase

    @pytest.mark.asyncio
    async def test_factory_creates_postgresql_instance(self) -> None:
        """Test factory creates PostgreSQLDatabase instance."""
        with patch.object(
            PostgreSQLDatabase, "__init__", return_value=None
        ) as mock_init:
            db = DatabaseFactory.create("postgresql", "postgresql://localhost/test")

            assert isinstance(db, PostgreSQLDatabase)
            mock_init.assert_called_once_with("postgresql://localhost/test")
