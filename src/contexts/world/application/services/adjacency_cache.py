"""Adjacency cache management for rumor propagation.

This module provides caching for location adjacency lookups during
rumor propagation to avoid repeated database queries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, Set, runtime_checkable

import structlog

logger = structlog.get_logger()


@runtime_checkable
class ILocationRepository(Protocol):
    """Protocol for location repository."""

    async def find_adjacent(self, location_id: str) -> List[str]:
        """Find all locations adjacent to the given location.

        Args:
            location_id: ID of the location to find adjacents for

        Returns:
            List of adjacent location IDs
        """
        ...


@dataclass
class AdjacencyCache:
    """Manages caching of world graph adjacency lists.

    This cache is designed to improve performance during rumor propagation
    by avoiding repeated database lookups for location adjacency information.

    Attributes:
        _location_repo: Repository for fetching adjacency data
        _cache: In-memory cache of location_id -> adjacent location_ids
    """

    _location_repo: ILocationRepository
    _cache: Dict[str, List[str]] = field(default_factory=dict)

    async def get_neighbors(self, location_id: str) -> List[str]:
        """Get cached neighbors or fetch from repository.

        Args:
            location_id: ID of the location to get neighbors for

        Returns:
            List of adjacent location IDs
        """
        if location_id in self._cache:
            logger.debug(
                "adjacency_cache_hit",
                location_id=location_id,
            )
            return self._cache[location_id]

        neighbors = await self._fetch_from_repo(location_id)
        self._cache[location_id] = neighbors
        return neighbors

    async def get_neighbors_batch(self, location_ids: Set[str]) -> Dict[str, List[str]]:
        """Get neighbors for multiple locations, using cache where available.

        Args:
            location_ids: Set of location IDs to get neighbors for

        Returns:
            Dictionary mapping location_id to list of adjacent location IDs
        """
        result: Dict[str, List[str]] = {}
        uncached_ids: List[str] = []

        for location_id in location_ids:
            if location_id in self._cache:
                result[location_id] = self._cache[location_id]
            else:
                uncached_ids.append(location_id)

        if uncached_ids:
            await self._prefetch_adjacency(set(uncached_ids))
            for location_id in uncached_ids:
                result[location_id] = self._cache.get(location_id, [])

        return result

    def invalidate(self, location_id: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            location_id: Specific location ID to invalidate, or None to clear all
        """
        if location_id:
            self._cache.pop(location_id, None)
            logger.debug(
                "adjacency_cache_invalidate",
                location_id=location_id,
            )
        else:
            cache_size = len(self._cache)
            self._cache.clear()
            logger.debug(
                "adjacency_cache_cleared",
                previous_size=cache_size,
            )

    async def _fetch_from_repo(self, location_id: str) -> List[str]:
        """Fetch adjacency data from repository.

        Args:
            location_id: ID of the location to fetch adjacents for

        Returns:
            List of adjacent location IDs
        """
        try:
            adjacent = await self._location_repo.find_adjacent(location_id)
            logger.debug(
                "adjacency_fetched",
                location_id=location_id,
                neighbor_count=len(adjacent),
            )
            return adjacent
        except Exception as e:
            logger.warning(
                "adjacency_fetch_failed",
                location_id=location_id,
                error=str(e),
            )
            return []

    async def _prefetch_adjacency(self, location_ids: Set[str]) -> None:
        """Pre-fetch and cache adjacency for multiple locations.

        Args:
            location_ids: Set of location IDs to prefetch
        """
        for location_id in location_ids:
            if location_id not in self._cache:
                try:
                    adjacent = await self._location_repo.find_adjacent(location_id)
                    self._cache[location_id] = adjacent
                except Exception as e:
                    logger.warning(
                        "adjacency_prefetch_failed",
                        location_id=location_id,
                        error=str(e),
                    )
                    self._cache[location_id] = []

        logger.debug(
            "adjacency_prefetch_complete",
            prefetched_count=len(location_ids),
            cache_size=len(self._cache),
        )

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._cache),
            "cached_location_count": len(self._cache),
        }

    @property
    def size(self) -> int:
        """Get the current cache size.

        Returns:
            Number of entries in the cache
        """
        return len(self._cache)
