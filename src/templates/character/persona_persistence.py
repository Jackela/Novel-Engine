#!/usr/bin/env python3
"""
Persona persistence and file I/O.
"""

import json
import logging
from pathlib import Path

from src.templates.context_renderer import RenderFormat

from .persona_models import (
    CharacterArchetype,
    CharacterContextProfile,
    CharacterPersona,
)

logger = logging.getLogger(__name__)


class PersonaPersistence:
    """Handles persona file persistence and discovery."""

    def __init__(self, personas_dir: Path):
        self.personas_dir = personas_dir

    def _discover_personas(self):
        """Discover enhanced existing personas from files"""
        for persona_file in self.personas_directory.glob("*.json"):
            try:
                with open(persona_file, "r", encoding="utf-8") as f:
                    persona_data = json.load(f)

                persona = CharacterPersona(
                    persona_id=persona_data["persona_id"],
                    name=persona_data["name"],
                    archetype=CharacterArchetype(persona_data["archetype"]),
                    description=persona_data.get("description", ""),
                    personality_traits=persona_data.get("personality_traits", []),
                    speech_patterns=persona_data.get("speech_patterns", {}),
                    behavioral_preferences=persona_data.get(
                        "behavioral_preferences", {}
                    ),
                    memory_priorities=persona_data.get("memory_priorities", {}),
                    emotional_tendencies=persona_data.get("emotional_tendencies", {}),
                    faction_data=persona_data.get("faction_data", []),
                    core_beliefs=persona_data.get("core_beliefs", []),
                    template_preferences=persona_data.get("template_preferences", {}),
                    usage_statistics=persona_data.get("usage_statistics", {}),
                )

                self._personas[persona.persona_id] = persona
                self._character_templates[persona.persona_id] = {}

                # Create enhanced context profile
                context_profile = CharacterContextProfile(
                    persona_id=persona.persona_id,
                    preferred_formats={fmt: 0.5 for fmt in RenderFormat},
                    context_emphasis=self._determine_archetype_emphasis(
                        persona.archetype
                    ),
                )
                self._context_profiles[persona.persona_id] = context_profile

                logger.info(
                    f"DISCOVERED PERSONA: {persona.persona_id} ({persona.archetype.value})"
                )

            except Exception as e:
                logger.error(f"FAILED TO LOAD PERSONA FROM {persona_file}: {e}")

    async def _save_persona_to_file(self, persona: CharacterPersona):
        """Save enhanced persona to file"""
        persona_file = self.personas_directory / f"{persona.persona_id}.json"

        persona_data = {
            "persona_id": persona.persona_id,
            "name": persona.name,
            "archetype": persona.archetype.value,
            "description": persona.description,
            "personality_traits": persona.personality_traits,
            "speech_patterns": persona.speech_patterns,
            "behavioral_preferences": persona.behavioral_preferences,
            "memory_priorities": persona.memory_priorities,
            "emotional_tendencies": persona.emotional_tendencies,
            "faction_data": persona.faction_data,
            "core_beliefs": persona.core_beliefs,
            "template_preferences": persona.template_preferences,
            "created_at": persona.created_at.isoformat(),
            "last_updated": persona.last_updated.isoformat(),
            "usage_statistics": persona.usage_statistics,
        }

        with open(persona_file, "w", encoding="utf-8") as f:
            json.dump(persona_data, f, indent=2, ensure_ascii=False)
