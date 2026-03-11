"""Redis State Store.

Redis-based implementation of the StateStore interface.
"""

import json
import pickle
from typing import Any, List, Optional

import structlog

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateKey, StateStoreConfig

# Import redis with async support
try:
    from redis import asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = structlog.get_logger(__name__)


class RedisStateStore(StateStore):
    """Redis-based state store for fast access."""

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize Redis state store.

        Args:
            config: State store configuration
        """
        self.config = config
        self.redis: Optional[Any] = None
        self._connected = False

        if not REDIS_AVAILABLE:
            logger.warning("redis_not_available")

    async def connect(self) -> None:
        """Initialize Redis connection."""
        if self._connected or not REDIS_AVAILABLE:
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
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from Redis.

        Args:
            key: State key to look up

        Returns:
            Stored value or None
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return None

        try:
            raw_value = await self.redis.get(key.to_string())
            if raw_value is None:
                return None

            # Try to deserialize as JSON first (if decodable as UTF-8), then pickle
            try:
                # Attempt to decode as UTF-8 and parse as JSON
                str_value = (
                    raw_value.decode("utf-8")
                    if isinstance(raw_value, bytes)
                    else raw_value
                )
                return json.loads(str_value)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # JSON parsing failed, try pickle (for binary data)
                try:
                    # nosec B301 - pickle used for internal Redis cache data only
                    # Data is stored by trusted application code, not external users
                    return pickle.loads(raw_value)  # nosec B301
                except Exception:
                    # Return as string if deserialization fails
                    return (
                        raw_value.decode("utf-8", errors="replace")
                        if isinstance(raw_value, bytes)
                        else raw_value
                    )

        except Exception as e:
            logger.error("redis_get_failed", key=key.to_string(), error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in Redis.

        Args:
            key: State key
            value: Value to store
            ttl: Optional time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return False

        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            elif isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = pickle.dumps(value).decode("latin-1")

            # Set with TTL
            ttl_seconds = ttl or self.config.cache_ttl
            result = await self.redis.setex(
                key.to_string(), ttl_seconds, serialized_value
            )
            return bool(result)

        except Exception as e:
            logger.error("redis_set_failed", key=key.to_string(), error=str(e))
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from Redis.

        Args:
            key: State key to delete

        Returns:
            True if deleted
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return False

        try:
            result = await self.redis.delete(key.to_string())
            return bool(result > 0)

        except Exception as e:
            logger.error("redis_delete_failed", key=key.to_string(), error=str(e))
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in Redis.

        Args:
            key: State key to check

        Returns:
            True if exists
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return False

        try:
            result = await self.redis.exists(key.to_string())
            return bool(result > 0)

        except Exception as e:
            logger.error("redis_exists_check_failed", key=key.to_string(), error=str(e))
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "namespace:*")

        Returns:
            List of matching keys
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return []

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
        """Increment counter value.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return None

        try:
            result = await self.redis.incrby(key.to_string(), amount)
            return int(result) if result is not None else None

        except Exception as e:
            logger.error("redis_increment_failed", key=key.to_string(), error=str(e))
            return None

    async def expire(self, key: StateKey, ttl: int) -> bool:
        """Set TTL for existing key.

        Args:
            key: State key
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        if not self.redis:
            return False

        try:
            result = await self.redis.expire(key.to_string(), ttl)
            return bool(result)

        except Exception as e:
            logger.error("redis_expire_failed", key=key.to_string(), error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check Redis health.

        Returns:
            True if healthy
        """
        try:
            if not self._connected:
                await self.connect()

            if not self.redis:
                return False

            await self.redis.ping()
            return True

        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("redis_connection_closed")
