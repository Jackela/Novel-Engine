#!/usr/bin/env python3
"""
Redis Cache and Session Manager
===============================

Enterprise Redis manager for high-performance caching, session storage,
and real-time data management in the Novel Engine framework.
"""

import asyncio
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import aioredis

logger = logging.getLogger(__name__)


class RedisDataType(Enum):
    """Redis data type strategies."""

    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    SORTED_SET = "zset"
    JSON = "json"
    STREAM = "stream"


class RedisStorageStrategy(Enum):
    """Redis storage and serialization strategies."""

    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    PLAIN = "plain"


@dataclass
class RedisConfig:
    """Redis connection and feature configuration."""

    # Connection settings
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0

    # Connection pool settings
    min_pool_size: int = 5
    max_pool_size: int = 100
    connection_timeout: float = 10.0
    socket_timeout: float = 5.0
    socket_keepalive: bool = True

    # SSL configuration
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None

    # Performance settings
    encoding: str = "utf-8"
    decode_responses: bool = True
    retry_on_timeout: bool = True
    health_check_interval: float = 30.0

    # Cache settings
    default_ttl: int = 3600  # 1 hour
    max_memory_policy: str = "allkeys-lru"

    # Cluster settings
    cluster_enabled: bool = False
    cluster_nodes: List[str] = field(default_factory=list)

    # Monitoring
    enable_monitoring: bool = True
    command_timeout: float = 30.0

    def get_connection_string(self) -> str:
        """Get Redis connection string."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class CacheKey:
    """Structured cache key builder."""

    namespace: str
    entity_type: str
    entity_id: str
    operation: Optional[str] = None
    version: Optional[str] = None

    def build(self) -> str:
        """Build cache key string."""
        parts = [self.namespace, self.entity_type, self.entity_id]

        if self.operation:
            parts.append(self.operation)

        if self.version:
            parts.append(f"v{self.version}")

        return ":".join(parts)


class RedisConnectionPool:
    """
    Enterprise Redis connection pool with advanced features.

    Features:
    - Connection pooling with health monitoring
    - Multiple serialization strategies
    - Intelligent caching patterns
    - Session management
    - Real-time data streaming
    - Performance monitoring
    """

    def __init__(self, config: RedisConfig):
        """Initialize Redis connection pool."""
        self.config = config
        self.pool: Optional[aioredis.ConnectionPool] = None
        self.redis: Optional[aioredis.Redis] = None
        self._initialized = False

        # Metrics tracking
        self._metrics = {
            "total_commands": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "avg_response_time": 0.0,
            "response_times": [],
            "active_connections": 0,
        }

        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_healthy = True

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            return

        try:
            if self.config.cluster_enabled:
                # Redis Cluster support
                self.redis = aioredis.RedisCluster(
                    startup_nodes=[
                        {"host": node.split(":")[0], "port": int(node.split(":")[1])}
                        for node in self.config.cluster_nodes
                    ],
                    password=self.config.password,
                    decode_responses=self.config.decode_responses,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.connection_timeout,
                )
            else:
                # Single Redis instance
                self.pool = aioredis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.database,
                    encoding=self.config.encoding,
                    decode_responses=self.config.decode_responses,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.connection_timeout,
                    socket_keepalive=self.config.socket_keepalive,
                    retry_on_timeout=self.config.retry_on_timeout,
                    max_connections=self.config.max_pool_size,
                )

                self.redis = aioredis.Redis(connection_pool=self.pool)

            # Test connection
            await self.redis.ping()

            # Configure Redis settings
            await self._configure_redis()

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            self._initialized = True
            logger.info(
                f"Redis connection pool initialized: {self.config.host}:{self.config.port}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            raise

    async def _configure_redis(self) -> None:
        """Configure Redis instance settings."""
        try:
            # Set memory policy
            await self.redis.config_set(
                "maxmemory-policy", self.config.max_memory_policy
            )
            logger.debug(f"Set Redis memory policy: {self.config.max_memory_policy}")

        except Exception as e:
            logger.warning(f"Failed to configure Redis: {e}")

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._initialized:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if not self._initialized:
                    break

                # Health check
                start_time = asyncio.get_event_loop().time()
                await self.redis.ping()
                response_time = asyncio.get_event_loop().time() - start_time

                # Update metrics
                self._metrics["response_times"].append(response_time)
                if len(self._metrics["response_times"]) > 1000:
                    self._metrics["response_times"] = self._metrics["response_times"][
                        -1000:
                    ]

                if self._metrics["response_times"]:
                    self._metrics["avg_response_time"] = sum(
                        self._metrics["response_times"]
                    ) / len(self._metrics["response_times"])

                self._is_healthy = True

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._is_healthy = False

    def _serialize_value(
        self, value: Any, strategy: RedisStorageStrategy = RedisStorageStrategy.JSON
    ) -> str:
        """Serialize value based on strategy."""
        if strategy == RedisStorageStrategy.JSON:
            return json.dumps(value, default=str)
        elif strategy == RedisStorageStrategy.PICKLE:
            return pickle.dumps(value).hex()
        elif strategy == RedisStorageStrategy.PLAIN:
            return str(value)
        else:
            # Default to JSON
            return json.dumps(value, default=str)

    def _deserialize_value(
        self, value: str, strategy: RedisStorageStrategy = RedisStorageStrategy.JSON
    ) -> Any:
        """Deserialize value based on strategy."""
        if not value:
            return None

        try:
            if strategy == RedisStorageStrategy.JSON:
                return json.loads(value)
            elif strategy == RedisStorageStrategy.PICKLE:
                return pickle.loads(bytes.fromhex(value))
            elif strategy == RedisStorageStrategy.PLAIN:
                return value
            else:
                # Default to JSON
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to deserialize value: {e}")
            return value

    # Basic Redis operations with monitoring

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        strategy: RedisStorageStrategy = RedisStorageStrategy.JSON,
    ) -> bool:
        """Set key-value pair with TTL."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_event_loop().time()

        try:
            serialized_value = self._serialize_value(value, strategy)
            expire_time = ttl or self.config.default_ttl

            result = await self.redis.setex(key, expire_time, serialized_value)

            self._metrics["total_commands"] += 1
            response_time = asyncio.get_event_loop().time() - start_time
            self._metrics["response_times"].append(response_time)

            return bool(result)

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis SET failed for key {key}: {e}")
            raise

    async def get(
        self, key: str, strategy: RedisStorageStrategy = RedisStorageStrategy.JSON
    ) -> Any:
        """Get value by key."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_event_loop().time()

        try:
            value = await self.redis.get(key)

            self._metrics["total_commands"] += 1
            response_time = asyncio.get_event_loop().time() - start_time
            self._metrics["response_times"].append(response_time)

            if value is not None:
                self._metrics["cache_hits"] += 1
                return self._deserialize_value(value, strategy)
            else:
                self._metrics["cache_misses"] += 1
                return None

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis GET failed for key {key}: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.delete(key)
            self._metrics["total_commands"] += 1
            return bool(result)

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.exists(key)
            self._metrics["total_commands"] += 1
            return bool(result)

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            raise

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.expire(key, ttl)
            self._metrics["total_commands"] += 1
            return bool(result)

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
            raise

    # Hash operations

    async def hset(
        self, key: str, field: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set hash field."""
        if not self._initialized:
            await self.initialize()

        try:
            serialized_value = self._serialize_value(value)
            result = await self.redis.hset(key, field, serialized_value)

            if ttl:
                await self.redis.expire(key, ttl)

            self._metrics["total_commands"] += 1
            return bool(result)

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis HSET failed for key {key}, field {field}: {e}")
            raise

    async def hget(self, key: str, field: str) -> Any:
        """Get hash field."""
        if not self._initialized:
            await self.initialize()

        try:
            value = await self.redis.hget(key, field)
            self._metrics["total_commands"] += 1

            if value is not None:
                return self._deserialize_value(value)
            return None

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis HGET failed for key {key}, field {field}: {e}")
            raise

    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.hgetall(key)
            self._metrics["total_commands"] += 1

            # Deserialize all values
            return {
                field: self._deserialize_value(value) for field, value in result.items()
            }

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis HGETALL failed for key {key}: {e}")
            raise

    # List operations

    async def lpush(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """Push values to list head."""
        if not self._initialized:
            await self.initialize()

        try:
            serialized_values = [self._serialize_value(v) for v in values]
            result = await self.redis.lpush(key, *serialized_values)

            if ttl:
                await self.redis.expire(key, ttl)

            self._metrics["total_commands"] += 1
            return result

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis LPUSH failed for key {key}: {e}")
            raise

    async def lrange(self, key: str, start: int = 0, stop: int = -1) -> List[Any]:
        """Get list range."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.lrange(key, start, stop)
            self._metrics["total_commands"] += 1

            return [self._deserialize_value(v) for v in result]

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis LRANGE failed for key {key}: {e}")
            raise

    # Set operations

    async def sadd(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """Add values to set."""
        if not self._initialized:
            await self.initialize()

        try:
            serialized_values = [self._serialize_value(v) for v in values]
            result = await self.redis.sadd(key, *serialized_values)

            if ttl:
                await self.redis.expire(key, ttl)

            self._metrics["total_commands"] += 1
            return result

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis SADD failed for key {key}: {e}")
            raise

    async def smembers(self, key: str) -> Set[Any]:
        """Get set members."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.smembers(key)
            self._metrics["total_commands"] += 1

            return {self._deserialize_value(v) for v in result}

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Redis SMEMBERS failed for key {key}: {e}")
            raise

    # Novel Engine specific operations

    async def cache_character(
        self, character_id: str, character_data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Cache character data."""
        cache_key = CacheKey("novel_engine", "character", character_id).build()
        return await self.set(cache_key, character_data, ttl)

    async def get_cached_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get cached character data."""
        cache_key = CacheKey("novel_engine", "character", character_id).build()
        return await self.get(cache_key)

    async def cache_interaction_result(
        self,
        session_id: str,
        interaction_id: str,
        result_data: Dict[str, Any],
        ttl: int = 1800,
    ) -> bool:
        """Cache interaction result."""
        cache_key = CacheKey(
            "novel_engine", "interaction", f"{session_id}:{interaction_id}"
        ).build()
        return await self.set(cache_key, result_data, ttl)

    async def store_session(
        self, session_id: str, session_data: Dict[str, Any], ttl: int = 7200
    ) -> bool:
        """Store session data."""
        session_key = CacheKey("novel_engine", "session", session_id).build()

        # Store as hash for efficient partial updates
        pipe = self.redis.pipeline()
        for session_field, value in session_data.items():
            await pipe.hset(session_key, session_field, self._serialize_value(value))
        await pipe.expire(session_key, ttl)

        await pipe.execute()
        return True

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        session_key = CacheKey("novel_engine", "session", session_id).build()
        return await self.hgetall(session_key)

    async def update_session_field(
        self, session_id: str, field: str, value: Any
    ) -> bool:
        """Update single session field."""
        session_key = CacheKey("novel_engine", "session", session_id).build()
        return await self.hset(session_key, field, value)

    async def store_agent_context(
        self, agent_id: str, context_data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Store agent context for quick access."""
        context_key = CacheKey("novel_engine", "agent_context", agent_id).build()
        return await self.set(context_key, context_data, ttl)

    async def get_agent_context(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent context."""
        context_key = CacheKey("novel_engine", "agent_context", agent_id).build()
        return await self.get(context_key)

    async def add_to_narrative_stream(
        self, narrative_id: str, event_data: Dict[str, Any]
    ) -> bool:
        """Add event to narrative stream."""
        stream_key = CacheKey("novel_engine", "narrative_stream", narrative_id).build()
        event_data["timestamp"] = datetime.now().isoformat()

        # Use list for simple streaming
        await self.lpush(stream_key, event_data, ttl=86400)  # 24 hours

        # Keep only last 1000 events
        await self.redis.ltrim(stream_key, 0, 999)

        return True

    async def get_narrative_stream(
        self, narrative_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get narrative event stream."""
        stream_key = CacheKey("novel_engine", "narrative_stream", narrative_id).build()
        return await self.lrange(stream_key, 0, limit - 1)

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self.redis:
            await self.redis.close()

        if self.pool:
            await self.pool.disconnect()

        self._initialized = False
        logger.info("Redis connection pool closed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get Redis performance metrics."""
        response_times = self._metrics["response_times"]

        hit_rate = (
            self._metrics["cache_hits"]
            / (self._metrics["cache_hits"] + self._metrics["cache_misses"])
            if (self._metrics["cache_hits"] + self._metrics["cache_misses"]) > 0
            else 0.0
        )

        return {
            "total_commands": self._metrics["total_commands"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "hit_rate": hit_rate,
            "errors": self._metrics["errors"],
            "avg_response_time": self._metrics["avg_response_time"],
            "max_response_time": max(response_times) if response_times else 0.0,
            "active_connections": self._metrics["active_connections"],
            "is_healthy": self._is_healthy,
        }


class RedisManager:
    """
    Central Redis manager for Novel Engine.

    Provides high-level caching, session management, and real-time data operations
    optimized for Novel Engine use cases.
    """

    def __init__(self, config: RedisConfig):
        """Initialize Redis manager."""
        self.config = config
        self.connection_pool = RedisConnectionPool(config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis manager."""
        if not self._initialized:
            await self.connection_pool.initialize()
            self._initialized = True
            logger.info("Redis manager initialized")

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            await self.connection_pool.redis.ping()

            info = await self.connection_pool.redis.info()
            metrics = self.connection_pool.get_metrics()

            return {
                "healthy": True,
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "metrics": metrics,
                "server_info": {
                    "version": info.get("redis_version"),
                    "uptime": info.get("uptime_in_seconds"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory"),
                    "used_memory_human": info.get("used_memory_human"),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def close(self) -> None:
        """Close Redis manager."""
        await self.connection_pool.close()
        self._initialized = False


# Factory functions for easy integration
def create_redis_config_from_env() -> RedisConfig:
    """Create Redis configuration from environment variables."""
    import os

    return RedisConfig(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        database=int(os.getenv("REDIS_DB", "0")),
        min_pool_size=int(os.getenv("REDIS_MIN_POOL_SIZE", "5")),
        max_pool_size=int(os.getenv("REDIS_MAX_POOL_SIZE", "100")),
        default_ttl=int(os.getenv("REDIS_DEFAULT_TTL", "3600")),
        cluster_enabled=os.getenv("REDIS_CLUSTER_ENABLED", "false").lower() == "true",
        ssl_enabled=os.getenv("REDIS_SSL_ENABLED", "false").lower() == "true",
    )


async def create_redis_manager(config: Optional[RedisConfig] = None) -> RedisManager:
    """Create and initialize Redis manager."""
    if config is None:
        config = create_redis_config_from_env()

    manager = RedisManager(config)
    await manager.initialize()
    return manager


__all__ = [
    "RedisConfig",
    "RedisConnectionPool",
    "RedisManager",
    "RedisDataType",
    "RedisStorageStrategy",
    "CacheKey",
    "create_redis_config_from_env",
    "create_redis_manager",
]
