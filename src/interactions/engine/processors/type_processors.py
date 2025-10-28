#!/usr/bin/env python3
"""
Type-specific interaction processors.
"""

import logging
from typing import Any, Dict

from src.core.data_models import ErrorInfo, MemoryItem, MemoryType, StandardResponse
from src.templates.dynamic_template_engine import TemplateContext, TemplateType
from src.interactions.engine.models.interaction_models import (
    InteractionContext,
    InteractionOutcome,
)

logger = logging.getLogger(__name__)


class TypeProcessors:
    """Handles type-specific interaction processing."""

    async def _process_dialogue_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Process enhanced dialogue interaction"""
        try:
            # Generate dialogue content for each participant
            dialogue_content = []

            for participant in context.participants:
                # Generate character-specific dialogue
                template_context = TemplateContext(
                    agent_id=participant,
                    current_location=context.location,
                    current_situation="Engaging in conversation",
                    active_participants=[
                        p for p in context.participants if p != participant
                    ],
                    custom_variables={
                        "dialogue_type": "conversation",
                        "interaction_context": context.interaction_type.value,
                    },
                )

                if participant in self.template_manager._active_personas:
                    dialogue_result = (
                        await self.template_manager.render_character_context(
                            participant, template_context, TemplateType.DIALOGUE
                        )
                    )

                    if dialogue_result.success:
                        dialogue_content.append(
                            {
                                "speaker": participant,
                                "content": dialogue_result.data[
                                    "render_result"
                                ].rendered_content,
                                "persona": dialogue_result.data["persona_id"],
                            }
                        )

            outcome.generated_content.extend(
                [f"{d['speaker']}: {d['content']}" for d in dialogue_content]
            )

            # Update relationship dynamics
            for i, participant1 in enumerate(context.participants):
                for participant2 in context.participants[i + 1 :]:
                    if participant1 not in outcome.relationship_changes:
                        outcome.relationship_changes[participant1] = {}
                    outcome.relationship_changes[participant1][
                        participant2
                    ] = 0.1  # Small positive change

            return StandardResponse(
                success=True, metadata={"blessing": "dialogue_processed"}
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="DIALOGUE_PROCESSING_FAILED", message=str(e)),
            )

    async def _process_combat_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Process enhanced combat interaction"""
        try:
            # Simulate combat resolution
            combatants = context.participants

            # Generate combat narrative
            combat_narrative = [
                f"Combat initiated at {context.location}",
                f"Combatants: {', '.join(combatants)}",
            ]

            # Apply combat effects
            for participant in combatants:
                # Simulate equipment usage and status changes
                if participant not in outcome.equipment_changes:
                    outcome.equipment_changes[participant] = []
                outcome.equipment_changes[participant].append("weapon_usage")

                # Generate combat memory
                combat_memory = MemoryItem(
                    agent_id=participant,
                    memory_type=MemoryType.EPISODIC,
                    content=f"Engaged in combat at {context.location}",
                    emotional_weight=8.0,  # High emotional impact
                    participants=[p for p in combatants if p != participant],
                    location=context.location,
                    tags=["combat", "action"],
                )
                outcome.memory_updates.append(combat_memory)

            outcome.generated_content.extend(combat_narrative)

            return StandardResponse(
                success=True, metadata={"blessing": "combat_processed"}
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="COMBAT_PROCESSING_FAILED", message=str(e)),
            )

    async def _process_cooperation_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Process enhanced cooperation interaction"""
        try:
            # Generate cooperation outcomes
            cooperation_results = [
                f"Collaborative effort at {context.location}",
                f"Participants: {', '.join(context.participants)}",
                "Cooperation strengthens bonds between participants",
            ]

            # Boost relationships between all participants
            for i, participant1 in enumerate(context.participants):
                for participant2 in context.participants[i + 1 :]:
                    if participant1 not in outcome.relationship_changes:
                        outcome.relationship_changes[participant1] = {}
                    outcome.relationship_changes[participant1][
                        participant2
                    ] = 0.2  # Positive cooperation boost

            outcome.generated_content.extend(cooperation_results)

            return StandardResponse(
                success=True, metadata={"blessing": "cooperation_processed"}
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="COOPERATION_PROCESSING_FAILED", message=str(e)),
            )

    # Placeholder implementations for other interaction types
    async def _process_negotiation_interaction(self, context, outcome):
        return StandardResponse(
            success=True, metadata={"blessing": "negotiation_processed"}
        )

    async def _process_instruction_interaction(self, context, outcome):
        return StandardResponse(
            success=True, metadata={"blessing": "instruction_processed"}
        )

    async def _process_ritual_interaction(self, context, outcome):
        return StandardResponse(success=True, metadata={"blessing": "ritual_processed"})

    async def _process_exploration_interaction(self, context, outcome):
        return StandardResponse(
            success=True, metadata={"blessing": "exploration_processed"}
        )

    async def _process_maintenance_interaction(self, context, outcome):
        return StandardResponse(
            success=True, metadata={"blessing": "maintenance_processed"}
        )

    async def _process_emergency_interaction(self, context, outcome):
        return StandardResponse(
            success=True, metadata={"blessing": "emergency_processed"}
        )
