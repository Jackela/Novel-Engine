"""Unit tests for PostgreSQLStateStore.

Tests cover connection management, CRUD operations, and error handling
for the PostgreSQL-based state store implementation.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.infrastructure.state_store.config import StateKey, StateStoreConfig
from src.infrastructure.state_store.postgres import PostgreSQLStateStore

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    pool = AsyncMock()
    return pool


@pytest.fixture
def mock_connection():
    """Create a mock asyncpg connection."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def state_store_config():
    """Create a state store configuration."""
    return StateStoreConfig(
        postgres_url="postgresql://user:pass@localhost/testdb",
        connection_timeout=30,
    )


@pytest.fixture
def postgres_state_store(state_store_config, mock_pool):
    """Create a PostgreSQL state store with mocked pool."""
    store = PostgreSQLStateStore(config=state_store_config)
    store.pool = mock_pool
    store._connected = True
    return store


@pytest.fixture
def sample_key():
    """Create a sample state key."""
    return StateKey(
        namespace="test",
        entity_type="character",
        entity_id="char-001",
    )


class TestPostgresStateStoreConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_initializes_pool(
        self, state_store_config, mock_pool
    ):
        """connect initializes PostgreSQL connection pool."""
        with patch("src.infrastructure.state_store.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            store = PostgreSQLStateStore(config=state_store_config)
            await store.connect()

            assert store._connected is True
            mock_asyncpg.create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_skips_if_already_connected(
        self, postgres_state_store, mock_pool
    ):
        """connect skips if already connected."""
        await postgres_state_store.connect()

        mock_pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_raises_on_connection_failure(
        self, state_store_config
    ):
        """connect raises exception on connection failure."""
        with patch("src.infrastructure.state_store.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.create_pool = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            store = PostgreSQLStateStore(config=state_store_config)

            with pytest.raises(Exception, match="Connection refused"):
                await store.connect()


class TestPostgresStateStoreInitializeTables:
    """Tests for _initialize_tables method."""

    @pytest.mark.asyncio
    async def test_initialize_tables_creates_required_tables(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """_initialize_tables creates required database tables."""
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await postgres_state_store._initialize_tables()

        mock_connection.execute.assert_called_once()
        # Verify CREATE TABLE statement is in the call
        call_args = mock_connection.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS state_data" in call_args


class TestPostgresStateStoreGet:
    """Tests for get method."""

    @pytest.mark.asyncio
    async def test_get_returns_value_when_found(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """get returns value when key exists."""
        mock_connection.fetchrow.return_value = {"data": {"name": "Test Character"}}
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.get(sample_key)

        assert result == {"name": "Test Character"}

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """get returns None when key not found."""
        mock_connection.fetchrow.return_value = None
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.get(sample_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """get returns None on error."""
        mock_connection.fetchrow.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.get(sample_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_skips_expired_entries(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """get skips entries that have expired."""
        mock_connection.fetchrow.return_value = {"data": {"name": "Test"}}
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await postgres_state_store.get(sample_key)

        call_args = mock_connection.fetchrow.call_args
        # Check that query includes expires_at check
        assert "expires_at" in str(call_args)


class TestPostgresStateStoreSet:
    """Tests for set method."""

    @pytest.mark.asyncio
    async def test_set_inserts_new_record(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """set inserts new record into database."""
        mock_connection.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.set(sample_key, {"name": "Test"})

        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_updates_existing_record(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """set updates existing record with ON CONFLICT."""
        mock_connection.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await postgres_state_store.set(sample_key, {"name": "Updated"})

        call_args = mock_connection.execute.call_args[0][0]
        assert "ON CONFLICT" in call_args

    @pytest.mark.asyncio
    async def test_set_sets_expiration_when_ttl_provided(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """set sets expiration when TTL provided."""
        mock_connection.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await postgres_state_store.set(sample_key, {"name": "Test"}, ttl=3600)

        call_args = mock_connection.execute.call_args
        # Verify expires_at is in the values
        assert call_args[0][7] is not None  # expires_at parameter

    @pytest.mark.asyncio
    async def test_set_returns_false_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """set returns False on error."""
        mock_connection.execute.side_effect = Exception("Insert failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.set(sample_key, {"name": "Test"})

        assert result is False


class TestPostgresStateStoreDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """delete returns True when record deleted."""
        mock_connection.execute.return_value = "DELETE 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.delete(sample_key)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """delete returns False when record not found."""
        mock_connection.execute.return_value = "DELETE 0"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.delete(sample_key)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """delete returns False on error."""
        mock_connection.execute.side_effect = Exception("Delete failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.delete(sample_key)

        assert result is False


class TestPostgresStateStoreExists:
    """Tests for exists method."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_exists(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """exists returns True when key exists."""
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.exists(sample_key)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_not_found(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """exists returns False when key not found."""
        mock_connection.fetchval.return_value = None
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.exists(sample_key)

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """exists returns False on error."""
        mock_connection.fetchval.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.exists(sample_key)

        assert result is False


class TestPostgresStateStoreListKeys:
    """Tests for list_keys method."""

    @pytest.mark.asyncio
    async def test_list_keys_returns_matching_keys(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """list_keys returns keys matching pattern."""
        mock_connection.fetch.return_value = [
            {"key_hash": "test:character:char-001"},
            {"key_hash": "test:character:char-002"},
        ]
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.list_keys("test:character:*")

        assert len(result) == 2
        assert result[0].namespace == "test"

    @pytest.mark.asyncio
    async def test_list_keys_converts_redis_pattern_to_sql(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """list_keys converts Redis * pattern to SQL % pattern."""
        mock_connection.fetch.return_value = []
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await postgres_state_store.list_keys("test:*")

        call_args = mock_connection.fetch.call_args
        # Verify % pattern is used instead of *
        assert "%" in str(call_args)

    @pytest.mark.asyncio
    async def test_list_keys_returns_empty_list_on_error(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """list_keys returns empty list on error."""
        mock_connection.fetch.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.list_keys("test:*")

        assert result == []


class TestPostgresStateStoreIncrement:
    """Tests for increment method."""

    @pytest.mark.asyncio
    async def test_increment_returns_new_value(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """increment returns new counter value."""
        mock_connection.fetchrow.return_value = {"data": "5"}
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.increment(sample_key, amount=5)

        assert result == 5

    @pytest.mark.asyncio
    async def test_increment_returns_none_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """increment returns None on error."""
        mock_connection.fetchrow.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.increment(sample_key)

        assert result is None


class TestPostgresStateStoreExpire:
    """Tests for expire method."""

    @pytest.mark.asyncio
    async def test_expire_returns_true_when_set(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """expire returns True when TTL updated."""
        mock_connection.execute.return_value = "UPDATE 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.expire(sample_key, ttl=600)

        assert result is True

    @pytest.mark.asyncio
    async def test_expire_returns_false_when_key_not_found(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """expire returns False when key not found."""
        mock_connection.execute.return_value = "UPDATE 0"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.expire(sample_key, ttl=600)

        assert result is False

    @pytest.mark.asyncio
    async def test_expire_returns_false_on_error(
        self, postgres_state_store, mock_pool, mock_connection, sample_key
    ):
        """expire returns False on error."""
        mock_connection.execute.side_effect = Exception("Update failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.expire(sample_key, ttl=600)

        assert result is False


class TestPostgresStateStoreHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_healthy(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """health_check returns True when PostgreSQL is healthy."""
        mock_connection.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unhealthy(
        self, postgres_state_store, mock_pool, mock_connection
    ):
        """health_check returns False when PostgreSQL is unhealthy."""
        mock_connection.fetchval.side_effect = Exception("Connection failed")
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await postgres_state_store.health_check()

        assert result is False


class TestPostgresStateStoreClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_pool(
        self, postgres_state_store, mock_pool
    ):
        """close closes PostgreSQL connection pool."""
        await postgres_state_store.close()

        mock_pool.close.assert_called_once()
        assert postgres_state_store._connected is False

    @pytest.mark.asyncio
    async def test_close_handles_none_pool(self, postgres_state_store):
        """close handles case when pool is None."""
        postgres_state_store.pool = None

        await postgres_state_store.close()

        assert postgres_state_store._connected is False
