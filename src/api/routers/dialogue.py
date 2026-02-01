"""
Character Dialogue API Router

This module provides endpoints for generating character dialogue
using AI-powered voice synthesis based on character psychology,
traits, and speaking style.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_optional_workspace_id
from src.api.schemas import (
    DialogueGenerationRequest,
    DialogueGenerationResponse,
)
from src.contexts.world.infrastructure.generators.llm_world_generator import (
    CharacterData,
    LLMWorldGenerator,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dialogue"])


def _get_generator(request: Request) -> LLMWorldGenerator:
    """Get or create the LLM World Generator from app state."""
    generator = getattr(request.app.state, "llm_world_generator", None)
    if generator is None:
        generator = LLMWorldGenerator()
        request.app.state.llm_world_generator = generator
    return generator


def _fetch_character_data(
    request: Request,
    character_id: str,
    workspace_id: Optional[str],
    payload: DialogueGenerationRequest,
) -> CharacterData:
    """Fetch character data from store or build from request overrides.

    Why this function exists: The dialogue generator needs CharacterData,
    which can come from either stored character records or from request
    overrides. This centralizes the logic for building that data.
    """
    # Check for override data in request
    if payload.psychology_override or payload.traits_override or payload.speaking_style_override:
        psychology_dict = None
        if payload.psychology_override:
            psychology_dict = {
                "openness": payload.psychology_override.openness,
                "conscientiousness": payload.psychology_override.conscientiousness,
                "extraversion": payload.psychology_override.extraversion,
                "agreeableness": payload.psychology_override.agreeableness,
                "neuroticism": payload.psychology_override.neuroticism,
            }
        return CharacterData(
            name=f"Character-{character_id}",
            psychology=psychology_dict,
            traits=payload.traits_override,
            speaking_style=payload.speaking_style_override,
        )

    # Try to get character from workspace store
    store = getattr(request.app.state, "workspace_character_store", None)
    if workspace_id and store:
        try:
            record = store.get(workspace_id, character_id)
            if record:
                # Extract data from workspace character record
                structured_data = record.get("structured_data", {}) or {}
                psychology = structured_data.get("psychology")
                traits = structured_data.get("traits", [])
                speaking_style = structured_data.get("speaking_style")

                return CharacterData(
                    name=record.get("name", f"Character-{character_id}"),
                    psychology=psychology,
                    traits=traits if traits else None,
                    speaking_style=speaking_style,
                )
        except ValueError:
            pass

    # Fallback: return minimal character data
    return CharacterData(name=f"Character-{character_id}")


@router.post(
    "/dialogue/generate",
    response_model=DialogueGenerationResponse,
)
async def generate_dialogue(
    request: Request,
    payload: DialogueGenerationRequest,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> DialogueGenerationResponse:
    """Generate dialogue in character voice.

    Uses the character's psychology (Big Five traits), character traits,
    and speaking style to produce authentic dialogue that sounds like
    the character would naturally speak.

    The context parameter describes the situation the character is responding
    to, such as "A stranger asks for directions" or "Their rival insults them".
    The optional mood parameter can modify normal speech patterns.
    """
    log = logger.bind(
        character_id=payload.character_id,
        mood=payload.mood,
        has_overrides=bool(
            payload.psychology_override
            or payload.traits_override
            or payload.speaking_style_override
        ),
    )
    log.info("Generating character dialogue")

    generator = _get_generator(request)
    character_data = _fetch_character_data(
        request, payload.character_id, workspace_id, payload
    )

    result = generator.generate_dialogue(
        character=character_data,
        context=payload.context,
        mood=payload.mood,
    )

    if result.is_error():
        log.warning("Dialogue generation returned error", error=result.error)

    return DialogueGenerationResponse(
        dialogue=result.dialogue,
        tone=result.tone,
        internal_thought=result.internal_thought,
        body_language=result.body_language,
        character_id=payload.character_id,
        error=result.error,
    )
