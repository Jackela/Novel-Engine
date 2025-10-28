#!/usr/bin/env python3
"""
Simulation Coordination Module for Novel Engine.

This module handles core simulation orchestration including agent management,
simulation status tracking, world state persistence, and overall coordination.
Extracted from DirectorAgent for better modularity and maintainability.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.persona_agent import PersonaAgent

logger = logging.getLogger(__name__)


class SimulationCoordinator:
    """
    Manages core simulation coordination and agent lifecycle.

    Responsibilities:
    - Agent registration and management
    - Simulation status tracking and reporting
    - World state persistence and loading
    - Simulation lifecycle coordination
    """

    def __init__(
        self, world_state_file_path: Optional[str] = None, max_turn_history: int = 100
    ):
        """
        Initialize the Simulation Coordinator.

        Args:
            world_state_file_path: Optional path to world state file
            max_turn_history: Maximum number of turns to keep in history
        """
        self.world_state_file_path = world_state_file_path
        self.max_turn_history = max_turn_history

        # Agent management
        self.registered_agents: List[PersonaAgent] = []

        # Simulation tracking
        self.simulation_start_time = datetime.now()
        self.current_turn_number = 0
        self.total_actions_processed = 0

        # World state management
        self.world_state_data: Dict[str, Any] = {}

        # Load world state if path provided
        if self.world_state_file_path:
            self._load_world_state()

    def register_agent(self, agent: PersonaAgent, log_event_callback) -> bool:
        """
        Register a PersonaAgent instance with the simulation for management.

        Validates the agent has required methods and adds it to the registered agents list.
        Includes comprehensive validation to ensure agent compatibility and prevent
        runtime errors during simulation execution.

        Args:
            agent: PersonaAgent instance to register
            log_event_callback: Callback function for logging events

        Returns:
            bool: True if registration successful, False if validation failed
        """
        try:
            logger.info("Attempting to register agent for simulation management")

            # Validate the agent instance
            if not isinstance(agent, PersonaAgent):
                logger.error(
                    f"Invalid agent type: {type(agent)}. Expected PersonaAgent instance"
                )
                return False

            # Validate that the agent has the required methods
            required_methods = ["decision_loop", "get_decision_with_reasoning"]
            for method_name in required_methods:
                if not hasattr(agent, method_name):
                    logger.error(f"Agent missing required method: {method_name}")
                    return False

                method = getattr(agent, method_name)
                if not callable(method):
                    logger.error(f"Agent attribute {method_name} is not callable")
                    return False

            # Validate agent ID
            if not hasattr(agent, "agent_id") or not agent.agent_id:
                logger.error("Agent missing valid agent_id")
                return False

            # Check for duplicate registration
            for existing_agent in self.registered_agents:
                if existing_agent.agent_id == agent.agent_id:
                    logger.warning(
                        f"Agent {agent.agent_id} already registered - skipping"
                    )
                    return False

            # Add to registered agents list
            self.registered_agents.append(agent)

            # Extract character information for logging
            character_name = agent.character_data.get("name", "Unknown")
            faction = agent.subjective_worldview.get("primary_faction", "Unknown")

            # Log successful registration
            registration_event = (
                f"**Agent Registration:** {character_name} ({agent.agent_id}) joined the simulation\\n"
                f"**Faction:** {faction}\\n"
                f"**Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                f"**Total Agents:** {len(self.registered_agents)}"
            )
            log_event_callback(registration_event)

            logger.info(
                f"Agent {agent.agent_id} ({character_name}) registered successfully"
            )
            logger.info(f"Total registered agents: {len(self.registered_agents)}")

            return True

        except AttributeError as e:
            logger.error(f"Agent validation failed - missing attribute: {str(e)}")
            return False
        except (TypeError, KeyError) as e:
            # Invalid agent data or registration errors
            logger.error(
                f"Invalid data during agent registration: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (ValueError, RuntimeError) as e:
            # Agent registration processing errors
            logger.error(
                f"Error during agent registration: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False

    def remove_agent(self, agent_id: str, log_event_callback) -> bool:
        """
        Remove an agent from the simulation.

        Args:
            agent_id: ID of the agent to remove
            log_event_callback: Callback function for logging events

        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        try:
            for i, agent in enumerate(self.registered_agents):
                if agent.agent_id == agent_id:
                    removed_agent = self.registered_agents.pop(i)
                    character_name = removed_agent.character_data.get("name", "Unknown")

                    logger.info(f"Agent removed: {agent_id} ({character_name})")

                    # Log removal event
                    removal_event = (
                        f"**Agent Departure:** {character_name} ({agent_id}) left the simulation\\n"
                        f"**Departure Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                        f"**Remaining Agents:** {len(self.registered_agents)}"
                    )
                    log_event_callback(removal_event)

                    return True

            logger.warning(f"Agent not found for removal: {agent_id}")
            return False

        except (AttributeError, KeyError, TypeError) as e:
            # Invalid agent data or removal errors
            logger.error(
                f"Invalid data removing agent {agent_id}: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (ValueError, RuntimeError) as e:
            # Agent removal processing errors
            logger.error(
                f"Error removing agent {agent_id}: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False

    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information about the current simulation state.

        Returns:
            Dict containing detailed simulation status information
        """
        current_time = datetime.now()
        simulation_duration = (
            current_time - self.simulation_start_time
        ).total_seconds()

        # Calculate agent statistics
        agent_stats = {}
        for agent in self.registered_agents:
            character_name = agent.character_data.get("name", "Unknown")
            faction = agent.subjective_worldview.get("primary_faction", "Unknown")
            agent_stats[agent.agent_id] = {
                "name": character_name,
                "faction": faction,
                "status": getattr(agent, "current_status", "active"),
                "morale": getattr(agent, "morale_level", 50),
            }

        return {
            "simulation_info": {
                "start_time": self.simulation_start_time.isoformat(),
                "current_time": current_time.isoformat(),
                "duration_seconds": simulation_duration,
                "current_turn": self.current_turn_number,
                "total_actions_processed": self.total_actions_processed,
            },
            "agents": {
                "total_count": len(self.registered_agents),
                "details": agent_stats,
            },
            "world_state": {
                "loaded": bool(self.world_state_data),
                "file_path": self.world_state_file_path,
                "last_modified": self.world_state_data.get("last_saved", "Never"),
            },
            "performance": {
                "turns_processed": self.current_turn_number,
                "actions_per_turn": self.total_actions_processed
                / max(self.current_turn_number, 1),
                "simulation_efficiency": "normal",  # Could be calculated based on metrics
            },
        }

    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all registered agents with basic information.

        Returns:
            List of dictionaries containing agent information
        """
        agent_list = []
        for agent in self.registered_agents:
            character_name = agent.character_data.get("name", "Unknown")
            faction = agent.subjective_worldview.get("primary_faction", "Unknown")

            agent_list.append(
                {
                    "agent_id": agent.agent_id,
                    "character_name": character_name,
                    "faction": faction,
                    "status": getattr(agent, "current_status", "active"),
                }
            )

        return agent_list

    def save_world_state(
        self, file_path: Optional[str] = None, log_event_callback=None
    ) -> bool:
        """
        Save current world state to file.

        Args:
            file_path: Optional path to save to (uses default if None)
            log_event_callback: Optional callback function for logging events

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            save_path = (
                file_path or self.world_state_file_path or "world_state_backup.json"
            )

            # Add current timestamp to world state
            self.world_state_data["last_saved"] = datetime.now().isoformat()
            self.world_state_data["save_info"] = {
                "turn_number": self.current_turn_number,
                "total_agents": len(self.registered_agents),
                "total_actions": self.total_actions_processed,
            }

            with open(save_path, "w", encoding="utf-8") as file:
                json.dump(self.world_state_data, file, indent=2, ensure_ascii=False)

            logger.info(f"World state saved to: {save_path}")
            if log_event_callback:
                log_event_callback(f"World state saved to {save_path}")

            return True

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors saving world state
            logger.error(
                f"File error saving world state: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (json.JSONEncodeError, TypeError, ValueError) as e:
            # World state serialization errors
            logger.error(
                f"Serialization error saving world state: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return False

    def _load_world_state(self) -> None:
        """
        Load world state from the configured file path.

        Raises:
            ValueError: If world state file contains invalid data
            OSError: If file operations fail
        """
        if not self.world_state_file_path:
            logger.info("No world state file path configured")
            self._initialize_default_world_state()
            return

        try:
            world_state_path = Path(self.world_state_file_path)

            if not world_state_path.exists():
                logger.info(f"World state file not found: {self.world_state_file_path}")
                logger.info("Initializing default world state")
                self._initialize_default_world_state()
                return

            # Load existing world state file
            with open(world_state_path, "r", encoding="utf-8") as file:
                self.world_state_data = json.load(file)

            logger.info(f"World state loaded from: {self.world_state_file_path}")

            # Validate loaded data
            self._validate_world_state_data()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in world state file: {str(e)}")
            logger.info("Initializing default world state due to JSON error")
            self._initialize_default_world_state()
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors loading world state
            logger.error(
                f"File error loading world state: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            logger.info("Initializing default world state due to file error")
            self._initialize_default_world_state()
        except (TypeError, ValueError) as e:
            # World state parsing or validation errors
            logger.error(
                f"Parse error loading world state: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            logger.info("Initializing default world state due to parse error")
            self._initialize_default_world_state()

    def _initialize_default_world_state(self) -> None:
        """
        Initialize a default world state structure.

        Creates a basic world state with standard fields for new simulations.
        """
        self.world_state_data = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "simulation_metadata": {
                "title": "Default Simulation",
                "description": "A default simulation environment",
                "settings": {
                    "max_turn_history": self.max_turn_history,
                    "auto_save": True,
                },
            },
            "world_state": {
                "environment": {
                    "type": "default",
                    "conditions": "normal",
                    "visibility": "clear",
                },
                "factions": {
                    "neutral": {"influence": 1.0, "status": "active"},
                },
                "locations": {
                    "default_area": {
                        "type": "open_field",
                        "threat_level": "low",
                        "resources": ["basic_supplies"],
                    },
                },
            },
            "turn_history": [],
            "events": [],
        }

        logger.info("Default world state initialized")

    def _validate_world_state_data(self) -> None:
        """
        Validate the structure and content of loaded world state data.

        Ensures that world state data contains required fields and valid values
        for proper simulation operation.

        Raises:
            ValueError: If world state data is invalid or corrupted
        """
        if not isinstance(self.world_state_data, dict):
            raise ValueError("World state data must be a dictionary")

        # Check for required top-level fields
        required_fields = ["world_state", "turn_history"]
        for field in required_fields:
            if field not in self.world_state_data:
                logger.warning(
                    f"Missing field '{field}' in world state - adding default"
                )
                if field == "world_state":
                    self.world_state_data[field] = {}
                elif field == "turn_history":
                    self.world_state_data[field] = []

        # Validate turn history structure
        if not isinstance(self.world_state_data["turn_history"], list):
            logger.warning("Invalid turn_history format - resetting to empty list")
            self.world_state_data["turn_history"] = []

        # Trim turn history if it's too long
        if len(self.world_state_data["turn_history"]) > self.max_turn_history:
            self.world_state_data["turn_history"] = self.world_state_data[
                "turn_history"
            ][-self.max_turn_history :]
            logger.info(f"Turn history trimmed to last {self.max_turn_history} entries")

        logger.debug("World state data validation completed")

    def get_registered_agents(self) -> List[PersonaAgent]:
        """Get list of currently registered agents."""
        return self.registered_agents.copy()

    def get_world_state_data(self) -> Dict[str, Any]:
        """Get current world state data."""
        return self.world_state_data.copy()

    def update_simulation_metrics(
        self, turn_number: int, actions_processed: int
    ) -> None:
        """Update simulation tracking metrics."""
        self.current_turn_number = turn_number
        self.total_actions_processed = actions_processed
