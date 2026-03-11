#!/usr/bin/env python3
"""
State and memory management for interactions.
"""

from typing import Any, Dict, List

import structlog

from src.core.data_models import (
    ErrorInfo,
    MemoryItem,
    MemoryType,
    StandardResponse,
)
from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionOutcome,
)

logger = structlog.get_logger(__name__)


class StateManager:
    """Manages state changes and memory updates."""

    def __init__(self) -> None:
        """Initialize state manager."""
        self.performance_metrics: Dict[str, int] = {"state_changes_applied": 0, "memory_updates_generated": 0}
        self.memory_system: Any = None

    async def _apply_state_changes(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Apply enhanced state changes from interaction"""
        try:
            changes_applied = 0

            # Apply participant state changes
            participant_outcomes: Dict[str, Any] = getattr(outcome, 'participant_outcomes', {})
            for participant, changes in participant_outcomes.items():
                # This would update actual participant states
                changes_applied += len(changes)

            # Apply equipment changes
            equipment_changes_dict: Dict[str, Any] = getattr(outcome, 'equipment_changes', {})
            for participant, equipment_changes in equipment_changes_dict.items():
                # This would update equipment states
                changes_applied += len(equipment_changes)

            # Apply relationship changes
            for (
                participant,
                relationship_updates,
            ) in outcome.relationship_changes.items():
                # This would update relationship database
                changes_applied += 1  # Each entry counts as one change

            # Apply environmental changes
            environmental_effects: List[Any] = getattr(outcome, 'environmental_effects', [])
            if environmental_effects:
                # This would update environment state
                changes_applied += len(environmental_effects)

            self.performance_metrics["state_changes_applied"] += changes_applied

            return StandardResponse(
                success=True,
                data={"changes_applied": changes_applied},
                metadata={"blessing": "state_changes_applied"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="STATE_CHANGES_FAILED", message=str(e)),
            )

    async def _generate_memory_updates(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Generate enhanced memory updates for interaction participants"""
        try:
            memory_updates: list[Any] = []
            for participant in context.participants:
                # Create interaction memory
                interaction_memory = MemoryItem(
                    agent_id=participant,
                    memory_type=MemoryType.EPISODIC,
                    content=f"Participated in {context.interaction_type.value} interaction at {context.location}",
                    emotional_weight=0.5,
                    participants=[p for p in context.participants if p != participant],
                    location=context.location,
                    tags=[context.interaction_type.value, "interaction"],
                    relevance_score=0.7,
                )
                memory_updates.append(interaction_memory)

                # Store memory in system
                if self.memory_system:
                    await self.memory_system.store_memory(interaction_memory)

            # Add any specific memory updates from outcome
            outcome_memory_updates: List[Any] = getattr(outcome, 'memory_updates', [])
            memory_updates.extend(outcome_memory_updates)

            self.performance_metrics["memory_updates_generated"] += len(memory_updates)

            return StandardResponse(
                success=True,
                data={"memory_updates": memory_updates},
                metadata={"blessing": "memory_updates_generated"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="MEMORY_GENERATION_FAILED", message=str(e)),
            )
