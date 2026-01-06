#!/usr/bin/env python3
"""
Context enhancement for persona-specific rendering.
"""

import logging
from typing import Optional

from src.memory.layered_memory import LayeredMemorySystem
from src.templates.context_renderer import RenderFormat
from src.templates.dynamic_template_engine import TemplateContext, TemplateType

from .persona_models import (
    CharacterArchetype,
    CharacterContextProfile,
    CharacterPersona,
    CharacterTemplate,
)

logger = logging.getLogger(__name__)


class ContextEnhancer:
    """Enhances rendering context with persona-specific adaptations."""

    def __init__(self, memory_system: Optional[LayeredMemorySystem] = None):
        self.memory_system = memory_system

    async def _enhance_context_for_persona(
        self,
        context: TemplateContext,
        persona: CharacterPersona,
        profile: CharacterContextProfile,
    ) -> TemplateContext:
        """Apply enhanced persona-specific context enhancements"""
        enhanced_context = context

        # Add enhanced persona information
        enhanced_context.custom_variables.update(
            {
                "persona_name": persona.name,
                "persona_archetype": persona.archetype.value,
                "personality_traits": persona.personality_traits,
                "core_beliefs": persona.core_beliefs,
                "faction_data": persona.faction_data,
            }
        )

        # Apply enhanced memory priorities
        if self.memory_system and enhanced_context.memory_context:
            prioritized_memories = []
            for memory in enhanced_context.memory_context:
                priority_boost = 0.0

                # Apply enhanced archetype-specific memory priorities
                for priority_type, boost_value in persona.memory_priorities.items():
                    if priority_type.lower() in memory.content.lower():
                        priority_boost += boost_value

                # Boost enhanced memory relevance
                memory.relevance_score = min(
                    1.0, memory.relevance_score + priority_boost
                )
                prioritized_memories.append(memory)

            # Sort enhanced memories by enhanced relevance
            prioritized_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            enhanced_context.memory_context = prioritized_memories

        # Apply enhanced behavioral preferences
        for behavior_key, behavior_value in persona.behavioral_preferences.items():
            if behavior_key not in enhanced_context.custom_variables:
                enhanced_context.custom_variables[behavior_key] = behavior_value

        return enhanced_context

    async def _select_optimal_template(
        self,
        persona_id: str,
        template_type: Optional[TemplateType],
        context: TemplateContext,
    ) -> Optional[CharacterTemplate]:
        """Select enhanced optimal template for persona and context"""
        if persona_id not in self._character_templates:
            return None

        persona_templates = self._character_templates[persona_id]

        if template_type:
            # Find enhanced templates matching type
            matching_templates = [
                t
                for t in persona_templates.values()
                if t.template_type == template_type
            ]
        else:
            matching_templates = list(persona_templates.values())

        if not matching_templates:
            return None

        # Select enhanced template based on performance and context
        best_template = None
        best_score = -1.0

        for template in matching_templates:
            score = 0.5  # Base score

            # Performance enhanced bonus
            avg_render_time = template.performance_metrics.get(
                "average_render_time", 100.0
            )
            if avg_render_time < 50.0:  # Fast templates get bonus
                score += 0.2

            # Context enhanced requirements match
            requirements_met = 0
            for requirement in template.context_requirements:
                if requirement in context.custom_variables:
                    requirements_met += 1

            if template.context_requirements:
                score += (requirements_met / len(template.context_requirements)) * 0.3

            if score > best_score:
                best_score = score
                best_template = template

        return best_template

    def _select_optimal_format(
        self,
        persona: CharacterPersona,
        profile: CharacterContextProfile,
        context: TemplateContext,
    ) -> RenderFormat:
        """Select enhanced optimal render format for persona"""
        # Get enhanced format preferences
        format_scores = profile.preferred_formats.copy()

        # Apply enhanced archetype biases
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
