"""Singleton chunk cache used by FastAPI streaming endpoints."""

from .chunk_cache import ChunkCache

chunk_cache = ChunkCache()

__all__ = ["chunk_cache"]
