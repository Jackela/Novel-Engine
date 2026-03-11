"""State Store Managers.

High-level managers for state storage operations.
"""

from typing import Any, Dict, Optional

import structlog

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateKey, StateStoreConfig
from src.infrastructure.state_store.redis import RedisStateStore

logger = structlog.get_logger(__name__)


class UnifiedStateManager:
    """Unified state manager that routes to appropriate stores.

    Provides intelligent routing of data to different storage backends
    based on data type and access patterns.
    """

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize unified state manager.

        Args:
            config: State store configuration
        """
        self.config = config

        # Lazy imports to avoid circular dependencies
        from src.infrastructure.state_store.postgres import PostgreSQLStateStore
        from src.infrastructure.state_store.s3 import S3StateStore

        self.redis_store = RedisStateStore(config)
        self.postgres_store = PostgreSQLStateStore(config)
        self.s3_store = S3StateStore(config)

        # Routing rules based on data type and size
        self.routing_rules = {
            "session": "redis",
            "cache": "redis",
            "agent": "postgres",
            "world": "postgres",
            "narrative": "s3",
            "media": "s3",
            "config": "postgres",
            "temp": "redis",
        }

    async def initialize(self) -> None:
        """Initialize all stores."""
        try:
            await self.redis_store.connect()
            await self.postgres_store.connect()
            await self.s3_store.connect()
            logger.info("unified_state_manager_initialized")
        except Exception as e:
            logger.error("state_manager_initialization_failed", error=str(e))
            raise

    def _get_store(self, key: StateKey) -> StateStore:
        """Get appropriate store for key.

        Args:
            key: State key

        Returns:
            Appropriate StateStore instance
        """
        store_type = self.routing_rules.get(key.entity_type, "postgres")

        if store_type == "redis":
            return self.redis_store
        elif store_type == "s3":
            return self.s3_store
        else:
            return self.postgres_store

    async def get(self, key: StateKey, use_cache: bool = True) -> Optional[Any]:
        """Get value with intelligent routing and caching.

        Args:
            key: State key
            use_cache: Whether to use cache layer

        Returns:
            Stored value or None
        """
        # Try cache first for non-cache keys
        if use_cache and key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=key.to_string(),
            )
            cached = await self.redis_store.get(cache_key)
            if cached is not None:
                return cached

        # Get from primary store
        store = self._get_store(key)
        value = await store.get(key)

        # Cache the result if not from cache already
        if value is not None and use_cache and key.entity_type != "cache":
            await self.redis_store.set(cache_key, value, ttl=300)  # 5 min cache

        return value

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with intelligent routing.

        Args:
            key: State key
            value: Value to store
            ttl: Optional time-to-live

        Returns:
            True if successful
        """
        store = self._get_store(key)
        result = await store.set(key, value, ttl)

        # Invalidate cache if applicable
        if key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=key.to_string(),
            )
            await self.redis_store.delete(cache_key)

        return result

    async def delete(self, key: StateKey) -> bool:
        """Delete value from appropriate store.

        Args:
            key: State key

        Returns:
            True if deleted
        """
        store = self._get_store(key)
        result = await store.delete(key)

        # Also delete from cache if exists
        if key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=key.to_string(),
            )
            await self.redis_store.delete(cache_key)

        return result

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists.

        Args:
            key: State key

        Returns:
            True if exists
        """
        store = self._get_store(key)
        return await store.exists(key)

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all stores.

        Returns:
            Dictionary of store health status
        """
        return {
            "redis": await self.redis_store.health_check(),
            "postgres": await self.postgres_store.health_check(),
            "s3": await self.s3_store.health_check(),
        }

    async def close(self) -> None:
        """Close all stores."""
        await self.redis_store.close()
        await self.postgres_store.close()
        await self.s3_store.close()
        logger.info("unified_state_manager_closed")


class StateStoreManager:
    """Manager for a single state store.

    Provides a simple interface for managing a single state store instance.
    """

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize state store manager.

        Args:
            config: State store configuration
        """
        self.config = config
        self._store = None
        self._initialized = False

        # Create the appropriate store based on config
        from src.infrastructure.state_store.factory import StateStoreFactory

        self._store = StateStoreFactory.create_store(config)

    async def _initialize_store(self) -> None:
        """Initialize the underlying store."""
        if self._store and hasattr(self._store, "connect"):
            await self._store.connect()

    async def initialize(self) -> None:
        """Initialize the state store manager."""
        await self._initialize_store()
        self._initialized = True

    def get_store(self) -> Optional[StateStore]:
        """Get the underlying store.

        Returns:
            The state store instance
        """
        return self._store

    async def get(self, key: StateKey) -> Optional[Any]:
        """Get value from store."""
        if self._store:
            return await self._store.get(key)
        return None

    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in store."""
        if self._store:
            result: bool = await self._store.set(key, value, ttl)
            return result
        return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from store."""
        if self._store:
            result: bool = await self._store.delete(key)
            return result
        return False


class ConfigurationManager:
    """Manager for configuration storage.

    Provides specialized interface for configuration data
    with PostgreSQL as the backend.
    """

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize configuration manager.

        Args:
            config: State store configuration
        """
        self.config = config

        from src.infrastructure.state_store.postgres import PostgreSQLStateStore

        self.store = PostgreSQLStateStore(config)

    async def initialize(self) -> None:
        """Initialize configuration manager."""
        await self.store.connect()

    async def get_config(
        self, config_type: str, config_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get configuration by type and ID.

        Args:
            config_type: Type of configuration
            config_id: Configuration identifier

        Returns:
            Configuration dictionary or None
        """
        key = StateKey(
            namespace="config",
            entity_type=config_type,
            entity_id=config_id,
        )
        return await self.store.get(key)

    async def set_config(
        self, config_type: str, config_id: str, config_data: Dict[str, Any]
    ) -> bool:
        """Set configuration.

        Args:
            config_type: Type of configuration
            config_id: Configuration identifier
            config_data: Configuration data

        Returns:
            True if successful
        """
        key = StateKey(
            namespace="config",
            entity_type=config_type,
            entity_id=config_id,
        )
        return await self.store.set(key, config_data)

    async def delete_config(self, config_type: str, config_id: str) -> bool:
        """Delete configuration.

        Args:
            config_type: Type of configuration
            config_id: Configuration identifier

        Returns:
            True if deleted
        """
        key = StateKey(
            namespace="config",
            entity_type=config_type,
            entity_id=config_id,
        )
        return await self.store.delete(key)

    async def list_configs(self, config_type: str) -> list:
        """List all configurations of a type.

        Args:
            config_type: Type of configuration

        Returns:
            List of configuration keys
        """
        return await self.store.list_keys(f"config:{config_type}:*")

    async def health_check(self) -> bool:
        """Check store health.

        Returns:
            True if healthy
        """
        return await self.store.health_check()

    async def close(self) -> None:
        """Close configuration manager."""
        await self.store.close()
