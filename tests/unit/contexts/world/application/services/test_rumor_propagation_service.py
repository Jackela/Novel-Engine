#!/usr/bin/env python3
"""Tests for RumorPropagationService.

Unit tests covering:
- Rumor propagation to adjacent locations
- Truth decay during spread
- Rumor creation from events
- Event type templates
- Statistics calculation
- Error handling
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock aioredis before any imports that might use it
sys.modules["aioredis"] = MagicMock()

from src.contexts.world.application.services.rumor_propagation_service import (
    ILocationRepository,
    IRumorRepository,
    RumorPropagationService,
    RumorStatistics,
)
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_location_repo() -> MagicMock:
    """Create mock location repository."""
    repo = MagicMock(spec=ILocationRepository)
    repo.find_adjacent = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_world_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_rumor_repo() -> MagicMock:
    """Create mock rumor repository."""
    repo = MagicMock(spec=IRumorRepository)
    repo.get_active_rumors = AsyncMock(return_value=[])
    repo.save = AsyncMock(side_effect=lambda r: r)
    repo.save_all = AsyncMock(side_effect=lambda rs: rs)
    repo.delete = AsyncMock(return_value=True)
    repo.get_by_world_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(
    mock_location_repo: MagicMock,
    mock_rumor_repo: MagicMock,
) -> RumorPropagationService:
    """Create RumorPropagationService with mock repos."""
    return RumorPropagationService(
        location_repo=mock_location_repo,
        rumor_repo=mock_rumor_repo,
    )


@pytest.fixture
def calendar() -> WorldCalendar:
    """Create a test calendar."""
    return WorldCalendar(
        year=1042,
        month=3,
        day=15,
        era_name="Third Age",
    )


@pytest.fixture
def world_state(calendar: WorldCalendar) -> WorldState:
    """Create a test WorldState."""
    world = MagicMock(spec=WorldState)
    world.id = "world-123"
    world.calendar = calendar
    return world


@pytest.fixture
def base_rumor(calendar: WorldCalendar) -> Rumor:
    """Create a base rumor for testing."""
    return Rumor(
        rumor_id="rumor-001",
        content="Word spreads of conflict between two great powers.",
        truth_value=80,
        origin_type=RumorOrigin.EVENT,
        source_event_id="event-001",
        origin_location_id="loc-capital",
        current_locations={"loc-capital"},
        created_date=calendar,
        spread_count=0,
    )


@pytest.fixture
def history_event() -> HistoryEvent:
    """Create a test history event."""
    return HistoryEvent(
        id="event-001",
        name="The Great War",
        description="A devastating conflict between kingdoms.",
        event_type=EventType.WAR,
        significance=EventSignificance.MAJOR,
        outcome=EventOutcome.MIXED,
        date_description="Year 1042 of the Third Age",
        location_ids=["loc-capital"],
        faction_ids=["faction-a", "faction-b"],
        impact_scope=ImpactScope.GLOBAL,
    )


# ============================================================================
# Test propagate_rumors
# ============================================================================


class TestPropagateRumors:
    """Tests for propagate_rumors method."""

    @pytest.mark.asyncio
    async def test_propagate_no_active_rumors(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_rumor_repo: MagicMock,
    ) -> None:
        """Should return empty list when no active rumors exist."""
        mock_rumor_repo.get_active_rumors.return_value = []

        result = await service.propagate_rumors(world_state)

        assert result.is_ok
        assert result.unwrap() == []
        mock_rumor_repo.get_active_rumors.assert_called_once_with(world_state.id)

    @pytest.mark.asyncio
    async def test_propagate_single_rumor_to_adjacent(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        base_rumor: Rumor,
    ) -> None:
        """Should spread rumor to adjacent locations."""
        # Setup: rumor at capital, adjacent to town
        mock_rumor_repo.get_active_rumors.return_value = [base_rumor]
        mock_location_repo.find_adjacent.return_value = ["loc-town"]

        result = await service.propagate_rumors(world_state)

        # Should have spread to town
        assert result.is_ok
        rumors = result.unwrap()
        assert len(rumors) == 1
        updated = rumors[0]
        assert "loc-town" in updated.current_locations
        assert "loc-capital" in updated.current_locations
        assert updated.spread_count == 1
        assert updated.truth_value == 70  # 80 - 10 decay

    @pytest.mark.asyncio
    async def test_propagate_to_multiple_adjacent(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        base_rumor: Rumor,
    ) -> None:
        """Should spread to all adjacent locations."""
        mock_rumor_repo.get_active_rumors.return_value = [base_rumor]
        mock_location_repo.find_adjacent.return_value = ["loc-town", "loc-village", "loc-fort"]

        result = await service.propagate_rumors(world_state)

        assert result.is_ok
        rumors = result.unwrap()
        assert len(rumors) == 1
        updated = rumors[0]
        # Should have spread to all three (each counts as one spread)
        assert len(updated.current_locations) == 4  # origin + 3 new
        assert updated.spread_count == 3
        # Truth decayed for each spread: 80 - 10*3 = 50
        assert updated.truth_value == 50

    @pytest.mark.asyncio
    async def test_propagate_does_not_duplicate(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        calendar: WorldCalendar,
    ) -> None:
        """Should not spread to locations already reached."""
        # Create rumor already at capital and town (frozen, so create new instance)
        rumor_at_multiple = Rumor(
            rumor_id="rumor-001",
            content="Word spreads of conflict between two great powers.",
            truth_value=80,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-001",
            origin_location_id="loc-capital",
            current_locations={"loc-capital", "loc-town"},
            created_date=calendar,
            spread_count=0,
        )
        mock_rumor_repo.get_active_rumors.return_value = [rumor_at_multiple]
        # Adjacent to capital includes town (already reached)
        mock_location_repo.find_adjacent.return_value = ["loc-town", "loc-village"]

        result = await service.propagate_rumors(world_state)

        assert result.is_ok
        rumors = result.unwrap()
        updated = rumors[0]
        # Should only spread to village (town already reached)
        assert len(updated.current_locations) == 3
        assert "loc-village" in updated.current_locations
        assert updated.spread_count == 1

    @pytest.mark.asyncio
    async def test_propagate_multiple_rumors(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        base_rumor: Rumor,
        calendar: WorldCalendar,
    ) -> None:
        """Should handle multiple rumors spreading."""
        rumor2 = Rumor(
            rumor_id="rumor-002",
            content="Merchants whisper about new trade routes.",
            truth_value=60,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-002",
            origin_location_id="loc-port",
            current_locations={"loc-port"},
            created_date=calendar,
            spread_count=0,
        )
        mock_rumor_repo.get_active_rumors.return_value = [base_rumor, rumor2]
        mock_location_repo.find_adjacent.return_value = ["loc-market"]

        result = await service.propagate_rumors(world_state)

        assert result.is_ok
        rumors = result.unwrap()
        assert len(rumors) == 2
        # Both rumors should be updated
        mock_rumor_repo.save_all.assert_called_once()
        saved = mock_rumor_repo.save_all.call_args[0][0]
        assert len(saved) == 2

    @pytest.mark.asyncio
    async def test_propagate_rumor_dies_at_zero_truth(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        calendar: WorldCalendar,
    ) -> None:
        """Should delete rumor when truth reaches 0."""
        # Start with low truth that will reach 0 after spread
        dying_rumor = Rumor(
            rumor_id="rumor-dying",
            content="Fading rumor...",
            truth_value=5,  # After one spread: -5 -> 0 (clamped)
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-003",
            origin_location_id="loc-far",
            current_locations={"loc-far"},
            created_date=calendar,
            spread_count=0,
        )
        mock_rumor_repo.get_active_rumors.return_value = [dying_rumor]
        mock_location_repo.find_adjacent.return_value = ["loc-near"]

        result = await service.propagate_rumors(world_state)

        # Rumor should be deleted (not in result)
        assert result.is_ok
        rumors = result.unwrap()
        assert len(rumors) == 0
        mock_rumor_repo.delete.assert_called_once_with("rumor-dying")

    @pytest.mark.asyncio
    async def test_propagate_handles_adjacent_error(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_location_repo: MagicMock,
        mock_rumor_repo: MagicMock,
        calendar: WorldCalendar,
    ) -> None:
        """Should continue propagation if adjacent lookup fails."""
        # Create rumor at two locations (frozen, so create new instance)
        rumor_at_multiple = Rumor(
            rumor_id="rumor-001",
            content="Word spreads of conflict between two great powers.",
            truth_value=80,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-001",
            origin_location_id="loc-capital",
            current_locations={"loc-capital", "loc-port"},
            created_date=calendar,
            spread_count=0,
        )
        mock_rumor_repo.get_active_rumors.return_value = [rumor_at_multiple]
        # First call fails, second succeeds
        mock_location_repo.find_adjacent.side_effect = [
            Exception("DB error"),
            ["loc-town"],
        ]

        result = await service.propagate_rumors(world_state)

        # Should still propagate from successful location
        assert result.is_ok
        rumors = result.unwrap()
        assert len(rumors) == 1

    @pytest.mark.asyncio
    async def test_propagate_handles_repo_error(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
        mock_rumor_repo: MagicMock,
    ) -> None:
        """Should return error on repository error."""
        mock_rumor_repo.get_active_rumors.side_effect = Exception("DB error")

        result = await service.propagate_rumors(world_state)

        assert result.is_error


# ============================================================================
# Test create_rumor_from_event
# ============================================================================


class TestCreateRumorFromEvent:
    """Tests for create_rumor_from_event method."""

    def test_create_from_war_event(
        self,
        service: RumorPropagationService,
        history_event: HistoryEvent,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with war template."""
        result = service.create_rumor_from_event(history_event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.source_event_id == history_event.id
        assert "conflict" in rumor.content.lower()
        assert rumor.truth_value == 90  # GLOBAL impact
        assert rumor.origin_location_id == "loc-capital"
        assert "loc-capital" in rumor.current_locations

    def test_create_from_trade_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with trade template."""
        event = HistoryEvent(
            id="event-trade",
            name="New Trade Route",
            description="A new trade route established.",
            event_type=EventType.TRADE,
            date_description="Year 1042",
            location_ids=["loc-port"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "merchants" in rumor.content.lower()
        assert "trade" in rumor.content.lower()
        assert rumor.truth_value == 70  # REGIONAL impact

    def test_create_from_death_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with death template."""
        event = HistoryEvent(
            id="event-death",
            name="King's Passing",
            description="The king has died.",
            event_type=EventType.DEATH,
            date_description="Year 1042",
            location_ids=["loc-castle"],
            key_figures=["King Aldric"],
            impact_scope=ImpactScope.GLOBAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "king aldric" in rumor.content.lower()
        assert "passing" in rumor.content.lower()

    def test_create_from_birth_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with birth template."""
        event = HistoryEvent(
            id="event-birth",
            name="Royal Birth",
            description="A prince is born.",
            event_type=EventType.BIRTH,
            date_description="Year 1042",
            key_figures=["Prince Edric"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "birth" in rumor.content.lower()
        assert "prince edric" in rumor.content.lower()

    def test_create_from_marriage_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with marriage template."""
        event = HistoryEvent(
            id="event-marriage",
            name="Royal Wedding",
            description="A royal marriage.",
            event_type=EventType.MARRIAGE,
            date_description="Year 1042",
            key_figures=["Prince Edric", "Princess Arya"],
            impact_scope=ImpactScope.GLOBAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "union" in rumor.content.lower()
        # Both names should appear
        assert "prince edric" in rumor.content.lower()

    def test_create_from_alliance_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with alliance template."""
        event = HistoryEvent(
            id="event-alliance",
            name="Great Alliance",
            description="Kingdoms unite.",
            event_type=EventType.ALLIANCE,
            date_description="Year 1042",
            faction_ids=["faction-a", "faction-b"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "alliance" in rumor.content.lower()

    def test_create_from_disaster_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with disaster template."""
        event = HistoryEvent(
            id="event-disaster",
            name="Great Flood",
            description="Flooding devastates the coast.",
            event_type=EventType.DISASTER,
            date_description="Year 1042",
            location_ids=["loc-coast"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "disaster" in rumor.content.lower() or "terrifying" in rumor.content.lower()

    def test_create_from_discovery_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with discovery template."""
        event = HistoryEvent(
            id="event-discovery",
            name="Ancient Ruins Found",
            description="Ancient ruins discovered.",
            event_type=EventType.DISCOVERY,
            date_description="Year 1042",
            location_ids=["loc-ruins"],
            impact_scope=ImpactScope.LOCAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "discovery" in rumor.content.lower() or "whispers" in rumor.content.lower()
        assert rumor.truth_value == 50  # LOCAL impact

    def test_create_from_revolution_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with revolution template."""
        event = HistoryEvent(
            id="event-revolution",
            name="The Uprising",
            description="People rise up.",
            event_type=EventType.REVOLUTION,
            date_description="Year 1042",
            location_ids=["loc-city"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "uprising" in rumor.content.lower() or "revolution" in rumor.content.lower()

    def test_create_from_miracle_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with miracle template."""
        event = HistoryEvent(
            id="event-miracle",
            name="Divine Blessing",
            description="A miracle occurred.",
            event_type=EventType.MIRACLE,
            date_description="Year 1042",
            location_ids=["loc-temple"],
            impact_scope=ImpactScope.GLOBAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "miracle" in rumor.content.lower()

    def test_create_from_magical_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with magical template."""
        event = HistoryEvent(
            id="event-magical",
            name="Arcane Surge",
            description="Magical energy released.",
            event_type=EventType.MAGICAL,
            date_description="Year 1042",
            location_ids=["loc-tower"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "magical" in rumor.content.lower()

    def test_create_from_coronation_event(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with coronation template."""
        event = HistoryEvent(
            id="event-coronation",
            name="Crown Prince Crowned",
            description="A new king crowned.",
            event_type=EventType.CORONATION,
            date_description="Year 1042",
            key_figures=["King Edric II"],
            impact_scope=ImpactScope.GLOBAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert "coronation" in rumor.content.lower()

    def test_create_from_unknown_event_type(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should create rumor with fallback template for unknown types."""
        event = HistoryEvent(
            id="event-unknown",
            name="Something Happened",
            description="Something occurred.",
            event_type=EventType.POLITICAL,  # Has generic template
            date_description="Year 1042",
            location_ids=["loc-somewhere"],
            impact_scope=ImpactScope.LOCAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.content  # Should have some content
        assert rumor.truth_value == 50

    def test_create_uses_affected_location_ids(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should prefer affected_location_ids over location_ids."""
        event = HistoryEvent(
            id="event-test",
            name="Test Event",
            description="Test.",
            event_type=EventType.WAR,
            date_description="Year 1042",
            location_ids=["loc-where"],
            affected_location_ids=["loc-affected"],
            impact_scope=ImpactScope.LOCAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.origin_location_id == "loc-affected"

    def test_create_fallback_to_location_ids(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should use location_ids if no affected_location_ids."""
        event = HistoryEvent(
            id="event-test",
            name="Test Event",
            description="Test.",
            event_type=EventType.WAR,
            date_description="Year 1042",
            location_ids=["loc-where"],
            impact_scope=ImpactScope.LOCAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.origin_location_id == "loc-where"

    def test_create_fallback_to_unknown_location(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should use 'unknown' if no locations."""
        event = HistoryEvent(
            id="event-test",
            name="Test Event",
            description="Test.",
            event_type=EventType.WAR,
            date_description="Year 1042",
            impact_scope=ImpactScope.LOCAL,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.origin_location_id == "unknown"

    def test_create_with_no_impact_scope(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should use LOCAL truth value if no impact_scope."""
        event = HistoryEvent(
            id="event-test",
            name="Test Event",
            description="Test.",
            event_type=EventType.WAR,
            date_description="Year 1042",
            location_ids=["loc-test"],
            impact_scope=None,
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.truth_value == 50  # Default LOCAL

    def test_create_sets_created_date_from_world(
        self,
        service: RumorPropagationService,
        world_state: WorldState,
    ) -> None:
        """Should set created_date from world calendar."""
        event = HistoryEvent(
            id="event-test",
            name="Test Event",
            description="Test.",
            event_type=EventType.WAR,
            date_description="Year 1042",
            location_ids=["loc-test"],
        )

        result = service.create_rumor_from_event(event, world_state)

        assert result.is_ok
        rumor = result.unwrap()
        assert rumor.created_date == world_state.calendar


# ============================================================================
# Test get_statistics
# ============================================================================


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_empty_rumors(self, service: RumorPropagationService) -> None:
        """Should return zero statistics for empty list."""
        result = service.get_statistics([])

        assert result.is_ok
        stats = result.unwrap()
        assert stats.total_rumors == 0
        assert stats.active_rumors == 0
        assert stats.avg_truth == 0.0
        assert stats.most_spread is None
        assert stats.dead_rumors == 0

    def test_single_active_rumor(
        self,
        service: RumorPropagationService,
        base_rumor: Rumor,
    ) -> None:
        """Should calculate stats for single rumor."""
        result = service.get_statistics([base_rumor])

        assert result.is_ok
        stats = result.unwrap()
        assert stats.total_rumors == 1
        assert stats.active_rumors == 1
        assert stats.avg_truth == 80.0
        assert stats.most_spread == base_rumor
        assert stats.dead_rumors == 0

    def test_multiple_active_rumors(
        self,
        service: RumorPropagationService,
        base_rumor: Rumor,
        calendar: WorldCalendar,
    ) -> None:
        """Should calculate average truth correctly."""
        rumor2 = Rumor(
            rumor_id="rumor-002",
            content="Second rumor",
            truth_value=60,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-002",
            origin_location_id="loc-b",
            current_locations={"loc-b"},
            created_date=calendar,
            spread_count=5,
        )

        result = service.get_statistics([base_rumor, rumor2])

        assert result.is_ok
        stats = result.unwrap()
        assert stats.total_rumors == 2
        assert stats.active_rumors == 2
        assert stats.avg_truth == 70.0  # (80 + 60) / 2
        assert stats.most_spread == rumor2  # Higher spread_count

    def test_dead_rumors_excluded_from_avg(
        self,
        service: RumorPropagationService,
        base_rumor: Rumor,
        calendar: WorldCalendar,
    ) -> None:
        """Should exclude dead rumors from average calculation."""
        dead_rumor = Rumor(
            rumor_id="rumor-dead",
            content="Dead rumor",
            truth_value=0,  # Dead
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-003",
            origin_location_id="loc-c",
            current_locations={"loc-c"},
            created_date=calendar,
            spread_count=10,
        )

        result = service.get_statistics([base_rumor, dead_rumor])

        assert result.is_ok
        stats = result.unwrap()
        assert stats.total_rumors == 2
        assert stats.active_rumors == 1
        assert stats.avg_truth == 80.0  # Only base_rumor
        assert stats.dead_rumors == 1
        # Dead rumor has higher spread but should still be most_spread
        assert stats.most_spread == dead_rumor

    def test_all_dead_rumors(
        self,
        service: RumorPropagationService,
        calendar: WorldCalendar,
    ) -> None:
        """Should handle all dead rumors."""
        dead1 = Rumor(
            rumor_id="dead-1",
            content="Dead 1",
            truth_value=0,
            origin_type=RumorOrigin.UNKNOWN,
            source_event_id=None,
            origin_location_id="loc-a",
            current_locations={"loc-a"},
            created_date=calendar,
        )
        dead2 = Rumor(
            rumor_id="dead-2",
            content="Dead 2",
            truth_value=0,
            origin_type=RumorOrigin.UNKNOWN,
            source_event_id=None,
            origin_location_id="loc-b",
            current_locations={"loc-b"},
            created_date=calendar,
        )

        result = service.get_statistics([dead1, dead2])

        assert result.is_ok
        stats = result.unwrap()
        assert stats.active_rumors == 0
        assert stats.avg_truth == 0.0
        assert stats.dead_rumors == 2

    def test_rounded_average(
        self,
        service: RumorPropagationService,
        calendar: WorldCalendar,
    ) -> None:
        """Should round average to 2 decimal places."""
        rumors = [
            Rumor(
                rumor_id=f"rumor-{i}",
                content=f"Rumor {i}",
                truth_value=33 + i,  # 33, 34, 35
                origin_type=RumorOrigin.EVENT,
                source_event_id=f"event-{i}",
                origin_location_id=f"loc-{i}",
                current_locations={f"loc-{i}"},
                created_date=calendar,
            )
            for i in range(3)
        ]

        result = service.get_statistics(rumors)

        # (33 + 34 + 35) / 3 = 34.0
        assert result.is_ok
        stats = result.unwrap()
        assert stats.avg_truth == 34.0


# ============================================================================
# Test RumorStatistics dataclass
# ============================================================================


class TestRumorStatistics:
    """Tests for RumorStatistics dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        stats = RumorStatistics()

        assert stats.total_rumors == 0
        assert stats.active_rumors == 0
        assert stats.avg_truth == 0.0
        assert stats.most_spread is None
        assert stats.dead_rumors == 0

    def test_custom_values(self, base_rumor: Rumor) -> None:
        """Should accept custom values."""
        stats = RumorStatistics(
            total_rumors=10,
            active_rumors=8,
            avg_truth=65.5,
            most_spread=base_rumor,
            dead_rumors=2,
        )

        assert stats.total_rumors == 10
        assert stats.active_rumors == 8
        assert stats.avg_truth == 65.5
        assert stats.most_spread == base_rumor
        assert stats.dead_rumors == 2


# ============================================================================
# Test helper methods
# ============================================================================


class TestHelperMethods:
    """Tests for private helper methods."""

    def test_format_faction_list_empty(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle empty faction list."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            faction_ids=[],
        )

        result = service._format_faction_list(event)
        assert result == "unknown parties"

    def test_format_faction_list_single(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle single faction."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            faction_ids=["faction-a"],
        )

        result = service._format_faction_list(event)
        assert result == "an unknown faction"

    def test_format_faction_list_two(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle two factions."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            faction_ids=["faction-a", "faction-b"],
        )

        result = service._format_faction_list(event)
        assert result == "two great powers"

    def test_format_faction_list_many(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle many factions."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            faction_ids=["a", "b", "c", "d", "e"],
        )

        result = service._format_faction_list(event)
        assert result == "5 factions"

    def test_format_location_list_empty(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle empty location list."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
        )

        result = service._format_location_list(event)
        assert result == "an unknown location"

    def test_format_location_list_single(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle single location."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            location_ids=["loc-a"],
        )

        result = service._format_location_list(event)
        assert result == "a distant land"

    def test_format_location_list_many(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Should handle many locations."""
        event = HistoryEvent(
            id="event-test",
            name="Test",
            event_type=EventType.WAR,
            date_description="Year 1",
            location_ids=["loc-a", "loc-b", "loc-c"],
        )

        result = service._format_location_list(event)
        assert result == "several locations"


# ============================================================================
# Test properties (placeholder implementations)
# ============================================================================


class TestProperties:
    """Tests for placeholder properties."""

    def test_total_rumors_property(self, service: RumorPropagationService) -> None:
        """total_rumors should return placeholder."""
        assert service.total_rumors == 0

    def test_avg_truth_property(self, service: RumorPropagationService) -> None:
        """avg_truth should return placeholder."""
        assert service.avg_truth == 0.0

    def test_most_spread_property(self, service: RumorPropagationService) -> None:
        """most_spread should return placeholder."""
        assert service.most_spread is None
