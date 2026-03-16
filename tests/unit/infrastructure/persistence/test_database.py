"""Tests for database abstraction layer."""

from __future__ import annotations

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.shared.infrastructure.persistence.database import (
    Database,
    DatabaseFactory,
    DEFAULT_POOL_MIN_SIZE,
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_COMMAND_TIMEOUT,
)


class MockDatabaseConnection:
    """Mock database connection for testing."""

    def __init__(self):
        self.execute = AsyncMock()
        self.fetch = AsyncMock(return_value=[])
        self.fetchrow = AsyncMock(return_value=None)
        self.fetchval = AsyncMock(return_value=None)
        self.execute_many = AsyncMock()


class MockDatabase(Database):
    """Mock database implementation for testing."""

    def __init__(self, dsn: str, **kwargs: Any) -> None:
        super().__init__(dsn, **kwargs)
        self._connection = MockDatabaseConnection()

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    @asynccontextmanager
    async def connection(self):
        """Yield a mock connection."""
        yield self._connection

    @asynccontextmanager
    async def transaction(self):
        """Yield a mock connection."""
        yield self._connection


class TestDatabase:
    """Test cases for Database base class."""

    @pytest.mark.asyncio
    async def test_initialization(self) -> None:
        """Test database initialization."""
        db = MockDatabase("postgresql://localhost/test")

        assert db._dsn == "postgresql://localhost/test"
        assert not db.is_connected
        assert db._kwargs == {}

    @pytest.mark.asyncio
    async def test_initialization_with_kwargs(self) -> None:
        """Test database initialization with additional kwargs."""
        db = MockDatabase("postgresql://localhost/test", min_size=10, ssl=True)

        assert db._kwargs == {"min_size": 10, "ssl": True}

    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self) -> None:
        """Test that connect sets the connected flag."""
        db = MockDatabase("postgresql://localhost/test")

        await db.connect()

        assert db.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_clears_connected_flag(self) -> None:
        """Test that disconnect clears the connected flag."""
        db = MockDatabase("postgresql://localhost/test")
        await db.connect()

        await db.disconnect()

        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test health check when database is healthy."""
        db = MockDatabase("postgresql://localhost/test")
        db._connection.execute.return_value = "SELECT 1"
        await db.connect()

        result = await db.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        """Test health check when database is unhealthy."""
        db = MockDatabase("postgresql://localhost/test")
        await db.connect()
        db._connection.execute.side_effect = Exception("Connection failed")

        result = await db.health_check()

        assert result is False


class TestDatabaseFactory:
    """Test cases for DatabaseFactory."""

    def test_register_database(self) -> None:
        """Test registering a database implementation."""
        DatabaseFactory._registry = {}  # Reset registry

        DatabaseFactory.register("mock", MockDatabase)

        assert "mock" in DatabaseFactory._registry
        assert DatabaseFactory._registry["mock"] == MockDatabase

    def test_create_database(self) -> None:
        """Test creating a database instance."""
        DatabaseFactory._registry = {}  # Reset registry
        DatabaseFactory.register("mock", MockDatabase)

        db = DatabaseFactory.create("mock", "postgresql://localhost/test")

        assert isinstance(db, MockDatabase)
        assert db._dsn == "postgresql://localhost/test"

    def test_create_database_with_kwargs(self) -> None:
        """Test creating a database instance with kwargs."""
        DatabaseFactory._registry = {}  # Reset registry
        DatabaseFactory.register("mock", MockDatabase)

        db = DatabaseFactory.create("mock", "postgresql://localhost/test", min_size=5)

        assert db._kwargs == {"min_size": 5}

    def test_create_unknown_backend_raises_error(self) -> None:
        """Test that creating an unknown backend raises ValueError."""
        DatabaseFactory._registry = {}  # Reset registry

        with pytest.raises(ValueError, match="Unknown database backend: unknown"):
            DatabaseFactory.create("unknown", "postgresql://localhost/test")


class TestDatabaseConstants:
    """Test cases for database constants."""

    def test_default_pool_min_size(self) -> None:
        """Test default minimum pool size constant."""
        assert DEFAULT_POOL_MIN_SIZE == 5

    def test_default_pool_max_size(self) -> None:
        """Test default maximum pool size constant."""
        assert DEFAULT_POOL_MAX_SIZE == 20

    def test_default_command_timeout(self) -> None:
        """Test default command timeout constant."""
        assert DEFAULT_COMMAND_TIMEOUT == 60.0


class MockDatabaseConnectionAdvanced:
    """Advanced mock for testing connection protocols."""

    def __init__(self):
        self.execute = AsyncMock(return_value="INSERT 0 1")
        self.fetch = AsyncMock(return_value=[{"id": 1, "name": "test"}])
        self.fetchrow = AsyncMock(return_value={"id": 1, "name": "test"})
        self.fetchval = AsyncMock(return_value=42)
        self.execute_many = AsyncMock()


class TestDatabaseConnectionProtocol:
    """Test cases for DatabaseConnection protocol."""

    @pytest.mark.asyncio
    async def test_execute_interface(self) -> None:
        """Test execute method interface."""
        conn = MockDatabaseConnectionAdvanced()

        result = await conn.execute("INSERT INTO test VALUES ($1)", 1)

        conn.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", 1)
        assert result == "INSERT 0 1"

    @pytest.mark.asyncio
    async def test_fetch_interface(self) -> None:
        """Test fetch method interface."""
        conn = MockDatabaseConnectionAdvanced()

        result = await conn.fetch("SELECT * FROM test")

        conn.fetch.assert_called_once_with("SELECT * FROM test")
        assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    async def test_fetchrow_interface(self) -> None:
        """Test fetchrow method interface."""
        conn = MockDatabaseConnectionAdvanced()

        result = await conn.fetchrow("SELECT * FROM test WHERE id = $1", 1)

        conn.fetchrow.assert_called_once_with("SELECT * FROM test WHERE id = $1", 1)
        assert result == {"id": 1, "name": "test"}

    @pytest.mark.asyncio
    async def test_fetchrow_returns_none(self) -> None:
        """Test fetchrow returns None when no row found."""
        conn = MockDatabaseConnectionAdvanced()
        conn.fetchrow = AsyncMock(return_value=None)

        result = await conn.fetchrow("SELECT * FROM test WHERE id = $1", 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetchval_interface(self) -> None:
        """Test fetchval method interface."""
        conn = MockDatabaseConnectionAdvanced()

        result = await conn.fetchval("SELECT COUNT(*) FROM test")

        conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_many_interface(self) -> None:
        """Test execute_many method interface."""
        conn = MockDatabaseConnectionAdvanced()
        args = [(1,), (2,), (3,)]

        await conn.execute_many("INSERT INTO test VALUES ($1)", args)

        conn.execute_many.assert_called_once_with("INSERT INTO test VALUES ($1)", args)
