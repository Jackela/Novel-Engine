"""
Tests for Database Manager Module

Coverage targets:
- Connection pooling
- Transaction management (commit, rollback)
- Connection failures and retries
- Query execution
- Context manager usage
"""

import asyncio
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.unit

from src.core.database_manager import (
    ConnectionState,
    DatabaseConfig,
    DatabaseConnection,
    DatabaseConnectionPool,
    DatabaseManager,
    DatabaseType,
    get_database_connection,
    get_database_manager,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DatabaseConfig()
        assert config.database_type == DatabaseType.SQLITE
        assert config.connection_string == "data/novel_engine.db"
        assert config.min_pool_size == 2
        assert config.max_pool_size == 20
        assert config.connection_timeout == 30.0
        assert config.idle_timeout == 300.0
        assert config.health_check_interval == 60.0
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.enable_wal_mode is True
        assert config.enable_foreign_keys is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DatabaseConfig(
            database_type=DatabaseType.POSTGRESQL,
            connection_string="postgresql://localhost/test",
            min_pool_size=5,
            max_pool_size=50,
            connection_timeout=60.0,
        )
        assert config.database_type == DatabaseType.POSTGRESQL
        assert config.connection_string == "postgresql://localhost/test"
        assert config.min_pool_size == 5
        assert config.max_pool_size == 50
        assert config.connection_timeout == 60.0


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_connection_states(self):
        """Test all connection states are defined."""
        assert ConnectionState.IDLE.value == "idle"
        assert ConnectionState.ACTIVE.value == "active"
        assert ConnectionState.UNHEALTHY.value == "unhealthy"
        assert ConnectionState.CLOSED.value == "closed"


@pytest.mark.asyncio
class TestDatabaseConnection:
    """Tests for DatabaseConnection class."""

    @pytest_asyncio.fixture
    async def mock_connection(self):
        """Create a mock aiosqlite connection."""
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=AsyncMock())
        conn.commit = AsyncMock()
        conn.rollback = AsyncMock()
        conn.close = AsyncMock()
        return conn

    @pytest_asyncio.fixture
    async def db_config(self):
        """Create a test database config."""
        return DatabaseConfig(
            database_type=DatabaseType.SQLITE,
            connection_string=":memory:",
            enable_wal_mode=True,
            enable_foreign_keys=True,
        )

    @pytest_asyncio.fixture
    async def db_connection(self, mock_connection, db_config):
        """Create a DatabaseConnection instance."""
        connection = DatabaseConnection(mock_connection, db_config)
        return connection

    async def test_initialization(self, mock_connection, db_config):
        """Test connection initialization."""
        connection = DatabaseConnection(mock_connection, db_config)
        assert connection.connection == mock_connection
        assert connection.config == db_config
        assert connection.state == ConnectionState.IDLE
        assert connection.metrics.total_queries == 0
        assert connection.metrics.successful_queries == 0
        assert connection.metrics.failed_queries == 0

    async def test_initialize_sqlite(self, mock_connection, db_config):
        """Test SQLite-specific initialization."""
        connection = DatabaseConnection(mock_connection, db_config)
        
        # Stop the health check task that gets created during initialization
        with patch.object(connection, '_health_check_task'):
            await connection.initialize()
            
            # Check that PRAGMA commands were executed
            assert mock_connection.execute.call_count >= 5  # Multiple PRAGMA settings
            mock_connection.commit.assert_called_once()

    async def test_execute_success(self, db_connection, mock_connection):
        """Test successful query execution."""
        # Mock cursor
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))
        mock_connection.execute = AsyncMock(return_value=mock_cursor)
        
        cursor = await db_connection.execute("SELECT 1", ())
        
        assert cursor == mock_cursor
        assert db_connection.metrics.total_queries == 1
        assert db_connection.metrics.successful_queries == 1
        assert db_connection.state == ConnectionState.IDLE

    async def test_execute_failure(self, db_connection, mock_connection):
        """Test query execution failure."""
        mock_connection.execute = AsyncMock(side_effect=Exception("Query failed"))
        
        with pytest.raises(Exception, match="Query failed"):
            await db_connection.execute("SELECT 1", ())
        
        assert db_connection.metrics.total_queries == 1
        assert db_connection.metrics.failed_queries == 1
        assert db_connection.metrics.last_error == "Query failed"

    async def test_execute_many_success(self, db_connection, mock_connection):
        """Test successful batch query execution."""
        mock_cursor = AsyncMock()
        mock_connection.executemany = AsyncMock(return_value=mock_cursor)
        
        params = [("value1",), ("value2",), ("value3",)]
        cursor = await db_connection.executemany("INSERT INTO test VALUES (?)", params)
        
        assert cursor == mock_cursor
        assert db_connection.metrics.total_queries == 3
        assert db_connection.metrics.successful_queries == 3

    async def test_commit(self, db_connection, mock_connection):
        """Test transaction commit."""
        await db_connection.commit()
        mock_connection.commit.assert_called_once()

    async def test_rollback(self, db_connection, mock_connection):
        """Test transaction rollback."""
        await db_connection.rollback()
        mock_connection.rollback.assert_called_once()

    async def test_close(self, db_connection, mock_connection):
        """Test connection close."""
        # Create a real asyncio task that completes quickly for testing
        import asyncio
        
        async def dummy_task():
            await asyncio.sleep(0)
        
        # Create and immediately cancel a real task to simulate the scenario
        task = asyncio.create_task(dummy_task())
        task.cancel()
        db_connection._health_check_task = task
        
        await db_connection.close()
        
        assert db_connection.state == ConnectionState.CLOSED
        mock_connection.close.assert_called_once()

    async def test_health_check_success(self, db_connection, mock_connection):
        """Test successful health check."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))
        mock_connection.execute = AsyncMock(return_value=mock_cursor)
        
        result = await db_connection.health_check()
        
        assert result is True
        assert db_connection.metrics.health_status is True
        assert db_connection.metrics.last_health_check is not None

    async def test_health_check_failure(self, db_connection, mock_connection):
        """Test failed health check."""
        mock_connection.execute = AsyncMock(side_effect=Exception("Connection lost"))
        
        result = await db_connection.health_check()
        
        assert result is False
        assert db_connection.metrics.health_status is False
        assert db_connection.state == ConnectionState.UNHEALTHY

    async def test_is_healthy_property(self, db_connection):
        """Test is_healthy property."""
        db_connection.state = ConnectionState.IDLE
        db_connection.metrics.health_status = True
        assert db_connection.is_healthy is True
        
        db_connection.state = ConnectionState.UNHEALTHY
        assert db_connection.is_healthy is False
        
        db_connection.state = ConnectionState.CLOSED
        assert db_connection.is_healthy is False

    async def test_is_idle_property(self, db_connection):
        """Test is_idle property."""
        db_connection.state = ConnectionState.IDLE
        assert db_connection.is_idle is True
        
        db_connection.state = ConnectionState.ACTIVE
        assert db_connection.is_idle is False

    async def test_get_metrics(self, db_connection):
        """Test get_metrics method."""
        db_connection.state = ConnectionState.IDLE
        db_connection.metrics.total_queries = 10
        db_connection.metrics.successful_queries = 8
        db_connection.metrics.failed_queries = 2
        
        metrics = db_connection.get_metrics()
        
        assert metrics["state"] == "idle"
        assert metrics["total_queries"] == 10
        assert metrics["successful_queries"] == 8
        assert metrics["failed_queries"] == 2
        assert metrics["success_rate"] == 0.8


@pytest.mark.asyncio
class TestDatabaseConnectionPool:
    """Tests for DatabaseConnectionPool class."""

    @pytest.fixture
    def db_config(self):
        """Create a test database config."""
        return DatabaseConfig(
            database_type=DatabaseType.SQLITE,
            connection_string=":memory:",
            min_pool_size=2,
            max_pool_size=5,
            connection_timeout=5.0,
        )

    @pytest_asyncio.fixture
    async def pool(self, db_config):
        """Create a DatabaseConnectionPool instance."""
        pool = DatabaseConnectionPool(db_config)
        return pool

    async def test_pool_initialization(self, db_config):
        """Test pool initialization."""
        pool = DatabaseConnectionPool(db_config)
        assert pool.config == db_config
        assert len(pool._available_connections) == 0
        assert len(pool._active_connections) == 0
        assert pool._initialized is False

    async def test_initialize_pool(self, db_config):
        """Test pool initialization creates min connections."""
        pool = DatabaseConnectionPool(db_config)
        
        # Skip actual connection creation by mocking _create_connection
        mock_conn = AsyncMock()
        mock_conn.initialize = AsyncMock()
        mock_conn._health_check_task = AsyncMock()
        mock_conn._health_check_task.done = Mock(return_value=True)
        
        with patch.object(pool, '_create_connection', return_value=mock_conn):
            await pool.initialize()
            
            assert pool._initialized is True
            assert pool._pool_metrics["total_connections_created"] == db_config.min_pool_size

    async def test_get_pool_status(self, pool):
        """Test get_pool_status method."""
        pool._initialized = True
        pool._closed = False
        
        # Add some mock connections
        mock_conn1 = Mock()
        mock_conn1.is_healthy = True
        mock_conn2 = Mock()
        mock_conn2.is_healthy = True
        
        pool._available_connections = [mock_conn1]
        pool._active_connections = {id(mock_conn2): mock_conn2}
        
        status = pool.get_pool_status()
        
        assert status["total_connections"] == 2
        assert status["available_connections"] == 1
        assert status["active_connections"] == 1
        assert status["min_pool_size"] == pool.config.min_pool_size
        assert status["max_pool_size"] == pool.config.max_pool_size
        assert status["initialized"] is True

    async def test_get_pool_metrics(self, pool):
        """Test get_pool_metrics method."""
        pool._pool_metrics["total_connections_created"] = 10
        pool._pool_metrics["total_connections_closed"] = 3
        pool._pool_metrics["peak_active_connections"] = 5
        
        metrics = pool.get_pool_metrics()
        
        assert metrics["total_connections_created"] == 10
        assert metrics["total_connections_closed"] == 3
        assert metrics["peak_active_connections"] == 5

    async def test_close_pool(self, pool):
        """Test pool shutdown."""
        # Create mock connections
        mock_conn1 = AsyncMock()
        mock_conn1.close = AsyncMock()
        mock_conn2 = AsyncMock()
        mock_conn2.close = AsyncMock()
        
        pool._available_connections = [mock_conn1]
        pool._active_connections = {id(mock_conn2): mock_conn2}
        
        # Mock maintenance task
        pool._maintenance_task = AsyncMock()
        pool._maintenance_task.done = Mock(return_value=True)
        
        await pool.close_pool()
        
        assert pool._closed is True
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()


@pytest.mark.asyncio
class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest_asyncio.fixture
    async def db_manager(self):
        """Create a DatabaseManager instance."""
        manager = DatabaseManager()
        return manager

    async def test_initialization(self, db_manager):
        """Test database manager initialization."""
        assert db_manager._initialized is False
        assert len(db_manager._pools) == 0
        assert db_manager._default_pool_name == "default"

    async def test_add_pool(self, db_manager):
        """Test adding a named pool."""
        config = DatabaseConfig(
            database_type=DatabaseType.SQLITE,
            connection_string=":memory:",
            min_pool_size=1,
            max_pool_size=3,
        )
        
        # Mock the pool initialization
        with patch.object(DatabaseConnectionPool, 'initialize', AsyncMock()):
            await db_manager.add_pool("test_pool", config)
            
            assert "test_pool" in db_manager._pools
            assert db_manager._pools["test_pool"].config == config

    async def test_add_duplicate_pool(self, db_manager):
        """Test adding duplicate pool raises error."""
        config = DatabaseConfig()
        
        with patch.object(DatabaseConnectionPool, 'initialize', AsyncMock()):
            await db_manager.add_pool("test_pool", config)
            
            with pytest.raises(ValueError, match="Pool test_pool already exists"):
                await db_manager.add_pool("test_pool", config)

    async def test_get_pool_status_all(self, db_manager):
        """Test getting status for all pools."""
        mock_pool = Mock()
        mock_pool.get_pool_status = Mock(return_value={"test": "status"})
        db_manager._pools["pool1"] = mock_pool
        db_manager._pools["pool2"] = mock_pool
        
        status = db_manager.get_pool_status()
        
        assert "pool1" in status
        assert "pool2" in status
        assert status["pool1"]["test"] == "status"

    async def test_get_pool_status_single(self, db_manager):
        """Test getting status for single pool."""
        mock_pool = Mock()
        mock_pool.get_pool_status = Mock(return_value={"test": "status"})
        db_manager._pools["test_pool"] = mock_pool
        
        status = db_manager.get_pool_status("test_pool")
        
        assert "test_pool" in status
        assert status["test_pool"]["test"] == "status"

    async def test_get_pool_status_not_found(self, db_manager):
        """Test getting status for non-existent pool raises error."""
        with pytest.raises(ValueError, match="Pool 'nonexistent' not found"):
            db_manager.get_pool_status("nonexistent")

    async def test_close_all_pools(self, db_manager):
        """Test closing all pools."""
        mock_pool = AsyncMock()
        mock_pool.close_pool = AsyncMock()
        db_manager._pools["pool1"] = mock_pool
        db_manager._pools["pool2"] = mock_pool
        db_manager._initialized = True
        
        await db_manager.close_all_pools()
        
        assert len(db_manager._pools) == 0
        assert db_manager._initialized is False
        assert mock_pool.close_pool.call_count == 2


class TestGlobalInstances:
    """Tests for global instances and convenience functions."""

    def test_get_database_manager_singleton(self):
        """Test that get_database_manager returns singleton."""
        # Clear any existing instance
        import src.core.database_manager as db_module
        original = db_module._global_database_manager
        db_module._global_database_manager = None
        
        try:
            manager1 = get_database_manager()
            manager2 = get_database_manager()
            assert manager1 is manager2
        finally:
            db_module._global_database_manager = original


class TestDatabaseType:
    """Tests for DatabaseType enum."""

    def test_database_types(self):
        """Test all database types are defined."""
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.MYSQL.value == "mysql"
        assert DatabaseType.REDIS.value == "redis"
