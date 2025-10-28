#!/usr/bin/env python3
"""
Turn Management Module for Novel Engine.

This module handles all turn-based simulation logic including turn execution,
world state preparation, agent action handling, and turn history management.
Extracted from DirectorAgent for better modularity and maintainability.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared_types import CharacterAction
from src.event_bus import EventBus
from src.persona_agent import PersonaAgent

logger = logging.getLogger(__name__)


class TurnManager:
    """
    Manages turn-based simulation execution and coordination.

    Responsibilities:
    - Turn lifecycle management (start, execute, complete)
    - World state preparation for turns and agents
    - Agent action handling and coordination
    - Turn history storage and management
    """

    def __init__(self, event_bus: EventBus, max_turn_history: int = 100):
        """
        Initialize the Turn Manager.

        Args:
            event_bus: Event bus for turn coordination
            max_turn_history: Maximum number of turns to keep in history
        """
        self.event_bus = event_bus
        self.max_turn_history = max_turn_history
        self.current_turn_number = 0
        self.total_actions_processed = 0

    def run_turn(
        self,
        registered_agents: List[PersonaAgent],
        world_state_data: Dict[str, Any],
        log_event_callback,
    ) -> Dict[str, Any]:
        """
        Execute a single simulation turn by emitting a 'TURN_START' event.

        Orchestrates the turn-based simulation by:
        1. Incrementing the turn counter and logging the turn start.
        2. Emitting a `TURN_START` event to all subscribed agents.
        3. Agents will react to this event and perform their actions asynchronously.
        4. The Director will handle agent actions via the `_handle_agent_action` callback.

        Args:
            registered_agents: List of currently registered agents
            world_state_data: Current world state data
            log_event_callback: Callback function for logging events

        Returns:
            A dictionary confirming the turn has started. Detailed turn results
            will be compiled as agents complete their actions.
        """
        turn_start_time = datetime.now()
        self.current_turn_number += 1

        logger.info(f"=== STARTING TURN {self.current_turn_number} ===")
        log_event_callback(f"TURN {self.current_turn_number} BEGINS")

        if not registered_agents:
            logger.warning("No registered agents found - turn will be empty")
            log_event_callback(f"TURN {self.current_turn_number} COMPLETED")
            return {"status": "empty_turn"}

        # Prepare a generic world state update for this turn
        world_state_update = self._prepare_world_state_for_turn(world_state_data)

        # Emit the turn start event for all agents to hear
        self.event_bus.emit("TURN_START", world_state_update=world_state_update)

        # The rest of the turn processing is now handled by event callbacks
        return {
            "status": "turn_started",
            "turn_number": self.current_turn_number,
            "timestamp": turn_start_time.isoformat(),
        }

    def _prepare_world_state_for_turn(
        self, world_state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepares a generic world state dictionary for the current turn.

        Args:
            world_state_data: Current world state data

        Returns:
            Dict containing prepared world state for the turn
        """
        return {
            "current_turn": self.current_turn_number,
            "simulation_time": datetime.now().isoformat(),
            "world_state": world_state_data,
        }

    def handle_agent_action(
        self, agent: PersonaAgent, action: Optional[CharacterAction], log_event_callback
    ) -> None:
        """
        Callback to handle an agent's action after they process a turn.

        Args:
            agent: The agent that performed the action
            action: The action performed (or None if waiting)
            log_event_callback: Callback function for logging events
        """
        if action:
            logger.info(f"Received action from {agent.agent_id}: {action.action_type}")
            # Process and log the action
            character_name = agent.character_data.get("name", "Unknown")
            action_description = (
                f"{character_name} ({agent.agent_id}) decided to {action.action_type}"
            )
            if action.reasoning:
                action_description += f": {action.reasoning}"
            log_event_callback(action_description)
            self.total_actions_processed += 1
        else:
            logger.info(f"{agent.agent_id} chose to wait.")
            log_event_callback(
                f"{agent.character_data.get('name', agent.agent_id)} is waiting and observing."
            )

    def prepare_world_state_for_agent(
        self,
        agent: PersonaAgent,
        registered_agents: List[PersonaAgent],
        world_state_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare world state information for a specific agent's decision-making.

        This method creates a customized world state update that includes both tactical
        information and rich narrative context when a campaign brief is loaded. The
        agent receives character-specific story elements alongside traditional simulation data.

        Args:
            agent: PersonaAgent instance to prepare world state for
            registered_agents: List of all registered agents
            world_state_data: Current world state data

        Returns:
            Dict containing world state information and narrative context relevant to the agent
        """
        # Basic world state update
        world_state_update = {
            "current_turn": self.current_turn_number,
            "simulation_time": datetime.now().isoformat(),
            "turn_number": self.current_turn_number,
            "world_state": {
                "current_turn": self.current_turn_number,
                "total_agents": len(registered_agents),
                "simulation_time": datetime.now().isoformat(),
            },
            "location_updates": {
                "current_area": {
                    "threat_level": "moderate",
                    "faction_presence": "mixed",
                    "resources_available": True,
                    "strategic_importance": "normal",
                }
            },
            "entity_updates": {
                # Information about other agents/entities the agent might be aware of
            },
            "faction_updates": {
                "alliance_network": {"activity": "normal", "influence": 0.6},
                "entropy_cult": {"activity": "low", "influence": 0.2},
                "freewind_collective": {"activity": "moderate", "influence": 0.2},
            },
            "recent_events": [
                {
                    "id": f"event_{self.current_turn_number}",
                    "type": "world_update",
                    "description": "The world is calm, but tensions remain",
                    "scope": "local",
                    "location": "simulation_space",
                }
            ],
            "turn_info": {
                "current_turn": self.current_turn_number,
                "timestamp": datetime.now().isoformat(),
                "phase": "action_selection",
            },
        }

        return world_state_update

    def store_turn_in_history(
        self, turn_summary: Dict[str, Any], world_state_data: Dict[str, Any]
    ) -> None:
        """
        Store turn summary in world state history for future reference.

        Maintains a history of all turns for analysis and potential AI integration.
        Implements memory management to prevent unbounded growth.

        Args:
            turn_summary: Complete turn summary data to store
            world_state_data: World state data to store history in
        """
        try:
            # Initialize turn history if it doesn't exist
            if "turn_history" not in world_state_data:
                world_state_data["turn_history"] = []

            # Add the turn data to the history
            world_state_data["turn_history"].append(turn_summary)

            # Implement memory management - keep only configured number of turns
            if len(world_state_data["turn_history"]) > self.max_turn_history:
                world_state_data["turn_history"] = world_state_data["turn_history"][
                    -self.max_turn_history :
                ]
                logger.info(
                    f"Turn history trimmed to last {self.max_turn_history} turns"
                )

            logger.debug(f"Turn {turn_summary['turn_number']} stored in history")

        except (AttributeError, KeyError, TypeError) as e:
            # Invalid world state or turn summary data errors
            logger.error(
                f"Invalid data storing turn in history: {e}",
                extra={"error_type": type(e).__name__},
            )
        except (ValueError, IndexError, RuntimeError) as e:
            # History management or data manipulation errors
            logger.error(
                f"Failed to store turn in history: {e}",
                extra={"error_type": type(e).__name__},
            )

    def get_current_turn_number(self) -> int:
        """Get the current turn number."""
        return self.current_turn_number

    def get_total_actions_processed(self) -> int:
        """Get the total number of actions processed."""
        return self.total_actions_processed
