"""Test suite for RumorPropagator.

Tests the core rumor propagation algorithm.
"""

from typing import List

import pytest

from src.contexts.world.application.services.adjacency_cache import AdjacencyCache
from src.contexts.world.application.services.rumor_propagator import RumorPropagator
from src.contexts.world.domain.entities.rumor import (
    TRUTH_DECAY_PER_HOP,
    Rumor,
    RumorOrigin,
)


class MockLocationRepository:
    """Mock repository for testing."""

    def __init__(self, adjacency_map: dict[str, list[str]]) -> None:
        self.adjacency_map = adjacency_map

    async def find_adjacent(self, location_id: str) -> List[str]:
        """Mock find_adjacent method."""
        return self.adjacency_map.get(location_id, [])


class MockRumorRepository:
    """Mock rumor repository."""

    def __init__(self) -> None:
        self.deleted_ids: List[str] = []
        self.saved_rumors: List[Rumor] = []

    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        """Mock save_all method."""
        self.saved_rumors.extend(rumors)
        return rumors

    async def delete(self, rumor_id: str) -> bool:
        """Mock delete method."""
        self.deleted_ids.append(rumor_id)
        return True


class TestRumorPropagator:
    """Test cases for RumorPropagator."""

    @pytest.fixture
    def adjacency_map(self) -> dict[str, list[str]]:
        """Create test adjacency map."""
        return {
            "loc1": ["loc2", "loc3"],
            "loc2": ["loc4"],
            "loc3": ["loc4"],
            "loc4": ["loc5"],
            "loc5": [],
        }

    @pytest.fixture
    def mock_repo(self, adjacency_map: dict[str, list[str]]) -> MockLocationRepository:
        """Create mock repository."""
        return MockLocationRepository(adjacency_map)

    @pytest.fixture
    def cache(self, mock_repo: MockLocationRepository) -> AdjacencyCache:
        """Create adjacency cache."""
        return AdjacencyCache(mock_repo)

    @pytest.fixture
    def propagator(self, cache: AdjacencyCache) -> RumorPropagator:
        """Create propagator instance."""
        return RumorPropagator(cache)

    @pytest.fixture
    def sample_rumor(self) -> Rumor:
        """Create a sample rumor."""
        return Rumor(
            content="Test Rumor",
            truth_value=100,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc1",
            current_locations={"loc1"},
            spread_count=0,
        )

    @pytest.mark.asyncio
    async def test_propagate_to_adjacent(
        self, propagator: RumorPropagator, sample_rumor: Rumor
    ) -> None:
        """Test basic propagation to adjacent locations."""
        updated, deleted = await propagator.propagate([sample_rumor])

        assert len(updated) == 1
        assert len(deleted) == 0

        updated_rumor = updated[0]
        assert "loc2" in updated_rumor.current_locations
        assert "loc3" in updated_rumor.current_locations
        assert updated_rumor.spread_count == 2

    @pytest.mark.asyncio
    async def test_propagate_no_new_locations(
        self, mock_repo: MockLocationRepository
    ) -> None:
        """Test propagation when no new locations to spread to."""
        # Create isolated adjacency map where loc1 has no neighbors
        isolated_repo = MockLocationRepository(
            {
                "loc1": [],  # No neighbors
                "loc2": [],
            }
        )
        cache = AdjacencyCache(isolated_repo)
        propagator = RumorPropagator(cache)

        # Rumor at location with no adjacent locations
        rumor = Rumor(
            content="Stuck Rumor",
            truth_value=50,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc1",
            current_locations={"loc1"},
            spread_count=2,
        )

        updated, deleted = await propagator.propagate([rumor])

        assert len(updated) == 1
        updated_rumor = updated[0]
        assert updated_rumor.spread_count == 2  # No change
        assert updated_rumor.truth_value == 50  # No change

    @pytest.mark.asyncio
    async def test_propagate_truth_decay(
        self, propagator: RumorPropagator, sample_rumor: Rumor
    ) -> None:
        """Test truth value decay during propagation."""
        updated, _ = await propagator.propagate([sample_rumor])

        updated_rumor = updated[0]
        expected_truth = max(0, 100 - (TRUTH_DECAY_PER_HOP * 2))  # 2 new locations
        assert updated_rumor.truth_value == expected_truth

    @pytest.mark.asyncio
    async def test_propagate_rumor_dies(self, propagator: RumorPropagator) -> None:
        """Test that rumor dies when truth value reaches 0."""
        # Create rumor with low truth that will die
        rumor = Rumor(
            content="Dying Rumor",
            truth_value=15,  # Less than TRUTH_DECAY_PER_HOP * 2
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc1",
            current_locations={"loc1"},
            spread_count=0,
        )

        updated, deleted = await propagator.propagate([rumor])

        assert len(updated) == 0
        assert len(deleted) == 1
        assert deleted[0] == rumor.rumor_id

    @pytest.mark.asyncio
    async def test_propagate_multiple_rumors(self, propagator: RumorPropagator) -> None:
        """Test propagating multiple rumors."""
        rumors = [
            Rumor(
                content="Rumor 1",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
                current_locations={"loc1"},
            ),
            Rumor(
                content="Rumor 2",
                truth_value=80,
                origin_type=RumorOrigin.NPC,
                origin_location_id="loc4",
                current_locations={"loc4"},
            ),
        ]

        updated, deleted = await propagator.propagate(rumors)

        assert len(updated) == 2
        assert len(deleted) == 0

    @pytest.mark.asyncio
    async def test_propagate_empty_list(self, propagator: RumorPropagator) -> None:
        """Test propagating empty list."""
        updated, deleted = await propagator.propagate([])

        assert len(updated) == 0
        assert len(deleted) == 0

    @pytest.mark.asyncio
    async def test_delete_rumors_batch(self, propagator: RumorPropagator) -> None:
        """Test batch deletion of rumors."""
        mock_rumor_repo = MockRumorRepository()
        rumor_ids = ["rumor1", "rumor2", "rumor3"]

        deleted_count = await propagator.delete_rumors_batch(mock_rumor_repo, rumor_ids)

        assert deleted_count == 3
        assert len(mock_rumor_repo.deleted_ids) == 3
        assert "rumor1" in mock_rumor_repo.deleted_ids

    @pytest.mark.asyncio
    async def test_cache_stats(
        self, propagator: RumorPropagator, sample_rumor: Rumor
    ) -> None:
        """Test getting cache statistics."""
        await propagator.propagate([sample_rumor])

        stats = propagator.get_cache_stats()

        assert "cache_size" in stats
        assert stats["cache_size"] > 0

    @pytest.mark.asyncio
    async def test_chain_propagation(self, propagator: RumorPropagator) -> None:
        """Test chained propagation across multiple hops."""
        # First hop: loc1 -> loc2, loc3
        rumor1 = Rumor(
            content="Chain Rumor",
            truth_value=100,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc1",
            current_locations={"loc1"},
            spread_count=0,
        )

        updated1, _ = await propagator.propagate([rumor1])
        rumor_after_1 = updated1[0]

        # Second hop: loc2 -> loc4, loc3 -> loc4
        updated2, _ = await propagator.propagate([rumor_after_1])
        rumor_after_2 = updated2[0]

        assert "loc4" in rumor_after_2.current_locations
        # loc4 is adjacent to both loc2 and loc3, but should only be added once
        assert rumor_after_2.spread_count == 3  # loc2, loc3, loc4
