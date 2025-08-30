"""
Turn Execution Engine
=====================

Manages the execution of simulation turns with comprehensive orchestration.
Handles turn preparation, agent coordination, and result processing.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .protocols import AgentManagerProtocol


class TurnPhase(Enum):
    """Phases of turn execution."""

    PREPARATION = "preparation"
    AGENT_DECISIONS = "agent_decisions"
    CONFLICT_RESOLUTION = "conflict_resolution"
    STATE_UPDATE = "state_update"
    FINALIZATION = "finalization"


@dataclass
class TurnContext:
    """Context information for turn execution."""

    turn_number: int
    start_time: datetime = field(default_factory=datetime.now)
    phase: TurnPhase = TurnPhase.PREPARATION
    agent_decisions: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    world_state_updates: Dict[str, Any] = field(default_factory=dict)
    narrative_events: List[Dict[str, Any]] = field(default_factory=list)
    execution_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnMetrics:
    """Performance metrics for turn execution."""

    total_duration: float = 0.0
    phase_durations: Dict[str, float] = field(default_factory=dict)
    agent_response_times: Dict[str, float] = field(default_factory=dict)
    success_rate: float = 1.0
    error_count: int = 0


class TurnExecutionEngine:
    """
    Orchestrates the execution of simulation turns.

    Responsibilities:
    - Turn preparation and context setup
    - Agent decision coordination
    - Conflict resolution
    - World state updates
    - Performance monitoring
    """

    def __init__(
        self,
        agent_manager: AgentManagerProtocol,
        logger: Optional[logging.Logger] = None,
    ):
        self.agent_manager = agent_manager
        self.logger = logger or logging.getLogger(__name__)

        self._turn_counter = 0
        self._current_context: Optional[TurnContext] = None
        self._turn_metrics: List[TurnMetrics] = []
        self._max_turn_duration = 30.0  # Maximum turn duration in seconds
        self._max_concurrent_agents = 10  # Maximum concurrent agent processing

        # Turn execution configuration
        self._config = {
            "enable_parallel_execution": True,
            "enable_conflict_resolution": True,
            "enable_narrative_events": True,
            "decision_timeout": 10.0,
            "max_retries": 3,
        }

    async def execute_turn(
        self, turn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete simulation turn.

        Args:
            turn_data: Optional data for turn configuration

        Returns:
            Dict containing turn results and metrics
        """
        self._turn_counter += 1
        turn_start_time = time.time()

        # Create turn context
        context = TurnContext(turn_number=self._turn_counter)
        self._current_context = context

        turn_result = {
            "success": False,
            "turn_number": self._turn_counter,
            "error": None,
            "agent_results": {},
            "world_state_changes": {},
            "narrative_events": [],
            "metrics": {},
        }

        try:
            self.logger.info(f"=== Starting Turn {self._turn_counter} ===")

            # Phase 1: Preparation
            prep_result = await self._execute_preparation_phase(context, turn_data)
            if not prep_result["success"]:
                turn_result["error"] = f"Preparation failed: {prep_result['error']}"
                return turn_result

            # Phase 2: Agent Decisions
            decision_result = await self._execute_decision_phase(context)
            if not decision_result["success"]:
                turn_result["error"] = (
                    f"Decision phase failed: {decision_result['error']}"
                )
                return turn_result

            # Phase 3: Conflict Resolution
            if self._config["enable_conflict_resolution"]:
                conflict_result = await self._execute_conflict_resolution_phase(context)
                if not conflict_result["success"]:
                    self.logger.warning(
                        f"Conflict resolution issues: {conflict_result['error']}"
                    )

            # Phase 4: State Update
            state_result = await self._execute_state_update_phase(context)
            if not state_result["success"]:
                turn_result["error"] = f"State update failed: {state_result['error']}"
                return turn_result

            # Phase 5: Finalization
            final_result = await self._execute_finalization_phase(context)
            if not final_result["success"]:
                self.logger.warning(f"Finalization issues: {final_result['error']}")

            # Compile results
            turn_duration = time.time() - turn_start_time
            context.execution_metrics["total_duration"] = turn_duration

            turn_result.update(
                {
                    "success": True,
                    "agent_results": context.agent_decisions,
                    "world_state_changes": context.world_state_updates,
                    "narrative_events": context.narrative_events,
                    "metrics": context.execution_metrics,
                }
            )

            # Record metrics
            metrics = TurnMetrics(
                total_duration=turn_duration,
                phase_durations=context.execution_metrics.get("phase_durations", {}),
                agent_response_times=context.execution_metrics.get(
                    "agent_response_times", {}
                ),
                success_rate=1.0,
                error_count=0,
            )
            self._turn_metrics.append(metrics)

            self.logger.info(
                f"Turn {self._turn_counter} completed successfully in {turn_duration:.2f}s"
            )

        except Exception as e:
            turn_duration = time.time() - turn_start_time
            self.logger.error(
                f"Turn {self._turn_counter} failed after {turn_duration:.2f}s: {e}"
            )

            turn_result.update(
                {
                    "error": str(e),
                    "metrics": {"total_duration": turn_duration, "error_count": 1},
                }
            )

            # Record failed metrics
            metrics = TurnMetrics(
                total_duration=turn_duration, success_rate=0.0, error_count=1
            )
            self._turn_metrics.append(metrics)

        finally:
            self._current_context = None

        return turn_result

    async def _execute_preparation_phase(
        self, context: TurnContext, turn_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute turn preparation phase."""
        phase_start = time.time()
        context.phase = TurnPhase.PREPARATION

        try:
            self.logger.debug(f"Turn {context.turn_number}: Preparation phase")

            # Validate agents
            agent_validation = await self.agent_manager.validate_agents()
            if agent_validation["invalid_agents"]:
                invalid_count = len(agent_validation["invalid_agents"])
                self.logger.warning(f"Found {invalid_count} invalid agents")

                # Remove invalid agents if configured
                # For now, just log the issue

            # Prepare turn context
            context.world_state_updates = (
                turn_data.get("world_state", {}) if turn_data else {}
            )

            # Setup phase metrics
            phase_duration = time.time() - phase_start
            if "phase_durations" not in context.execution_metrics:
                context.execution_metrics["phase_durations"] = {}
            context.execution_metrics["phase_durations"]["preparation"] = phase_duration

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_decision_phase(self, context: TurnContext) -> Dict[str, Any]:
        """Execute agent decision phase with parallel processing."""
        phase_start = time.time()
        context.phase = TurnPhase.AGENT_DECISIONS

        try:
            self.logger.debug(f"Turn {context.turn_number}: Decision phase")

            agents = await self.agent_manager.list_agents()
            if not agents:
                return {"success": False, "error": "No agents available for decisions"}

            # Execute agent decisions
            if self._config["enable_parallel_execution"] and len(agents) > 1:
                decision_results = await self._execute_parallel_decisions(
                    context, agents
                )
            else:
                decision_results = await self._execute_sequential_decisions(
                    context, agents
                )

            # Process results
            successful_decisions = 0
            for agent_id, result in decision_results.items():
                if result.get("success", False):
                    context.agent_decisions[agent_id] = result.get("decision", {})
                    successful_decisions += 1

                    # Update agent activity metrics
                    response_time = result.get("response_time", 0.0)
                    await self.agent_manager.update_agent_activity(
                        agent_id, response_time
                    )
                else:
                    self.logger.warning(
                        f"Agent {agent_id} decision failed: {result.get('error', 'Unknown')}"
                    )

            if successful_decisions == 0:
                return {"success": False, "error": "No successful agent decisions"}

            # Record metrics
            phase_duration = time.time() - phase_start
            context.execution_metrics["phase_durations"]["decisions"] = phase_duration
            context.execution_metrics["successful_decisions"] = successful_decisions
            context.execution_metrics["total_agents"] = len(agents)

            return {"success": True, "successful_decisions": successful_decisions}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_parallel_decisions(
        self, context: TurnContext, agents: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Execute agent decisions in parallel."""
        decision_tasks = []
        agent_ids = []

        for agent in agents:
            if hasattr(agent, "agent_id") and hasattr(agent, "make_decision"):
                agent_ids.append(agent.agent_id)
                task = self._execute_single_agent_decision(agent)
                decision_tasks.append(task)

        if not decision_tasks:
            return {}

        # Limit concurrent execution
        if len(decision_tasks) > self._max_concurrent_agents:
            # Process in batches
            results = {}
            for i in range(0, len(decision_tasks), self._max_concurrent_agents):
                batch_tasks = decision_tasks[i : i + self._max_concurrent_agents]
                batch_ids = agent_ids[i : i + self._max_concurrent_agents]

                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                for agent_id, result in zip(batch_ids, batch_results):
                    if isinstance(result, Exception):
                        results[agent_id] = {"success": False, "error": str(result)}
                    else:
                        results[agent_id] = result

            return results
        else:
            # Process all at once
            results_list = await asyncio.gather(*decision_tasks, return_exceptions=True)

            results = {}
            for agent_id, result in zip(agent_ids, results_list):
                if isinstance(result, Exception):
                    results[agent_id] = {"success": False, "error": str(result)}
                else:
                    results[agent_id] = result

            return results

    async def _execute_sequential_decisions(
        self, context: TurnContext, agents: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Execute agent decisions sequentially."""
        results = {}

        for agent in agents:
            if hasattr(agent, "agent_id") and hasattr(agent, "make_decision"):
                agent_id = agent.agent_id
                result = await self._execute_single_agent_decision(agent)
                results[agent_id] = result

        return results

    async def _execute_single_agent_decision(self, agent: Any) -> Dict[str, Any]:
        """Execute decision for a single agent with timeout and error handling."""
        agent_id = getattr(agent, "agent_id", "unknown")
        decision_start = time.time()

        try:
            # Execute with timeout
            decision_result = await asyncio.wait_for(
                agent.make_decision(), timeout=self._config["decision_timeout"]
            )

            response_time = time.time() - decision_start

            return {
                "success": True,
                "decision": decision_result,
                "response_time": response_time,
            }

        except asyncio.TimeoutError:
            response_time = time.time() - decision_start
            self.logger.warning(
                f"Agent {agent_id} decision timeout after {response_time:.2f}s"
            )
            return {
                "success": False,
                "error": "Decision timeout",
                "response_time": response_time,
            }

        except Exception as e:
            response_time = time.time() - decision_start
            self.logger.error(
                f"Agent {agent_id} decision error after {response_time:.2f}s: {e}"
            )
            return {"success": False, "error": str(e), "response_time": response_time}

    async def _execute_conflict_resolution_phase(
        self, context: TurnContext
    ) -> Dict[str, Any]:
        """Execute conflict resolution phase."""
        phase_start = time.time()
        context.phase = TurnPhase.CONFLICT_RESOLUTION

        try:
            self.logger.debug(f"Turn {context.turn_number}: Conflict resolution phase")

            # Identify conflicts between agent decisions
            conflicts = await self._identify_conflicts(context.agent_decisions)
            context.conflicts = conflicts

            if conflicts:
                self.logger.info(f"Found {len(conflicts)} conflicts to resolve")

                # Resolve conflicts
                for conflict in conflicts:
                    resolution = await self._resolve_conflict(conflict, context)
                    if resolution.get("success"):
                        # Apply conflict resolution
                        self._apply_conflict_resolution(resolution, context)
                    else:
                        self.logger.warning(
                            f"Failed to resolve conflict: {resolution.get('error')}"
                        )

            phase_duration = time.time() - phase_start
            context.execution_metrics["phase_durations"][
                "conflict_resolution"
            ] = phase_duration
            context.execution_metrics["conflicts_resolved"] = len(conflicts)

            return {"success": True, "conflicts_resolved": len(conflicts)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_state_update_phase(self, context: TurnContext) -> Dict[str, Any]:
        """Execute world state update phase."""
        phase_start = time.time()
        context.phase = TurnPhase.STATE_UPDATE

        try:
            self.logger.debug(f"Turn {context.turn_number}: State update phase")

            # Aggregate state changes from agent decisions
            state_changes = {}
            for agent_id, decision in context.agent_decisions.items():
                if isinstance(decision, dict) and "world_state_changes" in decision:
                    agent_changes = decision["world_state_changes"]
                    if isinstance(agent_changes, dict):
                        state_changes.update(agent_changes)

            # Merge with initial world state updates
            state_changes.update(context.world_state_updates)
            context.world_state_updates = state_changes

            phase_duration = time.time() - phase_start
            context.execution_metrics["phase_durations"][
                "state_update"
            ] = phase_duration
            context.execution_metrics["state_changes_count"] = len(state_changes)

            return {"success": True, "state_changes": len(state_changes)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_finalization_phase(self, context: TurnContext) -> Dict[str, Any]:
        """Execute turn finalization phase."""
        phase_start = time.time()
        context.phase = TurnPhase.FINALIZATION

        try:
            self.logger.debug(f"Turn {context.turn_number}: Finalization phase")

            # Generate narrative events if enabled
            if self._config["enable_narrative_events"]:
                narrative_events = await self._generate_narrative_events(context)
                context.narrative_events = narrative_events

            # Finalize turn context
            context.execution_metrics["finalized_at"] = datetime.now().isoformat()

            phase_duration = time.time() - phase_start
            context.execution_metrics["phase_durations"][
                "finalization"
            ] = phase_duration

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _identify_conflicts(
        self, agent_decisions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify conflicts between agent decisions."""
        conflicts = []

        # Simple conflict detection - can be enhanced
        decision_types = {}
        for agent_id, decision in agent_decisions.items():
            if isinstance(decision, dict) and "action_type" in decision:
                action_type = decision["action_type"]
                if action_type not in decision_types:
                    decision_types[action_type] = []
                decision_types[action_type].append((agent_id, decision))

        # Check for conflicting actions of the same type
        for action_type, decisions in decision_types.items():
            if len(decisions) > 1:
                conflicts.append(
                    {
                        "type": "action_conflict",
                        "action_type": action_type,
                        "agents": [d[0] for d in decisions],
                        "decisions": [d[1] for d in decisions],
                    }
                )

        return conflicts

    async def _resolve_conflict(
        self, conflict: Dict[str, Any], context: TurnContext
    ) -> Dict[str, Any]:
        """Resolve a specific conflict."""
        try:
            # Simple conflict resolution - prioritize first agent
            # More sophisticated resolution logic can be implemented
            agents = conflict.get("agents", [])
            if agents:
                winner = agents[0]  # Simple: first agent wins
                return {
                    "success": True,
                    "resolution": "priority_based",
                    "winner": winner,
                    "conflict": conflict,
                }

            return {"success": False, "error": "No agents in conflict"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _apply_conflict_resolution(
        self, resolution: Dict[str, Any], context: TurnContext
    ) -> None:
        """Apply conflict resolution to context."""
        if resolution.get("success") and "winner" in resolution:
            winner = resolution["winner"]
            conflict = resolution["conflict"]

            # Remove decisions from losing agents
            for agent_id in conflict.get("agents", []):
                if agent_id != winner and agent_id in context.agent_decisions:
                    # Mark as overridden rather than removing
                    context.agent_decisions[agent_id]["overridden"] = True
                    context.agent_decisions[agent_id]["overridden_by"] = winner

    async def _generate_narrative_events(
        self, context: TurnContext
    ) -> List[Dict[str, Any]]:
        """Generate narrative events based on turn results."""
        events = []

        # Generate events for successful decisions
        for agent_id, decision in context.agent_decisions.items():
            if isinstance(decision, dict) and not decision.get("overridden", False):
                event = {
                    "type": "agent_action",
                    "agent_id": agent_id,
                    "turn_number": context.turn_number,
                    "timestamp": datetime.now().isoformat(),
                    "action": decision.get("action_type", "unknown"),
                    "description": decision.get(
                        "description", f"Agent {agent_id} performed an action"
                    ),
                }
                events.append(event)

        # Generate events for conflicts
        for conflict in context.conflicts:
            event = {
                "type": "conflict_resolved",
                "turn_number": context.turn_number,
                "timestamp": datetime.now().isoformat(),
                "conflict_type": conflict.get("type", "unknown"),
                "agents_involved": conflict.get("agents", []),
                "description": f"Conflict resolved between {len(conflict.get('agents', []))} agents",
            }
            events.append(event)

        return events

    async def get_turn_metrics(self, last_n: int = 10) -> Dict[str, Any]:
        """Get turn execution metrics."""
        recent_metrics = self._turn_metrics[-last_n:] if self._turn_metrics else []

        if not recent_metrics:
            return {"error": "No metrics available"}

        # Calculate averages
        avg_duration = sum(m.total_duration for m in recent_metrics) / len(
            recent_metrics
        )
        avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(
            recent_metrics
        )
        total_errors = sum(m.error_count for m in recent_metrics)

        return {
            "total_turns": self._turn_counter,
            "recent_turns_analyzed": len(recent_metrics),
            "average_duration": avg_duration,
            "average_success_rate": avg_success_rate,
            "total_recent_errors": total_errors,
            "last_turn_duration": (
                recent_metrics[-1].total_duration if recent_metrics else 0
            ),
            "performance_trend": "stable",  # Could be enhanced with trend analysis
        }

    async def get_current_turn_info(self) -> Optional[Dict[str, Any]]:
        """Get information about currently executing turn."""
        if self._current_context:
            return {
                "turn_number": self._current_context.turn_number,
                "phase": self._current_context.phase.value,
                "start_time": self._current_context.start_time.isoformat(),
                "agents_processed": len(self._current_context.agent_decisions),
                "conflicts_detected": len(self._current_context.conflicts),
            }
        return None

    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update turn execution configuration."""
        self._config.update(config_updates)
        self.logger.info(f"Turn execution config updated: {config_updates}")

    def get_config(self) -> Dict[str, Any]:
        """Get current turn execution configuration."""
        return self._config.copy()
