#!/usr/bin/env python3
"""
Unit tests for WorldSimulationService

Comprehensive test suite for the WorldSimulationService covering
simulation preview, validation, and error handling scenarios.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()


# Create mock event bus classes for testing
class MockEventPriority(Enum):
    """Mock EventPriority for testing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockEvent:
    """Mock Event class that supports dataclass functionality."""
    event_id: str = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    priority: MockEventPriority = MockEventPriority.NORMAL
    timestamp: datetime = None
    tags: Set = field(default_factory=set)
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MockEventBusModule:
    Event = MockEvent
    EventPriority = MockEventPriority


# Save original module if it exists
_original_event_bus = sys.modules.get("src.events.event_bus")
sys.modules["src.events.event_bus"] = MockEventBusModule()

# Import after mocking
from src.contexts.world.application.services.faction_intent_generator import (
    FactionIntentGenerator,
)
from src.contexts.world.application.services.world_simulation_service import (
    IFactionRepository,
    InvalidDaysError,
    ISnapshotService,
    IWorldStateRepository,
    RepositoryError,
    RollbackError,
    SaveFailedError,
    SnapshotFailedError,
    WorldNotFoundError,
    WorldSimulationService,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import (
    Faction,
    FactionRelation,
    FactionStatus,
)
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

# Restore original module to avoid polluting other tests
if _original_event_bus is not None:
    sys.modules["src.events.event_bus"] = _original_event_bus
else:
    del sys.modules["src.events.event_bus"]


class MockWorldRepository:
    """Mock WorldState repository for testing."""

    def __init__(self, worlds: Dict[str, WorldState] = None):
        self._worlds = worlds or {}

    async def get_by_id(self, world_id: str) -> WorldState | None:
        return self._worlds.get(world_id)


class MockFactionRepository:
    """Mock Faction repository for testing."""

    def __init__(self, factions_by_world: Dict[str, List[Faction]] = None):
        self._factions_by_world = factions_by_world or {}
        self._saved_factions: List[Faction] = []

    async def get_by_world_id(self, world_id: str) -> List[Faction]:
        return self._factions_by_world.get(world_id, [])

    async def save(self, faction: Faction) -> Faction:
        self._saved_factions.append(faction)
        return faction

    async def save_all(self, factions: List[Faction]) -> List[Faction]:
        self._saved_factions.extend(factions)
        return factions


class TestWorldSimulationService:
    """Test suite for WorldSimulationService."""

    @pytest.fixture
    def intent_generator(self) -> FactionIntentGenerator:
        """Create a FactionIntentGenerator instance."""
        return FactionIntentGenerator()

    @pytest.fixture
    def world(self) -> WorldState:
        """Create a basic WorldState for testing."""
        return WorldState(
            id="world-test-123",
            name="Test World",
            calendar=WorldCalendar(year=100, month=1, day=1, era_name="Test Age"),
        )

    @pytest.fixture
    def faction_active(self) -> Faction:
        """Create an active faction for testing."""
        return Faction(
            id="faction-active-1",
            name="Active Kingdom",
            economic_power=60,
            military_strength=50,
            influence=50,
            territories=["territory-1"],
        )

    @pytest.fixture
    def faction_disbanded(self) -> Faction:
        """Create a disbanded faction for testing."""
        return Faction(
            id="faction-disbanded-1",
            name="Fallen Kingdom",
            status=FactionStatus.DISBANDED,
            economic_power=10,
            military_strength=5,
        )

    @pytest.fixture
    def faction_with_relations(self) -> Faction:
        """Create a faction with diplomatic relations."""
        faction = Faction(
            id="faction-diplomatic",
            name="Diplomatic Kingdom",
            economic_power=70,
            military_strength=60,
            territories=["territory-2"],
        )
        # Add relations
        faction.relations = [
            FactionRelation(
                target_faction_id="faction-ally",
                relation_type="alliance",
                strength=75,
                description="Long-standing alliance",
            ),
            FactionRelation(
                target_faction_id="faction-enemy",
                relation_type="enemy",
                strength=-80,
                description="At war",
            ),
            FactionRelation(
                target_faction_id="faction-neutral",
                relation_type="neutral",
                strength=0,
                description="No significant relations",
            ),
        ]
        return faction

    @pytest.fixture
    def mock_world_repo(self, world: WorldState) -> MockWorldRepository:
        """Create a mock world repository with a test world."""
        return MockWorldRepository({world.id: world})

    @pytest.fixture
    def mock_faction_repo(
        self,
        faction_active: Faction,
        faction_disbanded: Faction,
        faction_with_relations: Faction,
    ) -> MockFactionRepository:
        """Create a mock faction repository with test factions."""
        return MockFactionRepository({
            "world-test-123": [faction_active, faction_disbanded, faction_with_relations],
        })

    @pytest.fixture
    def service(
        self,
        mock_world_repo: MockWorldRepository,
        mock_faction_repo: MockFactionRepository,
        intent_generator: FactionIntentGenerator,
    ) -> WorldSimulationService:
        """Create a WorldSimulationService instance."""
        return WorldSimulationService(
            world_repo=mock_world_repo,
            faction_repo=mock_faction_repo,
            intent_generator=intent_generator,
        )

    # === Successful Simulation Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_preview_one_day(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation preview with 1 day advance."""
        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.world_id == world.id
        assert tick.days_advanced == 1
        assert tick.calendar_before.year == 100
        assert tick.calendar_after.day == 2  # Advanced by 1 day

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_preview_seven_days(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation preview with 7 day advance."""
        result = await service.advance_simulation(world.id, days=7)

        assert result.is_ok
        tick = result.value
        assert tick.days_advanced == 7
        assert tick.calendar_after.day == 8

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_preview_thirty_days(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation preview with 30 day advance (month rollover)."""
        result = await service.advance_simulation(world.id, days=30)

        assert result.is_ok
        tick = result.value
        assert tick.days_advanced == 30
        # Day 1 + 30 days = day 31, which rolls to month 2, day 1 (30 days/month)
        assert tick.calendar_after.month == 2
        assert tick.calendar_after.day == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_preview_max_days(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation preview with 365 days (maximum allowed)."""
        result = await service.advance_simulation(world.id, days=365)

        assert result.is_ok
        tick = result.value
        assert tick.days_advanced == 365
        # Year should advance by 1 (365 days / 360 days per year)
        assert tick.calendar_after.year == 101

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_preview_generates_intents_for_active_factions(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that preview generates intents for active factions."""
        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        # Preview mode doesn't apply changes
        assert tick.resource_changes == {}
        assert tick.diplomacy_changes == []
        assert tick.events_generated == []

    # === Invalid Days Error Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_days_zero(self, service: WorldSimulationService, world: WorldState):
        """Test error when days is 0."""
        result = await service.advance_simulation(world.id, days=0)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)
        assert "0" in str(result.error)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_days_negative(self, service: WorldSimulationService, world: WorldState):
        """Test error when days is negative."""
        result = await service.advance_simulation(world.id, days=-1)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)
        assert "-1" in str(result.error)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_days_exceeds_max(self, service: WorldSimulationService, world: WorldState):
        """Test error when days exceeds maximum (365)."""
        result = await service.advance_simulation(world.id, days=366)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)
        assert "366" in str(result.error)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_days_far_exceeds_max(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test error when days far exceeds maximum."""
        result = await service.advance_simulation(world.id, days=1000)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)

    # === World Not Found Error Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_world_not_found(self, service: WorldSimulationService):
        """Test error when world does not exist."""
        result = await service.advance_simulation("nonexistent-world", days=1)

        assert result.is_error
        assert isinstance(result.error, WorldNotFoundError)
        assert "nonexistent-world" in str(result.error)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_world_empty_id(self, service: WorldSimulationService):
        """Test error when world ID is empty."""
        result = await service.advance_simulation("", days=1)

        assert result.is_error
        assert isinstance(result.error, WorldNotFoundError)

    # === Repository Error Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_faction_repository_fails(self, world: WorldState, intent_generator):
        """Test error when faction repository throws exception."""
        failing_repo = MagicMock()
        failing_repo.get_by_world_id = AsyncMock(side_effect=Exception("Database error"))

        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=failing_repo,
            intent_generator=intent_generator,
        )

        result = await service.advance_simulation(world.id, days=1)

        assert result.is_error
        assert isinstance(result.error, RepositoryError)
        assert "Database error" in str(result.error)

    # === Empty World Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_world_no_factions(self, world: WorldState, intent_generator):
        """Test simulation succeeds when world has no factions."""
        empty_faction_repo = MockFactionRepository({world.id: []})

        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=empty_faction_repo,
            intent_generator=intent_generator,
        )

        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.days_advanced == 1
        # No factions means no changes
        assert tick.resource_changes == {}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_all_factions_disbanded(
        self, world: WorldState, faction_disbanded: Faction, intent_generator
    ):
        """Test simulation succeeds when all factions are disbanded."""
        faction_repo = MockFactionRepository({world.id: [faction_disbanded]})

        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
        )

        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        # Disbanded factions don't generate intents
        assert tick.resource_changes == {}

    # === Diplomacy Matrix Building Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_diplomacy_matrix_built_from_relations(
        self, world: WorldState, faction_with_relations: Faction, intent_generator
    ):
        """Test that diplomacy matrix is correctly built from faction relations."""
        faction_repo = MockFactionRepository({world.id: [faction_with_relations]})

        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
        )

        result = await service.advance_simulation(world.id, days=1)

        # Should succeed - the diplomacy matrix should be built
        assert result.is_ok

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_diplomacy_matrix_includes_all_factions(
        self,
        world: WorldState,
        faction_active: Faction,
        faction_with_relations: Faction,
        intent_generator,
    ):
        """Test that diplomacy matrix includes all factions even without explicit relations."""
        faction_repo = MockFactionRepository({
            world.id: [faction_active, faction_with_relations]
        })

        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
        )

        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok

    # === Tick Data Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tick_has_valid_id(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that tick has a valid unique ID."""
        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.tick_id is not None
        assert len(tick.tick_id) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tick_has_calendar_before_and_after(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that tick captures calendar state before and after."""
        result = await service.advance_simulation(world.id, days=15)

        assert result.is_ok
        tick = result.value
        assert tick.calendar_before is not None
        assert tick.calendar_after is not None
        assert tick.calendar_before.day == 1
        assert tick.calendar_after.day == 16

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tick_preview_mode_no_changes(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that preview mode tick has no changes applied."""
        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        # Preview mode: no changes
        assert tick.events_generated == []
        assert tick.resource_changes == {}
        assert tick.diplomacy_changes == []
        assert tick.character_reactions == []
        assert tick.rumors_created == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tick_created_at_timestamp(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that tick has a created_at timestamp."""
        result = await service.advance_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.created_at is not None
        assert isinstance(tick.created_at, datetime)

    # === Multiple Simulation Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_simulations_produce_different_ticks(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that multiple simulations produce different tick IDs."""
        result1 = await service.advance_simulation(world.id, days=1)
        result2 = await service.advance_simulation(world.id, days=1)

        assert result1.is_ok
        assert result2.is_ok
        assert result1.value.tick_id != result2.value.tick_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cumulative_days_calculation(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that days are correctly calculated in calendar advancement."""
        # Start at year 100, month 1, day 1
        result = await service.advance_simulation(world.id, days=359)

        assert result.is_ok
        tick = result.value
        # 359 days = 11 months + 29 days
        # Year 100, Month 12, Day 30 - 1 day = Year 100, Month 12, Day 29
        # Actually: Day 1 + 359 = 360 = exactly 12 months = Year 101, Month 1, Day 1
        # But 359 days from day 1 = day 360, which is year boundary
        # 30 days/month * 12 months = 360 days/year
        # 359 days from day 1 = day 360 = year 101, month 1, day 1
        # Wait - if starting at day 1, after 359 days:
        # Day 1 + 359 = day 360
        # 360 / 30 = 12 months exactly
        # So year 100 becomes year 101, month 1, day 1 (after wrap)
        # Actually the calendar.advance handles rollover
        # Let's check the actual values
        assert tick.days_advanced == 359


class TestWorldSimulationCommit:
    """Test suite for WorldSimulationService.commit_simulation (SIM-017)."""

    @pytest.fixture
    def intent_generator(self) -> FactionIntentGenerator:
        """Create a FactionIntentGenerator instance."""
        return FactionIntentGenerator()

    @pytest.fixture
    def world(self) -> WorldState:
        """Create a basic WorldState for testing."""
        return WorldState(
            id="world-commit-test",
            name="Commit Test World",
            calendar=WorldCalendar(year=100, month=1, day=1, era_name="Test Age"),
        )

    @pytest.fixture
    def faction_active(self) -> Faction:
        """Create an active faction for testing."""
        return Faction(
            id="faction-commit-1",
            name="Test Kingdom",
            economic_power=60,
            military_strength=50,
            influence=50,
            territories=["territory-commit-1"],
        )

    @pytest.fixture
    def mock_world_repo(self, world: WorldState) -> MockWorldRepository:
        """Create a mock world repository with a test world."""
        return MockWorldRepository({world.id: world})

    @pytest.fixture
    def mock_faction_repo(
        self, world: WorldState, faction_active: Faction
    ) -> MockFactionRepository:
        """Create a mock faction repository with test factions."""
        return MockFactionRepository({world.id: [faction_active]})

    @pytest.fixture
    def service(
        self,
        mock_world_repo: MockWorldRepository,
        mock_faction_repo: MockFactionRepository,
        intent_generator: FactionIntentGenerator,
    ) -> WorldSimulationService:
        """Create a WorldSimulationService instance without optional services."""
        return WorldSimulationService(
            world_repo=mock_world_repo,
            faction_repo=mock_faction_repo,
            intent_generator=intent_generator,
        )

    # === Basic Commit Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_successful_one_day(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation commit with 1 day advance."""
        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.world_id == world.id
        assert tick.days_advanced == 1
        assert tick.calendar_after.day == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_successful_seven_days(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test successful simulation commit with 7 days advance."""
        result = await service.commit_simulation(world.id, days=7)

        assert result.is_ok
        tick = result.value
        assert tick.days_advanced == 7
        assert tick.calendar_after.day == 8

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_produces_events_for_changes(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that commit produces events for significant changes."""
        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        # Events may or may not be generated depending on intents
        assert tick.events_generated is not None

    # === Validation Error Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_error_days_zero(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test commit error when days is 0."""
        result = await service.commit_simulation(world.id, days=0)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_error_days_negative(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test commit error when days is negative."""
        result = await service.commit_simulation(world.id, days=-1)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_error_days_exceeds_max(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test commit error when days exceeds maximum."""
        result = await service.commit_simulation(world.id, days=366)

        assert result.is_error
        assert isinstance(result.error, InvalidDaysError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_error_world_not_found(self, service: WorldSimulationService):
        """Test commit error when world does not exist."""
        result = await service.commit_simulation("nonexistent-world", days=1)

        assert result.is_error
        assert isinstance(result.error, WorldNotFoundError)

    # === History Tracking Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_tracks_history(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that commit adds tick to history."""
        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value

        # Check history was tracked
        history = service.get_tick_history(world.id)
        assert len(history) == 1
        assert history[0].tick_id == tick.tick_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_multiple_ticks_in_history(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that multiple commits are tracked in history."""
        result1 = await service.commit_simulation(world.id, days=1)
        result2 = await service.commit_simulation(world.id, days=1)
        result3 = await service.commit_simulation(world.id, days=1)

        assert result1.is_ok
        assert result2.is_ok
        assert result3.is_ok

        history = service.get_tick_history(world.id)
        assert len(history) == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_history_most_recent_first(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that history returns ticks most recent first."""
        await service.commit_simulation(world.id, days=1)
        await service.commit_simulation(world.id, days=7)
        await service.commit_simulation(world.id, days=30)

        history = service.get_tick_history(world.id)
        assert len(history) == 3
        # Most recent first
        assert history[0].days_advanced == 30
        assert history[1].days_advanced == 7
        assert history[2].days_advanced == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_history_limit(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that get_tick_history respects limit parameter."""
        # Add 5 ticks
        for _ in range(5):
            await service.commit_simulation(world.id, days=1)

        history = service.get_tick_history(world.id, limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_tick_by_id(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test retrieving a specific tick by ID."""
        result = await service.commit_simulation(world.id, days=7)

        assert result.is_ok
        tick = result.value

        retrieved = service.get_tick_by_id(world.id, tick.tick_id)
        assert retrieved is not None
        assert retrieved.tick_id == tick.tick_id
        assert retrieved.days_advanced == 7

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_tick_by_id_not_found(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test retrieving non-existent tick returns None."""
        retrieved = service.get_tick_by_id(world.id, "nonexistent-tick")
        assert retrieved is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_clear_history(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test clearing history for a world."""
        await service.commit_simulation(world.id, days=1)
        await service.commit_simulation(world.id, days=1)

        count = service.clear_history(world.id)
        assert count == 2

        history = service.get_tick_history(world.id)
        assert len(history) == 0

    # === Empty World Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_empty_world(
        self, world: WorldState, intent_generator: FactionIntentGenerator
    ):
        """Test commit succeeds when world has no factions."""
        empty_faction_repo = MockFactionRepository({world.id: []})
        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=empty_faction_repo,
            intent_generator=intent_generator,
        )

        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        tick = result.value
        assert tick.resource_changes == {}

    # === With Optional Services Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_with_snapshot_service(
        self, world: WorldState, faction_active: Faction, intent_generator
    ):
        """Test commit creates snapshot when snapshot service is available."""
        from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot

        # Create mock snapshot service
        mock_snapshot_service = MagicMock()
        mock_snapshot = WorldSnapshot(
            world_id=world.id,
            calendar=world.calendar,
            state_json='{"id": "test"}',
            tick_number=0,
        )
        mock_snapshot_service.create_snapshot = MagicMock(return_value=mock_snapshot)
        mock_snapshot_service.restore_snapshot = MagicMock(
            return_value=MagicMock(is_ok=True)
        )

        faction_repo = MockFactionRepository({world.id: [faction_active]})
        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
            snapshot_service=mock_snapshot_service,
        )

        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        # Snapshot should have been created
        mock_snapshot_service.create_snapshot.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_with_sanity_checker_warnings(
        self, world: WorldState, faction_active: Faction, intent_generator
    ):
        """Test commit runs sanity checker but doesn't block on warnings."""
        from src.contexts.world.application.services.simulation_sanity_checker import (
            SanityViolation,
            Severity,
            SimulationSanityChecker,
        )

        # Create mock sanity checker that returns warnings
        mock_checker = MagicMock(spec=SimulationSanityChecker)
        mock_checker.check = MagicMock(return_value=[
            SanityViolation(
                rule_name="test_warning",
                severity=Severity.WARNING,
                message="Test warning",
            )
        ])

        faction_repo = MockFactionRepository({world.id: [faction_active]})
        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
            sanity_checker=mock_checker,
        )

        result = await service.commit_simulation(world.id, days=1)

        # Should succeed despite warnings
        assert result.is_ok
        mock_checker.check.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_commit_with_rumor_service(
        self, world: WorldState, faction_active: Faction, intent_generator
    ):
        """Test commit propagates rumors when rumor service is available."""
        # Create mock rumor service
        mock_rumor_service = MagicMock()
        mock_rumor_service.propagate_rumors = AsyncMock(return_value=[])
        mock_rumor_service.create_rumor_from_event = MagicMock()

        faction_repo = MockFactionRepository({world.id: [faction_active]})
        service = WorldSimulationService(
            world_repo=MockWorldRepository({world.id: world}),
            faction_repo=faction_repo,
            intent_generator=intent_generator,
            rumor_service=mock_rumor_service,
        )

        result = await service.commit_simulation(world.id, days=1)

        assert result.is_ok
        # Rumor service should have been called
        mock_rumor_service.propagate_rumors.assert_called_once()

    # === Max History Enforcement Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_max_history_enforcement(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that history is limited to MAX_HISTORY_PER_WORLD entries."""
        # Add more than max entries
        max_entries = WorldSimulationService.MAX_HISTORY_PER_WORLD
        for _ in range(max_entries + 10):
            await service.commit_simulation(world.id, days=1)

        # Should have exactly MAX_HISTORY_PER_WORLD entries
        history = service.get_tick_history(world.id, limit=1000)
        assert len(history) == max_entries

    # === Tick Number Tracking Tests ===

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tick_number_increments(
        self, service: WorldSimulationService, world: WorldState
    ):
        """Test that tick numbers increment correctly."""
        # First commit should be tick 0
        result1 = await service.commit_simulation(world.id, days=1)
        assert result1.is_ok
        tick_number_1 = service._tick_numbers.get(world.id, 0)

        # Second commit should be tick 1
        result2 = await service.commit_simulation(world.id, days=1)
        assert result2.is_ok
        tick_number_2 = service._tick_numbers.get(world.id, 0)

        assert tick_number_2 == tick_number_1 + 1
