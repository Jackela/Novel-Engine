"""
Minimal pacing manager for generating phase-specific pacing adjustments.

This implementation provides basic pacing control by adjusting speed
modifiers based on the current story arc phase.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from ..value_objects import PacingAdjustment, StoryArcPhase, StoryArcState


class PacingManager:
    """Generate PacingAdjustment instances based on the current story arc state."""

    def adjust_pacing(self, *, state: StoryArcState) -> PacingAdjustment:
        """
        Produce minimal pacing adjustment aligned with the current arc phase.
        """

        adjustment_id = f"pacing-{state.arc_id}-{state.turn_number}-{uuid4().hex[:8]}"

        if state.current_phase == StoryArcPhase.CLIMAX:
            return PacingAdjustment(
                adjustment_id=adjustment_id,
                turn_number=state.turn_number,
                intensity_modifier=Decimal("2.0"),
                tension_target=Decimal("9.0"),
                speed_modifier=Decimal("1.5"),
                adjustment_reason="Climax phase requires faster pacing",
                triggered_by="phase_analysis",
            )

        if state.current_phase == StoryArcPhase.RESOLUTION:
            return PacingAdjustment(
                adjustment_id=adjustment_id,
                turn_number=state.turn_number,
                intensity_modifier=Decimal("-1.0"),
                tension_target=Decimal("2.0"),
                speed_modifier=Decimal("0.7"),
                adjustment_reason="Resolution phase requires slower pacing",
                triggered_by="phase_analysis",
            )

        return PacingAdjustment(
            adjustment_id=adjustment_id,
            turn_number=state.turn_number,
            intensity_modifier=Decimal("0"),
            tension_target=state.current_tension_level,
            speed_modifier=Decimal("1.0"),
            adjustment_reason="Maintain current pacing",
            triggered_by="default",
        )
