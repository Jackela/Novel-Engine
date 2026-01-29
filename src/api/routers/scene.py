"""Scene generation router.

Provides endpoints for generating narrative scenes based on character context.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    SceneGenerationRequest,
    SceneGenerationResponse,
)

router = APIRouter(tags=["generation"])


@router.post("/generation/scene", response_model=SceneGenerationResponse)
async def generate_scene(
    request: SceneGenerationRequest,
) -> SceneGenerationResponse:
    """Generate a scene based on character context.

    Args:
        request: Scene generation parameters including character context,
                 scene type, and optional tone.

    Returns:
        Generated scene with title, content, summary, and visual prompt.

    Raises:
        HTTPException: 501 Not Implemented (stub endpoint).

    NOTE: Stub implementation - returns 501 until LLM integration is complete.
    """
    raise HTTPException(
        status_code=501,
        detail="Scene generation not yet implemented",
    )
