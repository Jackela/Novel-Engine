#!/usr/bin/env python3
"""
Agent Coordination Component

Extracted from DirectorAgent for better separation of concerns.
Handles agent registration, lifecycle management, and coordination.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.types.shared_types import CharacterAction
from src.agents.persona_agent.agent import PersonaAgent

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Manages agent registration, lifecycle, and coordination.

    Responsibilities:
    - Agent registration and validation
    - Agent lifecycle management
    - Turn execution coordination
    - Agent communication and isolation
    """

    def __init__(self):
        """Initialize the agent coordinator."""
        self.registered_agents: List[PersonaAgent] = []
        self.total_actions_processed = 0
        self.current_turn_number = 0

    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a new agent with validation.

        Args:
            agent: PersonaAgent instance to register

        Returns:
            True if registration successful, False otherwise
        """
        if not isinstance(agent, PersonaAgent):
            logger.error(f"Invalid agent type: {type(agent)}. Expected PersonaAgent")
            return False

        # Check for duplicate agent IDs
        if any(
            existing.agent_id == agent.agent_id for existing in self.registered_agents
        ):
            logger.error(f"Agent with ID {agent.agent_id} is already registered")
            return False

        # Validate agent has required attributes
        if not hasattr(agent, "character_data") or not agent.character_data:
            logger.error(f"Agent {agent.agent_id} missing character_data")
            return False

        if not hasattr(agent, "agent_id") or not agent.agent_id:
            logger.error("Agent missing agent_id")
            return False

        # Register the agent
        self.registered_agents.append(agent)
        character_name = agent.character_data.get("name", "Unknown")

        logger.info(
            f"Successfully registered agent: {character_name} (ID: {agent.agent_id})"
        )
        logger.info(f"Total registered agents: {len(self.registered_agents)}")

        return True

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent by ID.

        Args:
            agent_id: ID of agent to remove

        Returns:
            True if removal successful, False if agent not found
        """
        for i, agent in enumerate(self.registered_agents):
            if agent.agent_id == agent_id:
                removed_agent = self.registered_agents.pop(i)
                character_name = removed_agent.character_data.get("name", "Unknown")
                logger.info(f"Removed agent: {character_name} (ID: {agent_id})")
                return True

        logger.warning(f"Agent with ID {agent_id} not found for removal")
        return False

    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get list of registered agents with basic info.

        Returns:
            List of dicts containing agent information
        """
        agent_list = []
        for agent in self.registered_agents:
            agent_info = {
                "agent_id": agent.agent_id,
                "character_name": agent.character_data.get("name", "Unknown"),
                "status": "active",  # Could be extended with actual status tracking
            }
            agent_list.append(agent_info)

        return agent_list

    def execute_turn(
        self, world_state_callback=None, action_handler=None
    ) -> Dict[str, Any]:
        """
        Execute a single simulation turn for all agents.

        Args:
            world_state_callback: Function to get world state for each agent
            action_handler: Function to handle agent actions

        Returns:
            Dict containing turn summary and results
        """
        self.current_turn_number += 1
        turn_start_time = datetime.now()

        logger.info(
            f"🎯 Starting Turn {self.current_turn_number} with {len(self.registered_agents)} agents"
        )

        turn_summary = {
            "turn_number": self.current_turn_number,
            "agents_active": len(self.registered_agents),
            "actions_taken": 0,
            "agents_waiting": 0,
            "timestamp": turn_start_time.isoformat(),
            "agent_actions": [],
        }

        # Process each agent's turn
        for agent in self.registered_agents:
            try:
                # Get world state for this agent
                world_state = {}
                if world_state_callback:
                    world_state = world_state_callback(agent)

                # Agent processes their turn
                logger.debug(f"Processing turn for agent: {agent.agent_id}")
                action = agent.process_turn(world_state)

                # Handle the action
                if action_handler:
                    action_handler(agent, action)

                # Record action in turn summary
                action_summary = self._create_action_summary(agent, action)
                turn_summary["agent_actions"].append(action_summary)

                if action:
                    turn_summary["actions_taken"] += 1
                    self.total_actions_processed += 1
                else:
                    turn_summary["agents_waiting"] += 1

            except Exception as e:
                logger.error(f"Error processing turn for agent {agent.agent_id}: {e}")
                # Record the error in turn summary
                error_summary = {
                    "agent_id": agent.agent_id,
                    "character_name": agent.character_data.get("name", "Unknown"),
                    "action_type": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                turn_summary["agent_actions"].append(error_summary)

        # Calculate turn duration
        turn_end_time = datetime.now()
        turn_summary["duration_seconds"] = (
            turn_end_time - turn_start_time
        ).total_seconds()

        logger.info(
            f"✅ Turn {self.current_turn_number} completed: "
            f"{turn_summary['actions_taken']} actions, "
            f"{turn_summary['agents_waiting']} waiting"
        )

        return turn_summary

    def _create_action_summary(
        self, agent: PersonaAgent, action: Optional[CharacterAction]
    ) -> Dict[str, Any]:
        """Create summary of agent's action for turn records."""
        character_name = agent.character_data.get("name", "Unknown")

        if action:
            return {
                "agent_id": agent.agent_id,
                "character_name": character_name,
                "action_type": action.action_type,
                "reasoning": action.reasoning,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "agent_id": agent.agent_id,
                "character_name": character_name,
                "action_type": "WAIT",
                "reasoning": "Agent chose to wait and observe",
                "timestamp": datetime.now().isoformat(),
            }

    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status and statistics."""
        return {
            "total_registered_agents": len(self.registered_agents),
            "current_turn": self.current_turn_number,
            "total_actions_processed": self.total_actions_processed,
            "agents": [
                {
                    "id": agent.agent_id,
                    "name": agent.character_data.get("name", "Unknown"),
                    "type": type(agent).__name__,
                }
                for agent in self.registered_agents
            ],
        }

    def validate_agents(self) -> List[str]:
        """
        Validate all registered agents and return any issues found.

        Returns:
            List of validation issue descriptions
        """
        issues = []

        for agent in self.registered_agents:
            # Check required attributes
            if not hasattr(agent, "agent_id") or not agent.agent_id:
                issues.append(f"Agent missing agent_id: {agent}")

            if not hasattr(agent, "character_data") or not agent.character_data:
                issues.append(
                    f"Agent {getattr(agent, 'agent_id', 'unknown')} missing character_data"
                )

            if not hasattr(agent, "process_turn"):
                issues.append(f"Agent {agent.agent_id} missing process_turn method")

            # Check for duplicate IDs
            agent_ids = [a.agent_id for a in self.registered_agents]
            if agent_ids.count(agent.agent_id) > 1:
                issues.append(f"Duplicate agent ID found: {agent.agent_id}")

        return issues

    def reset_coordination(self) -> None:
        """Reset coordination state (useful for testing or restarts)."""
        self.current_turn_number = 0
        self.total_actions_processed = 0
        logger.info("Agent coordination state reset")

    def get_agent_by_id(self, agent_id: str) -> Optional[PersonaAgent]:
        """Get agent by ID."""
        for agent in self.registered_agents:
            if agent.agent_id == agent_id:
                return agent
        return None



