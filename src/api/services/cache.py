from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, Iterable

from fastapi import HTTPException

from src.caching.global_chunk_cache import chunk_cache
from src.caching.registry import invalidate_by_tags
from src.metrics.global_metrics import metrics as global_metrics

logger = logging.getLogger(__name__)


def get_cache_metrics() -> Dict[str, Any]:
    try:
        return global_metrics.snapshot().to_dict()
    except Exception as exc:
        logger.error("metrics snapshot error: %s", exc)
        raise HTTPException(status_code=500, detail="metrics error") from exc


def invalidate_cache(tags_all_of: Iterable[str]) -> Dict[str, Any]:
    try:
        removed = invalidate_by_tags(list(tags_all_of))
        return {"removed": int(removed)}
    except Exception as exc:
        logger.error("invalidation error: %s", exc)
        raise HTTPException(status_code=500, detail="invalidation error") from exc


def append_chunk(key: str, seq: int, data: str) -> Dict[str, Any]:
    try:
        chunk_cache.add_chunk(key, seq, data)
        return {"ok": True}
    except Exception as exc:
        logger.error("chunk append error: %s", exc)
        raise HTTPException(status_code=500, detail="chunk append error") from exc


def mark_chunk_complete(key: str) -> Dict[str, Any]:
    try:
        chunk_cache.mark_complete(key)
        return {"ok": True}
    except Exception as exc:
        logger.error("chunk complete error: %s", exc)
        raise HTTPException(status_code=500, detail="chunk complete error") from exc


async def stream_chunks(key: str) -> AsyncIterator[str]:
    last_seq = -1
    idle = 0
    while True:
        chunks = chunk_cache.get_since(key, last_seq)
        for chunk in chunks:
            last_seq = chunk.seq
            yield f"data: {chunk.data}\n\n"
        if chunk_cache.is_complete(key):
            break
        await asyncio.sleep(0.2)
        idle += 1
        if idle > 300:  # ~60s timeout
            break
    yield "event: done\ndata: complete\n\n"

