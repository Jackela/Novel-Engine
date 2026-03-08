"""State Manager Module.

Manages world state, narrative intelligence, and story progression tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .types import AgentDialogue, EnhancedWorldState


class StateManager:
    """Manages simulation state and narrative intelligence."""

    def __init__(self) -> None:
        """Initialize the state manager."""
        self.enhanced_world_state: Optional[EnhancedWorldState] = None
        self.narrative_intelligence: Dict[str, Any] = {}
        self.story_progression_goals: Dict[str, float] = {}
        self.turn_history: List[Dict[str, Any]] = []

    def prepare_enhanced_world_state(
        self,
        turn_number: int,
        agent_relationships: Dict[str, Dict[str, float]],
        active_dialogues: List[AgentDialogue],
    ) -> EnhancedWorldState:
        """Prepare enhanced world state with AI intelligence."""
        from .types import EnhancedWorldState

        base_world_state = {
            "current_turn": turn_number,
            "simulation_time": datetime.now().isoformat(),
        }

        # Add narrative pressure based on story progression
        narrative_pressure = self._calculate_narrative_pressure()

        # Add story goals from AI analysis
        story_goals = self._generate_story_goals()

        # Get AI insights
        ai_insights = self._gather_ai_insights()

        enhanced_state = EnhancedWorldState(
            turn_number=turn_number,
            simulation_time=datetime.now().isoformat(),
            base_world_state=base_world_state,
            agent_relationships=agent_relationships.copy(),
            active_dialogues=list(active_dialogues),
            narrative_pressure=narrative_pressure,
            story_goals=story_goals,
            ai_insights=ai_insights,
            coordination_status={},
        )

        self.enhanced_world_state = enhanced_state
        return enhanced_state

    def _calculate_narrative_pressure(self) -> Dict[str, float]:
        """Calculate narrative pressure for story development."""
        return {
            "dialogue_pressure": 0.6,  # Story needs dialogue
            "conflict_pressure": 0.4,  # Story needs conflict
            "resolution_pressure": 0.3,  # Story needs resolution
        }

    def _generate_story_goals(self) -> Dict[str, Any]:
        """Generate AI-driven story goals."""
        return {
            "character_development": 0.7,
            "plot_advancement": 0.6,
            "relationship_evolution": 0.8,
            "conflict_resolution": 0.4,
        }

    def _gather_ai_insights(self) -> List[Dict[str, Any]]:
        """Gather insights from AI intelligence systems."""
        insights: List[Dict[str, Any]] = []
        # Get insights from stored narrative intelligence
        if "last_insights" in self.narrative_intelligence:
            insights.extend(self.narrative_intelligence["last_insights"])
        return insights

    def update_narrative_intelligence(
        self, post_turn_analysis: Dict[str, Any]
    ) -> None:
        """Update narrative intelligence based on turn analysis."""
        if post_turn_analysis.get("narrative_insights"):
            self.narrative_intelligence["last_insights"] = post_turn_analysis[
                "narrative_insights"
            ]
            self.narrative_intelligence["insight_count"] = (
                self.narrative_intelligence.get("insight_count", 0)
                + len(post_turn_analysis["narrative_insights"])
            )

        if post_turn_analysis.get("story_progression"):
            self.narrative_intelligence["story_progression"] = post_turn_analysis[
                "story_progression"
            ]

    def record_turn(
        self,
        turn_number: int,
        execution_time: float,
        dialogue_results: List[Dict[str, Any]],
    ) -> None:
        """Record turn data in history."""
        self.turn_history.append(
            {
                "turn_number": turn_number,
                "execution_time": execution_time,
                "dialogue_count": len(dialogue_results),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def get_turn_history(self) -> List[Dict[str, Any]]:
        """Get turn history."""
        return self.turn_history.copy()

    def get_average_execution_time(self) -> float:
        """Get average turn execution time."""
        if not self.turn_history:
            return 0.0
        vals = [t.get("execution_time", 0.0) for t in self.turn_history]
        return sum(vals) / max(1, len(vals))

    def get_narrative_intelligence(self) -> Dict[str, Any]:
        """Get narrative intelligence data."""
        return self.narrative_intelligence.copy()

    def analyze_pre_turn_state(
        self, agent_relationships: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Analyze state before turn execution."""
        analysis = {
            "relationship_tensions": [],
            "dialogue_opportunities": [],
            "narrative_pressure": self._calculate_narrative_pressure(),
            "ai_recommendations": [],
        }

        # Analyze relationship tensions
        for agent_id, relationships in agent_relationships.items():
            for other_agent, relationship_value in relationships.items():
                if relationship_value < -0.3:  # High tension
                    analysis["relationship_tensions"].append(
                        {
                            "agents": [agent_id, other_agent],
                            "tension_level": abs(relationship_value),
                            "recommended_interaction": "conflict_resolution",
                        }
                    )
                elif relationship_value > 0.7:  # Strong positive
                    analysis["dialogue_opportunities"].append(
                        {
                            "agents": [agent_id, other_agent],
                            "relationship_strength": relationship_value,
                            "recommended_interaction": "collaboration",
                        }
                    )

        return analysis

    def analyze_post_turn_results(
        self,
        base_turn_result: Dict[str, Any],
        dialogue_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze results after turn execution."""
        analysis = {
            "narrative_insights": [],
            "relationship_changes": [],
            "ai_insights": [],
            "story_progression": {},
        }

        # Analyze dialogue impacts
        for dialogue_result in dialogue_results:
            if dialogue_result.get("success") and dialogue_result.get(
                "relationship_impact"
            ):
                analysis["relationship_changes"].extend(
                    [
                        {
                            "agents": key.split("_"),
                            "change": value,
                            "source": "dialogue",
                        }
                        for key, value in dialogue_result[
                            "relationship_impact"
                        ].items()
                    ]
                )

        # Generate narrative insights
        if dialogue_results:
            analysis["narrative_insights"].append(
                {
                    "insight": f"Character interactions advanced story through {len(dialogue_results)} dialogues",
                    "impact": "story_progression",
                    "confidence": 0.8,
                }
            )

        return analysis

    def handle_narrative_pressure(self, pressure_data: Dict[str, Any]) -> None:
        """Handle narrative pressure changes."""
        pressure_type = pressure_data.get("type")
        pressure_value = pressure_data.get("value", 0.0)

        if pressure_type:
            if "narrative_pressure" not in self.narrative_intelligence:
                self.narrative_intelligence["narrative_pressure"] = {}

            self.narrative_intelligence["narrative_pressure"][
                pressure_type
            ] = pressure_value

    def handle_ai_insight(self, insight_data: Dict[str, Any]) -> None:
        """Handle AI-generated insights."""
        if "ai_insights" not in self.narrative_intelligence:
            self.narrative_intelligence["ai_insights"] = []

        self.narrative_intelligence["ai_insights"].append(
            {"timestamp": datetime.now().isoformat(), "insight": insight_data}
        )


__all__ = ["StateManager"]
