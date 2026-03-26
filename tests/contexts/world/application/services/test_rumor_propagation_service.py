"""Integration test suite for RumorPropagationService.

Tests the main service that orchestrates rumor propagation.
"""

from typing import List

import pytest

from src.contexts.world.application.services import RumorPropagationService
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.history_event import (
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.entities.location import Location
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin


class MockLocationRepository:
    """Mock location repository."""

    def __init__(
        self, locations: List[Location], adjacency_map: dict[str, list[str]]
    ) -> None:
        self.locations = locations
        self.adjacency_map = adjacency_map

    async def get_by_id(self, location_id: str) -> Location | None:
        for loc in self.locations:
            if loc.id == location_id:
                return loc
        return None

    async def get_by_world_id(self, world_id: str) -> List[Location]:
        return [loc for loc in self.locations if loc.world_id == world_id]

    async def find_adjacent(self, location_id: str) -> List[str]:
        return self.adjacency_map.get(location_id, [])


class MockRumorRepository:
    """Mock rumor repository."""

    def __init__(self, rumors: List[Rumor]) -> None:
        self.rumors = {r.rumor_id: r for r in rumors}
        self.saved_rumors: List[Rumor] = []
        self.deleted_ids: List[str] = []

    async def get_active_rumors(self, world_id: str) -> List[Rumor]:
        return [r for r in self.rumors.values() if r.truth_value > 0]

    async def get_by_world_id(self, world_id: str) -> List[Rumor]:
        return list(self.rumors.values())

    async def save(self, rumor: Rumor) -> Rumor:
        self.rumors[rumor.rumor_id] = rumor
        self.saved_rumors.append(rumor)
        return rumor

    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        for r in rumors:
            self.rumors[r.rumor_id] = r
            self.saved_rumors.append(r)
        return rumors

    async def delete(self, rumor_id: str) -> bool:
        if rumor_id in self.rumors:
            del self.rumors[rumor_id]
            self.deleted_ids.append(rumor_id)
            return True
        return False


class TestRumorPropagationService:
    """Integration test cases for RumorPropagationService."""

    @pytest.fixture
    def world(self) -> WorldState:
        """Create a test world."""
        return WorldState(id="world1")

    @pytest.fixture
    def locations(self) -> List[Location]:
        """Create test locations."""
        return [
            Location(name="City A", id="loc1", world_id="world1"),
            Location(name="City B", id="loc2", world_id="world1"),
            Location(name="City C", id="loc3", world_id="world1"),
        ]

    @pytest.fixture
    def adjacency_map(self) -> dict[str, list[str]]:
        """Create adjacency map."""
        return {
            "loc1": ["loc2"],
            "loc2": ["loc1", "loc3"],
            "loc3": ["loc2"],
        }

    @pytest.fixture
    def location_repo(
        self, locations: List[Location], adjacency_map: dict[str, list[str]]
    ) -> MockLocationRepository:
        """Create location repository."""
        return MockLocationRepository(locations, adjacency_map)

    @pytest.fixture
    def rumor_repo(self) -> MockRumorRepository:
        """Create empty rumor repository."""
        return MockRumorRepository([])

    @pytest.fixture
    def service(
        self, location_repo: MockLocationRepository, rumor_repo: MockRumorRepository
    ) -> RumorPropagationService:
        """Create propagation service."""
        return RumorPropagationService(location_repo, rumor_repo)

    @pytest.mark.asyncio
    async def test_propagate_rumors_no_active(
        self, service: RumorPropagationService, world: WorldState
    ) -> None:
        """Test propagation with no active rumors."""
        result = await service.propagate_rumors(world)

        assert result.is_ok
        assert result.value == []

    @pytest.mark.asyncio
    async def test_propagate_rumors_success(
        self,
        service: RumorPropagationService,
        world: WorldState,
        rumor_repo: MockRumorRepository,
    ) -> None:
        """Test successful rumor propagation."""
        # Add an active rumor
        rumor = Rumor(
            content="Test Rumor",
            truth_value=100,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc1",
            current_locations={"loc1"},
            spread_count=0,
        )
        rumor_repo.rumors[rumor.rumor_id] = rumor

        result = await service.propagate_rumors(world)

        assert result.is_ok
        updated_rumors = result.value
        assert len(updated_rumors) == 1
        assert "loc2" in updated_rumors[0].current_locations
        assert len(rumor_repo.saved_rumors) == 1

    @pytest.mark.asyncio
    async def test_propagate_rumors_batch(
        self,
        service: RumorPropagationService,
        world: WorldState,
        rumor_repo: MockRumorRepository,
    ) -> None:
        """Test batch propagation."""
        # Add multiple rumors
        for i in range(3):
            rumor = Rumor(
                content=f"Rumor {i}",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
                current_locations={"loc1"},
                spread_count=0,
            )
            rumor_repo.rumors[rumor.rumor_id] = rumor

        result = await service.propagate_rumors_batch(world, batch_size=2)

        assert result.is_ok
        assert len(result.value) == 3

    @pytest.mark.asyncio
    async def test_create_rumor_from_event_success(
        self, service: RumorPropagationService, world: WorldState
    ) -> None:
        """Test creating rumor from event."""
        event = HistoryEvent(
            name="Great Battle",
            event_type=EventType.BATTLE,
            location_ids=["loc1"],
            impact_scope=ImpactScope.GLOBAL,
        )

        result = service.create_rumor_from_event(event, world)

        assert result.is_ok
        rumor = result.value
        assert rumor.content is not None
        assert rumor.truth_value == 90  # GLOBAL impact
        assert rumor.origin_location_id == "loc1"

    @pytest.mark.asyncio
    async def test_create_rumor_from_event_no_location(
        self, service: RumorPropagationService, world: WorldState
    ) -> None:
        """Test creating rumor from event without location."""
        event = HistoryEvent(
            name="Unknown Event",
            event_type=EventType.OTHER,
            location_ids=[],
            affected_location_ids=[],
        )

        result = service.create_rumor_from_event(event, world)

        assert not result.is_ok
        assert result.is_err

    @pytest.mark.asyncio
    async def test_create_rumor_affected_locations(
        self, service: RumorPropagationService, world: WorldState
    ) -> None:
        """Test creating rumor using affected locations."""
        event = HistoryEvent(
            name="Plague",
            event_type=EventType.DISASTER,
            location_ids=[],
            affected_location_ids=["loc2", "loc3"],
            impact_scope=ImpactScope.REGIONAL,
        )

        result = service.create_rumor_from_event(event, world)

        assert result.is_ok
        assert result.value.origin_location_id == "loc2"  # First affected location
        assert result.value.truth_value == 70  # REGIONAL impact

    def test_clear_adjacency_cache(self, service: RumorPropagationService) -> None:
        """Test clearing adjacency cache."""
        result = service.clear_adjacency_cache()

        assert result.is_ok

    def test_get_cache_stats(self, service: RumorPropagationService) -> None:
        """Test getting cache statistics."""
        result = service.get_cache_stats()

        assert result.is_ok
        stats = result.value
        assert "cache_size" in stats

    def test_get_statistics(
        self,
        service: RumorPropagationService,
    ) -> None:
        """Test getting rumor statistics."""
        rumors = [
            Rumor(
                content="Rumor 1",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
                spread_count=10,
            ),
            Rumor(
                content="Rumor 2",
                truth_value=0,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc2",
                spread_count=5,
            ),
        ]

        result = service.get_statistics(rumors)

        assert result.is_ok
        stats = result.value
        assert stats.total_rumors == 2
        assert stats.active_rumors == 1
        assert stats.dead_rumors == 1

    def test_placeholder_properties(self, service: RumorPropagationService) -> None:
        """Test placeholder properties."""
        assert service.total_rumors == 0
        assert service.avg_truth == 0.0
        assert service.most_spread is None

    def test_truth_by_impact_mapping(self) -> None:
        """Test that truth values are correctly mapped to impact scopes."""
        assert RumorPropagationService.TRUTH_BY_IMPACT[ImpactScope.GLOBAL] == 90
        assert RumorPropagationService.TRUTH_BY_IMPACT[ImpactScope.REGIONAL] == 70
        assert RumorPropagationService.TRUTH_BY_IMPACT[ImpactScope.LOCAL] == 50

    def test_default_batch_size(self) -> None:
        """Test default batch size."""
        assert RumorPropagationService.DEFAULT_BATCH_SIZE == 500
