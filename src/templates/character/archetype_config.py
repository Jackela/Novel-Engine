#!/usr/bin/env python3
"""
Character archetype configurations and preferences.
"""

import logging
from typing import Dict, List

from src.templates.context_renderer import RenderFormat, RenderingConstraints
from src.templates.dynamic_template_engine import TemplateType

from .persona_models import CharacterArchetype, CharacterPersona

logger = logging.getLogger(__name__)


class ArchetypeConfiguration:
    """Manages archetype-specific configurations and preferences."""

    def _initialize_archetype_templates(
        self,
    ) -> Dict[CharacterArchetype, Dict[TemplateType, str]]:
        """Initialize enhanced base templates for each archetype"""
        return {
            CharacterArchetype.WARRIOR: {
                TemplateType.CHARACTER_PROMPT: """
You are {{persona_name}}, an enhanced guardian in service to the Founders' Council.

Character Traits: {{personality_traits|join(', ')}}
Current Location: {{current_location}}
Current Situation: {{current_situation}}

Your guardian instinct burns with unwavering resolve. You speak with conviction and act with decisive courage.
Readiness is your constant state. Shared purpose and collective duty guide every decision.

{% if memory_context %}Recent Battle Memories:
{% for memory in memory_context[:3] %}
- {{memory.content}}
{% endfor %}
{% endif %}

FOR THE COUNCIL!
""",
                TemplateType.DIALOGUE: """
{{persona_name}} speaks with the conviction of a true guardian:

"{{custom_variables.dialogue_content or 'The Council guides us, but we must be their hands.'}}"

*The warrior's stance radiates readiness for battle, eyes scanning for threats*
""",
                TemplateType.NARRATIVE_SCENE: """
## Battle-Hardened Warrior

{{persona_name}} stands ready, an exemplar of Alliance resolve. The guardian's presence commands respect and instills confidence in allies.

Current Status: {{character_state.current_state.value if character_state else 'Ready for Battle'}}
Location: {{current_location}}

{% if equipment_states %}
Equipment Status:
{% for item, status in equipment_states.items() %}
- {{item}}: {{status.condition if status.condition else status}} 
{% endfor %}
{% endif %}

The warrior's determination is unwavering, a beacon of Alliance strength in dark times.
""",
            },
            # Add more archetypes as needed...
        }

    def _determine_archetype_emphasis(
        self, archetype: CharacterArchetype
    ) -> Dict[str, float]:
        """Determine enhanced context emphasis for archetype"""
        base_emphasis = {
            "memory": 0.3,
            "emotion": 0.2,
            "relationship": 0.2,
            "environment": 0.15,
            "equipment": 0.15,
        }

        archetype_modifiers = {
            CharacterArchetype.WARRIOR: {"emotion": 0.1, "equipment": 0.2},
            CharacterArchetype.SCHOLAR: {"memory": 0.3, "environment": -0.1},
            CharacterArchetype.LEADER: {"relationship": 0.3, "memory": 0.1},
            CharacterArchetype.MYSTIC: {"emotion": 0.3, "equipment": -0.1},
            CharacterArchetype.ENGINEER: {"equipment": 0.3, "environment": 0.1},
            CharacterArchetype.DIPLOMAT: {"relationship": 0.4, "emotion": 0.1},
            CharacterArchetype.GUARDIAN: {"relationship": 0.2, "equipment": 0.1},
            CharacterArchetype.SURVIVOR: {"environment": 0.2, "memory": 0.1},
        }

        archetype_format_preferences = {
            CharacterArchetype.WARRIOR: {
                RenderFormat.CONVERSATIONAL: 0.3,
                RenderFormat.NARRATIVE: 0.2,
            },
            CharacterArchetype.SCHOLAR: {
                RenderFormat.TECHNICAL: 0.4,
                RenderFormat.SUMMARY: 0.2,
            },
            CharacterArchetype.LEADER: {
                RenderFormat.NARRATIVE: 0.3,
                RenderFormat.CONVERSATIONAL: 0.2,
            },
            CharacterArchetype.MYSTIC: {
                RenderFormat.NARRATIVE: 0.4,
                RenderFormat.CONVERSATIONAL: 0.1,
            },
            CharacterArchetype.ENGINEER: {
                RenderFormat.TECHNICAL: 0.4,
                RenderFormat.DEBUG: 0.2,
            },
            CharacterArchetype.DIPLOMAT: {
                RenderFormat.CONVERSATIONAL: 0.4,
                RenderFormat.SUMMARY: 0.1,
            },
            CharacterArchetype.GUARDIAN: {
                RenderFormat.NARRATIVE: 0.2,
                RenderFormat.TECHNICAL: 0.2,
            },
            CharacterArchetype.SURVIVOR: {
                RenderFormat.SUMMARY: 0.3,
                RenderFormat.TECHNICAL: 0.2,
            },
        }

        if persona.archetype in archetype_format_preferences:
            for fmt, bonus in archetype_format_preferences[persona.archetype].items():
                format_scores[fmt] = format_scores.get(fmt, 0.5) + bonus

        # Select enhanced highest scoring format
        best_format = max(format_scores, key=format_scores.get)
        return best_format

        archetype_constraints = {
            CharacterArchetype.WARRIOR: {"max_memories": 6, "emotional_threshold": 2.0},
            CharacterArchetype.SCHOLAR: {
                "max_memories": 12,
                "relevance_threshold": 0.6,
            },
            CharacterArchetype.LEADER: {
                "max_participants": 10,
                "emotional_threshold": 1.0,
            },
            CharacterArchetype.MYSTIC: {
                "emotional_threshold": 1.5,
                "include_technical_details": False,
            },
            CharacterArchetype.ENGINEER: {
                "include_technical_details": True,
                "max_memories": 8,
            },
            CharacterArchetype.DIPLOMAT: {
                "max_participants": 15,
                "relevance_threshold": 0.3,
            },
            CharacterArchetype.GUARDIAN: {
                "max_memories": 8,
                "emotional_threshold": 2.5,
            },
            CharacterArchetype.SURVIVOR: {"max_memories": 5, "time_window_hours": 12},
        }

        if persona.archetype in archetype_constraints:
            archetype_prefs = archetype_constraints[persona.archetype]
            for key, value in archetype_prefs.items():
                if hasattr(constraints, key):
                    setattr(constraints, key, value)

        return constraints
