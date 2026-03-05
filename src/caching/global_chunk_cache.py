"""Singleton chunk cache used by FastAPI streaming endpoints.

Provides a module-level singleton for SSE chunk caching across
the FastAPI application.

Example:
    >>> from src.caching.global_chunk_cache import chunk_cache
    >>> chunk_cache.add_chunk("stream-1", 1, "data")
"""

from .chunk_cache import ChunkCache

chunk_cache = ChunkCache()

__all__ = ["chunk_cache"]
