#!/usr/bin/env python3
"""
Content generation for interactions.
"""

import logging
from typing import Any, Dict, List, Optional

from src.core.data_models import CharacterState, MemoryItem, StandardResponse
from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionOutcome,
    InteractionType,
)
from src.templates.context_renderer import ContextRenderer, RenderFormat
from src.templates.dynamic_template_engine import TemplateContext, TemplateType

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates interaction content and context."""

    def __init__(self, context_renderer: Optional[ContextRenderer] = None):
        self.context_renderer = context_renderer

    async def _generate_initial_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Generate enhanced initial context for interaction participants"""
        try:
            participant_contexts = {}

            for participant in context.participants:
                # Create enhanced template context for participant
                template_context = TemplateContext(
                    agent_id=participant,
                    current_location=context.location,
                    current_situation=f"Engaging in {context.interaction_type.value} interaction",
                    active_participants=context.participants,
                    environmental_context=context.environment_state,
                    temporal_context=context.temporal_context,
                    custom_variables={
                        "interaction_id": context.interaction_id,
                        "interaction_type": context.interaction_type.value,
                        "interaction_priority": context.priority.value,
                        "expected_outcomes": context.expected_outcomes,
                        "risk_factors": context.risk_factors,
                    },
                )

                # Generate enhanced contextual information using template manager
                if participant in self.template_manager._active_personas:
                    context_result = (
                        await self.template_manager.render_character_context(
                            participant, template_context, TemplateType.CONTEXT_SUMMARY
                        )
                    )

                    if context_result.success:
                        participant_contexts[participant] = {
                            "rendered_context": context_result.data[
                                "render_result"
                            ].rendered_content,
                            "persona_id": context_result.data["persona_id"],
                            "archetype": context_result.data["archetype"],
                        }
                    else:
                        participant_contexts[participant] = {
                            "error": context_result.error.message,
                            "fallback_context": f"Participant {participant} in {context.interaction_type.value} interaction",
                        }
                else:
                    # Use enhanced basic context rendering
                    basic_result = await self.context_renderer.render_context(
                        template_context
                    )
                    participant_contexts[participant] = {
                        "rendered_context": (
                            basic_result.data["render_result"].rendered_content
                            if basic_result.success
                            else "Basic context unavailable"
                        ),
                        "persona_id": None,
                        "archetype": "Unknown",
                    }

            return StandardResponse(
                success=True,
                data={"participant_contexts": participant_contexts},
                metadata={"blessing": "initial_context_generated"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INITIAL_CONTEXT_GENERATION_FAILED", message=str(e)
                ),
            )

    async def _generate_interaction_content(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Generate enhanced content outputs for interaction"""
        try:
            generated_content = []

            # Generate interaction summary
            summary_template_context = TemplateContext(
                agent_id=context.initiator or "system",
                current_location=context.location,
                current_situation=f"Completed {context.interaction_type.value} interaction",
                active_participants=context.participants,
                custom_variables={
                    "interaction_id": context.interaction_id,
                    "interaction_type": context.interaction_type.value,
                    "success": outcome.success,
                    "phases_completed": outcome.phases_completed,
                    "duration_ms": outcome.duration_ms,
                },
            )

            summary_result = await self.context_renderer.render_context(
                summary_template_context, RenderFormat.SUMMARY
            )

            if summary_result.success:
                generated_content.append(
                    summary_result.data["render_result"].rendered_content
                )

            # Add type-specific content
            generated_content.extend(outcome.generated_content)

            self.performance_metrics["content_generation_count"] += len(
                generated_content
            )

            return StandardResponse(
                success=True,
                data={"generated_content": generated_content},
                metadata={"blessing": "content_generated"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CONTENT_GENERATION_FAILED", message=str(e)),
            )

    def _calculate_emotional_impact(
        self, context: InteractionContext, participant: str
    ) -> float:
        """Calculate enhanced emotional impact of interaction on participant"""
        base_impact = 1.0

        # Adjust based on interaction type
        type_impacts = {
            InteractionType.DIALOGUE: 1.0,
            InteractionType.COMBAT: 8.0,
            InteractionType.COOPERATION: 3.0,
            InteractionType.NEGOTIATION: 2.0,
            InteractionType.INSTRUCTION: 1.5,
            InteractionType.RITUAL: 5.0,
            InteractionType.EXPLORATION: 4.0,
            InteractionType.MAINTENANCE: 0.5,
            InteractionType.EMERGENCY: 9.0,
        }

        base_impact = type_impacts.get(context.interaction_type, 1.0)

        # Adjust for priority
        if context.priority == InteractionPriority.CRITICAL:
            base_impact *= 1.5
        elif context.priority == InteractionPriority.LOW:
            base_impact *= 0.7

        # Adjust for risk factors
        risk_multiplier = 1.0 + (len(context.risk_factors) * 0.2)
        base_impact *= risk_multiplier

        return min(10.0, max(-10.0, base_impact))
