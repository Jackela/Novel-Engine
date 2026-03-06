class UnifiedStateManager:
    """Unified state manager that routes to appropriate stores"""

    def __init__(self, config: StateStoreConfig) -> None:
        self.config = config
        self.redis_store = RedisStateStore(config)
        self.postgres_store = PostgreSQLStateStore(config)
        self.s3_store = S3StateStore(config)

        # Routing rules based on data type and size
        self.routing_rules = {
            "session": "redis",  # Session data -> Redis
            "cache": "redis",  # Cache data -> Redis
            "agent": "postgres",  # Agent state -> PostgreSQL
            "world": "postgres",  # World state -> PostgreSQL
            "narrative": "s3",  # Narrative documents -> S3
            "media": "s3",  # Media files -> S3
            "config": "postgres",  # Configuration -> PostgreSQL
            "temp": "redis",  # Temporary data -> Redis
        }

    async def initialize(self) -> None:
        """Initialize all stores"""
        try:
            await self.redis_store.connect()
            await self.postgres_store.connect()
            await self.s3_store.connect()
            logger.info("Unified state manager initialized")
        except Exception as e:
            logger.error("state_manager_initialization_failed", error=str(e), error_type=type(e).__name__)
            raise

    def _get_store(self, key: StateKey) -> StateStore:
        """Get appropriate store for key"""
        store_type = self.routing_rules.get(key.entity_type, "postgres")

        if store_type == "redis":
            return self.redis_store
        elif store_type == "s3":
            return self.s3_store
        else:
            return self.postgres_store

    async def get(self, key: StateKey, use_cache: bool = True) -> Optional[Any]:
        """Get value with intelligent routing and caching"""

        # Try cache first for non-cache keys
        if use_cache and key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=f"{key.entity_type}:{key.entity_id}",
                version=key.version,
            )

            cached_value = await self.redis_store.get(cache_key)
            if cached_value is not None:
                return cached_value

        # Get from primary store
        primary_store = self._get_store(key)
        value = await primary_store.get(key)

        # Cache in Redis if fetched from slower store
        if (
            value is not None
            and use_cache
            and key.entity_type != "cache"
            and primary_store != self.redis_store
        ):
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=f"{key.entity_type}:{key.entity_id}",
                version=key.version,
            )
            await self.redis_store.set(cache_key, value, ttl=300)  # 5 minute cache

        return value

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with intelligent routing"""
        primary_store = self._get_store(key)
        success = await primary_store.set(key, value, ttl)

        # Invalidate cache
        if success and key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=f"{key.entity_type}:{key.entity_id}",
                version=key.version,
            )
            await self.redis_store.delete(cache_key)

        return success

    async def delete(self, key: StateKey) -> bool:
        """Delete value from appropriate store"""
        primary_store = self._get_store(key)
        success = await primary_store.delete(key)

        # Invalidate cache
        if success and key.entity_type != "cache":
            cache_key = StateKey(
                namespace=f"cache:{key.namespace}",
                entity_type="cache",
                entity_id=f"{key.entity_type}:{key.entity_id}",
                version=key.version,
            )
            await self.redis_store.delete(cache_key)

        return success

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in appropriate store"""
        primary_store = self._get_store(key)
        return await primary_store.exists(key)

    async def list_keys(
        self, pattern: str, store_type: Optional[str] = None
    ) -> List[StateKey]:
        """List keys from appropriate store(s)"""
        if store_type:
            if store_type == "redis":
                return await self.redis_store.list_keys(pattern)
            elif store_type == "s3":
                return await self.s3_store.list_keys(pattern)
            else:
                return await self.postgres_store.list_keys(pattern)
        else:
            # Search all stores and combine results
            all_keys: list[Any] = []
            for store in [self.redis_store, self.postgres_store, self.s3_store]:
                try:
                    keys = await store.list_keys(pattern)
                    all_keys.extend(keys)
                except Exception as e:
                    logger.warning(f"Failed to list keys from store: {e}")

            return all_keys

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all stores"""
        return {
            "redis": await self.redis_store.health_check(),
            "postgres": await self.postgres_store.health_check(),
            "s3": await self.s3_store.health_check(),
        }

    async def cleanup_expired(self) -> None:
        """Cleanup expired data from all stores"""
        await self.postgres_store.cleanup_expired()
        # Redis handles expiration automatically
        # S3 expiration is handled by lifecycle policies

    async def close(self) -> None:
        """Close all store connections"""
        await self.redis_store.close()
        await self.postgres_store.close()
        await self.s3_store.close()
        logger.info("Unified state manager closed")


