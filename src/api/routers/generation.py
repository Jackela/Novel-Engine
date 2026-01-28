from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import (
    CharacterGenerationRequest,
    CharacterGenerationResponse,
)
from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    generate_character_card,
)

router = APIRouter(tags=["generation"])


@router.post("/generation/character", response_model=CharacterGenerationResponse)
async def generate_character(
    request: CharacterGenerationRequest,
) -> CharacterGenerationResponse:
    """Generate a character card using deterministic fallback logic."""
    result = generate_character_card(
        CharacterGenerationInput(
            concept=request.concept,
            archetype=request.archetype,
            tone=request.tone,
        ),
    )
    return CharacterGenerationResponse(
        name=result.name,
        tagline=result.tagline,
        bio=result.bio,
        visual_prompt=result.visual_prompt,
        traits=result.traits,
    )
