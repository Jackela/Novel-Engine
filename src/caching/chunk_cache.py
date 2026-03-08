"""Shared in-memory chunk cache used for SSE replay streams."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Dict, List


@dataclass
class Chunk:
    """A single SSE chunk.
    
    Attributes:
        seq: Sequence number for ordering
        data: Chunk payload
        ts: Timestamp
    """
    seq: int
    data: str
    ts: float


@dataclass
class _StreamState:
    """Internal state for a stream.
    
    Attributes:
        chunks: List of chunks in order
        complete: Whether stream is complete
        created_ts: Stream creation timestamp
    """
    chunks: List[Chunk]
    complete: bool = False
    created_ts: float = 0.0


class ChunkCache:
    """Cache for SSE stream chunks enabling replay.
    
    Stores chunks per stream key with TTL-based cleanup.
    """
    
    def __init__(self, ttl_seconds: int = 300) -> None:
        """Initialize chunk cache.
        
        Args:
            ttl_seconds: Stream TTL after completion
        """
        self.ttl_seconds = ttl_seconds
        self._streams: Dict[str, _StreamState] = {}
        self._lock = RLock()

    def add_chunk(self, key: str, seq: int, data: str) -> None:
        """Add a chunk to a stream.
        
        Args:
            key: Stream identifier
            seq: Sequence number
            data: Chunk data
        """
        with self._lock:
            stream = self._streams.setdefault(
                key, _StreamState(chunks=[], created_ts=time.time())
            )
            stream.chunks.append(Chunk(seq=seq, data=data, ts=time.time()))
            stream.chunks.sort(key=lambda c: c.seq)
            self._cleanup_expired()

    def mark_complete(self, key: str) -> None:
        """Mark a stream as complete.
        
        Args:
            key: Stream identifier
        """
        with self._lock:
            stream = self._streams.setdefault(
                key, _StreamState(chunks=[], created_ts=time.time())
            )
            stream.complete = True
            self._cleanup_expired()

    def get_since(self, key: str, last_seq: int) -> List[Chunk]:
        """Get chunks since a sequence number.
        
        Args:
            key: Stream identifier
            last_seq: Last received sequence number
            
        Returns:
            List of chunks with seq > last_seq
        """
        with self._lock:
            stream = self._streams.get(key)
            if not stream:
                return []
            return [chunk for chunk in stream.chunks if chunk.seq > last_seq]

    def is_complete(self, key: str) -> bool:
        """Check if a stream is complete.
        
        Args:
            key: Stream identifier
            
        Returns:
            True if stream is marked complete
        """
        with self._lock:
            stream = self._streams.get(key)
            return bool(stream and stream.complete)

    def _cleanup_expired(self) -> None:
        """Remove expired completed streams."""
        if not self.ttl_seconds:
            return
        cutoff = time.time() - self.ttl_seconds
        keys_to_delete = [
            key
            for key, stream in self._streams.items()
            if stream.complete and stream.chunks and stream.chunks[-1].ts < cutoff
        ]
        for key in keys_to_delete:
            self._streams.pop(key, None)
