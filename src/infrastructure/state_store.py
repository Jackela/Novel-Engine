#!/usr/bin/env python3
"""
State Store Infrastructure
========================

Milestone 3 Implementation: Redis/Postgres/S3 State Externalization

核心设计：
- Redis: 快速访问的会话状态和缓存
- PostgreSQL: 持久化的结构化数据存储
- S3: 大文件存储（叙事文档、媒体文件）
- 统一配置管理和环境感知部署

Features:
- StateStore抽象层: 统一的状态管理接口
- RedisStateStore: 高性能会话数据存储
- PostgreSQLStateStore: 关系型数据持久化
- S3StateStore: 大文件和叙事文档存储
- ConfigurationManager: 统一配置管理
"""

import hashlib
import json
import logging
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
import boto3

# External dependencies
import redis.asyncio as aioredis
import yaml
from botocore.exceptions import ClientError
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class StateStoreConfig(BaseModel):
    """State store configuration"""

    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = "postgresql://user:pass@localhost:5432/novelengine"
    s3_bucket: str = "novel-engine-storage"
    s3_region: str = "us-east-1"
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    encryption_key: Optional[str] = None
    cache_ttl: int = 3600  # 1 hour
    max_retries: int = 3
    connection_timeout: int = 30


@dataclass
class StateKey:
    """State key structure"""

    namespace: str
    entity_type: str
    entity_id: str
    version: Optional[str] = None

    def to_string(self) -> str:
        """Convert to string key"""
        parts = [self.namespace, self.entity_type, self.entity_id]
        if self.version:
            parts.append(self.version)
        return ":".join(parts)

    @classmethod
    def from_string(cls, key: str) -> "StateKey":
        """Create from string key"""
        parts = key.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid state key format: {key}")

        return cls(
            namespace=parts[0],
            entity_type=parts[1],
            entity_id=parts[2],
            version=parts[3] if len(parts) > 3 else None,
        )


class StateStore(ABC):
    """Abstract state store interface"""

    @abstractmethod
    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value by key"""
        pass

    @abstractmethod
    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Store value with key"""
        pass

    @abstractmethod
    async def delete(self, key: StateKey) -> bool:
        """Delete value by key"""
        pass

    @abstractmethod
    async def exists(self, key: StateKey) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check store health"""
        pass

    @abstractmethod
    async def close(self):
        """Close connections"""
        pass


class RedisStateStore(StateStore):
    """Redis-based state store for fast access"""

    def __init__(self, config: StateStoreConfig):
        self.config = config
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self):
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
            logger.info("Redis connection established")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
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
                    return pickle.loads(raw_value)
                except Exception:
                    # Return as string if deserialization fails
                    return (
                        raw_value.decode("utf-8")
                        if isinstance(raw_value, bytes)
                        else raw_value
                    )

        except Exception as e:
            logger.error(f"Failed to get key {key.to_string()}: {e}")
            return None

    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
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
            logger.error(f"Failed to set key {key.to_string()}: {e}")
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from Redis"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.delete(key.to_string())
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete key {key.to_string()}: {e}")
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in Redis"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.exists(key.to_string())
            return result > 0

        except Exception as e:
            logger.error(
                f"Failed to check existence of key {key.to_string()}: {e}"
            )
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        if not self._connected:
            await self.connect()

        try:
            keys = await self.redis.keys(pattern)
            return [
                StateKey.from_string(
                    key.decode() if isinstance(key, bytes) else key
                )
                for key in keys
            ]

        except Exception as e:
            logger.error(f"Failed to list keys with pattern {pattern}: {e}")
            return []

    async def increment(self, key: StateKey, amount: int = 1) -> Optional[int]:
        """Increment counter value"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.incrby(key.to_string(), amount)
            return result

        except Exception as e:
            logger.error(f"Failed to increment key {key.to_string()}: {e}")
            return None

    async def expire(self, key: StateKey, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self._connected:
            await self.connect()

        try:
            result = await self.redis.expire(key.to_string(), ttl)
            return result is True

        except Exception as e:
            logger.error(
                f"Failed to set expire for key {key.to_string()}: {e}"
            )
            return False

    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self._connected:
                await self.connect()

            await self.redis.ping()
            return True

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis connection closed")


class PostgreSQLStateStore(StateStore):
    """PostgreSQL-based state store for persistent data"""

    def __init__(self, config: StateStoreConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False

    async def connect(self):
        """Initialize PostgreSQL connection pool"""
        if self._connected:
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.config.postgres_url,
                min_size=5,
                max_size=20,
                command_timeout=self.config.connection_timeout,
                # Disable JIT for better predictability
                server_settings={"jit": "off"},
            )

            # Initialize tables
            await self._initialize_tables()
            self._connected = True
            logger.info("PostgreSQL connection pool established")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def _initialize_tables(self):
        """Initialize required tables"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS state_data (
            key_hash VARCHAR(64) PRIMARY KEY,
            namespace VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            entity_id VARCHAR(100) NOT NULL,
            version VARCHAR(50),
            data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE
        );

        CREATE INDEX IF NOT EXISTS idx_state_data_namespace ON state_data(namespace);
        CREATE INDEX IF NOT EXISTS idx_state_data_entity ON state_data(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_state_data_created ON state_data(created_at);
        CREATE INDEX IF NOT EXISTS idx_state_data_expires ON state_data(expires_at) WHERE expires_at IS NOT NULL;

        CREATE TABLE IF NOT EXISTS state_metadata (
            key_hash VARCHAR(64) PRIMARY KEY,
            metadata JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (key_hash) REFERENCES state_data(key_hash) ON DELETE CASCADE
        );
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_tables_sql)

    def _hash_key(self, key: StateKey) -> str:
        """Generate hash for state key"""
        key_str = key.to_string()
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from PostgreSQL"""
        if not self._connected:
            await self.connect()

        key_hash = self._hash_key(key)

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT data FROM state_data WHERE key_hash = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    key_hash,
                )

                if row:
                    return row["data"]
                return None

        except Exception as e:
            logger.error(f"Failed to get key {key.to_string()}: {e}")
            return None

    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Store value in PostgreSQL"""
        if not self._connected:
            await self.connect()

        key_hash = self._hash_key(key)
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl else None

        # Ensure value is JSON serializable
        try:
            if not isinstance(
                value, (dict, list, str, int, float, bool, type(None))
            ):
                # Convert complex objects to dict if possible
                if hasattr(value, "__dict__"):
                    value = value.__dict__
                elif hasattr(value, "_asdict"):  # namedtuple
                    value = value._asdict()
                else:
                    value = str(value)
        except Exception:
            value = str(value)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO state_data (key_hash, namespace, entity_type, entity_id, version, data, expires_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (key_hash)
                    DO UPDATE SET
                        data = EXCLUDED.data,
                        updated_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                    """,
                    key_hash,
                    key.namespace,
                    key.entity_type,
                    key.entity_id,
                    key.version,
                    value,
                    expires_at,
                )
                return True

        except Exception as e:
            logger.error(f"Failed to set key {key.to_string()}: {e}")
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from PostgreSQL"""
        if not self._connected:
            await self.connect()

        key_hash = self._hash_key(key)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM state_data WHERE key_hash = $1", key_hash
                )
                # Check if any rows were affected
                return result.split()[-1] != "0"

        except Exception as e:
            logger.error(f"Failed to delete key {key.to_string()}: {e}")
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in PostgreSQL"""
        if not self._connected:
            await self.connect()

        key_hash = self._hash_key(key)

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM state_data WHERE key_hash = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    key_hash,
                )
                return row is not None

        except Exception as e:
            logger.error(
                f"Failed to check existence of key {key.to_string()}: {e}"
            )
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        if not self._connected:
            await self.connect()

        # Convert Redis-style pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%").replace("?", "_")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT namespace, entity_type, entity_id, version
                    FROM state_data
                    WHERE CONCAT(namespace, ':', entity_type, ':', entity_id, COALESCE(':', version, '')) LIKE $1
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC
                    """,
                    sql_pattern,
                )

                return [
                    StateKey(
                        namespace=row["namespace"],
                        entity_type=row["entity_type"],
                        entity_id=row["entity_id"],
                        version=row["version"],
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to list keys with pattern {pattern}: {e}")
            return []

    async def query_by_namespace(
        self, namespace: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query data by namespace"""
        if not self._connected:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT namespace, entity_type, entity_id, version, data, created_at, updated_at
                    FROM state_data
                    WHERE namespace = $1
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    namespace,
                    limit,
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to query namespace {namespace}: {e}")
            return []

    async def cleanup_expired(self) -> int:
        """Clean up expired entries"""
        if not self._connected:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM state_data WHERE expires_at IS NOT NULL AND expires_at <= NOW()"
                )
                deleted_count = int(result.split()[-1])
                logger.info(f"Cleaned up {deleted_count} expired entries")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0

    async def health_check(self) -> bool:
        """Check PostgreSQL health"""
        try:
            if not self._connected:
                await self.connect()

            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    async def close(self):
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("PostgreSQL connection pool closed")


class S3StateStore(StateStore):
    """S3-based state store for large files and documents"""

    def __init__(self, config: StateStoreConfig):
        self.config = config
        self.s3_client = None
        self._connected = False

    async def connect(self):
        """Initialize S3 client"""
        if self._connected:
            return

        try:
            session = boto3.Session(
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
                region_name=self.config.s3_region,
            )

            self.s3_client = session.client("s3")

            # Test connection and create bucket if not exists
            try:
                await self._ensure_bucket_exists()
                self._connected = True
                logger.info("S3 connection established")
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoCredentialsError":
                    logger.warning(
                        "S3 credentials not configured, S3 storage disabled"
                    )
                    self._connected = False
                else:
                    raise

        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise

    async def _ensure_bucket_exists(self):
        """Ensure S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Create bucket
                try:
                    if self.config.s3_region == "us-east-1":
                        self.s3_client.create_bucket(
                            Bucket=self.config.s3_bucket
                        )
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.config.s3_bucket,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.config.s3_region
                            },
                        )
                    logger.info(f"Created S3 bucket: {self.config.s3_bucket}")
                except Exception as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise
            else:
                raise

    def _key_to_s3_key(self, key: StateKey) -> str:
        """Convert StateKey to S3 object key"""
        parts = [key.namespace, key.entity_type, key.entity_id]
        if key.version:
            parts.append(key.version)
        return "/".join(parts)

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return None

        s3_key = self._key_to_s3_key(key)

        try:
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket, Key=s3_key
            )

            content = response["Body"].read()

            # Try to deserialize based on content type
            content_type = response.get(
                "ContentType", "application/octet-stream"
            )

            if content_type == "application/json":
                return json.loads(content.decode("utf-8"))
            elif content_type.startswith("text/"):
                return content.decode("utf-8")
            else:
                return content

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                logger.error(f"Failed to get S3 object {s3_key}: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to get S3 object {s3_key}: {e}")
            return None

    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Store value in S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            # Prepare content and metadata
            if isinstance(value, str):
                content = value.encode("utf-8")
                content_type = "text/plain"
            elif isinstance(value, (dict, list)):
                content = json.dumps(value, default=str).encode("utf-8")
                content_type = "application/json"
            elif isinstance(value, bytes):
                content = value
                content_type = "application/octet-stream"
            else:
                # Serialize as JSON
                content = json.dumps(value, default=str).encode("utf-8")
                content_type = "application/json"

            # Prepare metadata
            metadata = {
                "namespace": key.namespace,
                "entity-type": key.entity_type,
                "entity-id": key.entity_id,
                "created-at": datetime.now().isoformat(),
            }

            if key.version:
                metadata["version"] = key.version

            # Set expiration if TTL provided
            extra_args = {"ContentType": content_type, "Metadata": metadata}

            if ttl:
                expires = datetime.now() + timedelta(seconds=ttl)
                extra_args["Expires"] = expires

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=content,
                **extra_args,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to set S3 object {s3_key}: {e}")
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            self.s3_client.delete_object(
                Bucket=self.config.s3_bucket, Key=s3_key
            )
            return True

        except Exception as e:
            logger.error(f"Failed to delete S3 object {s3_key}: {e}")
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            self.s3_client.head_object(
                Bucket=self.config.s3_bucket, Key=s3_key
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error(
                    f"Failed to check S3 object existence {s3_key}: {e}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to check S3 object existence {s3_key}: {e}")
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return []

        # Convert pattern to S3 prefix
        prefix = pattern.replace("*", "").replace(":", "/")
        if prefix.endswith("/"):
            prefix = prefix[:-1]

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket, Prefix=prefix, MaxKeys=1000
            )

            keys = []
            for obj in response.get("Contents", []):
                s3_key = obj["Key"]
                try:
                    # Convert S3 key back to StateKey
                    parts = s3_key.split("/")
                    if len(parts) >= 3:
                        state_key = StateKey(
                            namespace=parts[0],
                            entity_type=parts[1],
                            entity_id=parts[2],
                            version=parts[3] if len(parts) > 3 else None,
                        )
                        keys.append(state_key)
                except Exception:
                    continue

            return keys

        except Exception as e:
            logger.error(f"Failed to list S3 keys with prefix {prefix}: {e}")
            return []

    async def health_check(self) -> bool:
        """Check S3 health"""
        if not self._connected:
            await self.connect()

        try:
            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
            return True

        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False

    async def close(self):
        """Close S3 client"""
        # S3 client doesn't need explicit closing
        self._connected = False
        logger.info("S3 client closed")


class UnifiedStateManager:
    """Unified state manager that routes to appropriate stores"""

    def __init__(self, config: StateStoreConfig):
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

    async def initialize(self):
        """Initialize all stores"""
        try:
            await self.redis_store.connect()
            await self.postgres_store.connect()
            await self.s3_store.connect()
            logger.info("Unified state manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize state manager: {e}")
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

    async def get(
        self, key: StateKey, use_cache: bool = True
    ) -> Optional[Any]:
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
            # 5 minute cache
            await self.redis_store.set(cache_key, value, ttl=300)

        return value

    async def set(
        self, key: StateKey, value: Any, ttl: Optional[int] = None
    ) -> bool:
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
            all_keys = []
            for store in [
                self.redis_store,
                self.postgres_store,
                self.s3_store,
            ]:
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

    async def cleanup_expired(self):
        """Cleanup expired data from all stores"""
        await self.postgres_store.cleanup_expired()
        # Redis handles expiration automatically
        # S3 expiration is handled by lifecycle policies

    async def close(self):
        """Close all store connections"""
        await self.redis_store.close()
        await self.postgres_store.close()
        await self.s3_store.close()
        logger.info("Unified state manager closed")


class ConfigurationManager:
    """Unified configuration manager"""

    def __init__(self, config_paths: List[str] = None):
        self.config_paths = config_paths or [
            "/etc/novel-engine/configs/environments/development.yaml",
            "./configs/environments/development.yaml",
            "./configs/environments/environments.yaml",
        ]
        self.config_data: Dict[str, Any] = {}
        self.environment = os.getenv("ENVIRONMENT", "development")

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from files and environment"""

        # Start with default configuration
        self.config_data = self._get_default_config()

        # Load from config files
        for config_path in self.config_paths:
            if Path(config_path).exists():
                try:
                    with open(config_path, "r") as f:
                        file_config = yaml.safe_load(f)
                        if file_config:
                            self._merge_config(self.config_data, file_config)
                            logger.info(
                                f"Loaded configuration from {config_path}"
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to load config from {config_path}: {e}"
                    )

        # Apply environment-specific overrides
        env_config = self.config_data.get("environments", {}).get(
            self.environment, {}
        )
        if env_config:
            self._merge_config(self.config_data, env_config)

        # Override with environment variables
        self._apply_env_overrides()

        return self.config_data

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "state_store": {
                "redis_url": "redis://localhost:6379/0",
                "postgres_url": "postgresql://postgres:password@localhost:5432/novelengine",
                "s3_bucket": "novel-engine-storage",
                "s3_region": "us-east-1",
                "cache_ttl": 3600,
                "max_retries": 3,
                "connection_timeout": 30,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "api": {"host": "0.0.0.0", "port": 8000, "workers": 4},
            "security": {
                "encryption_key": None,
                "jwt_secret": None,
                "cors_origins": ["http://localhost:3000"],
            },
        }

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Merge configuration dictionaries"""
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            "REDIS_URL": ["state_store", "redis_url"],
            "POSTGRES_URL": ["state_store", "postgres_url"],
            "S3_BUCKET": ["state_store", "s3_bucket"],
            "S3_REGION": ["state_store", "s3_region"],
            "AWS_ACCESS_KEY_ID": ["state_store", "aws_access_key"],
            "AWS_SECRET_ACCESS_KEY": ["state_store", "aws_secret_key"],
            "ENCRYPTION_KEY": ["security", "encryption_key"],
            "JWT_SECRET": ["security", "jwt_secret"],
            "API_HOST": ["api", "host"],
            "API_PORT": ["api", "port"],
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Navigate to the nested config key
                current = self.config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Set the value, converting to appropriate type
                final_key = config_path[-1]
                if final_key in [
                    "port",
                    "workers",
                    "cache_ttl",
                    "max_retries",
                    "connection_timeout",
                ]:
                    current[final_key] = int(env_value)
                elif env_value.lower() in ["true", "false"]:
                    current[final_key] = env_value.lower() == "true"
                else:
                    current[final_key] = env_value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = key_path.split(".")
        current = self.config_data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def get_state_store_config(self) -> StateStoreConfig:
        """Get state store configuration"""
        state_config = self.config_data.get("state_store", {})
        return StateStoreConfig(**state_config)


# Factory functions
def create_unified_state_manager(
    config: Optional[StateStoreConfig] = None,
) -> UnifiedStateManager:
    """Create unified state manager"""
    if config is None:
        config_manager = ConfigurationManager()
        config_manager.load_configuration()
        config = config_manager.get_state_store_config()

    return UnifiedStateManager(config)


def create_configuration_manager(
    config_paths: List[str] = None,
) -> ConfigurationManager:
    """Create configuration manager"""
    return ConfigurationManager(config_paths)


if __name__ == "__main__":
    # Example usage
    async def example_usage():
        # Load configuration
        config_manager = create_configuration_manager()
        config_manager.load_configuration()

        # Create state manager
        state_manager = create_unified_state_manager()
        await state_manager.initialize()

        # Test different data types
        # Session data (Redis)
        session_key = StateKey("game_session", "session", "player_123")
        await state_manager.set(
            session_key, {"player_id": "123", "current_location": "forest"}
        )

        # Agent state (PostgreSQL)
        agent_key = StateKey("simulation", "agent", "alice")
        await state_manager.set(
            agent_key, {"name": "Alice", "personality": {"curiosity": 0.8}}
        )

        # Narrative document (S3)
        narrative_key = StateKey("story", "narrative", "chapter_1")
        await state_manager.set(
            narrative_key, "In the beginning, there was a mysterious forest..."
        )

        # Retrieve data
        session_data = await state_manager.get(session_key)
        agent_data = await state_manager.get(agent_key)
        narrative_data = await state_manager.get(narrative_key)

        print(f"Session: {session_data}")
        print(f"Agent: {agent_data}")
        print(f"Narrative: {narrative_data}")

        # Health check
        health = await state_manager.health_check()
        print(f"Health: {health}")

        # Cleanup
        await state_manager.close()

    # Run example
    # asyncio.run(example_usage())
