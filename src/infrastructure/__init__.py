#!/usr/bin/env python3
"""
Enterprise Infrastructure Package
==================================

Comprehensive enterprise infrastructure components for the Novel Engine framework
including PostgreSQL, Redis, S3, and unified storage management.
"""

from .enterprise_storage_manager import (
    DataCategory,
    EnterpriseStorageConfig,
    EnterpriseStorageManager,
    StorageBackend,
    StoragePolicy,
    create_enterprise_config_from_env,
    create_enterprise_storage_manager,
)
from .postgresql_manager import (
    PostgreSQLConfig,
    PostgreSQLConnectionPool,
    PostgreSQLFeature,
    PostgreSQLManager,
    create_postgresql_config_from_env,
    create_postgresql_manager,
)
from .redis_manager import (
    CacheKey,
    RedisConfig,
    RedisConnectionPool,
    RedisDataType,
    RedisManager,
    RedisStorageStrategy,
    create_redis_config_from_env,
    create_redis_manager,
)
from .s3_manager import (
    S3Config,
    S3ContentType,
    S3ObjectInfo,
    S3StorageClass,
    S3StorageManager,
    UploadProgress,
    create_s3_config_from_env,
    create_s3_manager,
)

__all__ = [
    # PostgreSQL
    "PostgreSQLManager",
    "PostgreSQLConfig",
    "PostgreSQLConnectionPool",
    "PostgreSQLFeature",
    "create_postgresql_config_from_env",
    "create_postgresql_manager",
    # Redis
    "RedisManager",
    "RedisConfig",
    "RedisConnectionPool",
    "RedisDataType",
    "RedisStorageStrategy",
    "CacheKey",
    "create_redis_config_from_env",
    "create_redis_manager",
    # S3
    "S3StorageManager",
    "S3Config",
    "S3StorageClass",
    "S3ContentType",
    "S3ObjectInfo",
    "UploadProgress",
    "create_s3_config_from_env",
    "create_s3_manager",
    # Enterprise Storage
    "EnterpriseStorageManager",
    "EnterpriseStorageConfig",
    "StorageBackend",
    "DataCategory",
    "StoragePolicy",
    "create_enterprise_config_from_env",
    "create_enterprise_storage_manager",
]
