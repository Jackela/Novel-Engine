#!/usr/bin/env python3
"""
Template selection logic.
"""

import logging
from typing import Optional

from src.templates.dynamic_template_engine import TemplateContext, TemplateType

from .persona_models import CharacterTemplate

logger = logging.getLogger(__name__)


class TemplateSelector:
    """Selects optimal templates based on context and persona."""

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
