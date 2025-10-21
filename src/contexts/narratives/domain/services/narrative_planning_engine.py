"""
Minimal narrative planning engine used for turn-level guidance generation.

This implementation satisfies the initial TDD expectations by returning
phase-specific narrative objectives for exposition and climax phases.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict
from uuid import uuid4

from ..value_objects import NarrativeGuidance, StoryArcPhase, StoryArcState


class NarrativePlanningEngine:
    """Generate NarrativeGuidance instances based on the current story arc state."""

    def generate_guidance_for_turn(self, *, state: StoryArcState) -> NarrativeGuidance:
        """
        Produce minimal narrative guidance aligned with the current arc phase.
        """

        guidance_id = f"guidance-{state.arc_id}-{state.turn_number}-{uuid4().hex[:8]}"
        base_payload: Dict[str, object] = {
            "guidance_id": guidance_id,
            "turn_number": state.turn_number,
            "arc_state": state,
            "secondary_narrative_goals": [],
        }

        if state.current_phase == StoryArcPhase.EXPOSITION:
            return NarrativeGuidance(
                primary_narrative_goal="Introduce new characters and establish setting",
                target_tension_level=Decimal("3.0"),
                **base_payload,
            )

        if state.current_phase == StoryArcPhase.RISING_ACTION:
            return NarrativeGuidance(
                primary_narrative_goal="Increase tension and develop conflicts",
                target_tension_level=Decimal("6.0"),
                **base_payload,
            )

        if state.current_phase == StoryArcPhase.CLIMAX:
            return NarrativeGuidance(
                primary_narrative_goal="Deliver high tension confrontation",
                target_tension_level=Decimal("9.0"),
                **base_payload,
            )

        if state.current_phase == StoryArcPhase.FALLING_ACTION:
            return NarrativeGuidance(
                primary_narrative_goal="Resolve subplots and reduce tension",
                target_tension_level=Decimal("4.0"),
                **base_payload,
            )

        if state.current_phase == StoryArcPhase.RESOLUTION:
            return NarrativeGuidance(
                primary_narrative_goal="Provide closure and finalize character arcs",
                target_tension_level=Decimal("2.0"),
                **base_payload,
            )

        return NarrativeGuidance(
            primary_narrative_goal="Maintain narrative continuity",
            **base_payload,
        )

