#!/usr/bin/env python3
"""
World State Coordinator
=======================

Manages world state data, persistence, and feedback generation including:
- World state loading and initialization
- World state preparation for agents
- Feedback generation for agent discoveries
- World state persistence and backup management

This component handles all aspects of world state management while maintaining
separation from turn orchestration and agent lifecycle concerns.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


class WorldStateCoordinator:
    """
    Coordinates world state management and agent feedback generation.

    Responsibilities:
    - World state data loading and validation
    - Dynamic world state updates and tracking
    - Agent-specific feedback generation
    - World state persistence and backup management
    - Environmental change tracking and notification
    """

    def __init__(self, world_state_file_path: Optional[str] = None):
        """
        Initialize the WorldStateCoordinator.

        Args:
            world_state_file_path: Optional path to world state file for persistence
        """
        self.world_state_file_path = world_state_file_path

        # Core world state data
        self.world_state_data: Dict[str, Any] = {}

        # Dynamic world state tracker
        self.world_state_tracker = {
            "discovered_clues": {},  # agent_id -> list of discovered clues
            "environmental_changes": {},  # location -> list of changes
            "agent_discoveries": {},  # turn_number -> {agent_id: discoveries}
            "temporal_markers": {},  # timestamp -> events
            "investigation_history": [],  # chronological list of all investigations
        }

        # Initialize world state
        self._load_world_state()

        logger.info("WorldStateCoordinator initialized")

    def _load_world_state(self) -> None:
        """
        Load world state data from file if provided.

        Prepares for future integration with WorldState_DB.json and validates
        the loaded data structure.

        Raises:
            ValueError: If world state file is malformed
            OSError: If file operations fail
        """
        if not self.world_state_file_path:
            logger.info("No world state file provided, using default empty state")
            self._initialize_default_world_state()
            return

        try:
            world_state_path = Path(self.world_state_file_path)

            if not world_state_path.exists():
                logger.info(
                    f"World state file {self.world_state_file_path} does not exist, creating default"
                )
                self._initialize_default_world_state()
                self.save_world_state()
                return

            logger.info(f"Loading world state from: {self.world_state_file_path}")

            with open(world_state_path, "r", encoding="utf-8") as file:
                loaded_state = json.load(file)

            # Validate loaded state structure
            if not isinstance(loaded_state, dict):
                raise ValueError("World state must be a dictionary")

            self.world_state_data = loaded_state
            logger.info(
                f"World state loaded successfully ({len(self.world_state_data)} keys)"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in world state file: {str(e)}")
            raise ValueError(f"World state file contains invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load world state: {str(e)}")
            raise OSError(f"World state loading failed: {str(e)}")

    def _initialize_default_world_state(self) -> None:
        """Initialize default world state structure."""
        self.world_state_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "locations": {
                "default_area": {
                    "name": "Unknown Region",
                    "description": "A mysterious area awaiting exploration",
                    "threat_level": "moderate",
                    "faction_control": "contested",
                    "resources": ["unknown"],
                    "notable_features": [],
                }
            },
            "global_events": [],
            "faction_status": {
                "imperium": {"influence": 0.4, "activity": "moderate"},
                "chaos": {"influence": 0.2, "activity": "low"},
                "ork": {"influence": 0.2, "activity": "moderate"},
                "other": {"influence": 0.2, "activity": "low"},
            },
            "environmental_state": {
                "weather": "stable",
                "visibility": "normal",
                "hazards": [],
            },
        }
        logger.info("Default world state initialized")

    def get_world_state_for_agent(
        self, agent_id: str, current_turn: int, total_agents: int
    ) -> Dict[str, Any]:
        """
        Prepare world state information for a specific agent.

        Creates agent-specific world state data that includes both general
        world information and agent-specific context and discoveries.

        Args:
            agent_id: ID of the agent requesting world state
            current_turn: Current simulation turn number
            total_agents: Total number of agents in simulation

        Returns:
            Dictionary containing world state information for the agent
        """
        try:
            # Base world state information
            world_state_update = {
                "current_turn": current_turn,
                "simulation_time": datetime.now().isoformat(),
                "world_state": self.world_state_data.copy(),
                "location_updates": self._get_location_updates(),
                "entity_updates": self._get_entity_updates(agent_id),
                "faction_updates": self._get_faction_updates(),
                "environmental_updates": self._get_environmental_updates(),
            }

            # Add agent-specific discoveries and feedback
            agent_feedback = self.generate_world_state_feedback(agent_id)
            if agent_feedback:
                world_state_update["agent_feedback"] = agent_feedback

            return world_state_update

        except Exception as e:
            logger.error(f"Error preparing world state for agent {agent_id}: {str(e)}")
            return {
                "current_turn": current_turn,
                "simulation_time": datetime.now().isoformat(),
                "world_state": {},
                "error": "Failed to prepare world state",
            }

    def _get_location_updates(self) -> Dict[str, Any]:
        """Get current location status updates."""
        locations = self.world_state_data.get("locations", {})

        if not locations:
            return {
                "current_area": {
                    "threat_level": "moderate",
                    "faction_presence": "mixed",
                    "resources_available": True,
                    "strategic_importance": "normal",
                }
            }

        # Return first available location as current area
        first_location_key = next(iter(locations.keys()))
        first_location = locations[first_location_key]

        return {
            "current_area": {
                "name": first_location.get("name", "Unknown Area"),
                "threat_level": first_location.get("threat_level", "moderate"),
                "faction_presence": first_location.get("faction_control", "contested"),
                "resources_available": bool(first_location.get("resources", [])),
                "strategic_importance": "normal",
            }
        }

    def _get_entity_updates(self, agent_id: str) -> Dict[str, Any]:
        """Get information about other entities/agents."""
        # Placeholder for entity information
        # In future versions, this could include information about other agents
        # that this agent is aware of based on proximity, faction, etc.
        return {}

    def _get_faction_updates(self) -> Dict[str, Any]:
        """Get current faction status information."""
        faction_status = self.world_state_data.get("faction_status", {})

        if not faction_status:
            return {
                "imperium": {"activity": "normal", "influence": 0.6},
                "chaos": {"activity": "low", "influence": 0.2},
                "ork": {"activity": "moderate", "influence": 0.2},
            }

        return faction_status.copy()

    def _get_environmental_updates(self) -> Dict[str, Any]:
        """Get environmental status updates."""
        environmental_state = self.world_state_data.get("environmental_state", {})

        if not environmental_state:
            return {"weather": "stable", "visibility": "normal", "hazards": []}

        return environmental_state.copy()

    def generate_world_state_feedback(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate dynamic world state feedback based on agent discoveries.

        Creates feedback that agents receive about the consequences of their
        previous actions and the evolving state of the world.

        Args:
            agent_id: ID of the agent to generate feedback for

        Returns:
            Dictionary containing world state feedback or None if no feedback available
        """
        feedback = {}
        has_feedback = False

        try:
            # Generate feedback on personal discoveries
            personal_discoveries = self._get_agent_discoveries_feedback(agent_id)
            if personal_discoveries:
                feedback["personal_discoveries"] = personal_discoveries
                has_feedback = True

            # Generate feedback on environmental changes
            environmental_changes = self._get_environmental_changes_feedback(agent_id)
            if environmental_changes:
                feedback["environmental_changes"] = environmental_changes
                has_feedback = True

            # Generate feedback on other agents' activities
            other_agent_activities = self._get_other_agents_activities_feedback(
                agent_id
            )
            if other_agent_activities:
                feedback["other_agent_activities"] = other_agent_activities
                has_feedback = True

            # Generate a summary of the world state
            world_state_summary = self._get_world_state_summary()
            if world_state_summary:
                feedback["world_state_summary"] = world_state_summary
                has_feedback = True

            return feedback if has_feedback else None

        except Exception as e:
            logger.error(
                f"Error generating world state feedback for {agent_id}: {str(e)}"
            )
            return None

    def _get_agent_discoveries_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about the agent's recent discoveries.

        Args:
            agent_id: ID of the agent

        Returns:
            List of discovery feedback messages
        """
        discovered_clues = self.world_state_tracker.get("discovered_clues", {}).get(
            agent_id, []
        )

        if not discovered_clues:
            return []

        feedback = []
        for clue in discovered_clues[-3:]:  # Most recent 3 discoveries
            feedback.append(f"You recall discovering: {clue}")

        return feedback

    def _get_environmental_changes_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about environmental changes in the area.

        Args:
            agent_id: ID of the agent

        Returns:
            List of environmental change feedback messages
        """
        environmental_changes = self.world_state_tracker.get(
            "environmental_changes", {}
        )

        feedback = []
        for location, changes in environmental_changes.items():
            for change in changes[-2:]:  # Most recent 2 changes per location
                feedback.append(f"Environmental change in {location}: {change}")

        return feedback

    def _get_other_agents_activities_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about other agents' visible activities.

        Args:
            agent_id: ID of the requesting agent

        Returns:
            List of other agents' activity feedback messages
        """
        # Placeholder for other agent activity tracking
        # In future versions, this could track visible actions by other agents
        return []

    def _get_world_state_summary(self) -> Dict[str, Any]:
        """
        Get a general summary of the current world state.

        Returns:
            Dictionary containing world state summary information
        """
        try:
            return {
                "overall_stability": "moderate",
                "major_factions_active": len(
                    self.world_state_data.get("faction_status", {})
                ),
                "known_locations": len(self.world_state_data.get("locations", {})),
                "recent_events_count": len(
                    self.world_state_data.get("global_events", [])
                ),
                "environmental_status": self.world_state_data.get(
                    "environmental_state", {}
                ).get("weather", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error generating world state summary: {str(e)}")
            return {}

    def record_agent_discovery(
        self, agent_id: str, discovery: str, turn_number: int
    ) -> None:
        """
        Record a discovery made by an agent.

        Args:
            agent_id: ID of the agent making the discovery
            discovery: Description of what was discovered
            turn_number: Turn number when discovery was made
        """
        try:
            # Add to agent's personal discoveries
            if agent_id not in self.world_state_tracker["discovered_clues"]:
                self.world_state_tracker["discovered_clues"][agent_id] = []
            self.world_state_tracker["discovered_clues"][agent_id].append(discovery)

            # Add to turn-based discovery tracking
            if turn_number not in self.world_state_tracker["agent_discoveries"]:
                self.world_state_tracker["agent_discoveries"][turn_number] = {}
            if (
                agent_id
                not in self.world_state_tracker["agent_discoveries"][turn_number]
            ):
                self.world_state_tracker["agent_discoveries"][turn_number][
                    agent_id
                ] = []
            self.world_state_tracker["agent_discoveries"][turn_number][agent_id].append(
                discovery
            )

            # Add to investigation history
            investigation_entry = {
                "agent_id": agent_id,
                "discovery": discovery,
                "turn_number": turn_number,
                "timestamp": datetime.now().isoformat(),
            }
            self.world_state_tracker["investigation_history"].append(
                investigation_entry
            )

            logger.info(f"Recorded discovery for {agent_id}: {discovery}")

        except Exception as e:
            logger.error(f"Error recording agent discovery: {str(e)}")

    def record_environmental_change(self, location: str, change: str) -> None:
        """
        Record an environmental change in a specific location.

        Args:
            location: Location where the change occurred
            change: Description of the environmental change
        """
        try:
            if location not in self.world_state_tracker["environmental_changes"]:
                self.world_state_tracker["environmental_changes"][location] = []

            self.world_state_tracker["environmental_changes"][location].append(change)

            # Add temporal marker
            timestamp = datetime.now().isoformat()
            self.world_state_tracker["temporal_markers"][timestamp] = {
                "type": "environmental_change",
                "location": location,
                "change": change,
            }

            logger.info(f"Recorded environmental change in {location}: {change}")

        except Exception as e:
            logger.error(f"Error recording environmental change: {str(e)}")

    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.

        Args:
            file_path: Optional path to save to (uses default if None)

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            save_path = (
                file_path or self.world_state_file_path or "world_state_backup.json"
            )

            # Prepare world state data for saving
            save_data = self.world_state_data.copy()
            save_data["last_saved"] = datetime.now().isoformat()
            save_data["world_state_tracker"] = self.world_state_tracker

            with open(save_path, "w", encoding="utf-8") as file:
                json.dump(save_data, file, indent=2, ensure_ascii=False)

            logger.info(f"World state saved to: {save_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to save world state: {str(e)}")
            return False

    def get_world_state_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive world state summary for monitoring.

        Returns:
            Dictionary containing world state metrics and information
        """
        try:
            return {
                "world_state_file": self.world_state_file_path,
                "locations_count": len(self.world_state_data.get("locations", {})),
                "global_events_count": len(
                    self.world_state_data.get("global_events", [])
                ),
                "tracked_agents": len(
                    self.world_state_tracker.get("discovered_clues", {})
                ),
                "total_discoveries": sum(
                    len(discoveries)
                    for discoveries in self.world_state_tracker.get(
                        "discovered_clues", {}
                    ).values()
                ),
                "environmental_changes": len(
                    self.world_state_tracker.get("environmental_changes", {})
                ),
                "investigation_history_count": len(
                    self.world_state_tracker.get("investigation_history", [])
                ),
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating world state summary: {str(e)}")
            return {"error": str(e)}
