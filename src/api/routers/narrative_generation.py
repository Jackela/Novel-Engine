"""Narrative Generation Router - SSE streaming for story generation.

Provides a streaming endpoint for AI-powered narrative generation.
Uses MOCK_LLM environment variable to toggle between mock and real generation.

Why this router:
    Separates narrative generation streaming from the structure management API.
    The streaming endpoint enables real-time text generation in the editor UI,
    giving users immediate feedback as the story unfolds.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/narrative/generate", tags=["narrative-generation"])


# ============ Request/Response Models ============


class GenerateStreamRequest(BaseModel):
    """Request body for narrative streaming generation.

    Attributes:
        scene_id: Optional UUID of the scene to generate content for.
        prompt: Optional custom prompt for generation.
        context: Optional context string to inform generation.
        max_tokens: Maximum tokens to generate (controls length).
    """

    scene_id: Optional[str] = Field(
        default=None, description="UUID of the scene to generate content for"
    )
    prompt: Optional[str] = Field(
        default=None, description="Custom prompt for generation"
    )
    context: Optional[str] = Field(
        default=None, description="Context string to inform generation"
    )
    max_tokens: int = Field(
        default=500, ge=50, le=4000, description="Maximum tokens to generate"
    )


class StreamChunk(BaseModel):
    """A chunk of streamed narrative content.

    Attributes:
        type: Event type (chunk, done, error).
        content: The text content of this chunk.
        sequence: Sequence number for ordering.
    """

    type: str = Field(description="Event type: chunk, done, or error")
    content: str = Field(description="Text content of this chunk")
    sequence: int = Field(description="Sequence number for ordering")


# ============ Mock Story Content ============


MOCK_STORY_LINES = [
    "The ancient library stood silent, its towering shelves stretching toward vaulted ceilings lost in shadow.",
    "",
    "Elara traced her fingers along the spines of leather-bound tomes, each one whispering forgotten secrets.",
    "Dust motes danced in the thin beams of moonlight that pierced the stained glass windows above.",
    "",
    '"There must be something here," she murmured, pulling a weathered journal from its resting place.',
    "",
    "The pages crackled as she opened them, revealing handwriting that seemed to shift and writhe in the dim light.",
    "Words she couldn't quite read, in a language that felt both familiar and impossibly ancient.",
    "",
    "A cold draft swept through the chamber, extinguishing the candles she had so carefully lit.",
    "In the sudden darkness, she heard it—a sound like breathing, slow and deliberate, coming from somewhere deep within the stacks.",
    "",
    '"Who\'s there?" Her voice echoed off stone walls.',
    "",
    "No answer came, only the soft shuffle of pages turning themselves, as if the books themselves were awakening.",
    "Elara steeled herself and stepped forward into the darkness, knowing that some mysteries demanded to be pursued.",
    "",
    "The floor creaked beneath her feet, ancient wood protesting after centuries of silence.",
    "Her hand found the cold iron of her lantern, but she hesitated to light it.",
    "",
    "Sometimes, she had learned, the darkness revealed what the light would hide.",
]


def is_mock_mode() -> bool:
    """Check if MOCK_LLM environment variable is set to enable mock generation.

    Why this check:
        Allows seamless switching between mock (testing/development) and
        real LLM (production) modes without code changes.
    """
    mock_value = os.getenv("MOCK_LLM", "").lower()
    return mock_value in ("true", "1", "yes")


async def generate_mock_stream(
    max_tokens: int,
) -> AsyncIterator[tuple[str, int]]:
    """Generate mock story content line by line.

    Why async generator:
        Simulates the streaming behavior of a real LLM API,
        allowing the frontend to progressively display content.

    Args:
        max_tokens: Maximum tokens to generate (used to limit output).

    Yields:
        Tuples of (content, sequence_number) for each line.
    """
    total_chars = 0
    max_chars = max_tokens * 4  # Rough approximation: 1 token ≈ 4 chars

    for sequence, line in enumerate(MOCK_STORY_LINES):
        if total_chars >= max_chars:
            break

        # Simulate LLM generation delay (50-150ms per line)
        await asyncio.sleep(0.05 + (len(line) * 0.002))

        total_chars += len(line)
        yield line, sequence


async def _sse_generator(request: GenerateStreamRequest) -> AsyncIterator[str]:
    """Generate SSE-formatted events for narrative streaming.

    Why SSE format:
        Server-Sent Events provide a standardized, browser-native way
        to stream data from server to client with automatic reconnection.

    Args:
        request: The generation request with parameters.

    Yields:
        SSE-formatted event strings.
    """
    start_time = time.perf_counter()
    total_chars = 0
    chunk_count = 0

    try:
        if is_mock_mode():
            # Mock mode: Stream hardcoded story content
            logger.info(
                "Starting mock narrative stream",
                extra={"mock_mode": True, "max_tokens": request.max_tokens},
            )

            async for content, sequence in generate_mock_stream(request.max_tokens):
                chunk_count += 1
                total_chars += len(content)

                chunk = StreamChunk(
                    type="chunk",
                    content=content,
                    sequence=sequence,
                )
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        else:
            # Real LLM mode: Placeholder for actual implementation
            # In production, this would call the LLM service
            logger.warning(
                "Real LLM generation not implemented, falling back to mock",
                extra={"mock_mode": False},
            )

            # Fall back to mock for now
            async for content, sequence in generate_mock_stream(request.max_tokens):
                chunk_count += 1
                total_chars += len(content)

                chunk = StreamChunk(
                    type="chunk",
                    content=content,
                    sequence=sequence,
                )
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        # Send completion event
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
                "mock_mode": is_mock_mode(),
            },
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

        logger.info(
            "Narrative stream completed",
            extra={
                "chunk_count": chunk_count,
                "total_chars": total_chars,
                "generation_time_ms": generation_time_ms,
                "mock_mode": is_mock_mode(),
            },
        )

    except Exception:
        # Log full exception internally, send generic message to client
        logger.exception("Error during narrative streaming")
        error_data = {
            "type": "error",
            "content": "An error occurred during narrative generation. Please try again.",
            "sequence": -1,
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/stream")
async def stream_narrative_generation(
    request: GenerateStreamRequest,
) -> StreamingResponse:
    """Stream narrative generation via Server-Sent Events.

    This endpoint generates narrative content and streams it in real-time.
    When MOCK_LLM=true, it streams a hardcoded story line by line.
    Otherwise, it calls the actual LLM service (when implemented).

    Why streaming:
        Provides immediate feedback to users, reducing perceived latency.
        Users see content appearing as it's generated rather than
        waiting for the entire response.

    Request body:
        - scene_id: Optional UUID of the scene to generate for
        - prompt: Optional custom generation prompt
        - context: Optional context string
        - max_tokens: Maximum tokens (50-4000, default 500)

    Response: SSE stream with events:
        - type: "chunk" - Content chunk with sequence number
        - type: "done" - Generation complete with metadata
        - type: "error" - Error occurred during generation

    Environment:
        - MOCK_LLM=true: Use mock generation (for testing)
        - MOCK_LLM=false or unset: Use real LLM (when implemented)

    Example with curl:
        ```bash
        curl -N -X POST http://localhost:8000/api/narrative/generate/stream \\
            -H "Content-Type: application/json" \\
            -d '{"max_tokens": 500}'
        ```
    """
    # Sanitize scene_id for logging (truncate and remove unsafe characters)
    safe_scene_id = (
        request.scene_id[:64].replace("\n", " ").replace("\r", " ")
        if request.scene_id else None
    )
    logger.info(
        "Starting narrative generation stream",
        extra={
            "scene_id": safe_scene_id,
            "has_prompt": request.prompt is not None,
            "has_context": request.context is not None,
            "max_tokens": request.max_tokens,
            "mock_mode": is_mock_mode(),
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
