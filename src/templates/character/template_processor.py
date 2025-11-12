#!/usr/bin/env python3
"""
Template generation and processing.
"""

import logging
import re
from typing import Any, Dict, List, Set

from src.templates.dynamic_template_engine import TemplateContext, TemplateType

from .persona_models import CharacterArchetype, CharacterPersona, CharacterTemplate

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Processes and generates character-specific templates."""

    async def _generate_archetype_template_content(
        self, archetype: CharacterArchetype, template_type: TemplateType
    ) -> str:
        """Generate enhanced template content for archetype and type"""
        base_templates = self._archetype_base_templates.get(archetype, {})
        return base_templates.get(
            template_type,
            f"""
ENHANCED {archetype.value.upper()} {template_type.value.upper()}

Character: {{{{persona_name}}}}
Archetype: {archetype.value.title()}
Current Context: {{{{current_situation}}}}

{{{{custom_variables.get('template_content', 'Standard archetype template content')}}}}

MAY THE SYSTEM GUIDE YOUR ACTIONS
""",
        )

    async def _apply_persona_adaptations(
        self,
        template_content: str,
        persona: CharacterPersona,
        template_type: TemplateType,
    ) -> str:
        """Apply enhanced persona-specific adaptations to template"""
        adapted_content = template_content

        # Apply enhanced personality trait integration
        if persona.personality_traits:
            traits_section = (
                "\nPersonality Traits: " + ", ".join(persona.personality_traits) + "\n"
            )
            adapted_content = adapted_content.replace(
                "{{persona_name}}", f"{{{{persona_name}}}}{traits_section}"
            )

        # Apply enhanced core beliefs integration
        if persona.core_beliefs:
            beliefs_section = (
                "\nCore Beliefs:\n"
                + "\n".join([f"- {belief}" for belief in persona.core_beliefs])
                + "\n"
            )
            adapted_content += beliefs_section

        # Apply enhanced faction data
        if persona.faction_data:
            faction_section = (
                "\nFaction Allegiance: " + ", ".join(persona.faction_data) + "\n"
            )
            adapted_content += faction_section

        return adapted_content

    def _determine_template_requirements(
        self, template_type: TemplateType, persona: CharacterPersona
    ) -> List[str]:
        """Determine enhanced template context requirements"""
        base_requirements = {
            TemplateType.CHARACTER_PROMPT: [
                "persona_name",
                "current_location",
                "current_situation",
            ],
            TemplateType.DIALOGUE: ["dialogue_content"],
            TemplateType.NARRATIVE_SCENE: ["character_state", "current_location"],
            TemplateType.CONTEXT_SUMMARY: ["memory_context"],
            TemplateType.EQUIPMENT_STATUS: ["equipment_states"],
        }

        requirements = base_requirements.get(template_type, [])

        # Add enhanced archetype-specific requirements
        if persona.archetype in [
            CharacterArchetype.WARRIOR,
            CharacterArchetype.GUARDIAN,
        ]:
            if "equipment_states" not in requirements:
                requirements.append("equipment_states")

        if persona.archetype == CharacterArchetype.DIPLOMAT:
            if "relationship_context" not in requirements:
                requirements.append("relationship_context")

        return requirements

    def _identify_dynamic_elements(self, template_content: str) -> List[str]:
        """Identify enhanced dynamic elements in template"""
        import re

        # Find enhanced Jinja2 variables
        variable_pattern = r"\{\{\s*([^}]+)\s*\}\}"
        variables = re.findall(variable_pattern, template_content)

        # Find enhanced Jinja2 blocks
        block_pattern = r"\{\%\s*(\w+)[^%]*\%\}"
        blocks = re.findall(block_pattern, template_content)

        dynamic_elements = list(set(variables + blocks))
        return dynamic_elements
