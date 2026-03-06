class PostgreSQLStateStore(StateStore):
    """PostgreSQL-based state store for persistent data"""

    def __init__(self, config: StateStoreConfig) -> None:
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False

    async def connect(self) -> None:
        """Initialize PostgreSQL connection pool"""
        if self._connected:
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.config.postgres_url,
                min_size=5,
                max_size=20,
                command_timeout=self.config.connection_timeout,
                server_settings={"jit": "off"},  # Disable JIT for better predictability
            )

            # Initialize tables
            await self._initialize_tables()
            self._connected = True
            logger.info("postgresql_connection_pool_established")

        except Exception as e:
            logger.error("postgresql_connection_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def _initialize_tables(self) -> None:
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
            logger.error("postgresql_get_failed", key=key.to_string(), error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in PostgreSQL"""
        if not self._connected:
            await self.connect()

        key_hash = self._hash_key(key)
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl else None

        # Ensure value is JSON serializable
        try:
            if not isinstance(value, (dict, list, str, int, float, bool, type(None))):
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
            logger.error("postgresql_set_failed", key=key.to_string(), error=str(e))
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
                return result.split()[-1] != "0"  # Check if any rows were affected

        except Exception as e:
            logger.error("postgresql_delete_failed", key=key.to_string(), error=str(e))
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
            logger.error("postgresql_exists_check_failed", key=key.to_string(), error=str(e))
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
            logger.error("postgresql_list_keys_failed", pattern=pattern, error=str(e))
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
            logger.error("postgresql_namespace_query_failed", namespace=namespace, error=str(e))
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
                logger.info("expired_entries_cleaned", deleted_count=deleted_count)
                return deleted_count

        except Exception as e:
            logger.error("expired_entries_cleanup_failed", error=str(e))
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
            logger.error("postgresql_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("postgresql_connection_pool_closed")


