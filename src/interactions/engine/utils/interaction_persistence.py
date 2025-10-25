#!/usr/bin/env python3
"""
Interaction persistence and metrics tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from src.core.data_models import CharacterInteraction, StandardResponse
from src.database.context_db import ContextDatabase

from ..models.interaction_models import InteractionContext, InteractionOutcome

logger = logging.getLogger(__name__)


class InteractionPersistence:
    """Handles interaction storage and metrics."""

    def __init__(self, db: ContextDatabase):
        self.db = db

    async def _store_interaction_outcome(self, outcome: InteractionOutcome):
        """Store enhanced interaction outcome in database"""
        try:
            # Create CharacterInteraction for database storage
            interaction_record = CharacterInteraction(
                interaction_id=outcome.interaction_id,
                interaction_type=(
                    outcome.interaction_id.split("_")[0]
                    if "_" in outcome.interaction_id
                    else "unknown"
                ),
                location=(
                    ", ".join(
                        [str(change) for change in outcome.state_changes.values()]
                    )
                    if outcome.state_changes
                    else ""
                ),
                description=f"Interaction completed {'successfully' if outcome.success else 'with errors'}",
                participants=list(outcome.participant_outcomes.keys()),
                outcomes=outcome.generated_content,
                emotional_impact={},  # Would be populated with actual emotional data
                world_state_changes=outcome.state_changes,
                timestamp=outcome.completion_time,
            )

            await self.database.store_enhanced_interaction(interaction_record)

        except Exception as e:
            logger.error(f"INTERACTION STORAGE FAILED: {e}")

    def _update_performance_metrics(
        self,
        context: InteractionContext,
        outcome: InteractionOutcome,
        duration_ms: float,
    ):
        """Update enhanced performance metrics"""
        self.performance_metrics["total_interactions_processed"] += 1

        if outcome.success:
            self.performance_metrics["successful_interactions"] += 1
        else:
            self.performance_metrics["failed_interactions"] += 1

        # Update average processing time
        total_processed = self.performance_metrics["total_interactions_processed"]
        current_avg = self.performance_metrics["average_processing_time"]
        self.performance_metrics["average_processing_time"] = (
            current_avg * (total_processed - 1) + duration_ms
        ) / total_processed

        # Update interaction type counts
        self.performance_metrics["interaction_type_counts"][
            context.interaction_type.value
        ] += 1
