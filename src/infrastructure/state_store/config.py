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
import structlog
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
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class StateStoreConfig(BaseModel):
    """State store configuration"""

    redis_url: str = Field(
        default="", description="Redis connection URL (set via REDIS_URL env var)"
    )
    postgres_url: str = Field(
        default="",
        description="PostgreSQL connection URL (set via POSTGRES_URL env var)",
    )
    s3_bucket: str = "novel-engine-storage"
    s3_region: str = "us-east-1"
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    encryption_key: Optional[str] = None
    cache_ttl: int = 3600  # 1 hour
    max_retries: int = 3
    connection_timeout: int = 30

    def __init__(self, **data) -> None:
        # Allow environment variable overrides for sensitive values
        if not data.get("redis_url"):
            data["redis_url"] = os.getenv("REDIS_URL", "")
        if not data.get("postgres_url"):
            data["postgres_url"] = os.getenv("POSTGRES_URL", "")
        super().__init__(**data)


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

    @abstractmethod
    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value with key"""

    @abstractmethod
    async def delete(self, key: StateKey) -> bool:
        """Delete value by key"""

    @abstractmethod
    async def exists(self, key: StateKey) -> bool:
        """Check if key exists"""

    @abstractmethod
    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check store health"""

    @abstractmethod
    async def close(self) -> None:
        """Close connections"""


