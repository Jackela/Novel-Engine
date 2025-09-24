#!/usr/bin/env python3
"""
Subjective Brief Phase Implementation

Generates subjective perception briefs for all agents using AI Gateway
with personalized context, memory integration, and narrative awareness.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from ...domain.value_objects import PhaseType
from .base_phase import (
    BasePhaseImplementation,
    PhaseExecutionContext,
    PhaseResult,
)


class SubjectiveBriefPhase(BasePhaseImplementation):
    """
    Implementation of subjective brief generation pipeline phase.

    Coordinates with AI Gateway and Agent contexts to:
    - Generate personalized perception briefs for each agent
    - Integrate world state changes with agent memory
    - Create narrative-aware subjective experiences
    - Handle agent-specific preferences and capabilities
    - Manage AI cost optimization and rate limiting
    """

    def __init__(self):
        super().__init__(PhaseType.SUBJECTIVE_BRIEF)
        self.execution_timeout_ms = 15000  # 15 seconds for AI operations
        self.ai_gateway_endpoint = "ai_gateway"
        self.agent_service_endpoint = "agent_context"

    async def _execute_phase_implementation(
        self, context: PhaseExecutionContext
    ) -> PhaseResult:
        """
        Execute subjective brief generation for all participants.

        Args:
            context: Phase execution context

        Returns:
            PhaseResult with brief generation results
        """
        if not context.configuration.ai_integration_enabled:
            return self._create_ai_disabled_result(context)

        # Initialize phase metrics
        briefs_generated = 0
        total_ai_cost = Decimal("0.00")
        failed_generations = 0

        try:
            # Step 1: Gather world state changes from previous phase
            world_changes = await self._gather_world_state_changes(context)

            # Step 2: Get agent configurations and preferences
            agent_configs = await self._get_agent_configurations(context)

            # Step 3: Generate subjective briefs for each participant
            brief_results = {}

            for participant_id in context.participants:
                try:
                    agent_config = agent_configs.get(participant_id, {})

                    # Generate subjective brief for this agent
                    brief_result = await self._generate_agent_subjective_brief(
                        context, participant_id, agent_config, world_changes
                    )

                    if brief_result["success"]:
                        briefs_generated += 1
                        brief_results[participant_id] = brief_result
                        total_ai_cost += Decimal(
                            str(brief_result.get("ai_cost", 0))
                        )
                    else:
                        failed_generations += 1

                except Exception:
                    failed_generations += 1
                    context.record_performance_metric(
                        "brief_generation_errors",
                        context.performance_metrics.get(
                            "brief_generation_errors", 0
                        )
                        + 1,
                    )

            # Step 4: Store briefs and create agent notifications
            await self._store_and_notify_briefs(context, brief_results)

            # Step 5: Generate integration events
            brief_events = await self._generate_brief_events(
                context, briefs_generated, failed_generations
            )

            # Record performance metrics
            context.record_performance_metric(
                "briefs_generated", float(briefs_generated)
            )
            context.record_performance_metric(
                "failed_generations", float(failed_generations)
            )
            context.record_performance_metric(
                "ai_cost_total", float(total_ai_cost)
            )

            # Calculate success rate
            total_participants = len(context.participants)
            success_rate = briefs_generated / max(1, total_participants)

            return PhaseResult(
                success=success_rate
                > 0.5,  # Success if more than half generated
                events_processed=len(world_changes),
                events_generated=brief_events,
                artifacts_created=[
                    f"subjective_briefs_{briefs_generated}_agents",
                    f"ai_interactions_{len(context.participants)}",
                    f"cost_tracking_{total_ai_cost}",
                ],
                metadata={
                    "subjective_brief_summary": {
                        "briefs_generated": briefs_generated,
                        "failed_generations": failed_generations,
                        "total_participants": total_participants,
                        "success_rate": success_rate,
                        "total_ai_cost": float(total_ai_cost),
                        "narrative_depth": context.configuration.narrative_analysis_depth,
                    }
                },
            )

        except Exception as e:
            return self._create_failure_result(
                context,
                f"Subjective brief generation failed: {e}",
                {
                    "partial_results": {
                        "briefs_generated": briefs_generated,
                        "failed_generations": failed_generations,
                        "total_ai_cost": float(total_ai_cost),
                    }
                },
            )

    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate preconditions for subjective brief generation.

        Args:
            context: Phase execution context

        Raises:
            ValueError: If preconditions are not met
        """
        # Check AI integration is enabled
        if not context.configuration.ai_integration_enabled:
            # This is valid - we'll generate a simplified result
            return

        # Check participants are available
        if not context.participants:
            raise ValueError(
                "No participants available for subjective brief generation"
            )

        # Check AI cost limits
        if context.configuration.max_ai_cost:
            estimated_cost = self._estimate_ai_cost(context)
            if estimated_cost > context.configuration.max_ai_cost:
                raise ValueError(
                    f"Estimated AI cost ({estimated_cost}) exceeds limit "
                    f"({context.configuration.max_ai_cost})"
                )

    async def _gather_world_state_changes(
        self, context: PhaseExecutionContext
    ) -> List[Dict[str, Any]]:
        """
        Gather world state changes from previous phase results.

        Args:
            context: Phase execution context

        Returns:
            List of world state changes relevant to agents
        """
        # Get world changes from previous phase
        world_response = await self._call_external_service(
            context,
            "world_context",
            "get_recent_changes",
            {
                "turn_id": str(context.turn_id),
                "include_entity_changes": True,
                "include_environment_changes": True,
                "include_time_changes": True,
            },
        )

        changes = world_response.get("changes", [])

        # Filter changes relevant to participants
        relevant_changes = []
        for change in changes:
            if self._is_change_relevant_to_participants(
                change, context.participants
            ):
                relevant_changes.append(change)

        return relevant_changes

    async def _get_agent_configurations(
        self, context: PhaseExecutionContext
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get agent configurations and preferences for brief generation.

        Args:
            context: Phase execution context

        Returns:
            Dictionary mapping agent IDs to their configurations
        """
        agent_configs = {}

        for participant_id in context.participants:
            try:
                # Get agent configuration
                agent_response = await self._call_external_service(
                    context,
                    self.agent_service_endpoint,
                    "get_agent_config",
                    {"agent_id": participant_id},
                )

                if agent_response.get("success"):
                    agent_configs[participant_id] = agent_response.get(
                        "config", {}
                    )

            except Exception:
                # Use default configuration for this agent
                agent_configs[
                    participant_id
                ] = self._get_default_agent_config()

        return agent_configs

    async def _generate_agent_subjective_brief(
        self,
        context: PhaseExecutionContext,
        agent_id: str,
        agent_config: Dict[str, Any],
        world_changes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate subjective brief for a specific agent.

        Args:
            context: Phase execution context
            agent_id: Agent identifier
            agent_config: Agent configuration and preferences
            world_changes: Relevant world state changes

        Returns:
            Brief generation result
        """
        try:
            # Step 1: Get agent's current context and memory
            agent_context = await self._get_agent_context(
                context, agent_id, agent_config
            )

            # Step 2: Build AI prompt for subjective brief
            prompt = await self._build_subjective_brief_prompt(
                context, agent_id, agent_config, agent_context, world_changes
            )

            # Step 3: Call AI Gateway for brief generation
            ai_model = agent_config.get("preferred_ai_model", "gpt-3.5-turbo")
            max_tokens = self._calculate_max_tokens_for_depth(
                context.configuration.narrative_analysis_depth
            )

            ai_response = await self._call_ai_service(
                context,
                self.ai_gateway_endpoint,
                "generate_subjective_brief",
                prompt=prompt,
                model=ai_model,
                max_tokens=max_tokens,
                temperature=context.configuration.ai_temperature,
            )

            # Step 4: Process and validate AI response
            brief_content = ai_response.get("content", "")
            if not self._validate_brief_content(brief_content, agent_config):
                raise ValueError("Generated brief content is invalid")

            # Step 5: Enrich brief with metadata
            enriched_brief = {
                "agent_id": agent_id,
                "content": brief_content,
                "generation_timestamp": datetime.now().isoformat(),
                "turn_id": str(context.turn_id),
                "world_changes_included": len(world_changes),
                "ai_model_used": ai_model,
                "narrative_depth": context.configuration.narrative_analysis_depth,
                "tokens_used": ai_response.get("tokens_used", 0),
                "generation_cost": float(
                    context.ai_usage_tracking.get("total_cost", 0)
                ),
            }

            return {
                "success": True,
                "brief": enriched_brief,
                "ai_cost": ai_response.get("tokens_used", 0)
                * 0.001,  # Rough cost estimate
            }

        except Exception as e:
            return {"success": False, "error": str(e), "agent_id": agent_id}

    async def _get_agent_context(
        self,
        context: PhaseExecutionContext,
        agent_id: str,
        agent_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for agent brief generation.

        Args:
            context: Phase execution context
            agent_id: Agent identifier
            agent_config: Agent configuration

        Returns:
            Agent context for brief generation
        """
        # Get agent's current state
        agent_state_response = await self._call_external_service(
            context,
            self.agent_service_endpoint,
            "get_agent_state",
            {"agent_id": agent_id},
        )

        # Get agent's recent memories
        memory_response = await self._call_external_service(
            context,
            self.agent_service_endpoint,
            "get_recent_memories",
            {
                "agent_id": agent_id,
                "memory_count": agent_config.get("memory_context_size", 5),
                "include_emotional_context": True,
            },
        )

        # Get agent's current goals and motivations
        goals_response = await self._call_external_service(
            context,
            self.agent_service_endpoint,
            "get_agent_goals",
            {"agent_id": agent_id},
        )

        return {
            "current_state": agent_state_response.get("state", {}),
            "recent_memories": memory_response.get("memories", []),
            "goals": goals_response.get("goals", []),
            "personality": agent_config.get("personality", {}),
            "preferences": agent_config.get("preferences", {}),
            "capabilities": agent_config.get("capabilities", []),
        }

    async def _build_subjective_brief_prompt(
        self,
        context: PhaseExecutionContext,
        agent_id: str,
        agent_config: Dict[str, Any],
        agent_context: Dict[str, Any],
        world_changes: List[Dict[str, Any]],
    ) -> str:
        """
        Build AI prompt for subjective brief generation.

        Args:
            context: Phase execution context
            agent_id: Agent identifier
            agent_config: Agent configuration
            agent_context: Agent context information
            world_changes: Relevant world changes

        Returns:
            Formatted prompt for AI service
        """
        # Extract key information
        agent_name = agent_config.get("name", f"Agent {agent_id}")
        personality = agent_context.get("personality", {})
        current_state = agent_context.get("current_state", {})
        recent_memories = agent_context.get("recent_memories", [])
        goals = agent_context.get("goals", [])

        # Build world changes summary
        changes_summary = self._summarize_world_changes(
            world_changes, agent_id
        )

        # Build memories context
        memories_text = self._format_memories_for_prompt(recent_memories)

        # Create depth-appropriate prompt
        depth = context.configuration.narrative_analysis_depth

        if depth == "comprehensive":
            prompt_template = self._get_comprehensive_prompt_template()
        elif depth == "detailed":
            prompt_template = self._get_detailed_prompt_template()
        elif depth == "standard":
            prompt_template = self._get_standard_prompt_template()
        else:  # basic
            prompt_template = self._get_basic_prompt_template()

        # Fill template
        prompt = prompt_template.format(
            agent_name=agent_name,
            personality_traits=personality.get("traits", []),
            current_location=current_state.get("location", "unknown"),
            current_health=current_state.get("health", "unknown"),
            current_mood=current_state.get("mood", "neutral"),
            world_changes=changes_summary,
            recent_memories=memories_text,
            current_goals=(
                goals[:3] if goals else ["No specific goals"]
            ),  # Limit to top 3
            time_passed=context.configuration.world_time_advance,
        )

        return prompt

    async def _store_and_notify_briefs(
        self,
        context: PhaseExecutionContext,
        brief_results: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Store generated briefs and notify agent systems.

        Args:
            context: Phase execution context
            brief_results: Results of brief generation
        """
        for agent_id, result in brief_results.items():
            if result.get("success"):
                brief = result["brief"]

                # Store brief in agent context
                await self._call_external_service(
                    context,
                    self.agent_service_endpoint,
                    "store_subjective_brief",
                    {
                        "agent_id": agent_id,
                        "brief": brief,
                        "turn_id": str(context.turn_id),
                    },
                )

                # Create brief storage artifact
                artifact_name = (
                    f"subjective_brief_{agent_id}_{context.turn_id}"
                )
                context.artifacts_created.append(artifact_name)

    async def _generate_brief_events(
        self,
        context: PhaseExecutionContext,
        briefs_generated: int,
        failed_generations: int,
    ) -> List:
        """
        Generate events for brief generation results.

        Args:
            context: Phase execution context
            briefs_generated: Number of successful brief generations
            failed_generations: Number of failed brief generations

        Returns:
            List of generated event IDs
        """
        events_generated = []

        # Generate brief generation summary event
        summary_event_id = self._record_event_generation(
            context,
            "subjective_briefs_generated",
            {
                "turn_id": str(context.turn_id),
                "briefs_generated": briefs_generated,
                "failed_generations": failed_generations,
                "participants": context.participants,
                "narrative_depth": context.configuration.narrative_analysis_depth,
                "total_ai_cost": float(
                    context.ai_usage_tracking.get("total_cost", 0)
                ),
                "completed_at": datetime.now().isoformat(),
            },
        )
        events_generated.append(summary_event_id)

        return events_generated

    # Helper methods

    def _create_ai_disabled_result(
        self, context: PhaseExecutionContext
    ) -> PhaseResult:
        """Create result when AI integration is disabled."""
        # Generate simple non-AI briefs
        simple_briefs = len(context.participants)

        return PhaseResult(
            success=True,
            events_processed=0,
            events_generated=[],
            artifacts_created=[f"simple_briefs_{simple_briefs}_agents"],
            metadata={
                "subjective_brief_summary": {
                    "ai_integration_disabled": True,
                    "simple_briefs_generated": simple_briefs,
                    "narrative_depth": "basic",
                }
            },
        )

    def _estimate_ai_cost(self, context: PhaseExecutionContext) -> Decimal:
        """Estimate AI cost for brief generation."""
        participant_count = len(context.participants)

        # Base cost per brief based on narrative depth
        depth_costs = {
            "basic": Decimal("0.10"),
            "standard": Decimal("0.25"),
            "detailed": Decimal("0.50"),
            "comprehensive": Decimal("1.00"),
        }

        base_cost = depth_costs.get(
            context.configuration.narrative_analysis_depth, Decimal("0.25")
        )

        return base_cost * participant_count

    def _is_change_relevant_to_participants(
        self, change: Dict[str, Any], participants: List[str]
    ) -> bool:
        """Check if world change is relevant to any participant."""
        # Check if change affects any participant directly
        affected_entities = change.get("affected_entities", [])
        if any(entity in participants for entity in affected_entities):
            return True

        # Check if change affects participant's area
        change_area = change.get("area")
        if change_area and change_area != "global":
            # In real implementation, check if participants are in this area
            return True

        # Global changes are always relevant
        return change.get("scope") == "global"

    def _get_default_agent_config(self) -> Dict[str, Any]:
        """Get default agent configuration."""
        return {
            "name": "Unknown Agent",
            "preferred_ai_model": "gpt-3.5-turbo",
            "memory_context_size": 3,
            "personality": {"traits": ["curious", "adaptive"]},
            "preferences": {},
            "capabilities": ["basic_interaction"],
        }

    def _calculate_max_tokens_for_depth(self, depth: str) -> int:
        """Calculate max tokens based on narrative depth."""
        depth_tokens = {
            "basic": 200,
            "standard": 500,
            "detailed": 1000,
            "comprehensive": 2000,
        }
        return depth_tokens.get(depth, 500)

    def _validate_brief_content(
        self, content: str, agent_config: Dict[str, Any]
    ) -> bool:
        """Validate generated brief content."""
        if not content or len(content.strip()) < 10:
            return False

        # Check for minimum content requirements
        if len(content.split()) < 5:  # At least 5 words
            return False

        # Check for agent name if specified
        agent_name = agent_config.get("name")
        if agent_name and agent_name not in content:
            # This is okay - brief might use pronouns
            pass

        return True

    def _summarize_world_changes(
        self, world_changes: List[Dict[str, Any]], agent_id: str
    ) -> str:
        """Summarize world changes relevant to agent."""
        if not world_changes:
            return "The world remains largely unchanged."

        summaries = []
        for change in world_changes[:5]:  # Limit to top 5 changes
            change_type = change.get("type", "unknown")
            description = change.get("description", "A change occurred")
            summaries.append(f"- {change_type.title()}: {description}")

        return "\n".join(summaries)

    def _format_memories_for_prompt(
        self, memories: List[Dict[str, Any]]
    ) -> str:
        """Format memories for inclusion in AI prompt."""
        if not memories:
            return "No recent memories to consider."

        memory_texts = []
        for memory in memories[:3]:  # Limit to most recent 3
            memory_text = memory.get("content", "")
            memory_emotion = memory.get("emotional_context", "")

            if memory_emotion:
                memory_texts.append(f"- {memory_text} (felt {memory_emotion})")
            else:
                memory_texts.append(f"- {memory_text}")

        return "\n".join(memory_texts)

    def _get_basic_prompt_template(self) -> str:
        """Get basic prompt template for brief generation."""
        return """
You are {agent_name}, currently at {current_location}.

Recent events in the world:
{world_changes}

Generate a brief subjective perception of these events from your character's perspective in 2-3 sentences.
"""

    def _get_standard_prompt_template(self) -> str:
        """Get standard prompt template for brief generation."""
        return """
You are {agent_name}, a character with these personality traits: {personality_traits}.
You are currently at {current_location} with {current_health} health and feeling {current_mood}.

Recent world events:
{world_changes}

Your recent memories:
{recent_memories}

Time has passed: {time_passed} seconds since your last awareness.

Generate a subjective perception of these events and changes from your character's perspective, including:
1. What you notice about the world changes
2. How these changes make you feel
3. Any connections to your recent memories

Respond in character, in 1-2 paragraphs.
"""

    def _get_detailed_prompt_template(self) -> str:
        """Get detailed prompt template for brief generation."""
        return """
You are {agent_name}, a character with personality traits: {personality_traits}.
Current status: At {current_location}, health: {current_health}, mood: {current_mood}

World changes since last awareness ({time_passed} seconds ago):
{world_changes}

Your recent memories:
{recent_memories}

Your current goals:
{current_goals}

Generate a detailed subjective brief that includes:
1. Immediate sensory impressions of the world changes
2. Emotional reactions based on your personality
3. Connections between current events and your memories
4. How these changes might affect your current goals
5. Any new thoughts or plans that emerge

Write in first person, maintaining your character's voice and perspective. Include internal thoughts and feelings.
"""

    def _get_comprehensive_prompt_template(self) -> str:
        """Get comprehensive prompt template for brief generation."""
        return """
You are {agent_name}, a complex character with these defining traits: {personality_traits}.

CURRENT SITUATION:
- Location: {current_location}
- Physical state: {current_health}
- Emotional state: {current_mood}
- Time elapsed since last conscious moment: {time_passed} seconds

WORLD CHANGES YOU PERCEIVE:
{world_changes}

RECENT MEMORIES INFLUENCING YOUR PERCEPTION:
{recent_memories}

YOUR DRIVING GOALS AND MOTIVATIONS:
{current_goals}

Generate a comprehensive subjective brief that captures your complete experience of this moment, including:

1. SENSORY EXPERIENCE: What you see, hear, feel, smell in rich detail
2. EMOTIONAL PROCESSING: Your immediate emotional reactions and deeper feelings
3. COGNITIVE ANALYSIS: How you interpret and understand these changes
4. MEMORY INTEGRATION: Connections to past experiences and learned patterns
5. GOAL ASSESSMENT: How current events impact your objectives and plans
6. FUTURE CONSIDERATIONS: What you anticipate or worry might happen next
7. INTERNAL DIALOGUE: Your private thoughts and self-reflection

Write as a stream of consciousness that moves naturally between external perception and internal processing. Maintain authentic character voice throughout. Length: 3-4 detailed paragraphs.
"""
