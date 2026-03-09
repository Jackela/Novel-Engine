"""PostgreSQL State Store.

PostgreSQL-based implementation of the StateStore interface.
"""

import json
from typing import Any, List, Optional

import structlog

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateKey, StateStoreConfig

# Import asyncpg if available
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

logger = structlog.get_logger(__name__)


class PostgreSQLStateStore(StateStore):
    """PostgreSQL-based state store for persistent data."""

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize PostgreSQL state store.

        Args:
            config: State store configuration
        """
        self.config = config
        self.pool: Optional[Any] = None
        self._connected = False

        if not ASYNCPG_AVAILABLE:
            logger.warning("asyncpg_not_available")

    async def connect(self) -> None:
        """Initialize PostgreSQL connection pool."""
        if self._connected or not ASYNCPG_AVAILABLE:
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.config.postgres_url,
                min_size=5,
                max_size=20,
                command_timeout=self.config.connection_timeout,
                server_settings={"jit": "off"},
            )

            # Initialize tables
            await self._initialize_tables()
            self._connected = True
            logger.info("postgresql_connection_pool_established")

        except Exception as e:
            logger.error("postgresql_connection_failed", error=str(e))
            raise

    async def _initialize_tables(self) -> None:
        """Initialize required tables."""
        if not self.pool:
            return

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
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_tables_sql)

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from PostgreSQL.

        Args:
            key: State key to look up

        Returns:
            Stored value or None
        """
        if not self._connected:
            await self.connect()

        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT data FROM state_data WHERE key_hash = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    key.to_string(),
                )

                if row:
                    return row["data"]
                return None

        except Exception as e:
            logger.error("postgres_get_failed", key=key.to_string(), error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in PostgreSQL.

        Args:
            key: State key
            value: Value to store
            ttl: Optional time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        if not self.pool:
            return False

        try:
            # Calculate expiration
            expires_at = None
            if ttl:
                from datetime import datetime, timedelta
                expires_at = datetime.now() + timedelta(seconds=ttl)

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO state_data (key_hash, namespace, entity_type, entity_id, version, data, expires_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (key_hash) DO UPDATE
                    SET data = EXCLUDED.data, updated_at = NOW(), expires_at = EXCLUDED.expires_at
                    """,
                    key.to_string(),
                    key.namespace,
                    key.entity_type,
                    key.entity_id,
                    key.version,
                    json.dumps(value, default=str),
                    expires_at,
                )
                return True

        except Exception as e:
            logger.error("postgres_set_failed", key=key.to_string(), error=str(e))
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from PostgreSQL.

        Args:
            key: State key to delete

        Returns:
            True if deleted
        """
        if not self._connected:
            await self.connect()

        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM state_data WHERE key_hash = $1",
                    key.to_string(),
                )
                return "DELETE 1" in result

        except Exception as e:
            logger.error("postgres_delete_failed", key=key.to_string(), error=str(e))
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in PostgreSQL.

        Args:
            key: State key to check

        Returns:
            True if exists
        """
        if not self._connected:
            await self.connect()

        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchval(
                    "SELECT 1 FROM state_data WHERE key_hash = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    key.to_string(),
                )
                return row is not None

        except Exception as e:
            logger.error("postgres_exists_check_failed", key=key.to_string(), error=str(e))
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match (SQL LIKE pattern)

        Returns:
            List of matching keys
        """
        if not self._connected:
            await self.connect()

        if not self.pool:
            return []

        try:
            # Convert Redis-style pattern to SQL LIKE
            sql_pattern = pattern.replace("*", "%")

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT key_hash FROM state_data WHERE key_hash LIKE $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    sql_pattern,
                )
                return [StateKey.from_string(row["key_hash"]) for row in rows]

        except Exception as e:
            logger.error("postgres_list_keys_failed", pattern=pattern, error=str(e))
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

        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                # Use PostgreSQL's atomic increment
                row = await conn.fetchrow(
                    """
                    INSERT INTO state_data (key_hash, namespace, entity_type, entity_id, version, data)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (key_hash) DO UPDATE
                    SET data = (COALESCE(state_data.data::text::int, 0) + $6)::text::jsonb,
                        updated_at = NOW()
                    RETURNING data
                    """,
                    key.to_string(),
                    key.namespace,
                    key.entity_type,
                    key.entity_id,
                    key.version,
                    str(amount),
                )
                return int(row["data"]) if row else None

        except Exception as e:
            logger.error("postgres_increment_failed", key=key.to_string(), error=str(e))
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

        if not self.pool:
            return False

        try:
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(seconds=ttl)

            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE state_data SET expires_at = $1, updated_at = NOW() WHERE key_hash = $2",
                    expires_at,
                    key.to_string(),
                )
                return "UPDATE 1" in result

        except Exception as e:
            logger.error("postgres_expire_failed", key=key.to_string(), error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check PostgreSQL health.

        Returns:
            True if healthy
        """
        try:
            if not self._connected:
                await self.connect()

            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True

        except Exception as e:
            logger.error("postgres_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("postgresql_connection_pool_closed")
