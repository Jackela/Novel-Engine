#!/usr/bin/env python3
"""
World State Management Component

Extracted from DirectorAgent for better separation of concerns.
Handles world state persistence, updates, and agent-specific context generation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorldStateManager:
    """
    Manages world state data, persistence, and agent-specific context generation.

    Responsibilities:
    - World state data loading and saving
    - Agent-specific world state preparation
    - Environmental feedback generation
    - State validation and consistency
    """

    def __init__(self, world_state_file_path: Optional[str] = None):
        """
        Initialize the world state manager.

        Args:
            world_state_file_path: Path to world state file (optional)
        """
        self.world_state_file_path = world_state_file_path
        self.world_state_data: Dict[str, Any] = {}
        self.turn_history: List[Dict[str, Any]] = []

        self._load_world_state()

    def _load_world_state(self) -> None:
        """Load world state from file or initialize default state."""
        if self.world_state_file_path and Path(self.world_state_file_path).exists():
            try:
                with open(self.world_state_file_path, "r") as f:
                    self.world_state_data = json.load(f)
                logger.info(f"Loaded world state from {self.world_state_file_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load world state: {e}")
                self._initialize_default_world_state()
        else:
            self._initialize_default_world_state()

    def _initialize_default_world_state(self) -> None:
        """Initialize default world state data."""
        self.world_state_data = {
            "world_metadata": {
                "name": "Default World",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            },
            "environmental_state": {
                "global_events": [],
                "weather": "stable",
                "threat_level": "moderate",
            },
            "entity_registry": {},
            "location_registry": {},
            "faction_registry": {},
        }
        logger.info("Initialized default world state")

    def prepare_world_state_for_agent(
        self, agent_id: str, current_turn: int, total_agents: int
    ) -> Dict[str, Any]:
        """
        Prepare customized world state for specific agent.

        Args:
            agent_id: ID of the agent requesting world state
            current_turn: Current simulation turn number
            total_agents: Total number of registered agents

        Returns:
            Dict containing agent-specific world state data
        """
        return {
            "current_turn": current_turn,
            "simulation_time": datetime.now().isoformat(),
            "turn_number": current_turn,
            "world_state": {
                "current_turn": current_turn,
                "total_agents": total_agents,
                "simulation_time": datetime.now().isoformat(),
            },
            "location_updates": self._get_location_updates_for_agent(agent_id),
            "entity_updates": self._get_entity_updates_for_agent(agent_id),
            "faction_updates": self._get_faction_updates_for_agent(agent_id),
            "environmental_updates": self._get_environmental_updates_for_agent(
                agent_id
            ),
        }

    def _get_location_updates_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get location-specific updates for agent."""
        return {
            "current_area": {
                "threat_level": "moderate",
                "faction_presence": "mixed",
                "resources_available": True,
                "strategic_importance": "normal",
            }
        }

    def _get_entity_updates_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get entity updates visible to specific agent."""
        return {}

    def _get_faction_updates_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get faction status updates relevant to agent."""
        return {}

    def _get_environmental_updates_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get environmental changes affecting agent."""
        return {
            "weather": self.world_state_data.get("environmental_state", {}).get(
                "weather", "stable"
            ),
            "global_events": self.world_state_data.get("environmental_state", {}).get(
                "global_events", []
            ),
        }

    def generate_world_state_feedback(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate feedback about world state changes for specific agent.

        Args:
            agent_id: ID of the agent to generate feedback for

        Returns:
            Dict containing world state feedback or None if no feedback
        """
        feedback = {
            "discoveries": self._get_agent_discoveries_feedback(agent_id),
            "environmental_changes": self._get_environmental_changes_feedback(agent_id),
            "other_agents_activities": self._get_other_agents_activities_feedback(
                agent_id
            ),
        }

        # Only return feedback if there's actual content
        if any(feedback.values()):
            return feedback
        return None

    def _get_agent_discoveries_feedback(self, agent_id: str) -> List[str]:
        """Get discoveries made by or relevant to specific agent."""
        return []

    def _get_environmental_changes_feedback(self, agent_id: str) -> List[str]:
        """Get environmental changes affecting specific agent."""
        return []

    def _get_other_agents_activities_feedback(self, agent_id: str) -> List[str]:
        """Get activities of other agents visible to specific agent."""
        return []

    def get_world_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive world state summary."""
        return {
            "total_entities": len(self.world_state_data.get("entity_registry", {})),
            "total_locations": len(self.world_state_data.get("location_registry", {})),
            "total_factions": len(self.world_state_data.get("faction_registry", {})),
            "global_threat_level": self.world_state_data.get(
                "environmental_state", {}
            ).get("threat_level", "unknown"),
            "active_global_events": len(
                self.world_state_data.get("environmental_state", {}).get(
                    "global_events", []
                )
            ),
        }

    def store_turn_in_history(self, turn_summary: Dict[str, Any]) -> None:
        """Store turn summary in world history."""
        turn_entry = {
            "turn_number": turn_summary.get("turn_number", 0),
            "timestamp": datetime.now().isoformat(),
            "summary": turn_summary,
            "world_state_snapshot": self.world_state_data.copy(),
        }

        self.turn_history.append(turn_entry)

        # Keep only last 100 turns to manage memory
        if len(self.turn_history) > 100:
            self.turn_history = self.turn_history[-100:]

    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.

        Args:
            file_path: Optional custom file path

        Returns:
            True if save successful, False otherwise
        """
        target_path = file_path or self.world_state_file_path

        if not target_path:
            logger.warning("No file path specified for world state save")
            return False

        try:
            with open(target_path, "w") as f:
                json.dump(self.world_state_data, f, indent=2)
            logger.info(f"World state saved to {target_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to save world state: {e}")
            return False

    def validate_world_state_data(self) -> None:
        """Validate world state data consistency."""
        required_keys = ["world_metadata", "environmental_state", "entity_registry"]

        for key in required_keys:
            if key not in self.world_state_data:
                logger.warning(f"Missing required world state key: {key}")
                # Auto-repair missing sections
                if key == "world_metadata":
                    self.world_state_data[key] = {
                        "name": "Unknown World",
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0",
                    }
                elif key == "environmental_state":
                    self.world_state_data[key] = {
                        "global_events": [],
                        "weather": "stable",
                        "threat_level": "moderate",
                    }
                elif key == "entity_registry":
                    self.world_state_data[key] = {}

        logger.info("World state validation completed")
