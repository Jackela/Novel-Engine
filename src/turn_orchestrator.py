#!/usr/bin/env python3
"""
Turn Orchestrator
=================

Handles the orchestration of simulation turns including:
- Turn execution flow and coordination
- Turn preparation and world state updates
- Agent action handling and processing
- Turn history storage and management

This component manages the temporal flow of the simulation while maintaining
clear separation from world state management and agent lifecycle concerns.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.types.shared_types import CharacterAction
from src.event_bus import EventBus

# Import agent and shared types
from src.persona_agent import PersonaAgent

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TurnState:
    """Represents the state of a simulation turn."""

    turn_number: int
    start_time: datetime
    agents_processed: List[str] = field(default_factory=list)
    actions_received: List[Dict[str, Any]] = field(default_factory=list)
    world_state_updates: Dict[str, Any] = field(default_factory=dict)
    narrative_events: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False


class TurnOrchestrator:
    """
    Orchestrates simulation turns and manages turn execution flow.

    Responsibilities:
    - Turn initiation and coordination
    - Agent action collection and processing
    - Turn state management and tracking
    - Turn history maintenance
    - World state preparation for turns
    """

    def __init__(self, event_bus: EventBus, max_turn_history: int = 100):
        """
        Initialize the TurnOrchestrator.

        Args:
            event_bus: EventBus instance for coordination
            max_turn_history: Maximum number of turns to keep in history
        """
        self.event_bus = event_bus
        self.max_turn_history = max_turn_history

        # Turn state tracking
        self.current_turn_number = 0
        self.turn_history: List[TurnState] = []
        self.current_turn_state: Optional[TurnState] = None

        # Performance tracking
        self.total_actions_processed = 0
        self.average_turn_duration = 0.0

        logger.info("TurnOrchestrator initialized")

    async def run_turn(
        self,
        registered_agents: List[PersonaAgent],
        world_state_data: Dict[str, Any],
        log_event_callback: callable,
    ) -> Dict[str, Any]:
        """
        Execute a single simulation turn with dynamic context loading.

        Orchestrates the turn-based simulation by:
        1. Incrementing turn counter and preparing turn state
        2. Loading fresh context for all agents (async concurrent)
        3. Preparing enhanced world state updates for agents
        4. Emitting turn start event to all agents
        5. Managing turn execution flow

        Args:
            registered_agents: List of registered agents to participate
            world_state_data: Current world state data
            log_event_callback: Callback function for logging events

        Returns:
            Dictionary containing turn execution results
        """
        turn_start_time = datetime.now()
        self.current_turn_number += 1

        logger.info(f"=== STARTING TURN {self.current_turn_number} ===")
        log_event_callback(f"TURN {self.current_turn_number} BEGINS")

        # Initialize turn state
        self.current_turn_state = TurnState(
            turn_number=self.current_turn_number, start_time=turn_start_time
        )

        if not registered_agents:
            logger.warning("No registered agents found - turn will be empty")
            log_event_callback(f"TURN {self.current_turn_number} COMPLETED")
            self._finalize_turn()
            return {
                "status": "empty_turn",
                "turn_number": self.current_turn_number,
            }

        # NEW: Dynamic context loading for all agents
        context_loading_start = datetime.now()
        context_results = await self._refresh_agent_contexts(registered_agents)
        context_loading_duration = (
            datetime.now() - context_loading_start
        ).total_seconds()

        # Enhanced world state preparation (with context data)
        world_state_update = self._prepare_enhanced_world_state_for_turn(
            world_state_data, registered_agents
        )

        # Store enhanced world state in turn state
        self.current_turn_state.world_state_updates = world_state_update

        # Emit the turn start event with enhanced context
        self.event_bus.emit(
            "TURN_START", world_state_update=world_state_update
        )

        return {
            "status": "turn_started",
            "turn_number": self.current_turn_number,
            "timestamp": turn_start_time.isoformat(),
            "participants": len(registered_agents),
            "context_loading_duration": context_loading_duration,
            "context_results": context_results,
        }

    def _prepare_world_state_for_turn(
        self, world_state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare world state information for the current turn.

        Creates a standardized world state update that includes temporal information
        and current simulation state for agent decision-making.

        Args:
            world_state_data: Current world state data

        Returns:
            Dictionary containing prepared world state information
        """
        return {
            "current_turn": self.current_turn_number,
            "simulation_time": datetime.now().isoformat(),
            "world_state": world_state_data,
            "turn_metadata": {
                "turn_number": self.current_turn_number,
                "turn_start_time": (
                    self.current_turn_state.start_time.isoformat()
                    if self.current_turn_state
                    else None
                ),
            },
        }

    def _prepare_world_state_for_agent(
        self,
        agent: PersonaAgent,
        world_state_data: Dict[str, Any],
        registered_agents: List[PersonaAgent],
    ) -> Dict[str, Any]:
        """
        Prepare world state information customized for a specific agent.

        Creates agent-specific world state updates that include both general simulation
        data and information relevant to the specific agent's perspective and capabilities.

        Args:
            agent: PersonaAgent to prepare world state for
            world_state_data: Current world state data
            registered_agents: All registered agents in simulation

        Returns:
            Dictionary containing agent-specific world state information
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
                # Information about other agents/entities the agent might be
                # aware of
            },
            "faction_updates": {
                "imperium": {"activity": "normal", "influence": 0.6},
                "chaos": {"activity": "low", "influence": 0.2},
                "ork": {"activity": "moderate", "influence": 0.2},
            },
        }

        # Add agent-specific context if available
        if hasattr(agent, "agent_id"):
            world_state_update["agent_context"] = {
                "agent_id": agent.agent_id,
                "character_name": getattr(agent, "character_name", "Unknown"),
            }

        return world_state_update

    async def _refresh_agent_contexts(
        self, agents: List[PersonaAgent]
    ) -> Dict[str, Any]:
        """Refresh contexts for all agents concurrently."""
        context_results = {
            "successful_refreshes": 0,
            "failed_refreshes": 0,
            "total_agents": len(agents),
            "refresh_duration": 0.0,
        }

        start_time = datetime.now()

        # Create concurrent context refresh tasks
        refresh_tasks = []
        for agent in agents:
            if hasattr(agent, "refresh_context"):
                task = asyncio.create_task(agent.refresh_context())
                refresh_tasks.append((agent.agent_id, task))

        # Wait for all context refreshes to complete
        for agent_id, task in refresh_tasks:
            try:
                success = await task
                if success:
                    context_results["successful_refreshes"] += 1
                    logger.debug(f"Context refreshed for agent {agent_id}")
                else:
                    context_results["failed_refreshes"] += 1
                    logger.warning(
                        f"Context refresh failed for agent {agent_id}"
                    )
            except Exception as e:
                context_results["failed_refreshes"] += 1
                logger.error(
                    f"Context refresh error for agent {agent_id}: {e}"
                )

        context_results["refresh_duration"] = (
            datetime.now() - start_time
        ).total_seconds()

        # Log context refresh summary
        success_rate = context_results["successful_refreshes"] / max(
            1, context_results["total_agents"]
        )
        logger.info(
            f"Context refresh completed: {context_results['successful_refreshes']}/{context_results['total_agents']} "
            f"agents ({success_rate:.1%}success rate) in {context_results['refresh_duration']:.2f}s"
        )

        return context_results

    def _prepare_enhanced_world_state_for_turn(
        self,
        world_state_data: Dict[str, Any],
        registered_agents: List[PersonaAgent],
    ) -> Dict[str, Any]:
        """Prepare enhanced world state information for the current turn with context data."""
        # Base world state preparation (existing logic)
        world_state_update = self._prepare_world_state_for_turn(
            world_state_data
        )

        # Add context enhancement metadata
        world_state_update["context_enhanced"] = True
        world_state_update["agents_with_enhanced_context"] = []

        # Track which agents have enhanced context loaded
        for agent in registered_agents:
            if hasattr(agent, "core") and hasattr(
                agent.core, "character_data"
            ):
                character_data = agent.core.character_data
                if (
                    "enhanced_context" in character_data
                    and character_data.get("context_load_success", False)
                ):
                    world_state_update["agents_with_enhanced_context"].append(
                        agent.agent_id
                    )

        context_enhanced_count = len(
            world_state_update["agents_with_enhanced_context"]
        )
        logger.info(
            f"Enhanced context available for {context_enhanced_count}/{len(registered_agents)} agents"
        )

        return world_state_update

    def handle_agent_action(
        self,
        agent: PersonaAgent,
        action: Optional[CharacterAction],
        log_event_callback: callable,
    ) -> bool:
        """
        Handle an agent's action during turn execution.

        Processes agent actions, logs them appropriately, and updates turn state.

        Args:
            agent: PersonaAgent that performed the action
            action: Action taken by the agent (or None if waiting)
            log_event_callback: Callback function for logging events

        Returns:
            bool: True if action was processed successfully
        """
        try:
            if not self.current_turn_state:
                logger.warning(
                    "No active turn state when handling agent action"
                )
                return False

            # Record that this agent has been processed
            if agent.agent_id not in self.current_turn_state.agents_processed:
                self.current_turn_state.agents_processed.append(agent.agent_id)

            if action:
                logger.info(
                    f"Received action from {agent.agent_id}: {action.action_type}"
                )

                # Create action record
                action_record = {
                    "agent_id": agent.agent_id,
                    "action_type": action.action_type,
                    "reasoning": getattr(action, "reasoning", ""),
                    "timestamp": datetime.now().isoformat(),
                }
                self.current_turn_state.actions_received.append(action_record)

                # Log the action
                character_name = getattr(agent, "character_data", {}).get(
                    "name", agent.agent_id
                )
                action_description = f"{character_name} ({agent.agent_id}) decided to {action.action_type}"
                if hasattr(action, "reasoning") and action.reasoning:
                    action_description += f": {action.reasoning}"

                log_event_callback(action_description)
                self.total_actions_processed += 1

            else:
                logger.info(f"{agent.agent_id} chose to wait.")

                # Create waiting record
                wait_record = {
                    "agent_id": agent.agent_id,
                    "action_type": "wait",
                    "reasoning": "Agent chose to observe and wait",
                    "timestamp": datetime.now().isoformat(),
                }
                self.current_turn_state.actions_received.append(wait_record)

                character_name = getattr(agent, "character_data", {}).get(
                    "name", agent.agent_id
                )
                log_event_callback(
                    f"{character_name} is waiting and observing."
                )

            return True

        except Exception as e:
            logger.error(
                f"Error handling agent action from {agent.agent_id}: {str(e)}"
            )
            return False

    def _store_turn_in_history(self, turn_summary: Dict[str, Any]) -> None:
        """
        Store completed turn information in turn history.

        Maintains a rolling history of turns for analysis and replay purposes.

        Args:
            turn_summary: Summary information about the completed turn
        """
        try:
            if not self.current_turn_state:
                logger.warning("No turn state to store in history")
                return

            # Finalize the turn state
            self.current_turn_state.completed = True

            # Add turn state to history
            self.turn_history.append(self.current_turn_state)

            # Maintain history size limit
            if len(self.turn_history) > self.max_turn_history:
                removed_turn = self.turn_history.pop(0)
                logger.debug(
                    f"Removed turn {removed_turn.turn_number}from history (limit: {self.max_turn_history})"
                )

            # Update performance metrics
            if self.current_turn_state.start_time:
                turn_duration = (
                    datetime.now() - self.current_turn_state.start_time
                ).total_seconds()
                if self.average_turn_duration == 0:
                    self.average_turn_duration = turn_duration
                else:
                    # Simple exponential moving average
                    self.average_turn_duration = (
                        0.9 * self.average_turn_duration + 0.1 * turn_duration
                    )

            logger.info(
                f"Turn {self.current_turn_number}stored in history ({len( self.turn_history)} total)"
            )

        except Exception as e:
            logger.error(f"Error storing turn in history: {str(e)}")

    def _finalize_turn(self) -> None:
        """Finalize the current turn and prepare for the next one."""
        if self.current_turn_state:
            self.current_turn_state.completed = True
            self._store_turn_in_history({})
        self.current_turn_state = None

    def get_turn_history(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get turn history information.

        Args:
            limit: Maximum number of turns to return (most recent first)

        Returns:
            List of turn summary dictionaries
        """
        try:
            history_data = []
            recent_turns = (
                self.turn_history[-limit:] if limit else self.turn_history
            )

            for turn_state in reversed(recent_turns):  # Most recent first
                turn_data = {
                    "turn_number": turn_state.turn_number,
                    "start_time": turn_state.start_time.isoformat(),
                    "agents_processed": len(turn_state.agents_processed),
                    "actions_count": len(turn_state.actions_received),
                    "completed": turn_state.completed,
                }
                history_data.append(turn_data)

            return history_data

        except Exception as e:
            logger.error(f"Error getting turn history: {str(e)}")
            return []

    def get_current_turn_state(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current turn state.

        Returns:
            Dictionary with current turn information or None if no active turn
        """
        if not self.current_turn_state:
            return None

        try:
            return {
                "turn_number": self.current_turn_state.turn_number,
                "start_time": self.current_turn_state.start_time.isoformat(),
                "agents_processed": self.current_turn_state.agents_processed.copy(),
                "actions_received": len(
                    self.current_turn_state.actions_received
                ),
                "completed": self.current_turn_state.completed,
            }
        except Exception as e:
            logger.error(f"Error getting current turn state: {str(e)}")
            return None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get turn orchestration performance metrics.

        Returns:
            Dictionary containing performance information
        """
        return {
            "total_turns_executed": len(self.turn_history),
            "current_turn_number": self.current_turn_number,
            "total_actions_processed": self.total_actions_processed,
            "average_turn_duration": self.average_turn_duration,
            "history_size": len(self.turn_history),
            "max_history_size": self.max_turn_history,
        }
