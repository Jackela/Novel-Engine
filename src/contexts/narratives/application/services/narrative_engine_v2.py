"""
NarrativeEngineV2 application service facade.

This facade coordinates the domain services (StoryArcManager, NarrativePlanningEngine,
PacingManager) to provide a unified interface for generating narrative context
for each turn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.services.narrative_planning_engine import NarrativePlanningEngine
    from ...domain.services.pacing_manager import PacingManager
    from ...domain.services.story_arc_manager import StoryArcManager
    from ...domain.value_objects import NarrativeGuidance, StoryArcState


class NarrativeEngineV2:
    """
    Application service facade that coordinates narrative generation.

    This facade integrates the StoryArcManager, NarrativePlanningEngine,
    and PacingManager to produce comprehensive narrative guidance for
    each turn.
    """

    def __init__(
        self,
        *,
        story_arc_manager: StoryArcManager,
        planning_engine: NarrativePlanningEngine,
        pacing_manager: PacingManager,
    ) -> None:
        """
        Initialize the facade with injected domain services.

        Args:
            story_arc_manager: Manages story arc state transitions
            planning_engine: Generates narrative guidance based on arc state
            pacing_manager: Produces pacing adjustments for the current state
        """
        self._story_arc_manager = story_arc_manager
        self._planning_engine = planning_engine
        self._pacing_manager = pacing_manager

    def get_narrative_context_for_turn(
        self,
        *,
        state: StoryArcState,
    ) -> NarrativeGuidance:
        """
        Generate comprehensive narrative context for the current turn.

        This method coordinates the planning and pacing managers to produce
        a NarrativeGuidance object that integrates both phase-specific
        narrative objectives and dynamic pacing adjustments.

        Args:
            state: The current story arc state

        Returns:
            NarrativeGuidance with integrated pacing adjustments
        """
        from ...domain.value_objects import NarrativeGuidance

        base_guidance = self._planning_engine.generate_guidance_for_turn(state=state)
        pacing_adjustment = self._pacing_manager.adjust_pacing(state=state)

        guidance_data = base_guidance.model_dump()
        guidance_data["target_tension_level"] = pacing_adjustment.tension_target

        return NarrativeGuidance(**guidance_data)

    def report_turn_completion(
        self,
        *,
        turn_outcome: dict,
    ) -> StoryArcState:
        """
        Update the story arc state after a turn completes.

        This method advances the narrative state based on the turn outcome,
        updating progress metrics and checking for phase transitions.

        Args:
            turn_outcome: Dictionary containing turn results and metrics

        Returns:
            Updated StoryArcState reflecting the turn's narrative impact
        """
        from decimal import Decimal

        from ...domain.value_objects import StoryArcState

        current_state = self._story_arc_manager.current_state

        updated_state_data = current_state.model_dump()
        updated_state_data["turn_number"] = current_state.turn_number + 1
        updated_state_data["sequence_number"] = current_state.sequence_number + 1
        updated_state_data["turns_in_current_phase"] = (
            current_state.turns_in_current_phase + 1
        )

        phase_progress_increment = Decimal("0.05")
        new_phase_progress = min(
            current_state.phase_progress + phase_progress_increment, Decimal("1.0")
        )
        updated_state_data["phase_progress"] = new_phase_progress

        overall_progress_increment = Decimal("0.02")
        new_overall_progress = min(
            current_state.overall_progress + overall_progress_increment, Decimal("1.0")
        )
        updated_state_data["overall_progress"] = new_overall_progress

        new_state = StoryArcState(**updated_state_data)
        self._story_arc_manager.update_state(new_state)

        return new_state
