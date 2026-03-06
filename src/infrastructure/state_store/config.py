"""State Store Configuration.

Configuration classes and key management for state stores.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StateStoreType(Enum):
    """Types of state store backends."""

    REDIS = "redis"
    POSTGRES = "postgres"
    POSTGRESQL = "postgresql"
    S3 = "s3"
    MEMORY = "memory"


@dataclass
class StateKey:
    """Structured key for state storage.

    Provides a consistent naming convention for state keys
    across different storage backends.
    """

    namespace: str
    entity_type: str
    entity_id: str
    version: Optional[str] = None

    def to_string(self) -> str:
        """Convert key to string representation.

        Returns:
            Colon-separated key string
        """
        parts = [self.namespace, self.entity_type, self.entity_id]
        if self.version:
            parts.append(self.version)
        return ":".join(parts)

    @classmethod
    def from_string(cls, key_str: str) -> "StateKey":
        """Parse key from string representation.

        Args:
            key_str: Colon-separated key string

        Returns:
            StateKey instance
        """
        parts = key_str.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid key format: {key_str}")

        return cls(
            namespace=parts[0],
            entity_type=parts[1],
            entity_id=parts[2],
            version=parts[3] if len(parts) > 3 else None,
        )

    def __hash__(self) -> int:
        """Hash based on string representation."""
        return hash(self.to_string())

    def __eq__(self, other: object) -> bool:
        """Equality based on string representation."""
        if not isinstance(other, StateKey):
            return False
        return self.to_string() == other.to_string()


@dataclass
class StateStoreConfig:
    """Configuration for state store connections.

    Contains all necessary configuration for connecting to
    Redis, PostgreSQL, and S3 backends.
    """

    # Store type selection
    store_type: StateStoreType = StateStoreType.REDIS
    default_store: StateStoreType = StateStoreType.REDIS

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None

    # PostgreSQL configuration
    postgres_url: str = "postgresql://user:pass@localhost/db"
    connection_string: str = "postgresql://user:pass@localhost/db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "user"
    postgres_password: str = "password"
    postgres_database: str = "novel_engine"

    # S3 configuration
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    s3_bucket: str = "novel-engine-state"
    s3_region: str = "us-east-1"
    s3_endpoint: Optional[str] = None

    # Connection settings
    connection_timeout: int = 30
    cache_ttl: int = 3600  # 1 hour default
    max_retries: int = 3

    # Cache settings
    max_cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour default

    # Feature flags
    enable_caching: bool = True
    enable_compression: bool = True
    enable_encryption: bool = False

    @classmethod
    def from_env(cls) -> "StateStoreConfig":
        """Create configuration from environment variables.

        Returns:
            StateStoreConfig with values from environment
        """
        import os

        return cls(
            default_store=StateStoreType(
                os.getenv("STATE_STORE_TYPE", "redis")
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            redis_password=os.getenv("REDIS_PASSWORD"),
            postgres_url=os.getenv(
                "DATABASE_URL",
                "postgresql://user:pass@localhost/db"
            ),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", "user"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "password"),
            postgres_database=os.getenv("POSTGRES_DB", "novel_engine"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            s3_bucket=os.getenv("S3_BUCKET", "novel-engine-state"),
            s3_region=os.getenv("AWS_REGION", "us-east-1"),
            s3_endpoint=os.getenv("S3_ENDPOINT"),
            connection_timeout=int(os.getenv("STATE_STORE_TIMEOUT", "30")),
            cache_ttl=int(os.getenv("STATE_STORE_CACHE_TTL", "3600")),
            enable_caching=os.getenv("STATE_STORE_ENABLE_CACHE", "true").lower() == "true",
            enable_encryption=os.getenv("STATE_STORE_ENABLE_ENCRYPTION", "false").lower() == "true",
        )
