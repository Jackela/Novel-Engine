"""Test suite for AdjacencyCache.

Tests the caching mechanism for location adjacency lookups.
"""

from typing import List

import pytest

from src.contexts.world.application.services.adjacency_cache import AdjacencyCache


class MockLocationRepository:
    """Mock repository for testing."""

    def __init__(self, adjacency_map: dict[str, list[str]]) -> None:
        self.adjacency_map = adjacency_map
        self.call_count = 0

    async def find_adjacent(self, location_id: str) -> List[str]:
        """Mock find_adjacent method."""
        self.call_count += 1
        return self.adjacency_map.get(location_id, [])


class TestAdjacencyCache:
    """Test cases for AdjacencyCache."""

    @pytest.fixture
    def mock_repo(self) -> MockLocationRepository:
        """Create a mock repository."""
        adjacency_map = {
            "loc1": ["loc2", "loc3"],
            "loc2": ["loc1", "loc4"],
            "loc3": ["loc1"],
            "loc4": ["loc2"],
        }
        return MockLocationRepository(adjacency_map)

    @pytest.fixture
    def cache(self, mock_repo: MockLocationRepository) -> AdjacencyCache:
        """Create an AdjacencyCache instance."""
        return AdjacencyCache(mock_repo)

    @pytest.mark.asyncio
    async def test_get_neighbors_from_repo(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test fetching neighbors from repository."""
        neighbors = await cache.get_neighbors("loc1")

        assert neighbors == ["loc2", "loc3"]
        assert mock_repo.call_count == 1

    @pytest.mark.asyncio
    async def test_get_neighbors_from_cache(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test fetching neighbors from cache."""
        await cache.get_neighbors("loc1")
        await cache.get_neighbors("loc1")

        assert mock_repo.call_count == 1  # Should not call repo twice

    @pytest.mark.asyncio
    async def test_get_neighbors_batch(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test batch fetching neighbors."""
        location_ids = {"loc1", "loc2"}
        result = await cache.get_neighbors_batch(location_ids)

        assert "loc1" in result
        assert "loc2" in result
        assert result["loc1"] == ["loc2", "loc3"]
        assert result["loc2"] == ["loc1", "loc4"]

    @pytest.mark.asyncio
    async def test_invalidate_single(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test invalidating a single cache entry."""
        await cache.get_neighbors("loc1")
        cache.invalidate("loc1")
        await cache.get_neighbors("loc1")

        assert mock_repo.call_count == 2  # Should call repo again

    @pytest.mark.asyncio
    async def test_invalidate_all(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test clearing entire cache."""
        await cache.get_neighbors("loc1")
        await cache.get_neighbors("loc2")
        cache.invalidate()
        await cache.get_neighbors("loc1")

        assert mock_repo.call_count == 3  # Initial 2 + 1 after clear

    @pytest.mark.asyncio
    async def test_empty_neighbors(self, cache: AdjacencyCache) -> None:
        """Test fetching neighbors for unknown location."""
        neighbors = await cache.get_neighbors("unknown")

        assert neighbors == []

    @pytest.mark.asyncio
    async def test_stats(
        self, cache: AdjacencyCache, mock_repo: MockLocationRepository
    ) -> None:
        """Test cache statistics."""
        await cache.get_neighbors("loc1")
        await cache.get_neighbors("loc2")

        stats = cache.get_stats()

        assert stats["cache_size"] == 2
        assert cache.size == 2

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test error handling during fetch."""

        class ErrorRepo:
            async def find_adjacent(self, location_id: str) -> List[str]:
                raise ValueError("Database error")

        cache = AdjacencyCache(ErrorRepo())
        neighbors = await cache.get_neighbors("loc1")

        assert neighbors == []
