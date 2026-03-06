class RedisStateStore(StateStore):
    """Redis-based state store for fast access"""

    def __init__(self, config: StateStoreConfig) -> None:
        self.config = config
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Initialize Redis connection"""
        if self._connected:
            return

        try:
            self.redis = aioredis.from_url(
                self.config.redis_url,
                socket_timeout=self.config.connection_timeout,
                socket_connect_timeout=self.config.connection_timeout,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("redis_connection_established")

        except Exception as e:
            logger.error("redis_connection_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from Redis"""
        if not self._connected:
            await self.connect()

        try:
            raw_value = await self.redis.get(key.to_string())
            if raw_value is None:
                return None

            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(raw_value)
            except json.JSONDecodeError:
                try:
                    return pickle.loads(
                        raw_value
                    )  # nosec B301 - trusted internal state data
                except Exception:
                    # Return as string if deserialization fails
                    return (
                        raw_value.decode("utf-8")
                        if isinstance(raw_value, bytes)
                        else raw_value
                    )

        except Exception as e:
            logger.error("redis_get_failed", key=key.to_string(), error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in Redis"""
        if not self._connected:
            await self.connect()

        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            elif isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = pickle.dumps(value)

            # Set with TTL
            ttl_seconds = ttl or self.config.cache_ttl
            result = await self.redis.setex(
                key.to_string(), ttl_seconds, serialized_value
            )
            return result is True

        except Exception as e:
            logger.error("redis_set_failed", key=key.to_string(), error=str(e))
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from Redis"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.delete(key.to_string())
            return result > 0

        except Exception as e:
            logger.error("redis_delete_failed", key=key.to_string(), error=str(e))
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in Redis"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.exists(key.to_string())
            return result > 0

        except Exception as e:
            logger.error("redis_exists_check_failed", key=key.to_string(), error=str(e))
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        if not self._connected:
            await self.connect()

        try:
            keys = await self.redis.keys(pattern)
            return [
                StateKey.from_string(key.decode() if isinstance(key, bytes) else key)
                for key in keys
            ]

        except Exception as e:
            logger.error("redis_list_keys_failed", pattern=pattern, error=str(e))
            return []

    async def increment(self, key: StateKey, amount: int = 1) -> Optional[int]:
        """Increment counter value"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.incrby(key.to_string(), amount)
            return result

        except Exception as e:
            logger.error("redis_increment_failed", key=key.to_string(), error=str(e))
            return None

    async def expire(self, key: StateKey, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.expire(key.to_string(), ttl)
            return result is True

        except Exception as e:
            logger.error("redis_expire_failed", key=key.to_string(), error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self._connected:
                await self.connect()

            await self.redis.ping()
            return True

        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("redis_connection_closed")


