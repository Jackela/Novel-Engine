from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Protocol


@dataclass(frozen=True)
class CharacterGenerationInput:
    concept: str
    archetype: str
    tone: str | None = None


@dataclass(frozen=True)
class CharacterGenerationResult:
    name: str
    tagline: str
    bio: str
    visual_prompt: str
    traits: List[str]


class CharacterGeneratorPort(Protocol):
    def generate(self, request: CharacterGenerationInput) -> CharacterGenerationResult:
        """Generate a character card from structured input."""


def _get_mock_template(archetype: str | None) -> dict:
    archetype_key = (archetype or "").strip().lower()
    templates = {
        "hero": {
            "name": "Astra Vale",
            "tagline": "A reluctant beacon in a broken world.",
            "bio": (
                "Astra is driven by a quiet resolve to protect the vulnerable, "
                "even when the odds are impossible."
            ),
            "traits": ["resilient", "empathetic", "principled"],
            "visual_prompt": (
                "heroic figure in weathered armor, soft cyan glow, determined gaze"
            ),
        },
        "antihero": {
            "name": "Kael Riven",
            "tagline": "The blade that cuts both ways.",
            "bio": (
                "Kael walks the line between survival and redemption, making brutal "
                "choices to keep the darkness at bay."
            ),
            "traits": ["cynical", "resourceful", "driven"],
            "visual_prompt": (
                "shadowed wanderer, scarred cloak, neon rim light, sharp silhouette"
            ),
        },
        "mentor": {
            "name": "Elder Suri",
            "tagline": "The wisdom that steadies the storm.",
            "bio": (
                "Suri teaches by example, guiding new heroes with patience "
                "and a steady hand."
            ),
            "traits": ["wise", "calm", "strategic"],
            "visual_prompt": (
                "serene elder with etched staff, soft gold accents, composed posture"
            ),
        },
        "villain": {
            "name": "Vesper Kain",
            "tagline": "Order forged through fear.",
            "bio": (
                "Vesper believes chaos is humanity's default and wields fear "
                "as the only true discipline."
            ),
            "traits": ["calculating", "ruthless", "charismatic"],
            "visual_prompt": (
                "regal antagonist, crimson highlights, angular armor, cold expression"
            ),
        },
    }
    return templates.get(
        archetype_key,
        {
            "name": "Nova Quinn",
            "tagline": "An uncharted spark in the system.",
            "bio": "Nova adapts quickly, turning unfamiliar terrain into opportunity.",
            "traits": ["adaptive", "curious", "grounded"],
            "visual_prompt": (
                "lone explorer, muted neon palette, tactical gear, soft haze"
            ),
        },
    )


class DeterministicCharacterGenerator:
    def generate(self, request: CharacterGenerationInput) -> CharacterGenerationResult:
        template = _get_mock_template(request.archetype)
        tone_suffix = (
            f" Tone: {request.tone.strip()}."
            if request.tone and request.tone.strip()
            else ""
        )
        concept_snippet = (
            request.concept.strip() if request.concept else "Unknown origin"
        )

        return CharacterGenerationResult(
            name=template["name"],
            tagline=template["tagline"],
            bio=f"{template['bio']} Concept: {concept_snippet}.{tone_suffix}",
            visual_prompt=template["visual_prompt"],
            traits=list(template["traits"]),
        )


def _select_default_generator() -> CharacterGeneratorPort:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return DeterministicCharacterGenerator()
    if os.getenv("ENABLE_LLM_GENERATION", "").lower() == "true":
        try:
            from src.contexts.character.infrastructure.generators.llm_character_generator import (
                LLMCharacterGenerator,
            )

            return LLMCharacterGenerator()
        except Exception:
            return DeterministicCharacterGenerator()
    return DeterministicCharacterGenerator()


def generate_character_card(
    request: CharacterGenerationInput,
    generator: CharacterGeneratorPort | None = None,
) -> CharacterGenerationResult:
    """Generate a character card via the configured generator."""
    return (generator or _select_default_generator()).generate(request)
