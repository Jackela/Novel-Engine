"""Unit tests for RedisStateStore.

Tests cover connection management, CRUD operations, and error handling
for the Redis-based state store implementation.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.infrastructure.state_store.config import StateKey, StateStoreConfig
from src.infrastructure.state_store.redis import RedisStateStore

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    redis = AsyncMock()
    redis.ping = AsyncMock()
    redis.get = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock()
    redis.keys = AsyncMock()
    redis.incrby = AsyncMock()
    redis.expire = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def state_store_config():
    """Create a state store configuration."""
    return StateStoreConfig(
        redis_url="redis://localhost:6379/0",
        cache_ttl=3600,
    )


@pytest.fixture
def redis_state_store(state_store_config, mock_redis):
    """Create a Redis state store with mocked Redis connection."""
    store = RedisStateStore(config=state_store_config)
    store.redis = mock_redis
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


class TestRedisStateStoreConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_initializes_redis_connection(
        self, state_store_config, mock_redis
    ):
        """connect initializes Redis connection."""
        with patch("src.infrastructure.state_store.redis.aioredis") as mock_aioredis:
            mock_aioredis.from_url = Mock(return_value=mock_redis)

            store = RedisStateStore(config=state_store_config)
            await store.connect()

            assert store._connected is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_skips_if_already_connected(
        self, redis_state_store, mock_redis
    ):
        """connect skips if already connected."""
        await redis_state_store.connect()

        mock_redis.ping.assert_not_called()  # Already connected

    @pytest.mark.asyncio
    async def test_connect_raises_on_connection_failure(
        self, state_store_config
    ):
        """connect raises exception on connection failure."""
        with patch("src.infrastructure.state_store.redis.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
            mock_aioredis.from_url = Mock(return_value=mock_redis)

            store = RedisStateStore(config=state_store_config)

            with pytest.raises(Exception, match="Connection refused"):
                await store.connect()


class TestRedisStateStoreGet:
    """Tests for get method."""

    @pytest.mark.asyncio
    async def test_get_returns_value_when_found(
        self, redis_state_store, mock_redis, sample_key
    ):
        """get returns value when key exists."""
        mock_redis.get.return_value = b'{"name": "Test Character"}'

        result = await redis_state_store.get(sample_key)

        assert result == {"name": "Test Character"}
        mock_redis.get.assert_called_once_with("test:character:char-001")

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(
        self, redis_state_store, mock_redis, sample_key
    ):
        """get returns None when key not found."""
        mock_redis.get.return_value = None

        result = await redis_state_store.get(sample_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_string_for_plain_text(
        self, redis_state_store, mock_redis, sample_key
    ):
        """get returns string for plain text values."""
        mock_redis.get.return_value = b"plain text value"

        result = await redis_state_store.get(sample_key)

        assert result == "plain text value"

    @pytest.mark.asyncio
    async def test_get_deserializes_pickle_when_json_fails(
        self, redis_state_store, mock_redis, sample_key
    ):
        """get deserializes pickle when JSON parsing fails."""
        import pickle

        pickled_data = pickle.dumps({"complex": "data"})
        mock_redis.get.return_value = pickled_data

        result = await redis_state_store.get(sample_key)

        assert result == {"complex": "data"}

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """get returns None on error."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await redis_state_store.get(sample_key)

        assert result is None


class TestRedisStateStoreSet:
    """Tests for set method."""

    @pytest.mark.asyncio
    async def test_set_stores_dict_as_json(
        self, redis_state_store, mock_redis, sample_key
    ):
        """set stores dictionary as JSON."""
        mock_redis.setex.return_value = True

        result = await redis_state_store.set(sample_key, {"name": "Test"})

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "test:character:char-001"
        assert b'"name": "Test"' in call_args[2]

    @pytest.mark.asyncio
    async def test_set_stores_string_directly(
        self, redis_state_store, mock_redis, sample_key
    ):
        """set stores string value directly."""
        mock_redis.setex.return_value = True

        result = await redis_state_store.set(sample_key, "test string")

        assert result is True
        call_args = mock_redis.setex.call_args[0]
        assert call_args[2] == "test string"

    @pytest.mark.asyncio
    async def test_set_uses_custom_ttl(
        self, redis_state_store, mock_redis, sample_key
    ):
        """set uses custom TTL when provided."""
        mock_redis.setex.return_value = True

        await redis_state_store.set(sample_key, {"data": "test"}, ttl=600)

        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == 600

    @pytest.mark.asyncio
    async def test_set_returns_false_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """set returns False on error."""
        mock_redis.setex.side_effect = Exception("Redis error")

        result = await redis_state_store.set(sample_key, {"data": "test"})

        assert result is False


class TestRedisStateStoreDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, redis_state_store, mock_redis, sample_key
    ):
        """delete returns True when key deleted."""
        mock_redis.delete.return_value = 1

        result = await redis_state_store.delete(sample_key)

        assert result is True
        mock_redis.delete.assert_called_once_with("test:character:char-001")

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, redis_state_store, mock_redis, sample_key
    ):
        """delete returns False when key not found."""
        mock_redis.delete.return_value = 0

        result = await redis_state_store.delete(sample_key)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """delete returns False on error."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await redis_state_store.delete(sample_key)

        assert result is False


class TestRedisStateStoreExists:
    """Tests for exists method."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_exists(
        self, redis_state_store, mock_redis, sample_key
    ):
        """exists returns True when key exists."""
        mock_redis.exists.return_value = 1

        result = await redis_state_store.exists(sample_key)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_not_found(
        self, redis_state_store, mock_redis, sample_key
    ):
        """exists returns False when key not found."""
        mock_redis.exists.return_value = 0

        result = await redis_state_store.exists(sample_key)

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """exists returns False on error."""
        mock_redis.exists.side_effect = Exception("Redis error")

        result = await redis_state_store.exists(sample_key)

        assert result is False


class TestRedisStateStoreListKeys:
    """Tests for list_keys method."""

    @pytest.mark.asyncio
    async def test_list_keys_returns_matching_keys(
        self, redis_state_store, mock_redis
    ):
        """list_keys returns keys matching pattern."""
        mock_redis.keys.return_value = [
            b"test:character:char-001",
            b"test:character:char-002",
        ]

        result = await redis_state_store.list_keys("test:character:*")

        assert len(result) == 2
        assert result[0].namespace == "test"
        assert result[0].entity_type == "character"

    @pytest.mark.asyncio
    async def test_list_keys_returns_empty_list_when_no_matches(
        self, redis_state_store, mock_redis
    ):
        """list_keys returns empty list when no matches."""
        mock_redis.keys.return_value = []

        result = await redis_state_store.list_keys("nonexistent:*")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_keys_returns_empty_list_on_error(
        self, redis_state_store, mock_redis
    ):
        """list_keys returns empty list on error."""
        mock_redis.keys.side_effect = Exception("Redis error")

        result = await redis_state_store.list_keys("test:*")

        assert result == []


class TestRedisStateStoreIncrement:
    """Tests for increment method."""

    @pytest.mark.asyncio
    async def test_increment_returns_new_value(
        self, redis_state_store, mock_redis, sample_key
    ):
        """increment returns new counter value."""
        mock_redis.incrby.return_value = 5

        result = await redis_state_store.increment(sample_key, amount=5)

        assert result == 5
        mock_redis.incrby.assert_called_once_with("test:character:char-001", 5)

    @pytest.mark.asyncio
    async def test_increment_uses_default_amount(
        self, redis_state_store, mock_redis, sample_key
    ):
        """increment uses default amount of 1."""
        mock_redis.incrby.return_value = 1

        await redis_state_store.increment(sample_key)

        mock_redis.incrby.assert_called_once_with("test:character:char-001", 1)

    @pytest.mark.asyncio
    async def test_increment_returns_none_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """increment returns None on error."""
        mock_redis.incrby.side_effect = Exception("Redis error")

        result = await redis_state_store.increment(sample_key)

        assert result is None


class TestRedisStateStoreExpire:
    """Tests for expire method."""

    @pytest.mark.asyncio
    async def test_expire_returns_true_when_set(
        self, redis_state_store, mock_redis, sample_key
    ):
        """expire returns True when TTL set."""
        mock_redis.expire.return_value = True

        result = await redis_state_store.expire(sample_key, ttl=600)

        assert result is True
        mock_redis.expire.assert_called_once_with("test:character:char-001", 600)

    @pytest.mark.asyncio
    async def test_expire_returns_false_when_key_not_found(
        self, redis_state_store, mock_redis, sample_key
    ):
        """expire returns False when key not found."""
        mock_redis.expire.return_value = False

        result = await redis_state_store.expire(sample_key, ttl=600)

        assert result is False

    @pytest.mark.asyncio
    async def test_expire_returns_false_on_error(
        self, redis_state_store, mock_redis, sample_key
    ):
        """expire returns False on error."""
        mock_redis.expire.side_effect = Exception("Redis error")

        result = await redis_state_store.expire(sample_key, ttl=600)

        assert result is False


class TestRedisStateStoreHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_healthy(
        self, redis_state_store, mock_redis
    ):
        """health_check returns True when Redis is healthy."""
        mock_redis.ping.return_value = True

        result = await redis_state_store.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unhealthy(
        self, redis_state_store, mock_redis
    ):
        """health_check returns False when Redis is unhealthy."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        result = await redis_state_store.health_check()

        assert result is False


class TestRedisStateStoreClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_connection(
        self, redis_state_store, mock_redis
    ):
        """close closes Redis connection."""
        await redis_state_store.close()

        mock_redis.close.assert_called_once()
        assert redis_state_store._connected is False
