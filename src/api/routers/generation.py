from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import (
    CharacterGenerationRequest,
    CharacterGenerationResponse,
    CharacterProfileGenerationRequest,
    CharacterProfileGenerationResponse,
)
from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    generate_character_card,
)
from src.contexts.world.infrastructure.generators.character_profile_generator import (
    CharacterProfileGenerator,
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


@router.post("/generation/character-profile", response_model=CharacterProfileGenerationResponse)
async def generate_character_profile(
    request: CharacterProfileGenerationRequest,
) -> CharacterProfileGenerationResponse:
    """Generate a detailed character profile using LLM or mock generator.

    Uses the CharacterProfileGenerator which automatically selects between
    LLM (Gemini) and mock generator based on the MOCK_LLM environment variable.

    Args:
        request: Character profile generation parameters including name,
                 archetype, and optional context.

    Returns:
        Generated character profile with aliases, traits, appearance,
        backstory, motivations, and quirks.
    """
    generator = CharacterProfileGenerator()
    result = generator.generate_character_profile(
        name=request.name,
        archetype=request.archetype,
        context=request.context or "",
    )
    return CharacterProfileGenerationResponse(
        name=result.name,
        aliases=result.aliases,
        archetype=result.archetype,
        traits=result.traits,
        appearance=result.appearance,
        backstory=result.backstory,
        motivations=result.motivations,
        quirks=result.quirks,
    )
