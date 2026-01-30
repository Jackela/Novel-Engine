"""
Narratives Router - Streaming narrative generation endpoints.

Provides SSE (Server-Sent Events) streaming for real-time narrative generation.
"""
from __future__ import annotations

import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    NarrativeStreamChunk,
    NarrativeStreamRequest,
)
from src.contexts.narratives.application.services.narrative_stream_service import (
    generate_narrative_stream,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Narratives"])


async def _sse_generator(request: NarrativeStreamRequest) -> AsyncIterator[str]:
    """
    Generate SSE-formatted events from narrative stream.

    Why SSE: Provides a standardized way to stream data from server to client.
    The text/event-stream format is well-supported by browsers and libraries.
    """
    start_time = time.perf_counter()
    total_chars = 0
    chunk_count = 0

    try:
        # Convert Pydantic model to dict for the service layer
        world_context_dict = {
            "characters": [c.model_dump() for c in request.world_context.characters],
            "locations": [loc.model_dump() for loc in request.world_context.locations],
            "entities": [e.model_dump() for e in request.world_context.entities],
            "current_scene": request.world_context.current_scene,
            "narrative_style": request.world_context.narrative_style,
        }

        # Generate narrative chunks
        for chunk in generate_narrative_stream(
            prompt=request.prompt,
            world_context=world_context_dict,
            chapter_title=request.chapter_title,
            tone=request.tone,
            max_tokens=request.max_tokens,
        ):
            chunk_count += 1
            total_chars += len(chunk.content)

            # Format as SSE event
            sse_data = NarrativeStreamChunk(
                type="chunk",
                content=chunk.content,
                sequence=chunk.sequence,
            )
            yield f"data: {json.dumps(sse_data.model_dump())}\n\n"

        # Send completion event with metadata
        end_time = time.perf_counter()
        generation_time_ms = int((end_time - start_time) * 1000)

        completion_data = {
            "type": "done",
            "content": "",
            "sequence": chunk_count,
            "metadata": {
                "total_chunks": chunk_count,
                "total_characters": total_chars,
                "generation_time_ms": generation_time_ms,
                "model_used": "deterministic-fallback",
            },
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

        logger.info(
            "Narrative stream completed",
            extra={
                "chunk_count": chunk_count,
                "total_chars": total_chars,
                "generation_time_ms": generation_time_ms,
            },
        )

    except Exception as exc:
        logger.exception("Error during narrative streaming")
        error_data = {
            "type": "error",
            "content": str(exc),
            "sequence": -1,
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/narratives/stream")
async def stream_narrative(request: NarrativeStreamRequest) -> StreamingResponse:
    """
    Stream narrative generation via Server-Sent Events.

    This endpoint accepts a prompt and world context, then streams
    generated narrative content in real-time. The response uses
    SSE format for browser-native streaming support.

    Why streaming: Provides immediate feedback to users, reducing
    perceived latency. Users see content appearing as it's generated
    rather than waiting for the entire response.

    Request body:
        - prompt: The narrative direction/prompt
        - world_context: Characters, locations, and entities for context
        - chapter_title: Optional chapter title
        - tone: Optional tone modifier (dark, hopeful, mysterious)
        - max_tokens: Maximum tokens to generate (100-8000)

    Response: SSE stream with events:
        - type: "chunk" - Content chunk with sequence number
        - type: "done" - Generation complete with metadata
        - type: "error" - Error occurred during generation
    """
    logger.info(
        "Starting narrative stream",
        extra={
            "prompt_length": len(request.prompt),
            "has_chapter_title": request.chapter_title is not None,
            "tone": request.tone,
            "character_count": len(request.world_context.characters),
        },
    )

    return StreamingResponse(
        _sse_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
