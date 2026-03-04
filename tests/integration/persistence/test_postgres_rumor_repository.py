#!/usr/bin/env python3
"""Integration tests for PostgreSQLRumorRepository.

Tests the PostgreSQL implementation of RumorRepository with real database.
Requires PostgreSQL to be running for integration tests.
"""

import os
import uuid
from typing import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio

from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.contexts.world.infrastructure.persistence.postgres_rumor_repository import (
    PostgreSQLRumorRepository,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def get_test_database_url() -> str:
    """Get test database URL from environment or use default."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "novel_engine_test")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest_asyncio.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create a test database connection pool."""
    dsn = await get_test_database_url()
    try:
        pool = await asyncpg.create_pool(
            dsn,
            min_size=1,
            max_size=5,
            command_timeout=60,
        )
        yield pool
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    else:
        await pool.close()


@pytest_asyncio.fixture
async def rumor_repo(db_pool: asyncpg.Pool) -> PostgreSQLRumorRepository:
    """Create a PostgreSQLRumorRepository with test pool."""
    repo = PostgreSQLRumorRepository(db_pool)
    # Clear table before each test
    await repo.clear()
    return repo


def create_test_rumor(
    content: str = "Test rumor content",
    truth_value: int = 75,
    origin_type: RumorOrigin = RumorOrigin.EVENT,
    origin_location_id: str = None,
    **kwargs
) -> Rumor:
    """Create a test Rumor with default values."""
    if origin_location_id is None:
        origin_location_id = str(uuid.uuid4())
    
    return Rumor(
        content=content,
        truth_value=truth_value,
        origin_type=origin_type,
        origin_location_id=origin_location_id,
        source_event_id=kwargs.get("source_event_id"),
        current_locations=kwargs.get("current_locations", {origin_location_id}),
        created_date=kwargs.get("created_date"),
        spread_count=kwargs.get("spread_count", 0),
    )


class TestPostgreSQLRumorRepositoryBasic:
    """Basic CRUD operations tests."""

    @pytest.mark.integration
    async def test_save_and_get_by_id(self, rumor_repo: PostgreSQLRumorRepository):
        """Test saving a rumor and retrieving it by ID."""
        origin_id = str(uuid.uuid4())
        rumor = create_test_rumor(
            content="Dragon sighted in the north!",
            origin_location_id=origin_id,
        )
        
        saved = await rumor_repo.save(rumor)
        assert saved.rumor_id == rumor.rumor_id
        assert saved.content == "Dragon sighted in the north!"
        
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        assert retrieved is not None
        assert retrieved.rumor_id == rumor.rumor_id
        assert retrieved.content == "Dragon sighted in the north!"
        assert retrieved.truth_value == 75
        assert retrieved.origin_type == RumorOrigin.EVENT

    @pytest.mark.integration
    async def test_get_by_id_not_found(self, rumor_repo: PostgreSQLRumorRepository):
        """Test retrieving a non-existent rumor returns None."""
        result = await rumor_repo.get_by_id(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.integration
    async def test_update_existing_rumor(self, rumor_repo: PostgreSQLRumorRepository):
        """Test updating an existing rumor."""
        origin_id = str(uuid.uuid4())
        rumor = create_test_rumor(content="Original content", origin_location_id=origin_id)
        await rumor_repo.save(rumor)
        
        # Create new instance with same ID but updated content (Rumor is immutable)
        updated_rumor = Rumor(
            rumor_id=rumor.rumor_id,
            content="Updated content",
            truth_value=50,
            origin_type=rumor.origin_type,
            origin_location_id=rumor.origin_location_id,
            current_locations=rumor.current_locations,
        )
        await rumor_repo.save(updated_rumor)
        
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        assert retrieved is not None
        assert retrieved.content == "Updated content"
        assert retrieved.truth_value == 50

    @pytest.mark.integration
    async def test_delete_rumor(self, rumor_repo: PostgreSQLRumorRepository):
        """Test deleting a rumor."""
        origin_id = str(uuid.uuid4())
        rumor = create_test_rumor(origin_location_id=origin_id)
        await rumor_repo.save(rumor)
        
        # Verify it exists
        assert await rumor_repo.get_by_id(rumor.rumor_id) is not None
        
        # Delete it
        deleted = await rumor_repo.delete(rumor.rumor_id)
        assert deleted is True
        
        # Verify it's gone
        assert await rumor_repo.get_by_id(rumor.rumor_id) is None

    @pytest.mark.integration
    async def test_delete_nonexistent_rumor(self, rumor_repo: PostgreSQLRumorRepository):
        """Test deleting a non-existent rumor returns False."""
        result = await rumor_repo.delete(str(uuid.uuid4()))
        assert result is False


class TestPostgreSQLRumorRepositoryActiveRumors:
    """Active rumors query tests."""

    @pytest.mark.integration
    async def test_get_active_rumors_filters_by_truth_value(self, rumor_repo: PostgreSQLRumorRepository):
        """Test that get_active_rumors only returns rumors with truth_value > 0."""
        origin_id = str(uuid.uuid4())
        
        # Create active rumor (truth > 0)
        active_rumor = create_test_rumor(
            content="Active rumor",
            truth_value=75,
            origin_location_id=origin_id,
        )
        await rumor_repo.save(active_rumor)
        
        # Create dead rumor (truth = 0)
        dead_rumor = create_test_rumor(
            content="Dead rumor",
            truth_value=0,
            origin_location_id=origin_id,
        )
        await rumor_repo.save(dead_rumor)
        
        active_rumors = await rumor_repo.get_active_rumors(origin_id)
        assert len(active_rumors) == 1
        assert active_rumors[0].rumor_id == active_rumor.rumor_id

    @pytest.mark.integration
    async def test_get_active_rumors_sorted_by_truth(self, rumor_repo: PostgreSQLRumorRepository):
        """Test that active rumors are sorted by truth_value descending."""
        origin_id = str(uuid.uuid4())
        
        # Create rumors with different truth values
        rumor_high = create_test_rumor(content="High truth", truth_value=90, origin_location_id=origin_id)
        rumor_low = create_test_rumor(content="Low truth", truth_value=30, origin_location_id=origin_id)
        rumor_medium = create_test_rumor(content="Medium truth", truth_value=60, origin_location_id=origin_id)
        
        await rumor_repo.save(rumor_low)
        await rumor_repo.save(rumor_high)
        await rumor_repo.save(rumor_medium)
        
        active_rumors = await rumor_repo.get_active_rumors(origin_id)
        assert len(active_rumors) == 3
        assert active_rumors[0].truth_value == 90
        assert active_rumors[1].truth_value == 60
        assert active_rumors[2].truth_value == 30

    @pytest.mark.integration
    async def test_get_by_world_id_includes_dead_rumors(self, rumor_repo: PostgreSQLRumorRepository):
        """Test that get_by_world_id returns all rumors including dead ones."""
        origin_id = str(uuid.uuid4())
        
        active_rumor = create_test_rumor(
            content="Active",
            truth_value=50,
            origin_location_id=origin_id,
        )
        dead_rumor = create_test_rumor(
            content="Dead",
            truth_value=0,
            origin_location_id=origin_id,
        )
        
        await rumor_repo.save(active_rumor)
        await rumor_repo.save(dead_rumor)
        
        all_rumors = await rumor_repo.get_by_world_id(origin_id)
        assert len(all_rumors) == 2


class TestPostgreSQLRumorRepositoryLocationQueries:
    """Location-based query tests."""

    @pytest.mark.integration
    async def test_get_by_location_id(self, rumor_repo: PostgreSQLRumorRepository):
        """Test retrieving rumors by location ID."""
        loc1 = str(uuid.uuid4())
        loc2 = str(uuid.uuid4())
        origin_id = str(uuid.uuid4())
        
        # Create rumors at different locations
        rumor1 = create_test_rumor(
            content="At location 1",
            origin_location_id=origin_id,
            current_locations={loc1, origin_id},
        )
        rumor2 = create_test_rumor(
            content="Also at location 1",
            origin_location_id=origin_id,
            current_locations={loc1, origin_id},
        )
        rumor3 = create_test_rumor(
            content="At location 2 only",
            origin_location_id=origin_id,
            current_locations={loc2, origin_id},
        )
        
        await rumor_repo.save(rumor1)
        await rumor_repo.save(rumor2)
        await rumor_repo.save(rumor3)
        
        results = await rumor_repo.get_by_location_id(loc1)
        assert len(results) == 2
        assert all(r.rumor_id in [rumor1.rumor_id, rumor2.rumor_id] for r in results)

    @pytest.mark.integration
    async def test_get_by_event_id(self, rumor_repo: PostgreSQLRumorRepository):
        """Test retrieving rumors by source event ID."""
        event_id = str(uuid.uuid4())
        origin_id = str(uuid.uuid4())
        
        # Create rumors from same event
        rumor1 = create_test_rumor(
            content="From event",
            origin_location_id=origin_id,
            source_event_id=event_id,
        )
        rumor2 = create_test_rumor(
            content="Also from event",
            origin_location_id=origin_id,
            source_event_id=event_id,
        )
        rumor3 = create_test_rumor(
            content="From different event",
            origin_location_id=origin_id,
            source_event_id=str(uuid.uuid4()),
        )
        
        await rumor_repo.save(rumor1)
        await rumor_repo.save(rumor2)
        await rumor_repo.save(rumor3)
        
        results = await rumor_repo.get_by_event_id(event_id)
        assert len(results) == 2
        assert all(r.rumor_id in [rumor1.rumor_id, rumor2.rumor_id] for r in results)


class TestPostgreSQLRumorRepositoryBatchOperations:
    """Batch operation tests."""

    @pytest.mark.integration
    async def test_save_all_multiple_rumors(self, rumor_repo: PostgreSQLRumorRepository):
        """Test saving multiple rumors in one operation."""
        origin_id = str(uuid.uuid4())
        rumors = [
            create_test_rumor(content=f"Batch rumor {i}", origin_location_id=origin_id)
            for i in range(5)
        ]
        
        saved = await rumor_repo.save_all(rumors)
        assert len(saved) == 5
        
        # Verify all were saved
        for rumor in rumors:
            retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
            assert retrieved is not None
            assert retrieved.content == rumor.content

    @pytest.mark.integration
    async def test_save_all_empty_list(self, rumor_repo: PostgreSQLRumorRepository):
        """Test save_all with empty list."""
        result = await rumor_repo.save_all([])
        assert result == []


class TestPostgreSQLRumorRepositoryComplexData:
    """Tests for complex data types."""

    @pytest.mark.integration
    async def test_rumor_with_all_fields(self, rumor_repo: PostgreSQLRumorRepository):
        """Test saving and retrieving a rumor with all fields populated."""
        origin_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())
        loc1 = str(uuid.uuid4())
        loc2 = str(uuid.uuid4())
        calendar = WorldCalendar(1042, 6, 15, "Third Age")
        
        rumor = Rumor(
            content="The king has been assassinated!",
            truth_value=85,
            origin_type=RumorOrigin.EVENT,
            source_event_id=event_id,
            origin_location_id=origin_id,
            current_locations={origin_id, loc1, loc2},
            created_date=calendar,
            spread_count=3,
        )
        
        await rumor_repo.save(rumor)
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        
        assert retrieved is not None
        assert retrieved.content == "The king has been assassinated!"
        assert retrieved.truth_value == 85
        assert retrieved.origin_type == RumorOrigin.EVENT
        assert retrieved.source_event_id == event_id
        assert retrieved.origin_location_id == origin_id
        assert retrieved.current_locations == {origin_id, loc1, loc2}
        assert retrieved.spread_count == 3
        assert retrieved.created_date is not None
        assert retrieved.created_date.year == 1042
        assert retrieved.created_date.month == 6
        assert retrieved.created_date.day == 15

    @pytest.mark.integration
    async def test_rumor_origin_types(self, rumor_repo: PostgreSQLRumorRepository):
        """Test that all origin types are correctly preserved."""
        origin_id = str(uuid.uuid4())
        
        for origin_type in RumorOrigin:
            rumor = create_test_rumor(
                content=f"Rumor from {origin_type.value}",
                origin_type=origin_type,
                origin_location_id=origin_id,
            )
            await rumor_repo.save(rumor)
            
            retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
            assert retrieved is not None
            assert retrieved.origin_type == origin_type

    @pytest.mark.integration
    async def test_rumor_spread_simulation(self, rumor_repo: PostgreSQLRumorRepository):
        """Test simulating rumor spread across locations."""
        origin_id = str(uuid.uuid4())
        loc1 = str(uuid.uuid4())
        loc2 = str(uuid.uuid4())
        
        # Create initial rumor
        rumor = create_test_rumor(
            content="Treasure hidden in the castle",
            truth_value=100,
            origin_location_id=origin_id,
            current_locations={origin_id},
            spread_count=0,
        )
        await rumor_repo.save(rumor)
        
        # Simulate spread to new location
        spread_rumor = rumor.spread_to(loc1)
        await rumor_repo.save(spread_rumor)
        
        # Simulate another spread
        spread_rumor2 = spread_rumor.spread_to(loc2)
        await rumor_repo.save(spread_rumor2)
        
        # Verify truth decay
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        assert retrieved is not None
        assert retrieved.truth_value == 80  # 100 - 10 - 10
        assert retrieved.spread_count == 2
        assert loc1 in retrieved.current_locations
        assert loc2 in retrieved.current_locations

    @pytest.mark.integration
    async def test_clear_all_rumors(self, rumor_repo: PostgreSQLRumorRepository):
        """Test clearing all rumors."""
        origin_id = str(uuid.uuid4())
        
        # Create some rumors
        for i in range(3):
            await rumor_repo.save(create_test_rumor(content=f"Rumor {i}", origin_location_id=origin_id))
        
        # Clear all
        await rumor_repo.clear()
        
        # Verify all are gone
        rumors = await rumor_repo.get_by_world_id(origin_id)
        assert len(rumors) == 0


class TestPostgreSQLRumorRepositoryEdgeCases:
    """Edge case tests."""

    @pytest.mark.integration
    async def test_rumor_with_empty_locations(self, rumor_repo: PostgreSQLRumorRepository):
        """Test rumor with empty current_locations."""
        origin_id = str(uuid.uuid4())
        
        rumor = Rumor(
            content="Secret rumor",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id=origin_id,
            current_locations=set(),
        )
        
        await rumor_repo.save(rumor)
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        
        assert retrieved is not None
        assert retrieved.current_locations == set()

    @pytest.mark.integration
    async def test_rumor_without_source_event(self, rumor_repo: PostgreSQLRumorRepository):
        """Test rumor with no source event (npc or unknown origin)."""
        origin_id = str(uuid.uuid4())
        
        rumor = Rumor(
            content="Heard from a traveler",
            truth_value=40,
            origin_type=RumorOrigin.NPC,
            source_event_id=None,
            origin_location_id=origin_id,
        )
        
        await rumor_repo.save(rumor)
        retrieved = await rumor_repo.get_by_id(rumor.rumor_id)
        
        assert retrieved is not None
        assert retrieved.source_event_id is None
        assert retrieved.origin_type == RumorOrigin.NPC
