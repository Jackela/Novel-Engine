"""Unit tests for RedisManager and RedisConnectionPool.

Tests cover connection management, caching operations, session management,
and error handling for the Redis manager.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.infrastructure.redis_manager import (
    CacheKey,
    RedisConfig,
    RedisConnectionPool,
    RedisManager,
    RedisStorageStrategy,
    create_redis_config_from_env,
    create_redis_manager,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def redis_config():
    """Create a Redis configuration."""
    return RedisConfig(
        host="localhost",
        port=6379,
        database=0,
        default_ttl=3600,
    )


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection."""
    redis = AsyncMock()
    redis.ping = AsyncMock()
    redis.config_set = AsyncMock()
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock()
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.hset = AsyncMock(return_value=1)
    redis.hget = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.lpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.ltrim = AsyncMock()
    redis.sadd = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())
    redis.incrby = AsyncMock(return_value=1)
    redis.close = AsyncMock()
    redis.pipeline = Mock(return_value=AsyncMock())
    return redis


@pytest.fixture
def connection_pool(redis_config, mock_redis):
    """Create a connection pool with mocked Redis."""
    pool = RedisConnectionPool(config=redis_config)
    pool.redis = mock_redis
    pool._initialized = True
    return pool


@pytest.fixture
def redis_manager(redis_config, mock_redis):
    """Create a Redis manager with mocked connection pool."""
    manager = RedisManager(config=redis_config)
    manager.connection_pool.redis = mock_redis
    manager.connection_pool._initialized = True
    manager._initialized = True
    return manager


class TestRedisConfig:
    """Tests for RedisConfig dataclass."""

    def test_default_values(self):
        """RedisConfig has correct default values."""
        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.database == 0
        assert config.default_ttl == 3600
        assert config.min_pool_size == 5
        assert config.max_pool_size == 100

    def test_get_connection_string_without_password(self):
        """get_connection_string returns correct URL without password."""
        config = RedisConfig(host="redis.example.com", port=6380, database=1)

        result = config.get_connection_string()

        assert result == "redis://redis.example.com:6380/1"

    def test_get_connection_string_with_password(self):
        """get_connection_string returns correct URL with password."""
        config = RedisConfig(
            host="redis.example.com", port=6379, password="secret", database=0
        )

        result = config.get_connection_string()

        assert result == "redis://:secret@redis.example.com:6379/0"


class TestCacheKey:
    """Tests for CacheKey dataclass."""

    def test_build_basic_key(self):
        """build creates correct key with basic fields."""
        key = CacheKey(
            namespace="novel_engine", entity_type="character", entity_id="char-001"
        )

        result = key.build()

        assert result == "novel_engine:character:char-001"

    def test_build_with_operation(self):
        """build includes operation when provided."""
        key = CacheKey(
            namespace="novel_engine",
            entity_type="character",
            entity_id="char-001",
            operation="stats",
        )

        result = key.build()

        assert result == "novel_engine:character:char-001:stats"

    def test_build_with_version(self):
        """build includes version when provided."""
        key = CacheKey(
            namespace="novel_engine",
            entity_type="character",
            entity_id="char-001",
            version="v2",
        )

        result = key.build()

        assert result == "novel_engine:character:char-001:vv2"

    def test_build_full_key(self):
        """build creates full key with all fields."""
        key = CacheKey(
            namespace="novel_engine",
            entity_type="session",
            entity_id="sess-001",
            operation="data",
            version="v1",
        )

        result = key.build()

        assert result == "novel_engine:session:sess-001:data:vv1"


class TestRedisConnectionPoolInitialize:
    """Tests for RedisConnectionPool initialization."""

    @pytest.mark.asyncio
    async def test_initialize_sets_up_connection(self, redis_config, mock_redis):
        """initialize sets up Redis connection."""
        with patch("src.infrastructure.redis_manager.aioredis") as mock_aioredis:
            mock_aioredis.ConnectionPool = Mock()
            mock_aioredis.Redis = Mock(return_value=mock_redis)

            pool = RedisConnectionPool(config=redis_config)
            await pool.initialize()

            assert pool._initialized is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_skips_if_already_initialized(self, connection_pool):
        """initialize skips if already initialized."""
        await connection_pool.initialize()

        # Should not call ping again since already initialized
        connection_pool.redis.ping.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_raises_on_connection_failure(self, redis_config):
        """initialize raises exception on connection failure."""
        with patch("src.infrastructure.redis_manager.aioredis") as mock_aioredis:
            mock_aioredis.ConnectionPool = Mock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
            mock_aioredis.Redis = Mock(return_value=mock_redis)

            pool = RedisConnectionPool(config=redis_config)

            with pytest.raises(Exception, match="Connection refused"):
                await pool.initialize()


class TestRedisConnectionPoolBasicOperations:
    """Tests for basic Redis operations."""

    @pytest.mark.asyncio
    async def test_set_stores_value(self, connection_pool, mock_redis):
        """set stores value in Redis."""
        result = await connection_pool.set("test-key", {"data": "value"})

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_raises_when_not_initialized(self, redis_config):
        """set raises when pool not initialized."""
        pool = RedisConnectionPool(config=redis_config)

        with pytest.raises(AssertionError):
            await pool.set("key", "value")

    @pytest.mark.asyncio
    async def test_get_retrieves_value(self, connection_pool, mock_redis):
        """get retrieves value from Redis."""
        mock_redis.get.return_value = b'{"data": "value"}'

        result = await connection_pool.get("test-key")

        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, connection_pool, mock_redis):
        """get returns None for missing key."""
        mock_redis.get.return_value = None

        result = await connection_pool.get("missing-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, connection_pool, mock_redis):
        """delete removes key from Redis."""
        result = await connection_pool.delete("test-key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_exists_checks_key_presence(self, connection_pool, mock_redis):
        """exists checks if key exists in Redis."""
        mock_redis.exists.return_value = 1

        result = await connection_pool.exists("test-key")

        assert result is True

    @pytest.mark.asyncio
    async def test_expire_sets_ttl(self, connection_pool, mock_redis):
        """expire sets TTL for key."""
        result = await connection_pool.expire("test-key", 600)

        assert result is True
        mock_redis.expire.assert_called_once_with("test-key", 600)


class TestRedisConnectionPoolHashOperations:
    """Tests for hash operations."""

    @pytest.mark.asyncio
    async def test_hset_stores_hash_field(self, connection_pool, mock_redis):
        """hset stores hash field."""
        result = await connection_pool.hset("hash-key", "field1", "value1")

        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_hset_with_ttl_sets_expiration(self, connection_pool, mock_redis):
        """hset with TTL sets expiration."""
        await connection_pool.hset("hash-key", "field1", "value1", ttl=600)

        mock_redis.expire.assert_called_once_with("hash-key", 600)

    @pytest.mark.asyncio
    async def test_hget_retrieves_hash_field(self, connection_pool, mock_redis):
        """hget retrieves hash field."""
        mock_redis.hget.return_value = b'"value1"'

        result = await connection_pool.hget("hash-key", "field1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_hgetall_retrieves_all_fields(self, connection_pool, mock_redis):
        """hgetall retrieves all hash fields."""
        mock_redis.hgetall.return_value = {
            b"field1": b'"value1"',
            b"field2": b'"value2"',
        }

        result = await connection_pool.hgetall("hash-key")

        assert result == {"field1": "value1", "field2": "value2"}


class TestRedisConnectionPoolListOperations:
    """Tests for list operations."""

    @pytest.mark.asyncio
    async def test_lpush_adds_to_list(self, connection_pool, mock_redis):
        """lpush adds values to list."""
        result = await connection_pool.lpush("list-key", "value1", "value2")

        assert result == 1
        mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_lrange_retrieves_list_range(self, connection_pool, mock_redis):
        """lrange retrieves list range."""
        mock_redis.lrange.return_value = [b'"item1"', b'"item2"']

        result = await connection_pool.lrange("list-key", 0, -1)

        assert result == ["item1", "item2"]


class TestRedisConnectionPoolSetOperations:
    """Tests for set operations."""

    @pytest.mark.asyncio
    async def test_sadd_adds_to_set(self, connection_pool, mock_redis):
        """sadd adds values to set."""
        result = await connection_pool.sadd("set-key", "member1", "member2")

        assert result == 1
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_smembers_retrieves_set_members(self, connection_pool, mock_redis):
        """smembers retrieves set members."""
        mock_redis.smembers.return_value = {b'"member1"', b'"member2"'}

        result = await connection_pool.smembers("set-key")

        assert result == {"member1", "member2"}


class TestRedisConnectionPoolNovelEngineOperations:
    """Tests for Novel Engine specific operations."""

    @pytest.mark.asyncio
    async def test_cache_character_stores_character_data(
        self, connection_pool, mock_redis
    ):
        """cache_character stores character data."""
        character_data = {"name": "Hero", "level": 10}

        result = await connection_pool.cache_character("char-001", character_data)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert "novel_engine:character:char-001" in call_args

    @pytest.mark.asyncio
    async def test_get_cached_character_retrieves_data(
        self, connection_pool, mock_redis
    ):
        """get_cached_character retrieves character data."""
        mock_redis.get.return_value = b'{"name": "Hero"}'

        result = await connection_pool.get_cached_character("char-001")

        assert result == {"name": "Hero"}

    @pytest.mark.asyncio
    async def test_store_session_uses_hash(self, connection_pool, mock_redis):
        """store_session stores session as hash."""
        session_data = {"user_id": "user-001", "status": "active"}
        mock_pipeline = AsyncMock()
        mock_redis.pipeline.return_value = mock_pipeline

        result = await connection_pool.store_session("sess-001", session_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_session_retrieves_hash(self, connection_pool, mock_redis):
        """get_session retrieves session hash."""
        mock_redis.hgetall.return_value = {"user_id": "user-001"}

        result = await connection_pool.get_session("sess-001")

        assert result == {"user_id": "user-001"}

    @pytest.mark.asyncio
    async def test_add_to_narrative_stream_pushes_and_trims(
        self, connection_pool, mock_redis
    ):
        """add_to_narrative_stream pushes event and trims list."""
        event_data = {"type": "dialogue", "text": "Hello"}

        result = await connection_pool.add_to_narrative_stream("narr-001", event_data)

        assert result is True
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once_with(
            "novel_engine:narrative_stream:narr-001", 0, 999
        )


class TestRedisConnectionPoolSerialization:
    """Tests for serialization strategies."""

    def test_serialize_value_json(self, connection_pool):
        """_serialize_value serializes dict to JSON."""
        result = connection_pool._serialize_value({"key": "value"})

        assert result == '{"key": "value"}'

    def test_serialize_value_pickle(self, connection_pool):
        """_serialize_value serializes to pickle when requested."""
        import pickle

        result = connection_pool._serialize_value(
            {"key": "value"}, strategy=RedisStorageStrategy.PICKLE
        )

        # Result should be hex-encoded pickle
        decoded = pickle.loads(bytes.fromhex(result))
        assert decoded == {"key": "value"}

    def test_serialize_value_plain(self, connection_pool):
        """_serialize_value converts to string for plain strategy."""
        result = connection_pool._serialize_value(
            123, strategy=RedisStorageStrategy.PLAIN
        )

        assert result == "123"

    def test_deserialize_value_json(self, connection_pool):
        """_deserialize_value parses JSON."""
        result = connection_pool._deserialize_value('{"key": "value"}')

        assert result == {"key": "value"}

    def test_deserialize_value_pickle(self, connection_pool):
        """_deserialize_value parses pickle."""
        import pickle

        pickled = pickle.dumps({"key": "value"}).hex()

        result = connection_pool._deserialize_value(
            pickled, strategy=RedisStorageStrategy.PICKLE
        )

        assert result == {"key": "value"}

    def test_deserialize_value_returns_original_on_error(self, connection_pool):
        """_deserialize_value returns original on parse error."""
        result = connection_pool._deserialize_value("invalid json")

        assert result == "invalid json"


class TestRedisConnectionPoolMetrics:
    """Tests for metrics tracking."""

    def test_get_metrics_returns_metrics_dict(self, connection_pool):
        """get_metrics returns metrics dictionary."""
        # Simulate some operations
        connection_pool._metrics["total_commands"] = 10
        connection_pool._metrics["cache_hits"] = 7
        connection_pool._metrics["cache_misses"] = 3

        result = connection_pool.get_metrics()

        assert result["total_commands"] == 10
        assert result["cache_hits"] == 7
        assert result["cache_misses"] == 3
        assert result["hit_rate"] == 0.7

    def test_get_metrics_handles_zero_operations(self, connection_pool):
        """get_metrics handles case with no operations."""
        result = connection_pool.get_metrics()

        assert result["hit_rate"] == 0.0


class TestRedisConnectionPoolClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_connections(self, connection_pool, mock_redis):
        """close closes Redis connections."""
        await connection_pool.close()

        mock_redis.close.assert_called_once()
        assert connection_pool._initialized is False


class TestRedisManager:
    """Tests for RedisManager."""

    @pytest.mark.asyncio
    async def test_initialize_initializes_connection_pool(
        self, redis_config, mock_redis
    ):
        """initialize initializes connection pool."""
        with patch(
            "src.infrastructure.redis_manager.RedisConnectionPool"
        ) as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool.initialize = AsyncMock()
            mock_pool_class.return_value = mock_pool

            manager = RedisManager(config=redis_config)
            await manager.initialize()

            assert manager._initialized is True
            mock_pool.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_skips_if_already_initialized(
        self, redis_manager, mock_redis
    ):
        """initialize skips if already initialized."""
        await redis_manager.initialize()

        # Should not re-initialize
        redis_manager.connection_pool.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_status(self, redis_manager, mock_redis):
        """health_check returns healthy status when Redis is up."""
        mock_redis.ping = AsyncMock()
        mock_redis.info = AsyncMock(return_value={"redis_version": "6.0.0"})

        result = await redis_manager.health_check()

        assert result["healthy"] is True
        assert result["host"] == "localhost"
        assert "server_info" in result

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(
        self, redis_manager, mock_redis
    ):
        """health_check returns unhealthy status on error."""
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_manager.health_check()

        assert result["healthy"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_close_closes_connection_pool(self, redis_manager, mock_redis):
        """close closes connection pool."""
        redis_manager.connection_pool.close = AsyncMock()

        await redis_manager.close()

        redis_manager.connection_pool.close.assert_called_once()
        assert redis_manager._initialized is False


class TestCreateRedisConfigFromEnv:
    """Tests for create_redis_config_from_env function."""

    def test_uses_default_values_when_no_env_vars(self):
        """Uses default values when no environment variables set."""
        with patch.dict("os.environ", {}, clear=True):
            config = create_redis_config_from_env()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.database == 0

    def test_uses_env_var_values(self):
        """Uses values from environment variables."""
        env_vars = {
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "secret",
            "REDIS_DB": "1",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            config = create_redis_config_from_env()

        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.password == "secret"
        assert config.database == 1


class TestCreateRedisManager:
    """Tests for create_redis_manager function."""

    @pytest.mark.asyncio
    async def test_creates_and_initializes_manager(self, redis_config):
        """create_redis_manager creates and initializes manager."""
        with patch(
            "src.infrastructure.redis_manager.RedisConnectionPool"
        ) as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool.initialize = AsyncMock()
            mock_pool_class.return_value = mock_pool

            manager = await create_redis_manager(redis_config)

            assert isinstance(manager, RedisManager)
            assert manager._initialized is True
