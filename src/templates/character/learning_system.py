#!/usr/bin/env python3
"""
Usage learning and optimization system.
"""

import logging
from datetime import datetime
from typing import Any

from src.templates.context_renderer import RenderFormat
from src.templates.dynamic_template_engine import TemplateContext

logger = logging.getLogger(__name__)


class LearningSystem:
    """Learns from usage patterns and optimizes template selection."""

    async def _learn_from_context(self, persona_id: str, context: TemplateContext):
        """Learn enhanced patterns from context usage"""
        if not self.enable_learning:
            return

        profile = self._context_profiles.get(persona_id)
        if not profile:
            return

        # Track enhanced context element usage
        context_elements = {
            "memory_count": len(context.memory_context),
            "participant_count": len(context.active_participants),
            "has_equipment": bool(context.equipment_states),
            "has_environment": bool(context.environmental_context),
            "has_relationships": bool(context.relationship_context),
        }

        profile.learning_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "context_elements": context_elements,
                "situation": context.current_situation,
            }
        )

        # Keep enhanced learning history manageable
        if len(profile.learning_history) > 100:
            profile.learning_history = profile.learning_history[-50:]

        self.usage_statistics["learning_updates"] += 1

    async def _learn_from_rendering(
        self, persona_id: str, render_result: Any, context: TemplateContext
    ):
        """Learn enhanced patterns from rendering performance"""
        if not self.enable_learning or not hasattr(render_result, "render_time_ms"):
            return

        profile = self._context_profiles.get(persona_id)
        if not profile:
            return

        # Update enhanced format preferences based on performance
        if hasattr(render_result, "format_used") and render_result.format_used:
            fmt = RenderFormat(render_result.format_used)

            # Good performance boosts preference
            if render_result.render_time_ms < 100:
                profile.preferred_formats[fmt] = min(
                    1.0, profile.preferred_formats.get(fmt, 0.5) + 0.05
                )
            elif render_result.render_time_ms > 500:
                profile.preferred_formats[fmt] = max(
                    0.0, profile.preferred_formats.get(fmt, 0.5) - 0.05
                )
