"""Agent Coordinator Module.

Manages agent-to-agent interactions, relationship tracking, and dialogue coordination.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .types import AgentDialogue, CommunicationType

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Coordinates agent interactions and relationship management."""

    def __init__(self) -> None:
        """Initialize the agent coordinator."""
        self.agent_relationships: Dict[str, Dict[str, float]] = {}
        self.communication_history: List[Dict[str, Any]] = []
        self.communication_metrics: Dict[str, Any] = {
            "total_communications": 0,
            "successful_dialogues": 0,
            "failed_dialogues": 0,
            "average_resolution_time": 0.0,
            "relationship_changes": 0,
        }

    def get_relationship(self, agent_a: str, agent_b: str) -> float:
        """Get the relationship value between two agents."""
        if agent_a in self.agent_relationships:
            return self.agent_relationships[agent_a].get(agent_b, 0.0)
        return 0.0

    def update_relationship(
        self, agent_a: str, agent_b: str, change: float
    ) -> float:
        """Update relationship between two agents.

        Args:
            agent_a: First agent ID
            agent_b: Second agent ID
            change: Relationship change value (-1.0 to 1.0)

        Returns:
            New relationship value
        """
        if agent_a not in self.agent_relationships:
            self.agent_relationships[agent_a] = {}

        current_value = self.agent_relationships[agent_a].get(agent_b, 0.0)
        new_value = max(-1.0, min(1.0, current_value + change))
        self.agent_relationships[agent_a][agent_b] = new_value

        self.communication_metrics["relationship_changes"] += 1
        return new_value

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status information for an agent."""
        return {
            "agent_id": agent_id,
            "relationships": self.agent_relationships.get(agent_id, {}),
            "communication_history": [
                comm
                for comm in self.communication_history[-10:]
                if agent_id in comm.get("participants", [])
            ],
        }

    def record_communication(
        self,
        participants: List[str],
        comm_type: str,
        result: Dict[str, Any],
    ) -> None:
        """Record a communication event."""
        from datetime import datetime

        self.communication_history.append(
            {
                "timestamp": datetime.now(),
                "participants": participants,
                "type": comm_type,
                "result": result,
            }
        )

        self.communication_metrics["total_communications"] += 1
        if result.get("success"):
            self.communication_metrics["successful_dialogues"] += 1
        else:
            self.communication_metrics["failed_dialogues"] += 1

    def update_communication_metrics(
        self, dialogue_results: List[Dict[str, Any]], execution_time: float
    ) -> None:
        """Update communication performance metrics."""
        self.communication_metrics["total_communications"] += len(dialogue_results)

        successful_dialogues = len(
            [d for d in dialogue_results if d.get("success")]
        )
        self.communication_metrics["successful_dialogues"] += successful_dialogues
        self.communication_metrics["failed_dialogues"] += (
            len(dialogue_results) - successful_dialogues
        )

        # Update average resolution time
        if dialogue_results:
            total_time = (
                self.communication_metrics["average_resolution_time"]
                * (
                    self.communication_metrics["total_communications"]
                    - len(dialogue_results)
                )
                + execution_time
            )
            self.communication_metrics["average_resolution_time"] = (
                total_time / self.communication_metrics["total_communications"]
            )

    def identify_dialogue_opportunities(
        self, active_dialogues: Dict[str, AgentDialogue], narrative_intelligence: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify opportunities for agent dialogue based on current state."""
        opportunities: List[Dict[str, Any]] = []

        # Check relationship-based opportunities
        for agent_id, relationships in self.agent_relationships.items():
            for other_agent, relationship_value in relationships.items():
                # High tension = conflict dialogue opportunity
                if relationship_value < -0.5:
                    opportunities.append(
                        {
                            "participants": [agent_id, other_agent],
                            "type": "negotiation",
                            "probability": min(abs(relationship_value), 0.9),
                            "context": {"relationship_tension": relationship_value},
                        }
                    )

                # Strong positive = collaboration opportunity
                elif relationship_value > 0.6:
                    opportunities.append(
                        {
                            "participants": [agent_id, other_agent],
                            "type": "collaboration",
                            "probability": min(relationship_value * 0.8, 0.8),
                            "context": {"relationship_strength": relationship_value},
                        }
                    )

        # Add narrative-driven opportunities
        if narrative_intelligence.get("dialogue_pressure", 0) > 0.7:
            opportunities.append(
                {
                    "participants": ["any", "any"],
                    "type": "dialogue",
                    "probability": 0.8,
                    "context": {"narrative_requirement": True},
                }
            )

        return opportunities

    def analyze_relationship_tensions(self) -> List[Dict[str, Any]]:
        """Analyze relationship tensions that might lead to interactions."""
        tensions = []
        for agent_id, relationships in self.agent_relationships.items():
            for other_agent, relationship_value in relationships.items():
                if relationship_value < -0.3:  # High tension
                    tensions.append(
                        {
                            "agents": [agent_id, other_agent],
                            "tension_level": abs(relationship_value),
                            "recommended_interaction": "conflict_resolution",
                        }
                    )
                elif relationship_value > 0.7:  # Strong positive relationship
                    tensions.append(
                        {
                            "agents": [agent_id, other_agent],
                            "relationship_strength": relationship_value,
                            "recommended_interaction": "collaboration",
                        }
                    )
        return tensions

    def get_metrics(self) -> Dict[str, Any]:
        """Get communication metrics."""
        return self.communication_metrics.copy()


__all__ = ["AgentCoordinator"]
