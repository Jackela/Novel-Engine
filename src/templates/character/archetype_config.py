#!/usr/bin/env python3
"""
Character archetype configurations and preferences.
"""

import logging
from typing import Dict

from src.templates.dynamic_template_engine import TemplateType

from .persona_models import CharacterArchetype

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
        for key, delta in archetype_modifiers.get(archetype, {}).items():
            base_emphasis[key] = max(0.0, base_emphasis.get(key, 0.0) + delta)
        total = sum(base_emphasis.values()) or 1.0
        return {key: value / total for key, value in base_emphasis.items()}
