"""Database integration tests using testcontainers."""

from __future__ import annotations

from uuid import uuid4

import asyncpg
import pytest

# Skip tests if testcontainers is not installed
pytest.importorskip("testcontainers", reason="testcontainers not installed")


try:
    from testcontainers.postgres import PostgresContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    PostgresContainer = None  # type: ignore


@pytest.fixture(scope="module")
def postgres_container():
    """Create PostgreSQL container."""
    if not HAS_TESTCONTAINERS:
        pytest.skip("testcontainers not installed")

    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture
async def db_pool(postgres_container):
    """Create database pool connected to test container."""
    from src.shared.infrastructure.persistence.connection_pool import (
        DatabaseConnectionPool,
    )

    pool = DatabaseConnectionPool(
        database_url=postgres_container.get_connection_url(), max_connections=5
    )
    await pool.initialize()
    yield pool
    await pool.close()


@pytest.fixture
async def db_connection(db_pool) -> asyncpg.Connection:
    """Provide a database connection from pool."""
    async with db_pool.acquire() as conn:
        yield conn


@pytest.mark.integration
@pytest.mark.requires_services
@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
class TestDatabaseConnectionPool:
    """Test database connection pool integration."""

    async def test_pool_initialization(self, postgres_container):
        """Test connection pool initializes correctly."""
        from src.shared.infrastructure.persistence.connection_pool import (
            DatabaseConnectionPool,
        )

        pool = DatabaseConnectionPool(
            database_url=postgres_container.get_connection_url(), max_connections=5
        )
        await pool.initialize()

        assert pool._pool is not None
        assert pool._max_connections == 5

        await pool.close()

    async def test_connection_acquisition(self, db_pool):
        """Test acquiring connection from pool."""
        async with db_pool.acquire() as conn:
            assert conn is not None
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    async def test_multiple_connections(self, db_pool):
        """Test acquiring multiple connections."""
        connections = []
        for _ in range(3):
            async with db_pool.acquire() as conn:
                connections.append(conn)
                result = await conn.fetchval("SELECT 1")
                assert result == 1
        assert len(connections) == 3


@pytest.mark.integration
@pytest.mark.requires_services
@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
class TestKnowledgeRepositoryIntegration:
    """Test Knowledge repository with real database."""

    async def test_knowledge_base_crud(self, db_connection):
        """Test knowledge base CRUD operations."""
        from src.contexts.knowledge.domain.aggregates.knowledge_base import (
            KnowledgeBase,
        )
        from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
            PostgresKnowledgeRepository,
        )

        # Create table for testing
        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                owner_id UUID,
                project_id UUID,
                embedding_model VARCHAR(100),
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'
            )
        """)

        repo = PostgresKnowledgeRepository(db_connection)

        # Create knowledge base
        kb_id = uuid4()
        kb = KnowledgeBase(
            id=kb_id,
            name="Test Knowledge Base",
            description="Test Description",
            embedding_model="text-embedding-3-small",
        )
        await repo.save(kb)

        # Read
        result = await repo.get_by_id(kb_id)
        assert result is not None
        assert result.name == "Test Knowledge Base"
        assert result.description == "Test Description"

        # Update
        kb.name = "Updated Knowledge Base"
        await repo.save(kb)

        result = await repo.get_by_id(kb_id)
        assert result.name == "Updated Knowledge Base"

        # Delete
        await repo.delete(kb_id)
        result = await repo.get_by_id(kb_id)
        assert result is None

    async def test_get_by_name(self, db_connection):
        """Test retrieving knowledge base by name."""
        from src.contexts.knowledge.domain.aggregates.knowledge_base import (
            KnowledgeBase,
        )
        from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
            PostgresKnowledgeRepository,
        )

        # Ensure table exists
        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                owner_id UUID,
                project_id UUID,
                embedding_model VARCHAR(100),
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'
            )
        """)

        repo = PostgresKnowledgeRepository(db_connection)

        kb_id = uuid4()
        kb = KnowledgeBase(
            id=kb_id, name="Unique Test KB", description="Test Description"
        )
        await repo.save(kb)

        result = await repo.get_by_name("Unique Test KB")
        assert result is not None
        assert result.id == kb_id

        # Clean up
        await repo.delete(kb_id)


@pytest.mark.integration
@pytest.mark.requires_services
@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
class TestDatabaseTransactionIntegration:
    """Test database transaction handling."""

    async def test_transaction_commit(self, db_connection):
        """Test transaction commit works correctly."""
        # Create test table
        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS test_transactions (
                id UUID PRIMARY KEY,
                data VARCHAR(255)
            )
        """)

        test_id = uuid4()

        async with db_connection.transaction():
            await db_connection.execute(
                "INSERT INTO test_transactions (id, data) VALUES ($1, $2)",
                test_id,
                "test data",
            )

        result = await db_connection.fetchval(
            "SELECT data FROM test_transactions WHERE id = $1", test_id
        )
        assert result == "test data"

        # Clean up
        await db_connection.execute(
            "DELETE FROM test_transactions WHERE id = $1", test_id
        )

    async def test_transaction_rollback(self, db_connection):
        """Test transaction rollback works correctly."""
        # Create test table
        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS test_transactions (
                id UUID PRIMARY KEY,
                data VARCHAR(255)
            )
        """)

        test_id = uuid4()

        try:
            async with db_connection.transaction():
                await db_connection.execute(
                    "INSERT INTO test_transactions (id, data) VALUES ($1, $2)",
                    test_id,
                    "rollback data",
                )
                raise ValueError("Force rollback")
        except ValueError:
            pass

        result = await db_connection.fetchval(
            "SELECT data FROM test_transactions WHERE id = $1", test_id
        )
        assert result is None


@pytest.mark.integration
@pytest.mark.requires_services
@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
class TestConnectionPoolConcurrency:
    """Test connection pool under concurrent load."""

    async def test_concurrent_queries(self, db_pool):
        """Test handling concurrent queries."""
        import asyncio

        async def query_task(task_id: int) -> int:
            async with db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT $1::int", task_id)
                return result

        tasks = [query_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert results == list(range(10))
