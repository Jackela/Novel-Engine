#!/usr/bin/env python3
"""
Interaction Orchestration Phase Implementation

Orchestrates agent interactions, negotiations, and decision-making
with conflict resolution, multi-party coordination, and action validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ...domain.value_objects import PhaseType
from .base_phase import BasePhaseImplementation, PhaseExecutionContext, PhaseResult


class InteractionSession:
    """Represents an active interaction session between agents."""

    def __init__(
        self,
        session_id: str,
        participants: List[str],
        interaction_type: str,
        context: Dict[str, Any],
    ):
        self.session_id = session_id
        self.participants = participants
        self.interaction_type = interaction_type
        self.context = context
        self.started_at = datetime.now()
        self.actions_proposed: List[Dict[str, Any]] = []
        self.negotiations: List[Dict[str, Any]] = []
        self.status = "active"
        self.resolution: Optional[Dict[str, Any]] = None


class InteractionOrchestrationPhase(BasePhaseImplementation):
    """
    Implementation of interaction orchestration pipeline phase.

    Coordinates agent interactions including:
    - Multi-party negotiations and discussions
    - Action proposal and validation
    - Conflict resolution mechanisms
    - Resource allocation and sharing
    - Collaborative decision making
    - Time-constrained interaction windows
    """

    def __init__(self):
        super().__init__(PhaseType.INTERACTION_ORCHESTRATION)
        self.execution_timeout_ms = 20000  # 20 seconds for interactions
        self.interaction_service_endpoint = "interaction_context"
        self.agent_service_endpoint = "agent_context"

    async def _execute_phase_implementation(
        self, context: PhaseExecutionContext
    ) -> PhaseResult:
        """
        Execute interaction orchestration for all participants.

        Args:
            context: Phase execution context

        Returns:
            PhaseResult with interaction orchestration results
        """
        # Initialize phase metrics
        interactions_completed = 0
        negotiations_resolved = 0
        actions_proposed = 0
        conflicts_resolved = 0

        try:
            # Step 1: Analyze interaction opportunities
            interaction_opportunities = await self._analyze_interaction_opportunities(
                context
            )

            # Step 2: Create interaction sessions
            active_sessions = await self._create_interaction_sessions(
                context, interaction_opportunities
            )

            # Step 3: Execute interaction sessions
            session_results = {}
            for session in active_sessions:
                try:
                    result = await self._execute_interaction_session(context, session)
                    session_results[session.session_id] = result

                    if result.get("completed"):
                        interactions_completed += 1

                    negotiations_resolved += result.get("negotiations_resolved", 0)
                    actions_proposed += result.get("actions_proposed", 0)
                    conflicts_resolved += result.get("conflicts_resolved", 0)

                except Exception:
                    # Log session failure but continue with others
                    context.record_performance_metric(
                        "interaction_session_failures",
                        context.performance_metrics.get(
                            "interaction_session_failures", 0
                        )
                        + 1,
                    )

            # Step 4: Process interaction outcomes
            await self._process_interaction_outcomes(
                context, session_results
            )

            # Step 5: Generate interaction events
            interaction_events = await self._generate_interaction_events(
                context, interactions_completed, negotiations_resolved
            )

            # Record performance metrics
            context.record_performance_metric(
                "interactions_completed", float(interactions_completed)
            )
            context.record_performance_metric(
                "negotiations_resolved", float(negotiations_resolved)
            )
            context.record_performance_metric(
                "actions_proposed", float(actions_proposed)
            )
            context.record_performance_metric(
                "conflicts_resolved", float(conflicts_resolved)
            )

            # Calculate success metrics
            total_opportunities = len(interaction_opportunities)
            completion_rate = interactions_completed / max(1, total_opportunities)

            return PhaseResult(
                success=completion_rate
                > 0.3,  # Success if >30% of opportunities completed
                events_processed=len(interaction_opportunities),
                events_generated=interaction_events,
                artifacts_created=[
                    f"interaction_sessions_{len(active_sessions)}",
                    f"negotiations_{negotiations_resolved}",
                    f"proposed_actions_{actions_proposed}",
                    f"resolved_conflicts_{conflicts_resolved}",
                ],
                metadata={
                    "interaction_summary": {
                        "total_opportunities": total_opportunities,
                        "sessions_created": len(active_sessions),
                        "interactions_completed": interactions_completed,
                        "negotiations_resolved": negotiations_resolved,
                        "actions_proposed": actions_proposed,
                        "conflicts_resolved": conflicts_resolved,
                        "completion_rate": completion_rate,
                    }
                },
            )

        except Exception as e:
            return self._create_failure_result(
                context,
                f"Interaction orchestration failed: {e}",
                {
                    "partial_results": {
                        "interactions_completed": interactions_completed,
                        "negotiations_resolved": negotiations_resolved,
                        "actions_proposed": actions_proposed,
                    }
                },
            )

    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate preconditions for interaction orchestration.

        Args:
            context: Phase execution context

        Raises:
            ValueError: If preconditions are not met
        """
        # Check that we have participants for interactions
        if not context.participants:
            raise ValueError("No participants available for interaction orchestration")

        # Single participant can still have valid interactions (with environment, NPCs, etc.)
        if len(context.participants) == 1:
            # This is valid - agent can interact with world, NPCs, objects
            pass

        # Check negotiation timeout is reasonable
        if context.configuration.negotiation_timeout_seconds <= 0:
            raise ValueError("Negotiation timeout must be positive")

    async def _analyze_interaction_opportunities(
        self, context: PhaseExecutionContext
    ) -> List[Dict[str, Any]]:
        """
        Analyze potential interaction opportunities between agents.

        Args:
            context: Phase execution context

        Returns:
            List of interaction opportunities
        """
        # Get current agent states and positions
        agent_states = {}
        for participant_id in context.participants:
            try:
                agent_response = await self._call_external_service(
                    context,
                    self.agent_service_endpoint,
                    "get_agent_interaction_state",
                    {"agent_id": participant_id},
                )

                if agent_response.get("success"):
                    agent_states[participant_id] = agent_response.get("state", {})

            except Exception:
                # Use default state if agent state unavailable
                agent_states[participant_id] = self._get_default_agent_state()

        # Analyze opportunities based on proximity, goals, and context
        opportunities = []

        # Direct agent-to-agent interactions
        if len(context.participants) > 1:
            opportunities.extend(
                await self._find_agent_interaction_opportunities(context, agent_states)
            )

        # Agent-environment interactions
        opportunities.extend(
            await self._find_environment_interaction_opportunities(
                context, agent_states
            )
        )

        # Agent-NPC interactions
        opportunities.extend(
            await self._find_npc_interaction_opportunities(context, agent_states)
        )

        # Collaborative opportunities
        if len(context.participants) > 2:
            opportunities.extend(
                await self._find_collaborative_opportunities(context, agent_states)
            )

        # Priority sorting - highest priority interactions first
        opportunities.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return opportunities

    async def _find_agent_interaction_opportunities(
        self, context: PhaseExecutionContext, agent_states: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find opportunities for direct agent-to-agent interactions."""
        opportunities = []
        participants = context.participants

        # Check all pairs of agents
        for i, agent_a in enumerate(participants):
            for agent_b in participants[i + 1 :]:
                # Check proximity
                proximity_score = self._calculate_agent_proximity(
                    agent_states.get(agent_a, {}), agent_states.get(agent_b, {})
                )

                if proximity_score > 0.3:  # Close enough to interact
                    # Check goal alignment or conflict
                    interaction_type = self._determine_interaction_type(
                        agent_states.get(agent_a, {}), agent_states.get(agent_b, {})
                    )

                    priority = self._calculate_interaction_priority(
                        interaction_type, proximity_score, agent_states
                    )

                    if priority > 0.2:  # Worth pursuing
                        opportunities.append(
                            {
                                "type": "agent_interaction",
                                "interaction_subtype": interaction_type,
                                "participants": [agent_a, agent_b],
                                "priority": priority,
                                "proximity_score": proximity_score,
                                "estimated_duration": self._estimate_interaction_duration(
                                    interaction_type
                                ),
                            }
                        )

        return opportunities

    async def _find_environment_interaction_opportunities(
        self, context: PhaseExecutionContext, agent_states: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find opportunities for agent-environment interactions."""
        opportunities = []

        # Get environmental interaction possibilities
        env_response = await self._call_external_service(
            context,
            "world_context",
            "get_interaction_opportunities",
            {
                "agent_positions": {
                    agent_id: state.get("position", {})
                    for agent_id, state in agent_states.items()
                },
                "interaction_types": ["object", "location", "resource"],
            },
        )

        env_opportunities = env_response.get("opportunities", [])

        for opportunity in env_opportunities:
            # Check if any agents can interact with this opportunity
            eligible_agents = []
            for agent_id, agent_state in agent_states.items():
                if self._can_agent_interact_with_environment(agent_state, opportunity):
                    eligible_agents.append(agent_id)

            if eligible_agents:
                opportunities.append(
                    {
                        "type": "environment_interaction",
                        "interaction_subtype": opportunity.get("type"),
                        "participants": eligible_agents,
                        "target": opportunity.get("target"),
                        "priority": opportunity.get("priority", 0.3),
                        "estimated_duration": opportunity.get(
                            "estimated_duration", 5000
                        ),
                    }
                )

        return opportunities

    async def _find_npc_interaction_opportunities(
        self, context: PhaseExecutionContext, agent_states: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find opportunities for agent-NPC interactions."""
        opportunities = []

        # Get NPCs in the area
        npc_response = await self._call_external_service(
            context,
            "world_context",
            "get_nearby_npcs",
            {
                "agent_positions": {
                    agent_id: state.get("position", {})
                    for agent_id, state in agent_states.items()
                },
                "interaction_radius": 100,  # meters or game units
            },
        )

        npcs = npc_response.get("npcs", [])

        for npc in npcs:
            # Find agents that can interact with this NPC
            eligible_agents = []
            for agent_id, agent_state in agent_states.items():
                if self._can_agent_interact_with_npc(agent_state, npc):
                    eligible_agents.append(agent_id)

            if eligible_agents:
                opportunities.append(
                    {
                        "type": "npc_interaction",
                        "interaction_subtype": npc.get("interaction_type", "dialogue"),
                        "participants": eligible_agents,
                        "npc": npc,
                        "priority": npc.get("importance", 0.2),
                        "estimated_duration": 3000,  # 3 seconds for NPC interactions
                    }
                )

        return opportunities

    async def _find_collaborative_opportunities(
        self, context: PhaseExecutionContext, agent_states: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find opportunities for multi-agent collaboration."""
        opportunities = []

        # Check for collaborative goals or tasks
        collaborative_tasks = await self._identify_collaborative_tasks(
            context, agent_states
        )

        for task in collaborative_tasks:
            required_participants = task.get("required_participants", [])
            available_participants = [
                p for p in required_participants if p in context.participants
            ]

            if len(available_participants) >= task.get("min_participants", 2):
                opportunities.append(
                    {
                        "type": "collaboration",
                        "interaction_subtype": task.get("task_type"),
                        "participants": available_participants,
                        "task": task,
                        "priority": task.get("priority", 0.5),
                        "estimated_duration": task.get("estimated_duration", 10000),
                    }
                )

        return opportunities

    async def _create_interaction_sessions(
        self, context: PhaseExecutionContext, opportunities: List[Dict[str, Any]]
    ) -> List[InteractionSession]:
        """Create interaction sessions from opportunities."""
        sessions = []
        used_participants: Set[str] = set()

        # Create sessions for highest priority opportunities first
        for opportunity in opportunities:
            participants = opportunity["participants"]

            # Check if participants are already in use
            if not any(p in used_participants for p in participants):
                # Create session
                session = InteractionSession(
                    session_id=str(uuid4()),
                    participants=participants,
                    interaction_type=opportunity["type"],
                    context=opportunity,
                )

                sessions.append(session)
                used_participants.update(participants)

                # Limit concurrent sessions based on configuration
                if len(sessions) >= context.configuration.max_concurrent_operations:
                    break

        return sessions

    async def _execute_interaction_session(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> Dict[str, Any]:
        """Execute a single interaction session."""
        session_start = datetime.now()

        try:
            # Initialize session
            await self._initialize_interaction_session(context, session)

            # Execute based on interaction type
            if session.interaction_type == "agent_interaction":
                result = await self._execute_agent_interaction(context, session)
            elif session.interaction_type == "environment_interaction":
                result = await self._execute_environment_interaction(context, session)
            elif session.interaction_type == "npc_interaction":
                result = await self._execute_npc_interaction(context, session)
            elif session.interaction_type == "collaboration":
                result = await self._execute_collaboration(context, session)
            else:
                result = {"completed": False, "error": "Unknown interaction type"}

            # Record session completion
            session_duration = (datetime.now() - session_start).total_seconds() * 1000
            result["session_duration_ms"] = session_duration
            result["session_id"] = session.session_id

            return result

        except Exception as e:
            return {
                "completed": False,
                "error": str(e),
                "session_id": session.session_id,
                "session_duration_ms": (datetime.now() - session_start).total_seconds()
                * 1000,
            }

    async def _execute_agent_interaction(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> Dict[str, Any]:
        """Execute agent-to-agent interaction."""
        interaction_subtype = session.context.get("interaction_subtype")

        # Get agent intentions and proposals
        agent_proposals = {}
        for agent_id in session.participants:
            proposal_response = await self._call_external_service(
                context,
                self.agent_service_endpoint,
                "get_interaction_proposal",
                {
                    "agent_id": agent_id,
                    "interaction_type": interaction_subtype,
                    "other_agents": [a for a in session.participants if a != agent_id],
                    "context": session.context,
                },
            )

            if proposal_response.get("success"):
                agent_proposals[agent_id] = proposal_response.get("proposal", {})

        # Resolve interaction based on proposals
        if interaction_subtype == "negotiation":
            resolution = await self._resolve_negotiation(
                context, session, agent_proposals
            )
        elif interaction_subtype == "cooperation":
            resolution = await self._resolve_cooperation(
                context, session, agent_proposals
            )
        elif interaction_subtype == "conflict":
            resolution = await self._resolve_conflict(context, session, agent_proposals)
        else:
            resolution = await self._resolve_general_interaction(
                context, session, agent_proposals
            )

        # Apply interaction results
        await self._apply_interaction_results(context, session, resolution)

        return {
            "completed": True,
            "interaction_subtype": interaction_subtype,
            "participants": session.participants,
            "resolution": resolution,
            "actions_proposed": len(agent_proposals),
            "negotiations_resolved": 1 if interaction_subtype == "negotiation" else 0,
            "conflicts_resolved": 1 if interaction_subtype == "conflict" else 0,
        }

    async def _execute_environment_interaction(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> Dict[str, Any]:
        """Execute agent-environment interaction."""
        target = session.context.get("target")
        interaction_subtype = session.context.get("interaction_subtype")

        actions_executed = 0

        for agent_id in session.participants:
            # Get agent's intended action with the environment
            action_response = await self._call_external_service(
                context,
                self.agent_service_endpoint,
                "get_environment_action",
                {
                    "agent_id": agent_id,
                    "target": target,
                    "interaction_type": interaction_subtype,
                },
            )

            if action_response.get("success"):
                action = action_response.get("action", {})

                # Execute action in world context
                execution_response = await self._call_external_service(
                    context,
                    "world_context",
                    "execute_environment_action",
                    {
                        "agent_id": agent_id,
                        "action": action,
                        "target": target,
                        "turn_id": str(context.turn_id),
                    },
                )

                if execution_response.get("success"):
                    actions_executed += 1

        return {
            "completed": actions_executed > 0,
            "interaction_subtype": interaction_subtype,
            "participants": session.participants,
            "target": target,
            "actions_proposed": actions_executed,
            "actions_executed": actions_executed,
        }

    async def _execute_npc_interaction(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> Dict[str, Any]:
        """Execute agent-NPC interaction."""
        npc = session.context.get("npc")

        interactions_completed = 0

        for agent_id in session.participants:
            # Execute NPC interaction
            interaction_response = await self._call_external_service(
                context,
                self.interaction_service_endpoint,
                "execute_npc_interaction",
                {
                    "agent_id": agent_id,
                    "npc_id": npc.get("id"),
                    "interaction_type": session.context.get("interaction_subtype"),
                    "context": session.context,
                },
            )

            if interaction_response.get("success"):
                interactions_completed += 1

        return {
            "completed": interactions_completed > 0,
            "interaction_subtype": session.context.get("interaction_subtype"),
            "participants": session.participants,
            "npc": npc,
            "interactions_completed": interactions_completed,
        }

    async def _execute_collaboration(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> Dict[str, Any]:
        """Execute multi-agent collaboration."""
        task = session.context.get("task")

        # Coordinate collaborative action
        coordination_response = await self._call_external_service(
            context,
            self.interaction_service_endpoint,
            "coordinate_collaborative_action",
            {
                "participants": session.participants,
                "task": task,
                "turn_id": str(context.turn_id),
            },
        )

        collaboration_success = coordination_response.get("success", False)

        return {
            "completed": collaboration_success,
            "interaction_subtype": task.get("task_type"),
            "participants": session.participants,
            "task": task,
            "collaboration_outcome": coordination_response.get("outcome", {}),
        }

    # Helper methods for interaction resolution

    async def _resolve_negotiation(
        self,
        context: PhaseExecutionContext,
        session: InteractionSession,
        agent_proposals: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve negotiation between agents."""
        # Simple negotiation resolution - could be much more sophisticated
        if len(agent_proposals) < 2:
            return {"outcome": "failed", "reason": "insufficient_proposals"}

        # Find common ground or compromise
        proposals = list(agent_proposals.values())

        # Check for direct agreement
        if self._proposals_compatible(proposals):
            return {
                "outcome": "agreement",
                "agreed_terms": self._merge_compatible_proposals(proposals),
            }

        # Attempt compromise
        compromise = self._find_compromise(proposals)
        if compromise:
            return {"outcome": "compromise", "compromise_terms": compromise}

        return {"outcome": "deadlock", "reason": "incompatible_proposals"}

    async def _resolve_cooperation(
        self,
        context: PhaseExecutionContext,
        session: InteractionSession,
        agent_proposals: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve cooperation between agents."""
        # Cooperative interactions generally succeed if agents can contribute
        contributions = {}
        total_benefit = 0

        for agent_id, proposal in agent_proposals.items():
            contribution = proposal.get("contribution", {})
            benefit = proposal.get("expected_benefit", 0)

            contributions[agent_id] = contribution
            total_benefit += benefit

        return {
            "outcome": "success",
            "contributions": contributions,
            "total_benefit": total_benefit,
            "cooperation_type": session.context.get("interaction_subtype"),
        }

    async def _resolve_conflict(
        self,
        context: PhaseExecutionContext,
        session: InteractionSession,
        agent_proposals: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve conflict between agents."""
        # Simple conflict resolution - could involve complex game mechanics
        agents = list(agent_proposals.keys())
        proposals = list(agent_proposals.values())

        # Determine winner based on proposal strength
        winner_index = 0
        max_strength = 0

        for i, proposal in enumerate(proposals):
            strength = proposal.get("action_strength", 0)
            if strength > max_strength:
                max_strength = strength
                winner_index = i

        winner = agents[winner_index]
        losers = [a for i, a in enumerate(agents) if i != winner_index]

        return {
            "outcome": "resolution",
            "winner": winner,
            "losers": losers,
            "winning_action": proposals[winner_index],
            "conflict_type": session.context.get("interaction_subtype"),
        }

    async def _resolve_general_interaction(
        self,
        context: PhaseExecutionContext,
        session: InteractionSession,
        agent_proposals: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve general interaction between agents."""
        # Default resolution for unspecified interactions
        return {
            "outcome": "completed",
            "interaction_type": "general",
            "participants": session.participants,
            "proposals_processed": len(agent_proposals),
        }

    # Additional helper methods (continuing from previous implementation)

    def _calculate_agent_proximity(
        self, agent_a_state: Dict[str, Any], agent_b_state: Dict[str, Any]
    ) -> float:
        """Calculate proximity score between two agents (0.0-1.0)."""
        pos_a = agent_a_state.get("position", {})
        pos_b = agent_b_state.get("position", {})

        if not pos_a or not pos_b:
            return 0.0  # No proximity if positions unknown

        # Simple distance calculation - could be more sophisticated
        x_diff = abs(pos_a.get("x", 0) - pos_b.get("x", 0))
        y_diff = abs(pos_a.get("y", 0) - pos_b.get("y", 0))
        distance = (x_diff**2 + y_diff**2) ** 0.5

        # Convert distance to proximity score (closer = higher score)
        max_interaction_distance = 100  # Game units
        proximity = max(0, 1.0 - (distance / max_interaction_distance))

        return min(1.0, proximity)

    def _determine_interaction_type(
        self, agent_a_state: Dict[str, Any], agent_b_state: Dict[str, Any]
    ) -> str:
        """Determine type of interaction between two agents."""
        # Check for conflicting goals
        goals_a = agent_a_state.get("current_goals", [])
        goals_b = agent_b_state.get("current_goals", [])

        if self._goals_conflict(goals_a, goals_b):
            return "conflict"

        # Check for cooperative potential
        if self._goals_cooperative(goals_a, goals_b):
            return "cooperation"

        # Check for trade/negotiation potential
        resources_a = agent_a_state.get("resources", {})
        resources_b = agent_b_state.get("resources", {})

        if self._can_trade_resources(resources_a, resources_b):
            return "negotiation"

        # Default to general interaction
        return "general"

    def _calculate_interaction_priority(
        self,
        interaction_type: str,
        proximity_score: float,
        agent_states: Dict[str, Dict[str, Any]],
    ) -> float:
        """Calculate interaction priority score."""
        # Base priority by interaction type
        type_priorities = {
            "conflict": 0.8,
            "cooperation": 0.7,
            "negotiation": 0.6,
            "general": 0.3,
        }

        base_priority = type_priorities.get(interaction_type, 0.3)

        # Adjust by proximity (closer interactions are higher priority)
        proximity_bonus = proximity_score * 0.3

        return min(1.0, base_priority + proximity_bonus)

    def _estimate_interaction_duration(self, interaction_type: str) -> int:
        """Estimate interaction duration in milliseconds."""
        durations = {
            "conflict": 3000,  # 3 seconds
            "cooperation": 5000,  # 5 seconds
            "negotiation": 8000,  # 8 seconds
            "general": 2000,  # 2 seconds
        }

        return durations.get(interaction_type, 3000)

    def _get_default_agent_state(self) -> Dict[str, Any]:
        """Get default agent state when state is unavailable."""
        return {
            "position": {"x": 0, "y": 0},
            "current_goals": [],
            "resources": {},
            "status": "active",
        }

    async def _initialize_interaction_session(
        self, context: PhaseExecutionContext, session: InteractionSession
    ) -> None:
        """Initialize interaction session."""
        # Notify interaction context about new session
        await self._call_external_service(
            context,
            self.interaction_service_endpoint,
            "initialize_session",
            {
                "session_id": session.session_id,
                "participants": session.participants,
                "interaction_type": session.interaction_type,
                "turn_id": str(context.turn_id),
            },
        )

    async def _apply_interaction_results(
        self,
        context: PhaseExecutionContext,
        session: InteractionSession,
        resolution: Dict[str, Any],
    ) -> None:
        """Apply interaction results to agent states."""
        # Update agent states based on interaction outcome
        for agent_id in session.participants:
            await self._call_external_service(
                context,
                self.agent_service_endpoint,
                "apply_interaction_result",
                {
                    "agent_id": agent_id,
                    "interaction_result": resolution,
                    "session_id": session.session_id,
                },
            )

    async def _process_interaction_outcomes(
        self, context: PhaseExecutionContext, session_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process all interaction outcomes and create summary."""
        total_sessions = len(session_results)
        successful_sessions = len(
            [r for r in session_results.values() if r.get("completed", False)]
        )

        return {
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "success_rate": successful_sessions / max(1, total_sessions),
            "session_details": session_results,
        }

    async def _generate_interaction_events(
        self,
        context: PhaseExecutionContext,
        interactions_completed: int,
        negotiations_resolved: int,
    ) -> List:
        """Generate events for interaction results."""
        events_generated = []

        # Generate interaction summary event
        summary_event_id = self._record_event_generation(
            context,
            "interactions_orchestrated",
            {
                "turn_id": str(context.turn_id),
                "interactions_completed": interactions_completed,
                "negotiations_resolved": negotiations_resolved,
                "participants": context.participants,
                "completed_at": datetime.now().isoformat(),
            },
        )
        events_generated.append(summary_event_id)

        return events_generated

    # Helper methods for specific game logic

    def _goals_conflict(self, goals_a: List, goals_b: List) -> bool:
        """Check if two sets of goals conflict."""
        # Simplified conflict detection
        return any(
            goal_a.get("type") == "exclusive"
            and goal_a.get("target") == goal_b.get("target")
            for goal_a in goals_a
            for goal_b in goals_b
        )

    def _goals_cooperative(self, goals_a: List, goals_b: List) -> bool:
        """Check if two sets of goals can be cooperative."""
        # Simplified cooperation detection
        return any(
            goal_a.get("type") == "shared"
            or goal_a.get("target") == goal_b.get("target")
            for goal_a in goals_a
            for goal_b in goals_b
        )

    def _can_trade_resources(
        self, resources_a: Dict[str, Any], resources_b: Dict[str, Any]
    ) -> bool:
        """Check if agents can trade resources."""
        # Check for complementary resource needs
        needs_a = resources_a.get("needs", [])
        has_b = list(resources_b.get("inventory", {}).keys())

        needs_b = resources_b.get("needs", [])
        has_a = list(resources_a.get("inventory", {}).keys())

        return any(need in has_b for need in needs_a) or any(
            need in has_a for need in needs_b
        )

    def _proposals_compatible(self, proposals: List[Dict[str, Any]]) -> bool:
        """Check if proposals are compatible."""
        # Simple compatibility check
        return all(proposal.get("compatible", True) for proposal in proposals)

    def _merge_compatible_proposals(
        self, proposals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge compatible proposals into agreed terms."""
        merged = {}
        for proposal in proposals:
            merged.update(proposal.get("terms", {}))
        return merged

    def _find_compromise(
        self, proposals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find compromise between incompatible proposals."""
        # Simple compromise logic
        if len(proposals) == 2:
            proposal_a, proposal_b = proposals

            # Find middle ground in numeric values
            compromise = {}
            terms_a = proposal_a.get("terms", {})
            terms_b = proposal_b.get("terms", {})

            for key in set(terms_a.keys()) & set(terms_b.keys()):
                value_a = terms_a[key]
                value_b = terms_b[key]

                if isinstance(value_a, (int, float)) and isinstance(
                    value_b, (int, float)
                ):
                    compromise[key] = (value_a + value_b) / 2
                elif value_a == value_b:
                    compromise[key] = value_a

            return compromise if compromise else None

        return None

    async def _identify_collaborative_tasks(
        self, context: PhaseExecutionContext, agent_states: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify tasks that require collaboration."""
        # Get collaborative opportunities from world or quest system
        collab_response = await self._call_external_service(
            context,
            "world_context",
            "get_collaborative_tasks",
            {
                "agents": list(agent_states.keys()),
                "area": "current_location",  # Could be more sophisticated
            },
        )

        return collab_response.get("tasks", [])

    def _can_agent_interact_with_environment(
        self, agent_state: Dict[str, Any], opportunity: Dict[str, Any]
    ) -> bool:
        """Check if agent can interact with environment opportunity."""
        agent_capabilities = agent_state.get("capabilities", [])
        required_capability = opportunity.get("required_capability")

        if required_capability and required_capability not in agent_capabilities:
            return False

        # Check proximity
        agent_pos = agent_state.get("position", {})
        opportunity_pos = opportunity.get("position", {})

        if agent_pos and opportunity_pos:
            distance = self._calculate_distance(agent_pos, opportunity_pos)
            max_range = opportunity.get("interaction_range", 50)

            return distance <= max_range

        return True  # Default to true if positions unknown

    def _can_agent_interact_with_npc(
        self, agent_state: Dict[str, Any], npc: Dict[str, Any]
    ) -> bool:
        """Check if agent can interact with NPC."""
        # Check basic requirements
        agent_status = agent_state.get("status")
        if agent_status in ["unconscious", "dead"]:
            return False

        # Check NPC availability
        npc_status = npc.get("status", "available")
        if npc_status != "available":
            return False

        return True

    def _calculate_distance(
        self, pos_a: Dict[str, Any], pos_b: Dict[str, Any]
    ) -> float:
        """Calculate distance between two positions."""
        x_diff = abs(pos_a.get("x", 0) - pos_b.get("x", 0))
        y_diff = abs(pos_a.get("y", 0) - pos_b.get("y", 0))
        return (x_diff**2 + y_diff**2) ** 0.5
