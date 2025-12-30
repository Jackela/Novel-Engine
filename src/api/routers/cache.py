from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.schemas import ChunkInRequest, InvalidationRequest
from src.api.services.cache import (
    append_chunk,
    get_cache_metrics,
    invalidate_cache,
    mark_chunk_complete,
    stream_chunks,
)

router = APIRouter(tags=["cache"])


@router.get("/cache/metrics")
async def cache_metrics():
    return get_cache_metrics()


@router.post("/cache/invalidate")
async def cache_invalidate(req: InvalidationRequest):
    return invalidate_cache(req.all_of)


@router.post("/cache/chunk/{key}")
async def cache_chunk_append(key: str, req: ChunkInRequest):
    return append_chunk(key, req.seq, req.data)


@router.post("/cache/chunk/{key}/complete")
async def cache_chunk_complete(key: str):
    return mark_chunk_complete(key)


@router.get("/cache/stream/{key}")
async def cache_stream(key: str):
    return StreamingResponse(stream_chunks(key), media_type="text/event-stream")
