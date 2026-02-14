"""Scene generation router.

Provides endpoints for generating narrative scenes based on character context.
"""

from __future__ import annotations

import os

from fastapi import APIRouter

from src.api.schemas import (
    SceneGenerationRequest,
    SceneGenerationResponse,
)
from src.contexts.story.application.ports.scene_generator_port import (
    SceneGeneratorPort,
)
from src.contexts.story.application.services.scene_service import (
    DeterministicSceneGenerator,
)
from src.contexts.story.application.services.scene_service import (
    generate_scene as generate_scene_service,
)

router = APIRouter(tags=["generation"])


def _get_scene_generator() -> SceneGeneratorPort:
    """Get the appropriate scene generator based on configuration.

    This is the composition root for scene generation - it handles
    dependency injection of the appropriate generator implementation.
    """
    if os.getenv("ENABLE_LLM_GENERATION", "").lower() == "true":
        try:
            from src.contexts.story.infrastructure.generators.llm_scene_generator import (
                LLMSceneGenerator,
            )

            return LLMSceneGenerator()
        except Exception:
            return DeterministicSceneGenerator()
    return DeterministicSceneGenerator()


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
    generator = _get_scene_generator()
    result = generate_scene_service(
        character_context=request.character_context,
        scene_type=request.scene_type,
        tone=request.tone,
        generator=generator,
    )
    return SceneGenerationResponse(
        title=result.title,
        content=result.content,
        summary=result.summary,
        visual_prompt=result.visual_prompt,
    )
