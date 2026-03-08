"""Metrics collection and reporting interfaces.

Provides abstractions for tracking cache performance, cost savings,
and system-wide metrics across the Novel Engine.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class MetricsSnapshot:
    """Immutable snapshot of system metrics at a point in time.
    
    Captures all cache and cost-related metrics for reporting
    and monitoring purposes.
    
    Attributes:
        ts: ISO8601 timestamp of the snapshot
        cache_exact_hits: Number of exact cache matches
        cache_semantic_hits: Number of semantic cache matches
        cache_tool_hits: Number of tool result cache hits
        cache_size: Current number of entries in cache
        evictions: Number of entries evicted from cache
        invalidations: Number of entries invalidated
        single_flight_merged: Requests merged via single-flight pattern
        replay_hits: SSE replay cache hits
        saved_tokens: Tokens saved through caching
        saved_cost: Estimated cost saved through caching
    """
    ts: str
    cache_exact_hits: int
    cache_semantic_hits: int
    cache_tool_hits: int
    cache_size: int
    evictions: int
    invalidations: int
    single_flight_merged: int
    replay_hits: int
    saved_tokens: int
    saved_cost: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary.
        
        Returns:
            Dictionary with all metric fields
        """
        return self.__dict__.copy()


class MetricsPublisher:
    """Abstract interface for publishing metrics.
    
    Implementations record various system events and aggregate
    them into metrics snapshots for reporting.
    """
    
    def record_hit(self, kind: str) -> None:
        """Record a cache hit.
        
        Args:
            kind: Type of hit ('exact', 'semantic', or 'tool')
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def record_eviction(self, count: int = 1) -> None:
        """Record cache eviction(s).
        
        Args:
            count: Number of entries evicted (default: 1)
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def record_invalidation(self, count: int = 1) -> None:
        """Record cache invalidation(s).
        
        Args:
            count: Number of entries invalidated (default: 1)
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def record_single_flight_merged(self, count: int = 1) -> None:
        """Record single-flight merged requests.
        
        Args:
            count: Number of merged requests (default: 1)
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def record_replay_hit(self, count: int = 1) -> None:
        """Record SSE replay cache hits.
        
        Args:
            count: Number of replay hits (default: 1)
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def record_savings(self, tokens: int, cost: float) -> None:
        """Record cost savings from caching.
        
        Args:
            tokens: Number of tokens saved
            cost: Estimated monetary cost saved
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def snapshot(self) -> MetricsSnapshot:
        """Get current metrics snapshot.
        
        Returns:
            MetricsSnapshot with all recorded metrics
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
