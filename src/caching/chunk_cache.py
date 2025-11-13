"""Shared in-memory chunk cache used for SSE replay streams."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Dict, List


@dataclass
class Chunk:
    seq: int
    data: str
    ts: float


@dataclass
class _StreamState:
    chunks: List[Chunk]
    complete: bool = False
    created_ts: float = 0.0


class ChunkCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._streams: Dict[str, _StreamState] = {}
        self._lock = RLock()

    def add_chunk(self, key: str, seq: int, data: str) -> None:
        with self._lock:
            stream = self._streams.setdefault(
                key, _StreamState(chunks=[], created_ts=time.time())
            )
            stream.chunks.append(Chunk(seq=seq, data=data, ts=time.time()))
            stream.chunks.sort(key=lambda c: c.seq)
            self._cleanup_expired()

    def mark_complete(self, key: str) -> None:
        with self._lock:
            stream = self._streams.setdefault(
                key, _StreamState(chunks=[], created_ts=time.time())
            )
            stream.complete = True
            self._cleanup_expired()

    def get_since(self, key: str, last_seq: int) -> List[Chunk]:
        with self._lock:
            stream = self._streams.get(key)
            if not stream:
                return []
            return [chunk for chunk in stream.chunks if chunk.seq > last_seq]

    def is_complete(self, key: str) -> bool:
        with self._lock:
            stream = self._streams.get(key)
            return bool(stream and stream.complete)

    def _cleanup_expired(self) -> None:
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
