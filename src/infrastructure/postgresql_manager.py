#!/usr/bin/env python3
"""
PostgreSQL Database Manager
===========================

Enterprise PostgreSQL database manager with connection pooling, advanced features,
and production-ready configuration for high-scale novel engine deployments.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


class PostgreSQLFeature(Enum):
    """PostgreSQL-specific features."""

    FULL_TEXT_SEARCH = "full_text_search"
    JSON_QUERIES = "json_queries"
    PARTITIONING = "partitioning"
    REPLICATION = "replication"
    EXTENSIONS = "extensions"


@dataclass
class PostgreSQLConfig:
    """PostgreSQL connection and feature configuration."""

    host: str = "localhost"
    port: int = 5432
    database: str = "novel_engine"
    username: str = "novel_engine_user"
    password: str = ""

    # Connection pool settings
    min_pool_size: int = 5
    max_pool_size: int = 50
    connection_timeout: float = 30.0
    command_timeout: float = 60.0

    # SSL configuration
    ssl_mode: str = "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None

    # Advanced features
    enable_json_features: bool = True
    enable_full_text_search: bool = True
    enable_partitioning: bool = True
    enable_extensions: List[str] = field(
        default_factory=lambda: ["uuid-ossp", "pg_trgm", "btree_gin"]
    )

    # Performance tuning
    statement_cache_size: int = 1024
    prepared_statement_cache_size: int = 100

    # Monitoring
    enable_query_logging: bool = False
    slow_query_threshold: float = 1.0  # seconds

    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        ssl_param = f"?sslmode={self.ssl_mode}" if self.ssl_mode != "disable" else ""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_param}"


class PostgreSQLConnectionPool:
    """
    Enterprise PostgreSQL connection pool with advanced features.

    Features:
    - Connection pooling with health monitoring
    - Prepared statement caching
    - JSON document support
    - Full-text search capabilities
    - Connection load balancing
    - Query performance monitoring
    """

    def __init__(self, config: PostgreSQLConfig):
        """Initialize PostgreSQL connection pool."""
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        self._metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "total_queries": 0,
            "slow_queries": 0,
            "errors": 0,
            "query_times": [],
        }

    async def initialize(self) -> None:
        """Initialize connection pool and extensions."""
        if self._initialized:
            return

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                command_timeout=self.config.command_timeout,
                server_settings={
                    "jit": "off",  # Disable JIT for consistent performance
                    "application_name": "novel_engine",
                },
            )

            # Initialize database extensions and features
            await self._initialize_extensions()
            await self._initialize_schema()

            self._initialized = True
            logger.info(
                f"PostgreSQL connection pool initialized: {self.config.host}:{self.config.port}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise

    async def _initialize_extensions(self) -> None:
        """Initialize PostgreSQL extensions."""
        if not self.config.enable_extensions:
            return

        async with self.pool.acquire() as conn:
            for extension in self.config.enable_extensions:
                try:
                    await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
                    logger.debug(f"Enabled PostgreSQL extension: {extension}")
                except Exception as e:
                    logger.warning(f"Failed to enable extension {extension}: {e}")

    async def _initialize_schema(self) -> None:
        """Initialize database schema for Novel Engine."""
        schema_queries = [
            # Characters table with JSON support
            """
            CREATE TABLE IF NOT EXISTS characters (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) NOT NULL,
                character_data JSONB NOT NULL,
                search_vector tsvector,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                version INTEGER DEFAULT 1
            )
            """,
            # Memory system tables
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                agent_id VARCHAR(255) NOT NULL,
                memory_type VARCHAR(50) NOT NULL,
                content JSONB NOT NULL,
                embedding vector(1536),
                search_vector tsvector,
                importance_score FLOAT DEFAULT 0.0,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            # Interactions table with full-text search
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id VARCHAR(255) NOT NULL,
                participants JSONB NOT NULL,
                interaction_data JSONB NOT NULL,
                search_vector tsvector,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE
            )
            """,
            # Narrative events with causal relationships
            """
            CREATE TABLE IF NOT EXISTS narrative_events (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_type VARCHAR(100) NOT NULL,
                event_data JSONB NOT NULL,
                causal_links JSONB DEFAULT '[]',
                narrative_weight FLOAT DEFAULT 1.0,
                coherence_score FLOAT DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            # System state and configuration
            """
            CREATE TABLE IF NOT EXISTS system_state (
                key VARCHAR(255) PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_by VARCHAR(255) DEFAULT 'system'
            )
            """,
        ]

        # Create indexes for performance
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_characters_search ON characters USING gin(search_vector)",
            "CREATE INDEX IF NOT EXISTS idx_characters_data ON characters USING gin(character_data)",
            "CREATE INDEX IF NOT EXISTS idx_memory_agent_type ON memory_items (agent_id, memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memory_search ON memory_items USING gin(search_vector)",
            "CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory_items USING ivfflat(embedding) WITH (lists = 100)",
            "CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions (session_id)",
            "CREATE INDEX IF NOT EXISTS idx_interactions_search ON interactions USING gin(search_vector)",
            "CREATE INDEX IF NOT EXISTS idx_narrative_events_type ON narrative_events (event_type)",
            "CREATE INDEX IF NOT EXISTS idx_narrative_events_created ON narrative_events (created_at)",
        ]

        async with self.pool.acquire() as conn:
            # Create schema
            for query in schema_queries:
                try:
                    await conn.execute(query)
                    logger.debug("Created database table")
                except Exception as e:
                    logger.warning(f"Schema creation warning: {e}")

            # Create indexes
            for query in index_queries:
                try:
                    await conn.execute(query)
                    logger.debug("Created database index")
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")

            logger.info("PostgreSQL schema initialization complete")

    @asynccontextmanager
    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection with automatic release."""
        if not self._initialized:
            await self.initialize()

        async with self.pool.acquire() as conn:
            try:
                self._metrics["active_connections"] += 1
                yield conn
            finally:
                self._metrics["active_connections"] -= 1

    async def execute_query(
        self, query: str, *args, fetch_mode: str = "none"  # none, one, all
    ) -> Any:
        """Execute query with performance monitoring."""
        start_time = asyncio.get_running_loop().time()

        try:
            async with self.get_connection() as conn:
                if fetch_mode == "one":
                    result = await conn.fetchrow(query, *args)
                elif fetch_mode == "all":
                    result = await conn.fetch(query, *args)
                else:
                    result = await conn.execute(query, *args)

                # Track performance metrics
                execution_time = asyncio.get_running_loop().time() - start_time
                self._metrics["total_queries"] += 1
                self._metrics["query_times"].append(execution_time)

                # Track slow queries
                if execution_time > self.config.slow_query_threshold:
                    self._metrics["slow_queries"] += 1
                    if self.config.enable_query_logging:
                        logger.warning(
                            f"Slow query ({execution_time:.3f}s): {query[:100]}..."
                        )

                # Limit metrics history
                if len(self._metrics["query_times"]) > 1000:
                    self._metrics["query_times"] = self._metrics["query_times"][-1000:]

                return result

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"PostgreSQL query failed: {e}")
            raise

    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in a transaction."""
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    for query, args in queries:
                        await conn.execute(query, *args)

                logger.debug(f"Transaction completed with {len(queries)} queries")
                return True

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

    # Novel Engine specific operations

    async def store_character(
        self, character_id: str, character_data: Dict[str, Any]
    ) -> bool:
        """Store character data with full-text search support."""
        search_text = f"{character_data.get('name', '')} {character_data.get('description', '')} {' '.join(character_data.get('traits', []))}"

        query = """
        INSERT INTO characters (id, name, character_data, search_vector, updated_at)
        VALUES ($1, $2, $3, to_tsvector('english', $4), NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            character_data = EXCLUDED.character_data,
            search_vector = EXCLUDED.search_vector,
            updated_at = NOW(),
            version = characters.version + 1
        """

        await self.execute_query(
            query,
            character_id,
            character_data.get("name", ""),
            json.dumps(character_data),
            search_text,
        )

        return True

    async def search_characters(
        self, search_query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search characters using full-text search."""
        query = """
        SELECT id, name, character_data, 
               ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
        FROM characters
        WHERE search_vector @@ plainto_tsquery('english', $1)
        ORDER BY rank DESC
        LIMIT $2
        """

        results = await self.execute_query(query, search_query, limit, fetch_mode="all")

        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "data": (
                    json.loads(row["character_data"])
                    if isinstance(row["character_data"], str)
                    else row["character_data"]
                ),
                "relevance": float(row["rank"]),
            }
            for row in results
        ]

    async def store_memory_item(
        self,
        agent_id: str,
        memory_type: str,
        content: Dict[str, Any],
        importance_score: float = 0.0,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Store memory item with vector embedding support."""
        search_text = f"{content.get('description', '')} {content.get('context', '')}"

        query = """
        INSERT INTO memory_items (agent_id, memory_type, content, embedding, search_vector, importance_score)
        VALUES ($1, $2, $3, $4, to_tsvector('english', $5), $6)
        RETURNING id
        """

        result = await self.execute_query(
            query,
            agent_id,
            memory_type,
            json.dumps(content),
            embedding,
            search_text,
            importance_score,
            fetch_mode="one",
        )

        return str(result["id"])

    async def search_memories(
        self,
        agent_id: str,
        search_query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search agent memories with filtering."""
        where_clauses = [
            "agent_id = $1",
            "search_vector @@ plainto_tsquery('english', $2)",
        ]
        params = [agent_id, search_query]

        if memory_types:
            where_clauses.append("memory_type = ANY($3)")
            params.append(memory_types)
            limit_param = "$4"
        else:
            limit_param = "$3"

        query = f"""
        SELECT id, memory_type, content, importance_score,
               ts_rank(search_vector, plainto_tsquery('english', $2)) as rank,
               created_at, access_count
        FROM memory_items
        WHERE {' AND '.join(where_clauses)}
        ORDER BY rank DESC, importance_score DESC
        LIMIT {limit_param}
        """

        params.append(limit)
        results = await self.execute_query(query, *params, fetch_mode="all")

        return [
            {
                "id": str(row["id"]),
                "type": row["memory_type"],
                "content": (
                    json.loads(row["content"])
                    if isinstance(row["content"], str)
                    else row["content"]
                ),
                "importance": float(row["importance_score"]),
                "relevance": float(row["rank"]),
                "created_at": row["created_at"],
                "access_count": row["access_count"],
            }
            for row in results
        ]

    async def store_interaction(
        self, session_id: str, participants: List[str], interaction_data: Dict[str, Any]
    ) -> str:
        """Store interaction with full-text search."""
        search_text = f"{interaction_data.get('summary', '')} {interaction_data.get('dialogue', '')}"

        query = """
        INSERT INTO interactions (session_id, participants, interaction_data, search_vector)
        VALUES ($1, $2, $3, to_tsvector('english', $4))
        RETURNING id
        """

        result = await self.execute_query(
            query,
            session_id,
            json.dumps(participants),
            json.dumps(interaction_data),
            search_text,
            fetch_mode="one",
        )

        return str(result["id"])

    async def get_system_state(self, key: str) -> Optional[Any]:
        """Get system state value."""
        query = "SELECT value FROM system_state WHERE key = $1"
        result = await self.execute_query(query, key, fetch_mode="one")

        if result:
            return (
                json.loads(result["value"])
                if isinstance(result["value"], str)
                else result["value"]
            )
        return None

    async def set_system_state(
        self, key: str, value: Any, updated_by: str = "system"
    ) -> bool:
        """Set system state value."""
        query = """
        INSERT INTO system_state (key, value, updated_by, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (key) DO UPDATE SET
            value = EXCLUDED.value,
            updated_by = EXCLUDED.updated_by,
            updated_at = NOW()
        """

        await self.execute_query(query, key, json.dumps(value), updated_by)

        # Publish index/model config change events for cache invalidation (best-effort)
        try:
            from src.caching.invalidation import invalidate_event

            if str(key).lower() in {
                "semantic_index_version",
                "retrieval_index_version",
                "index_version",
            }:
                invalidate_event({"type": "IndexRebuilt", "version": str(value)})
            if str(key).lower() in {"model_name", "model_version", "llm_model"}:
                invalidate_event(
                    {"type": "ModelConfigChanged", "model_name": str(value)}
                )
        except Exception:
            pass
        return True

    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("PostgreSQL connection pool closed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics."""
        query_times = self._metrics["query_times"]

        return {
            "total_connections": self._metrics["total_connections"],
            "active_connections": self._metrics["active_connections"],
            "total_queries": self._metrics["total_queries"],
            "slow_queries": self._metrics["slow_queries"],
            "errors": self._metrics["errors"],
            "average_query_time": (
                sum(query_times) / len(query_times) if query_times else 0.0
            ),
            "max_query_time": max(query_times) if query_times else 0.0,
            "pool_size": {
                "min": self.config.min_pool_size,
                "max": self.config.max_pool_size,
                "current": self.pool.get_size() if self.pool else 0,
            },
        }


class PostgreSQLManager:
    """
    Central PostgreSQL manager for Novel Engine.

    Provides high-level database operations with connection pooling,
    performance monitoring, and Novel Engine-specific functionality.
    """

    def __init__(self, config: PostgreSQLConfig):
        """Initialize PostgreSQL manager."""
        self.config = config
        self.connection_pool = PostgreSQLConnectionPool(config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize PostgreSQL manager."""
        if not self._initialized:
            await self.connection_pool.initialize()
            self._initialized = True
            logger.info("PostgreSQL manager initialized")

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            await self.connection_pool.execute_query("SELECT 1", fetch_mode="one")

            metrics = self.connection_pool.get_metrics()

            return {
                "healthy": True,
                "database": self.config.database,
                "host": self.config.host,
                "port": self.config.port,
                "metrics": metrics,
                "features_enabled": {
                    "json_support": self.config.enable_json_features,
                    "full_text_search": self.config.enable_full_text_search,
                    "partitioning": self.config.enable_partitioning,
                    "extensions": self.config.enable_extensions,
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
        """Close PostgreSQL manager."""
        await self.connection_pool.close()
        self._initialized = False


# Factory functions for easy integration
def create_postgresql_config_from_env() -> PostgreSQLConfig:
    """Create PostgreSQL configuration from environment variables."""
    import os

    return PostgreSQLConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "novel_engine"),
        username=os.getenv("POSTGRES_USER", "novel_engine_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        min_pool_size=int(os.getenv("POSTGRES_MIN_POOL_SIZE", "5")),
        max_pool_size=int(os.getenv("POSTGRES_MAX_POOL_SIZE", "50")),
        ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
    )


async def create_postgresql_manager(
    config: Optional[PostgreSQLConfig] = None,
) -> PostgreSQLManager:
    """Create and initialize PostgreSQL manager."""
    if config is None:
        config = create_postgresql_config_from_env()

    manager = PostgreSQLManager(config)
    await manager.initialize()
    return manager


__all__ = [
    "PostgreSQLConfig",
    "PostgreSQLConnectionPool",
    "PostgreSQLManager",
    "PostgreSQLFeature",
    "create_postgresql_config_from_env",
    "create_postgresql_manager",
]
