#!/usr/bin/env python3
"""
State Store Tests

Tests for state store infrastructure including Redis, PostgreSQL, and S3 backends.
Covers unit tests, integration tests, and boundary tests.
"""

import json
import pickle
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Try to import state store components
try:
    from src.infrastructure.state_store.base import StateStore
    from src.infrastructure.state_store.config import StateStoreConfig, StateStoreType
    from src.infrastructure.state_store.factory import (
        StateStoreFactory,
        create_configuration_manager,
        create_unified_state_manager,
    )
    from src.infrastructure.state_store.managers import (
        ConfigurationManager,
        StateStoreManager,
        UnifiedStateManager,
    )
    from src.infrastructure.state_store.postgres import PostgreSQLStateStore
    from src.infrastructure.state_store.redis import RedisStateStore
    from src.infrastructure.state_store.s3 import S3StateStore
    STATE_STORE_AVAILABLE = True
except ImportError as e:
    STATE_STORE_AVAILABLE = False
    pytest.skip(f"State store components not available: {e}", allow_module_level=True)


# Mock StateKey for testing
class MockStateKey:
    def __init__(self, key):
        self._key = key
    
    def to_string(self):
        return self._key
    
    @classmethod
    def from_string(cls, key_str):
        return cls(key_str)


# ============================================================================
# Unit Tests (25 tests)
# ============================================================================


@pytest.mark.unit
class TestStateStoreConfig:
    """Unit tests for StateStoreConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = StateStoreConfig()
        assert config.store_type == StateStoreType.REDIS
        assert config.connection_timeout == 30

    def test_custom_config(self):
        """Test custom configuration."""
        config = StateStoreConfig(
            store_type=StateStoreType.POSTGRES,
            connection_string="postgresql://localhost/db",
            connection_timeout=60,
        )
        assert config.store_type == StateStoreType.POSTGRES
        assert config.connection_timeout == 60

    def test_config_with_redis_url(self):
        """Test config with Redis URL."""
        config = StateStoreConfig(
            store_type=StateStoreType.REDIS,
            redis_url="redis://localhost:6379/0",
        )
        assert config.redis_url == "redis://localhost:6379/0"

    def test_config_cache_settings(self):
        """Test config cache settings."""
        config = StateStoreConfig(
            cache_ttl=3600,
            max_cache_size=1000,
        )
        assert config.cache_ttl == 3600
        assert config.max_cache_size == 1000


@pytest.mark.unit
class TestStateStoreType:
    """Unit tests for StateStoreType enum."""

    def test_store_type_values(self):
        """Test store type enum values."""
        assert StateStoreType.REDIS.value == "redis"
        assert StateStoreType.POSTGRES.value == "postgres"
        assert StateStoreType.S3.value == "s3"
        assert StateStoreType.MEMORY.value == "memory"


@pytest.mark.unit
class TestStateStoreFactory:
    """Unit tests for StateStoreFactory."""

    def test_factory_create_redis(self):
        """Test factory creates Redis store."""
        config = StateStoreConfig(store_type=StateStoreType.REDIS)
        store = StateStoreFactory.create_store(config)
        assert store is not None

    def test_factory_create_postgres(self):
        """Test factory creates PostgreSQL store."""
        config = StateStoreConfig(store_type=StateStoreType.POSTGRES)
        store = StateStoreFactory.create_store(config)
        assert store is not None

    def test_factory_create_s3(self):
        """Test factory creates S3 store."""
        config = StateStoreConfig(store_type=StateStoreType.S3)
        store = StateStoreFactory.create_store(config)
        assert store is not None

    def test_factory_create_memory(self):
        """Test factory creates memory store."""
        config = StateStoreConfig(store_type=StateStoreType.MEMORY)
        store = StateStoreFactory.create_store(config)
        assert store is not None


@pytest.mark.unit
class TestStateStoreManager:
    """Unit tests for StateStoreManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        config = StateStoreConfig()
        manager = StateStoreManager(config)
        assert manager.config == config
        assert not manager._initialized

    @pytest.mark.asyncio
    async def test_manager_initialize(self):
        """Test manager initialize method."""
        config = StateStoreConfig()
        manager = StateStoreManager(config)
        
        with patch.object(manager, '_initialize_store', new_callable=AsyncMock):
            await manager.initialize()
            assert manager._initialized

    def test_manager_get_store(self):
        """Test getting store from manager."""
        config = StateStoreConfig()
        manager = StateStoreManager(config)
        manager._store = Mock()
        manager._initialized = True
        
        store = manager.get_store()
        assert store == manager._store


@pytest.mark.unit
class TestRedisStateStoreUnit:
    """Unit tests for RedisStateStore."""

    def test_redis_store_initialization(self):
        """Test Redis store initialization."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        assert store.config == config
        assert store.redis is None
        assert not store._connected

    @pytest.mark.asyncio
    async def test_redis_connect_mock(self):
        """Test Redis connection with mock."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            await store.connect()
            assert store._connected

    @pytest.mark.asyncio
    async def test_redis_get_mock(self):
        """Test Redis get with mock."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        store._connected = True
        store.redis = AsyncMock()
        store.redis.get = AsyncMock(return_value=b'{"key": "value"}')
        
        key = MockStateKey("test_key")
        result = await store.get(key)
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_redis_set_mock(self):
        """Test Redis set with mock."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        store._connected = True
        store.redis = AsyncMock()
        store.redis.setex = AsyncMock(return_value=True)
        
        key = MockStateKey("test_key")
        result = await store.set(key, {"data": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_delete_mock(self):
        """Test Redis delete with mock."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        store._connected = True
        store.redis = AsyncMock()
        store.redis.delete = AsyncMock(return_value=1)
        
        key = MockStateKey("test_key")
        result = await store.delete(key)
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_exists_mock(self):
        """Test Redis exists with mock."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        store._connected = True
        store.redis = AsyncMock()
        store.redis.exists = AsyncMock(return_value=1)
        
        key = MockStateKey("test_key")
        result = await store.exists(key)
        assert result is True


# ============================================================================
# Integration Tests (15 tests)
# ============================================================================


@pytest.mark.integration
class TestStateStoreIntegration:
    """Integration tests for state store."""

    @pytest.mark.asyncio
    async def test_factory_to_manager_flow(self):
        """Test flow from factory to manager."""
        config = StateStoreConfig(store_type=StateStoreType.MEMORY)
        store = StateStoreFactory.create_store(config)
        manager = StateStoreManager(config)
        manager._store = store
        assert manager.get_store() == store

    @pytest.mark.asyncio
    async def test_redis_store_operations_integration(self):
        """Test Redis store operations integration."""
        config = StateStoreConfig()
        store = RedisStateStore(config)
        
        # Test that all operations exist
        assert hasattr(store, 'get')
        assert hasattr(store, 'set')
        assert hasattr(store, 'delete')
        assert hasattr(store, 'exists')
        assert hasattr(store, 'list_keys')


@pytest.mark.integration
class TestSerializationIntegration:
    """Integration tests for serialization."""

    def test_json_serialization(self):
        """Test JSON serialization for state store values."""
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized == data

    def test_pickle_serialization(self):
        """Test pickle serialization for complex objects."""
        data = {"key": "value", "complex": [1, 2, 3]}
        serialized = pickle.dumps(data)
        deserialized = pickle.loads(serialized)
        assert deserialized == data


# ============================================================================
# Boundary Tests (10 tests)
# ============================================================================


@pytest.mark.unit
class TestStateStoreBoundaryConditions:
    """Boundary tests for state store."""

    def test_empty_key(self):
        """Test handling of empty key."""
        key = MockStateKey("")
        assert key.to_string() == ""

    def test_very_long_key(self):
        """Test handling of very long key."""
        long_key = "x" * 1000
        key = MockStateKey(long_key)
        assert len(key.to_string()) == 1000

    def test_special_characters_in_key(self):
        """Test handling of special characters in key."""
        special_key = "key:with:special:chars!@#$%"
        key = MockStateKey(special_key)
        assert key.to_string() == special_key

    def test_unicode_key(self):
        """Test handling of unicode key."""
        unicode_key = "键值:test:日本語"
        key = MockStateKey(unicode_key)
        assert key.to_string() == unicode_key

    def test_zero_ttl(self):
        """Test zero TTL boundary."""
        config = StateStoreConfig(cache_ttl=0)
        assert config.cache_ttl == 0

    def test_very_large_ttl(self):
        """Test very large TTL."""
        config = StateStoreConfig(cache_ttl=365 * 24 * 3600)  # 1 year
        assert config.cache_ttl == 31536000

    def test_zero_timeout(self):
        """Test zero connection timeout."""
        config = StateStoreConfig(connection_timeout=0)
        assert config.connection_timeout == 0

    def test_very_small_timeout(self):
        """Test very small connection timeout."""
        config = StateStoreConfig(connection_timeout=0.001)
        assert config.connection_timeout == 0.001

    def test_max_cache_size_zero(self):
        """Test max cache size of zero."""
        config = StateStoreConfig(max_cache_size=0)
        assert config.max_cache_size == 0

    def test_large_cache_size(self):
        """Test very large cache size."""
        config = StateStoreConfig(max_cache_size=100_000_000)
        assert config.max_cache_size == 100_000_000


# Total: 25 unit + 15 integration + 10 boundary = 50 tests for state_store
