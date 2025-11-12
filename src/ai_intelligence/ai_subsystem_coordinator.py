#!/usr/bin/env python3
"""
AI Subsystem Coordinator
========================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Manages AI intelligence subsystems including AI orchestrator and narrative engine.

Responsibilities:
- Initialize and manage AIIntelligenceOrchestrator
- Initialize and manage V2 Narrative Engine
- Provide subsystem availability checks
- Coordinate AI system startup
- Provide narrative guidance interface

This class follows the Single Responsibility Principle by focusing solely on
AI subsystem coordination, separate from integration orchestration.
"""

import logging
from decimal import Decimal
from typing import Any, Dict

from src.core.data_models import ErrorInfo, StandardResponse
from src.event_bus import EventBus

from .ai_orchestrator import (
    AIIntelligenceOrchestrator,
    AISystemConfig,
    IntelligenceLevel,
)

logger = logging.getLogger(__name__)


class AISubsystemCoordinator:
    """
    Coordinates AI intelligence subsystems including orchestrator and narrative engine.

    This class encapsulates all AI subsystem management logic, providing a clean
    interface for initialization, startup, and access to AI capabilities.
    """

    def __init__(
        self,
        event_bus: EventBus,
        ai_config: AISystemConfig,
        ai_feature_gates: Dict[str, bool],
    ):
        """
        Initialize the AI subsystem coordinator.

        Args:
            event_bus: Event bus for cross-system communication
            ai_config: AI system configuration
            ai_feature_gates: Feature gate settings for AI capabilities
        """
        self.event_bus = event_bus
        self.ai_config = ai_config
        self.ai_feature_gates = ai_feature_gates

        # Initialize AI intelligence orchestrator
        self.ai_orchestrator = AIIntelligenceOrchestrator(event_bus, ai_config)

        # Initialize V2 Narrative Engine
        self.narrative_engine_v2 = None
        self.current_arc_state = None
        self._initialize_narrative_engine_v2()

        logger.info("AI Subsystem Coordinator initialized successfully")

    # ===================================================================
    # Property Methods for AI Subsystem Availability
    # ===================================================================

    @property
    def has_recommendation_engine(self) -> bool:
        """
        Check if recommendation engine is available and enabled.

        Returns:
            bool: True if recommendation engine can be used
        """
        return (
            hasattr(self.ai_orchestrator, "recommendation_engine")
            and self.ai_orchestrator.recommendation_engine is not None
            and self.ai_feature_gates.get("recommendations", False)
        )

    @property
    def has_story_quality_engine(self) -> bool:
        """
        Check if story quality engine is available and enabled.

        Returns:
            bool: True if story quality engine can be used
        """
        return (
            hasattr(self.ai_orchestrator, "story_quality_engine")
            and self.ai_orchestrator.story_quality_engine is not None
            and self.ai_feature_gates.get("story_quality", False)
        )

    @property
    def has_analytics_platform(self) -> bool:
        """
        Check if analytics platform is available and enabled.

        Returns:
            bool: True if analytics platform can be used
        """
        return (
            hasattr(self.ai_orchestrator, "analytics_platform")
            and self.ai_orchestrator.analytics_platform is not None
            and self.ai_feature_gates.get("analytics", False)
        )

    # ===================================================================
    # AI Subsystem Lifecycle Methods
    # ===================================================================

    async def startup_ai_systems(self) -> StandardResponse:
        """
        Start AI intelligence orchestrator.

        Returns:
            StandardResponse: Result of AI system startup
        """
        ai_result = await self.ai_orchestrator.initialize_systems()

        return StandardResponse(success=ai_result.get("success", True), data=ai_result)

    async def shutdown_ai_systems(self) -> StandardResponse:
        """
        Shutdown AI intelligence orchestrator.

        Returns:
            StandardResponse: Result of AI system shutdown
        """
        ai_result = await self.ai_orchestrator.shutdown_systems()

        return StandardResponse(success=ai_result.get("success", True), data=ai_result)

    async def get_system_dashboard(self) -> Dict[str, Any]:
        """
        Get AI system status dashboard.

        Returns:
            Dictionary with AI system status information
        """
        return await self.ai_orchestrator.get_system_dashboard()

    # ===================================================================
    # Narrative Engine Integration
    # ===================================================================

    def get_narrative_guidance(self) -> Dict[str, Any]:
        """
        Get current narrative guidance from the V2 Narrative Engine.

        Returns:
            Dictionary containing narrative objectives, tension targets, and pacing info
        """
        try:
            guidance = self.narrative_engine_v2.get_narrative_context_for_turn(
                state=self.current_arc_state
            )

            return {
                "primary_goal": guidance.primary_narrative_goal,
                "secondary_goals": guidance.secondary_narrative_goals,
                "target_tension": float(guidance.target_tension_level),
                "pacing_intensity": guidance.recommended_pacing_intensity,
                "narrative_tone": guidance.narrative_tone,
                "themes_to_emphasize": guidance.themes_to_emphasize,
                "phase": self.current_arc_state.current_phase.value,
                "phase_progress": float(self.current_arc_state.phase_progress),
                "overall_progress": float(self.current_arc_state.overall_progress),
            }

        except Exception as e:
            logger.warning(f"Failed to get narrative guidance: {str(e)}")
            return {
                "primary_goal": "Maintain narrative continuity",
                "secondary_goals": [],
                "target_tension": 5.0,
                "pacing_intensity": "moderate",
                "narrative_tone": "balanced",
                "themes_to_emphasize": [],
                "phase": "exposition",
                "phase_progress": 0.0,
                "overall_progress": 0.0,
            }

    def report_turn_completion(self, turn_outcome: Dict[str, Any]):
        """
        Report turn completion to narrative engine and update arc state.

        Args:
            turn_outcome: Dictionary with turn outcome data
        """
        self.current_arc_state = self.narrative_engine_v2.report_turn_completion(
            turn_outcome=turn_outcome
        )

    # ===================================================================
    # Private Initialization Methods
    # ===================================================================

    def _initialize_narrative_engine_v2(self) -> None:
        """Initialize the V2 Narrative Engine with all required dependencies."""
        from src.contexts.narratives.application.services.narrative_engine_v2 import (
            NarrativeEngineV2,
        )
        from src.contexts.narratives.domain.services.narrative_planning_engine import (
            NarrativePlanningEngine,
        )
        from src.contexts.narratives.domain.services.pacing_manager import PacingManager
        from src.contexts.narratives.domain.services.story_arc_manager import (
            StoryArcManager,
        )
        from src.contexts.narratives.domain.value_objects import (
            StoryArcPhase,
            StoryArcState,
        )

        initial_state = StoryArcState(
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.0"),
            overall_progress=Decimal("0.0"),
            arc_id="main-story-arc",
            turn_number=0,
            sequence_number=0,
            turns_in_current_phase=0,
            current_tension_level=Decimal("3.0"),
            active_plot_thread_count=0,
            unresolved_conflict_count=0,
        )

        story_arc_manager = StoryArcManager(initial_state=initial_state)
        planning_engine = NarrativePlanningEngine()
        pacing_manager = PacingManager()

        self.narrative_engine_v2 = NarrativeEngineV2(
            story_arc_manager=story_arc_manager,
            planning_engine=planning_engine,
            pacing_manager=pacing_manager,
        )

        self.current_arc_state = initial_state

        logger.info("V2 Narrative Engine initialized with EXPOSITION phase")


__all__ = ["AISubsystemCoordinator"]
