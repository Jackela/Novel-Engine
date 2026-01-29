"""Scene generation router.

Provides endpoints for generating narrative scenes based on character context.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import (
    SceneGenerationRequest,
    SceneGenerationResponse,
)
from src.contexts.story.application.services.scene_service import (
    generate_scene as generate_scene_service,
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
    """
    result = generate_scene_service(
        character_context=request.character_context,
        scene_type=request.scene_type,
        tone=request.tone,
    )
    return SceneGenerationResponse(
        title=result.title,
        content=result.content,
        summary=result.summary,
        visual_prompt=result.visual_prompt,
    )
