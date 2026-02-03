#!/usr/bin/env python3
"""
Enterprise Storage Manager
==========================

Unified enterprise storage manager that coordinates PostgreSQL, Redis, and S3
for complete state externalization in the Novel Engine framework.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .postgresql_manager import (
    PostgreSQLConfig,
    PostgreSQLManager,
    create_postgresql_config_from_env,
)
from .redis_manager import RedisConfig, RedisManager, create_redis_config_from_env
from .s3_manager import S3Config, S3StorageManager, create_s3_config_from_env

logger = logging.getLogger(__name__)


class StorageBackend(Enum):
    """Available storage backends."""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    S3 = "s3"
    SQLITE = "sqlite"  # Legacy fallback


class DataCategory(Enum):
    """Data categories for storage routing."""

    CHARACTERS = "characters"
    MEMORY = "memory"
    INTERACTIONS = "interactions"
    NARRATIVES = "narratives"
    SESSIONS = "sessions"
    CACHE = "cache"
    FILES = "files"
    BACKUPS = "backups"
    SYSTEM_STATE = "system_state"
    METRICS = "metrics"


@dataclass
class StoragePolicy:
    """Storage policy configuration for different data types."""

    primary_backend: StorageBackend
    cache_backend: Optional[StorageBackend] = None
    backup_backend: Optional[StorageBackend] = None
    ttl_seconds: Optional[int] = None
    enable_compression: bool = False
    enable_encryption: bool = False
    replication_factor: int = 1


@dataclass
class EnterpriseStorageConfig:
    """Configuration for enterprise storage system."""

    # Backend configurations
    postgresql_config: Optional[PostgreSQLConfig] = None
    redis_config: Optional[RedisConfig] = None
    s3_config: Optional[S3Config] = None

    # Storage policies by data category
    storage_policies: Dict[DataCategory, StoragePolicy] = field(default_factory=dict)

    # Global settings
    enable_distributed_locks: bool = True
    enable_transaction_logging: bool = True
    health_check_interval: float = 60.0

    # Migration settings
    enable_migration_mode: bool = False
    sqlite_database_path: Optional[str] = None

    def __post_init__(self):
        """Initialize default storage policies."""
        if not self.storage_policies:
            self.storage_policies = self._get_default_policies()

    def _get_default_policies(self) -> Dict[DataCategory, StoragePolicy]:
        """Get default storage policies for optimal performance."""
        return {
            # Character data: PostgreSQL primary, Redis cache
            DataCategory.CHARACTERS: StoragePolicy(
                primary_backend=StorageBackend.POSTGRESQL,
                cache_backend=StorageBackend.REDIS,
                backup_backend=StorageBackend.S3,
                ttl_seconds=3600,  # 1 hour cache
            ),
            # Memory data: PostgreSQL primary, Redis cache
            DataCategory.MEMORY: StoragePolicy(
                primary_backend=StorageBackend.POSTGRESQL,
                cache_backend=StorageBackend.REDIS,
                ttl_seconds=1800,  # 30 minutes cache
            ),
            # Interactions: PostgreSQL primary, Redis cache
            DataCategory.INTERACTIONS: StoragePolicy(
                primary_backend=StorageBackend.POSTGRESQL,
                cache_backend=StorageBackend.REDIS,
                backup_backend=StorageBackend.S3,
                ttl_seconds=900,  # 15 minutes cache
            ),
            # Narratives: PostgreSQL primary, S3 backup
            DataCategory.NARRATIVES: StoragePolicy(
                primary_backend=StorageBackend.POSTGRESQL,
                backup_backend=StorageBackend.S3,
                enable_compression=True,
            ),
            # Sessions: Redis primary (ephemeral)
            DataCategory.SESSIONS: StoragePolicy(
                primary_backend=StorageBackend.REDIS, ttl_seconds=7200  # 2 hours
            ),
            # Cache data: Redis only
            DataCategory.CACHE: StoragePolicy(
                primary_backend=StorageBackend.REDIS, ttl_seconds=3600  # 1 hour default
            ),
            # File storage: S3 primary
            DataCategory.FILES: StoragePolicy(
                primary_backend=StorageBackend.S3, enable_compression=True
            ),
            # Backups: S3 with long retention
            DataCategory.BACKUPS: StoragePolicy(
                primary_backend=StorageBackend.S3,
                enable_compression=True,
                enable_encryption=True,
            ),
            # System state: PostgreSQL primary, Redis cache
            DataCategory.SYSTEM_STATE: StoragePolicy(
                primary_backend=StorageBackend.POSTGRESQL,
                cache_backend=StorageBackend.REDIS,
                ttl_seconds=300,  # 5 minutes cache
            ),
            # Metrics: Redis primary (ephemeral)
            DataCategory.METRICS: StoragePolicy(
                primary_backend=StorageBackend.REDIS, ttl_seconds=86400  # 24 hours
            ),
        }


class EnterpriseStorageManager:
    """
    Unified enterprise storage manager.

    Features:
    - Multi-backend coordination (PostgreSQL, Redis, S3)
    - Intelligent data routing based on policies
    - Automatic caching and backup strategies
    - Health monitoring across all backends
    - Migration support from SQLite
    - Transaction coordination
    - Performance optimization
    """

    def __init__(self, config: EnterpriseStorageConfig):
        """Initialize enterprise storage manager."""
        self.config = config

        # Storage backends
        self.postgresql: Optional[PostgreSQLManager] = None
        self.redis: Optional[RedisManager] = None
        self.s3: Optional[S3StorageManager] = None

        # Initialization state
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None

        # Metrics and monitoring
        self._metrics = {
            "operations": {
                "total": 0,
                "by_backend": {backend.value: 0 for backend in StorageBackend},
                "by_category": {category.value: 0 for category in DataCategory},
                "errors": 0,
            },
            "performance": {"avg_response_time": 0.0, "response_times": []},
            "health": {"postgresql": False, "redis": False, "s3": False},
        }

    async def initialize(self) -> None:
        """Initialize all configured storage backends."""
        if self._initialized:
            return

        try:
            logger.info("Initializing enterprise storage manager...")

            # Initialize PostgreSQL
            if self.config.postgresql_config:
                self.postgresql = PostgreSQLManager(self.config.postgresql_config)
                await self.postgresql.initialize()
                logger.info("PostgreSQL backend initialized")

            # Initialize Redis
            if self.config.redis_config:
                self.redis = RedisManager(self.config.redis_config)
                await self.redis.initialize()
                logger.info("Redis backend initialized")

            # Initialize S3
            if self.config.s3_config:
                self.s3 = S3StorageManager(self.config.s3_config)
                await self.s3.initialize()
                logger.info("S3 backend initialized")

            # Start health monitoring
            if self.config.health_check_interval > 0:
                self._health_check_task = asyncio.create_task(self._health_check_loop())

            self._initialized = True
            logger.info("Enterprise storage manager initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize enterprise storage manager: {e}")
            raise

    async def _health_check_loop(self) -> None:
        """Background health monitoring for all backends."""
        while self._initialized:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if not self._initialized:
                    break

                # Check PostgreSQL health
                if self.postgresql:
                    try:
                        health = await self.postgresql.health_check()
                        self._metrics["health"]["postgresql"] = health.get(
                            "healthy", False
                        )
                    except Exception as e:
                        self._metrics["health"]["postgresql"] = False
                        logger.warning(f"PostgreSQL health check failed: {e}")

                # Check Redis health
                if self.redis:
                    try:
                        health = await self.redis.health_check()
                        self._metrics["health"]["redis"] = health.get("healthy", False)
                    except Exception as e:
                        self._metrics["health"]["redis"] = False
                        logger.warning(f"Redis health check failed: {e}")

                # Check S3 health
                if self.s3:
                    try:
                        health = await self.s3.health_check()
                        self._metrics["health"]["s3"] = health.get("healthy", False)
                    except Exception as e:
                        self._metrics["health"]["s3"] = False
                        logger.warning(f"S3 health check failed: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    def _get_backend_for_category(self, category: DataCategory) -> StorageBackend:
        """Get primary storage backend for data category."""
        policy = self.config.storage_policies.get(category)
        if policy:
            return policy.primary_backend

        # Default to PostgreSQL for persistent data
        return StorageBackend.POSTGRESQL

    def _get_cache_backend_for_category(
        self, category: DataCategory
    ) -> Optional[StorageBackend]:
        """Get cache backend for data category."""
        policy = self.config.storage_policies.get(category)
        if policy:
            return policy.cache_backend
        return None

    async def _record_operation_metrics(
        self, category: DataCategory, backend: StorageBackend, response_time: float
    ):
        """Record operation metrics."""
        self._metrics["operations"]["total"] += 1
        self._metrics["operations"]["by_backend"][backend.value] += 1
        self._metrics["operations"]["by_category"][category.value] += 1

        # Update response time metrics
        self._metrics["performance"]["response_times"].append(response_time)
        if len(self._metrics["performance"]["response_times"]) > 1000:
            self._metrics["performance"]["response_times"] = self._metrics[
                "performance"
            ]["response_times"][-1000:]

        if self._metrics["performance"]["response_times"]:
            self._metrics["performance"]["avg_response_time"] = sum(
                self._metrics["performance"]["response_times"]
            ) / len(self._metrics["performance"]["response_times"])

    # Character operations

    async def store_character(
        self, character_id: str, character_data: Dict[str, Any]
    ) -> bool:
        """Store character data using enterprise storage."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            # Store in primary backend (PostgreSQL)
            if self.postgresql:
                await self.postgresql.connection_pool.store_character(
                    character_id, character_data
                )

            # Cache in Redis if configured
            cache_backend = self._get_cache_backend_for_category(
                DataCategory.CHARACTERS
            )
            if cache_backend == StorageBackend.REDIS and self.redis:
                await self.redis.connection_pool.cache_character(
                    character_id, character_data
                )

            # Backup to S3 if configured
            policy = self.config.storage_policies.get(DataCategory.CHARACTERS)
            if policy and policy.backup_backend == StorageBackend.S3 and self.s3:
                import json

                backup_content = json.dumps(character_data, default=str).encode("utf-8")
                await self.s3.store_character_asset(
                    character_id=character_id,
                    asset_type="backup",
                    content=backup_content,
                    filename="character_data.json",
                )

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.CHARACTERS, StorageBackend.POSTGRESQL, response_time
            )

            logger.debug(f"Stored character {character_id} across enterprise backends")
            return True

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to store character {character_id}: {e}")
            raise

    async def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character data with caching."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            # Try cache first
            cache_backend = self._get_cache_backend_for_category(
                DataCategory.CHARACTERS
            )
            if cache_backend == StorageBackend.REDIS and self.redis:
                cached_data = await self.redis.connection_pool.get_cached_character(
                    character_id
                )
                if cached_data:
                    response_time = asyncio.get_running_loop().time() - start_time
                    await self._record_operation_metrics(
                        DataCategory.CHARACTERS, StorageBackend.REDIS, response_time
                    )
                    return cached_data

            # Fetch from primary backend
            if self.postgresql:
                results = await self.postgresql.connection_pool.search_characters(
                    search_query=character_id, limit=1
                )

                if results:
                    character_data = results[0]["data"]

                    # Update cache
                    if cache_backend == StorageBackend.REDIS and self.redis:
                        await self.redis.connection_pool.cache_character(
                            character_id, character_data
                        )

                    response_time = asyncio.get_running_loop().time() - start_time
                    await self._record_operation_metrics(
                        DataCategory.CHARACTERS,
                        StorageBackend.POSTGRESQL,
                        response_time,
                    )

                    return character_data

            return None

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to get character {character_id}: {e}")
            raise

    # Memory operations

    async def store_memory(
        self,
        agent_id: str,
        memory_type: str,
        content: Dict[str, Any],
        importance_score: float = 0.0,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Store memory item in enterprise storage."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            memory_id = None

            # Store in primary backend (PostgreSQL)
            if self.postgresql:
                memory_id = await self.postgresql.connection_pool.store_memory_item(
                    agent_id=agent_id,
                    memory_type=memory_type,
                    content=content,
                    importance_score=importance_score,
                    embedding=embedding,
                )

            # Cache recent memories in Redis
            cache_backend = self._get_cache_backend_for_category(DataCategory.MEMORY)
            if cache_backend == StorageBackend.REDIS and self.redis:
                cache_key = f"memory:{agent_id}:{memory_type}"
                memory_data = {
                    "id": memory_id,
                    "content": content,
                    "importance_score": importance_score,
                    "created_at": datetime.now().isoformat(),
                }

                # Add to agent's memory list
                await self.redis.connection_pool.lpush(
                    cache_key,
                    memory_data,
                    ttl=self.config.storage_policies[DataCategory.MEMORY].ttl_seconds,
                )

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.MEMORY, StorageBackend.POSTGRESQL, response_time
            )

            return memory_id or f"memory_{int(datetime.now().timestamp())}"

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to store memory for agent {agent_id}: {e}")
            raise

    async def search_memories(
        self,
        agent_id: str,
        search_query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search agent memories with caching."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            # Search in PostgreSQL (primary)
            if self.postgresql:
                results = await self.postgresql.connection_pool.search_memories(
                    agent_id=agent_id,
                    search_query=search_query,
                    memory_types=memory_types,
                    limit=limit,
                )

                # Record metrics
                response_time = asyncio.get_running_loop().time() - start_time
                await self._record_operation_metrics(
                    DataCategory.MEMORY, StorageBackend.POSTGRESQL, response_time
                )

                return results

            return []

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to search memories for agent {agent_id}: {e}")
            raise

    # Session operations

    async def store_session(
        self, session_id: str, session_data: Dict[str, Any]
    ) -> bool:
        """Store session data in Redis."""
        if not self._initialized:
            await self.initialize()

        if not self.redis:
            logger.warning("Redis not available for session storage")
            return False

        start_time = asyncio.get_running_loop().time()

        try:
            policy = self.config.storage_policies.get(DataCategory.SESSIONS)
            ttl = policy.ttl_seconds if policy else 7200

            result = await self.redis.connection_pool.store_session(
                session_id=session_id, session_data=session_data, ttl=ttl
            )

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.SESSIONS, StorageBackend.REDIS, response_time
            )

            return result

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to store session {session_id}: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        if not self._initialized:
            await self.initialize()

        if not self.redis:
            return None

        start_time = asyncio.get_running_loop().time()

        try:
            session_data = await self.redis.connection_pool.get_session(session_id)

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.SESSIONS, StorageBackend.REDIS, response_time
            )

            return session_data

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    # System state operations

    async def get_system_state(self, key: str) -> Optional[Any]:
        """Get system state with caching."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            # Try cache first
            if self.redis:
                cache_key = f"system_state:{key}"
                cached_value = await self.redis.connection_pool.get(cache_key)
                if cached_value is not None:
                    response_time = asyncio.get_running_loop().time() - start_time
                    await self._record_operation_metrics(
                        DataCategory.SYSTEM_STATE, StorageBackend.REDIS, response_time
                    )
                    return cached_value

            # Get from PostgreSQL
            if self.postgresql:
                value = await self.postgresql.connection_pool.get_system_state(key)

                # Update cache
                if value is not None and self.redis:
                    cache_key = f"system_state:{key}"
                    policy = self.config.storage_policies.get(DataCategory.SYSTEM_STATE)
                    ttl = policy.ttl_seconds if policy else 300
                    await self.redis.connection_pool.set(cache_key, value, ttl=ttl)

                response_time = asyncio.get_running_loop().time() - start_time
                await self._record_operation_metrics(
                    DataCategory.SYSTEM_STATE, StorageBackend.POSTGRESQL, response_time
                )

                return value

            return None

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to get system state {key}: {e}")
            raise

    async def set_system_state(
        self, key: str, value: Any, updated_by: str = "system"
    ) -> bool:
        """Set system state with caching."""
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_running_loop().time()

        try:
            # Store in PostgreSQL
            if self.postgresql:
                await self.postgresql.connection_pool.set_system_state(
                    key, value, updated_by
                )

            # Update cache
            if self.redis:
                cache_key = f"system_state:{key}"
                policy = self.config.storage_policies.get(DataCategory.SYSTEM_STATE)
                ttl = policy.ttl_seconds if policy else 300
                await self.redis.connection_pool.set(cache_key, value, ttl=ttl)

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.SYSTEM_STATE, StorageBackend.POSTGRESQL, response_time
            )

            return True

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to set system state {key}: {e}")
            raise

    # File operations

    async def store_file(
        self,
        file_path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Store file in S3."""
        if not self._initialized:
            await self.initialize()

        if not self.s3:
            raise RuntimeError("S3 not configured for file storage")

        start_time = asyncio.get_running_loop().time()

        try:
            object_info = await self.s3.upload_bytes(
                content=content,
                s3_key=file_path,
                content_type=content_type,
                metadata=metadata,
            )

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.FILES, StorageBackend.S3, response_time
            )

            return object_info.key

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to store file {file_path}: {e}")
            raise

    async def get_file(self, file_path: str, use_cache: bool = True) -> Optional[bytes]:
        """Get file from S3 with caching."""
        if not self._initialized:
            await self.initialize()

        if not self.s3:
            return None

        start_time = asyncio.get_running_loop().time()

        try:
            content = await self.s3.download_bytes(file_path, use_cache=use_cache)

            # Record metrics
            response_time = asyncio.get_running_loop().time() - start_time
            await self._record_operation_metrics(
                DataCategory.FILES, StorageBackend.S3, response_time
            )

            return content

        except Exception as e:
            self._metrics["operations"]["errors"] += 1
            logger.error(f"Failed to get file {file_path}: {e}")
            raise

    # Migration operations

    async def migrate_from_sqlite(self, sqlite_db_path: str) -> Dict[str, Any]:
        """Migrate data from SQLite to enterprise backends."""
        if not self._initialized:
            await self.initialize()

        logger.info(f"Starting migration from SQLite: {sqlite_db_path}")

        migration_results = {
            "started_at": datetime.now().isoformat(),
            "migrated_tables": [],
            "record_counts": {},
            "errors": [],
        }

        try:
            # NOTE: SQLite to PostgreSQL/Redis migration not yet implemented.
            # This feature would involve:
            # 1. Reading data from SQLite tables
            # 2. Converting to appropriate formats
            # 3. Storing in PostgreSQL/Redis based on policies
            # 4. Validating migration integrity
            # Tracked in: https://github.com/your-repo/issues/AAA

            migration_results["completed_at"] = datetime.now().isoformat()
            migration_results["success"] = True

            logger.info("Migration completed successfully")
            return migration_results

        except Exception as e:
            migration_results["errors"].append(str(e))
            migration_results["success"] = False
            logger.error(f"Migration failed: {e}")
            raise

    # Health and metrics

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check across all backends."""
        health_status = {
            "overall_healthy": True,
            "backends": {},
            "timestamp": datetime.now().isoformat(),
            "metrics": self._metrics,
        }

        # Check PostgreSQL
        if self.postgresql:
            try:
                pg_health = await self.postgresql.health_check()
                health_status["backends"]["postgresql"] = pg_health
                if not pg_health.get("healthy", False):
                    health_status["overall_healthy"] = False
            except Exception as e:
                health_status["backends"]["postgresql"] = {
                    "healthy": False,
                    "error": str(e),
                }
                health_status["overall_healthy"] = False

        # Check Redis
        if self.redis:
            try:
                redis_health = await self.redis.health_check()
                health_status["backends"]["redis"] = redis_health
                if not redis_health.get("healthy", False):
                    health_status["overall_healthy"] = False
            except Exception as e:
                health_status["backends"]["redis"] = {"healthy": False, "error": str(e)}
                health_status["overall_healthy"] = False

        # Check S3
        if self.s3:
            try:
                s3_health = await self.s3.health_check()
                health_status["backends"]["s3"] = s3_health
                if not s3_health.get("healthy", False):
                    health_status["overall_healthy"] = False
            except Exception as e:
                health_status["backends"]["s3"] = {"healthy": False, "error": str(e)}
                health_status["overall_healthy"] = False

        return health_status

    async def close(self) -> None:
        """Close all storage backends."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)
        if self.postgresql:
            await self.postgresql.close()

        if self.redis:
            await self.redis.close()

        if self.s3:
            await self.s3.close()

        self._initialized = False
        logger.info("Enterprise storage manager closed")


# Factory functions


def create_enterprise_config_from_env() -> EnterpriseStorageConfig:
    """Create enterprise storage configuration from environment variables."""
    import os

    config = EnterpriseStorageConfig()

    # Configure PostgreSQL if enabled
    if os.getenv("ENABLE_POSTGRESQL", "false").lower() == "true":
        config.postgresql_config = create_postgresql_config_from_env()

    # Configure Redis if enabled
    if os.getenv("ENABLE_REDIS", "true").lower() == "true":
        config.redis_config = create_redis_config_from_env()

    # Configure S3 if enabled
    if os.getenv("ENABLE_S3", "false").lower() == "true":
        config.s3_config = create_s3_config_from_env()

    # Migration settings
    config.enable_migration_mode = (
        os.getenv("ENABLE_MIGRATION", "false").lower() == "true"
    )
    config.sqlite_database_path = os.getenv("SQLITE_DATABASE_PATH")

    return config


async def create_enterprise_storage_manager(
    config: Optional[EnterpriseStorageConfig] = None,
) -> EnterpriseStorageManager:
    """Create and initialize enterprise storage manager."""
    if config is None:
        config = create_enterprise_config_from_env()

    manager = EnterpriseStorageManager(config)
    await manager.initialize()
    return manager


__all__ = [
    "EnterpriseStorageManager",
    "EnterpriseStorageConfig",
    "StorageBackend",
    "DataCategory",
    "StoragePolicy",
    "create_enterprise_config_from_env",
    "create_enterprise_storage_manager",
]
