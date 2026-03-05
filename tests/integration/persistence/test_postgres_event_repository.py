#!/usr/bin/env python3
"""Integration tests for PostgreSQLEventRepository.

Tests the PostgreSQL implementation of EventRepository with real database.
Requires PostgreSQL to be running for integration tests.
"""

import os
import uuid
from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio

# Skip all tests in this module if asyncpg is not installed
asyncpg = pytest.importorskip("asyncpg")

from src.contexts.world.domain.entities.history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.contexts.world.infrastructure.persistence.postgres_event_repository import (
    PostgreSQLEventRepository,
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
async def event_repo(db_pool: asyncpg.Pool) -> PostgreSQLEventRepository:
    """Create a PostgreSQLEventRepository with test pool."""
    repo = PostgreSQLEventRepository(db_pool)
    # Clear table before each test
    await repo.clear()
    return repo


def create_test_event(
    name: str = "Test Event",
    event_type: EventType = EventType.POLITICAL,
    significance: EventSignificance = EventSignificance.MODERATE,
    **kwargs
) -> HistoryEvent:
    """Create a test HistoryEvent with default values."""
    return HistoryEvent(
        name=name,
        description="A test event description",
        event_type=event_type,
        significance=significance,
        outcome=EventOutcome.NEUTRAL,
        date_description="Year 1042 of the Third Age",
        location_ids=kwargs.get("location_ids", []),
        faction_ids=kwargs.get("faction_ids", []),
        narrative_importance=kwargs.get("narrative_importance", 50),
        is_secret=kwargs.get("is_secret", False),
    )


class TestPostgreSQLEventRepositoryBasic:
    """Basic CRUD operations tests."""

    @pytest.mark.integration
    async def test_save_and_get_by_id(self, event_repo: PostgreSQLEventRepository):
        """Test saving an event and retrieving it by ID."""
        event = create_test_event(name="Battle of Test Plains")
        
        saved = await event_repo.save(event)
        assert saved.id == event.id
        assert saved.name == "Battle of Test Plains"
        
        retrieved = await event_repo.get_by_id(event.id)
        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.name == "Battle of Test Plains"
        assert retrieved.event_type == EventType.POLITICAL

    @pytest.mark.integration
    async def test_get_by_id_not_found(self, event_repo: PostgreSQLEventRepository):
        """Test retrieving a non-existent event returns None."""
        result = await event_repo.get_by_id(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.integration
    async def test_update_existing_event(self, event_repo: PostgreSQLEventRepository):
        """Test updating an existing event."""
        event = create_test_event(name="Original Name")
        await event_repo.save(event)
        
        # Modify and save again
        event.name = "Updated Name"
        event.description = "Updated description"
        await event_repo.save(event)
        
        retrieved = await event_repo.get_by_id(event.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.description == "Updated description"

    @pytest.mark.integration
    async def test_delete_event(self, event_repo: PostgreSQLEventRepository):
        """Test deleting an event."""
        event = create_test_event()
        await event_repo.save(event)
        
        # Verify it exists
        assert await event_repo.get_by_id(event.id) is not None
        
        # Delete it
        deleted = await event_repo.delete(event.id)
        assert deleted is True
        
        # Verify it's gone
        assert await event_repo.get_by_id(event.id) is None

    @pytest.mark.integration
    async def test_delete_nonexistent_event(self, event_repo: PostgreSQLEventRepository):
        """Test deleting a non-existent event returns False."""
        result = await event_repo.delete(str(uuid.uuid4()))
        assert result is False


class TestPostgreSQLEventRepositoryQueries:
    """Query operation tests."""

    @pytest.mark.integration
    async def test_get_by_location_id(self, event_repo: PostgreSQLEventRepository):
        """Test retrieving events by location ID."""
        location_id = str(uuid.uuid4())
        
        # Create events at different locations
        event1 = create_test_event(name="Event at Location 1", location_ids=[location_id])
        event2 = create_test_event(name="Event at Location 1 too", location_ids=[location_id])
        event3 = create_test_event(name="Event elsewhere", location_ids=[str(uuid.uuid4())])
        
        await event_repo.save(event1)
        await event_repo.save(event2)
        await event_repo.save(event3)
        
        results = await event_repo.get_by_location_id(location_id)
        assert len(results) == 2
        assert all(e.id in [event1.id, event2.id] for e in results)

    @pytest.mark.integration
    async def test_get_by_faction_id(self, event_repo: PostgreSQLEventRepository):
        """Test retrieving events by faction ID."""
        faction_id = str(uuid.uuid4())
        
        # Create events with different factions
        event1 = create_test_event(name="Faction Event 1", faction_ids=[faction_id])
        event2 = create_test_event(name="Faction Event 2", faction_ids=[faction_id])
        event3 = create_test_event(name="Other Faction Event", faction_ids=[str(uuid.uuid4())])
        
        await event_repo.save(event1)
        await event_repo.save(event2)
        await event_repo.save(event3)
        
        results = await event_repo.get_by_faction_id(faction_id)
        assert len(results) == 2
        assert all(e.id in [event1.id, event2.id] for e in results)

    @pytest.mark.integration
    async def test_get_by_world_id_with_pagination(self, event_repo: PostgreSQLEventRepository):
        """Test retrieving events by world ID with pagination."""
        world_id = str(uuid.uuid4())
        
        # Create multiple events in the same world (via location_id)
        events = []
        for i in range(5):
            event = create_test_event(
                name=f"World Event {i}",
                location_ids=[world_id],
                narrative_importance=50 + i * 10
            )
            await event_repo.save(event)
            events.append(event)
        
        # Get first page
        page1 = await event_repo.get_by_world_id(world_id, limit=3, offset=0)
        assert len(page1) == 3
        
        # Get second page
        page2 = await event_repo.get_by_world_id(world_id, limit=3, offset=3)
        assert len(page2) == 2

    @pytest.mark.integration
    async def test_results_sorted_by_narrative_importance(self, event_repo: PostgreSQLEventRepository):
        """Test that results are sorted by narrative_importance descending."""
        location_id = str(uuid.uuid4())
        
        # Create events with different importance
        event_low = create_test_event(name="Low Importance", location_ids=[location_id], narrative_importance=30)
        event_high = create_test_event(name="High Importance", location_ids=[location_id], narrative_importance=90)
        event_medium = create_test_event(name="Medium Importance", location_ids=[location_id], narrative_importance=60)
        
        await event_repo.save(event_low)
        await event_repo.save(event_high)
        await event_repo.save(event_medium)
        
        results = await event_repo.get_by_location_id(location_id)
        assert len(results) == 3
        assert results[0].narrative_importance == 90
        assert results[1].narrative_importance == 60
        assert results[2].narrative_importance == 30


class TestPostgreSQLEventRepositoryBatchOperations:
    """Batch operation tests."""

    @pytest.mark.integration
    async def test_save_all_multiple_events(self, event_repo: PostgreSQLEventRepository):
        """Test saving multiple events in one operation."""
        events = [
            create_test_event(name=f"Batch Event {i}")
            for i in range(5)
        ]
        
        saved = await event_repo.save_all(events)
        assert len(saved) == 5
        
        # Verify all were saved
        for event in events:
            retrieved = await event_repo.get_by_id(event.id)
            assert retrieved is not None
            assert retrieved.name == event.name

    @pytest.mark.integration
    async def test_save_all_empty_list(self, event_repo: PostgreSQLEventRepository):
        """Test save_all with empty list."""
        result = await event_repo.save_all([])
        assert result == []


class TestPostgreSQLEventRepositoryComplexData:
    """Tests for complex data types and relationships."""

    @pytest.mark.integration
    async def test_event_with_all_fields(self, event_repo: PostgreSQLEventRepository):
        """Test saving and retrieving an event with all fields populated."""
        calendar = WorldCalendar(1042, 3, 15, "Third Age")
        
        event = HistoryEvent(
            name="The Great Sundering",
            description="A cataclysmic event that split the continent",
            event_type=EventType.DISASTER,
            significance=EventSignificance.WORLD_CHANGING,
            outcome=EventOutcome.NEGATIVE,
            date_description="Year 1042 of the Third Age",
            duration_description="Three days and nights",
            location_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
            faction_ids=[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
            key_figures=["King Aldric", "Archmage Selene"],
            causes=["Ancient ritual gone wrong", "Hubris of mages"],
            consequences=["Continent split in two", "Magic drained from the land"],
            preceding_event_ids=[str(uuid.uuid4())],
            following_event_ids=[str(uuid.uuid4())],
            related_event_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
            is_secret=True,
            sources=["Ancient texts", "Eyewitness accounts"],
            narrative_importance=95,
            impact_scope=ImpactScope.GLOBAL,
            affected_faction_ids=[str(uuid.uuid4())],
            affected_location_ids=[str(uuid.uuid4())],
            structured_date=calendar,
        )
        
        await event_repo.save(event)
        retrieved = await event_repo.get_by_id(event.id)
        
        assert retrieved is not None
        assert retrieved.name == "The Great Sundering"
        assert retrieved.event_type == EventType.DISASTER
        assert retrieved.significance == EventSignificance.WORLD_CHANGING
        assert retrieved.outcome == EventOutcome.NEGATIVE
        assert retrieved.is_secret is True
        assert retrieved.narrative_importance == 95
        assert retrieved.impact_scope == ImpactScope.GLOBAL
        assert len(retrieved.location_ids) == 2
        assert len(retrieved.faction_ids) == 3
        assert len(retrieved.key_figures) == 2
        assert len(retrieved.causes) == 2
        assert len(retrieved.consequences) == 2
        assert retrieved.structured_date is not None
        assert retrieved.structured_date.year == 1042

    @pytest.mark.integration
    async def test_event_enums_preserved(self, event_repo: PostgreSQLEventRepository):
        """Test that all enum types are correctly preserved."""
        for event_type in EventType:
            event = create_test_event(name=f"Event type {event_type.value}", event_type=event_type)
            await event_repo.save(event)
            
            retrieved = await event_repo.get_by_id(event.id)
            assert retrieved is not None
            assert retrieved.event_type == event_type

    @pytest.mark.integration
    async def test_clear_all_events(self, event_repo: PostgreSQLEventRepository):
        """Test clearing all events."""
        # Create some events
        for i in range(3):
            await event_repo.save(create_test_event(name=f"Event {i}"))
        
        # Clear all
        await event_repo.clear()
        
        # Verify all are gone
        events = await event_repo.get_by_world_id(str(uuid.uuid4()))
        assert len(events) == 0


class TestPostgreSQLEventRepositoryFactoryMethods:
    """Tests using factory methods from HistoryEvent."""

    @pytest.mark.integration
    async def test_save_war_event(self, event_repo: PostgreSQLEventRepository):
        """Test saving a war event created via factory method."""
        war = HistoryEvent.create_war(
            name="The War of Tests",
            description="A conflict to test all systems",
            date_description="Year 1042",
            faction_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        )
        
        await event_repo.save(war)
        retrieved = await event_repo.get_by_id(war.id)
        
        assert retrieved is not None
        assert retrieved.name == "The War of Tests"
        assert retrieved.event_type == EventType.WAR
        assert retrieved.significance == EventSignificance.MAJOR

    @pytest.mark.integration
    async def test_save_founding_event(self, event_repo: PostgreSQLEventRepository):
        """Test saving a founding event created via factory method."""
        founding = HistoryEvent.create_founding(
            name="Founding of Test City",
            description="A new settlement was established",
            date_description="After the Great Migration",
            location_ids=[str(uuid.uuid4())],
        )
        
        await event_repo.save(founding)
        retrieved = await event_repo.get_by_id(founding.id)
        
        assert retrieved is not None
        assert retrieved.name == "Founding of Test City"
        assert retrieved.event_type == EventType.FOUNDING
        assert retrieved.outcome == EventOutcome.POSITIVE

    @pytest.mark.integration
    async def test_save_disaster_event(self, event_repo: PostgreSQLEventRepository):
        """Test saving a disaster event created via factory method."""
        disaster = HistoryEvent.create_disaster(
            name="The Great Test Flood",
            description="Waters rose to test our resolve",
            date_description="The Year of Testing",
            location_ids=[str(uuid.uuid4())],
            significance=EventSignificance.WORLD_CHANGING,
        )
        
        await event_repo.save(disaster)
        retrieved = await event_repo.get_by_id(disaster.id)
        
        assert retrieved is not None
        assert retrieved.name == "The Great Test Flood"
        assert retrieved.event_type == EventType.DISASTER
        assert retrieved.significance == EventSignificance.WORLD_CHANGING
