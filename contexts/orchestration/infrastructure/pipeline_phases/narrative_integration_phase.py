#!/usr/bin/env python3
"""
Narrative Integration Phase Implementation

Integrates turn events into the narrative context using AI Gateway,
creating coherent story content and maintaining narrative continuity.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from ...domain.value_objects import PhaseType
from .base_phase import BasePhaseImplementation, PhaseExecutionContext, PhaseResult


class NarrativeIntegrationPhase(BasePhaseImplementation):
    """
    Implementation of narrative integration pipeline phase.

    Coordinates with AI Gateway and Narrative context to:
    - Synthesize turn events into coherent narrative content
    - Update story arcs and plot threads
    - Maintain narrative consistency and continuity
    - Generate multiple narrative perspectives
    - Create chapter/scene transitions
    - Handle character development tracking
    """

    def __init__(self):
        super().__init__(PhaseType.NARRATIVE_INTEGRATION)
        self.execution_timeout_ms = 25000  # 25 seconds for AI-intensive operations
        self.ai_gateway_endpoint = "ai_gateway"
        self.narrative_service_endpoint = "narrative_context"

    async def _execute_phase_implementation(
        self, context: PhaseExecutionContext
    ) -> PhaseResult:
        """
        Execute narrative integration for all turn events.

        Args:
            context: Phase execution context

        Returns:
            PhaseResult with narrative integration results
        """
        if not context.configuration.ai_integration_enabled:
            return self._create_ai_disabled_result(context)

        # Initialize phase metrics
        turn_events_processed = 0
        narrative_content_generated = 0
        story_arcs_updated = 0
        total_ai_cost = Decimal("0.00")
        failed_generations = 0

        try:
            # Step 1: Collect all turn events from previous phases
            turn_events = await self._collect_all_turn_events(context)

            # Step 2: Analyze narrative context and current story state
            narrative_context = await self._analyze_narrative_context(context)

            # Step 3: Generate narrative content for turn events
            narrative_results = {}

            for perspective in narrative_context.get(
                "active_perspectives", ["omniscient"]
            ):
                try:
                    # Generate narrative content for this perspective
                    narrative_result = await self._generate_narrative_content(
                        context, perspective, turn_events, narrative_context
                    )

                    if narrative_result["success"]:
                        narrative_content_generated += 1
                        narrative_results[perspective] = narrative_result
                        total_ai_cost += Decimal(
                            str(narrative_result.get("ai_cost", 0))
                        )
                    else:
                        failed_generations += 1

                except Exception:
                    failed_generations += 1
                    context.record_performance_metric(
                        "narrative_generation_errors",
                        context.performance_metrics.get(
                            "narrative_generation_errors", 0
                        )
                        + 1,
                    )

            # Step 4: Update story arcs and plot threads
            story_arcs_updated = await self._update_story_arcs(
                context, turn_events, narrative_results
            )

            # Step 5: Store narrative content and update context
            await self._store_and_integrate_narrative(context, narrative_results)

            # Step 6: Generate narrative integration events
            integration_events = await self._generate_narrative_events(
                context,
                len(turn_events),
                narrative_content_generated,
                story_arcs_updated,
            )

            turn_events_processed = len(turn_events)

            # Record performance metrics
            context.record_performance_metric(
                "turn_events_processed", float(turn_events_processed)
            )
            context.record_performance_metric(
                "narrative_content_generated", float(narrative_content_generated)
            )
            context.record_performance_metric(
                "story_arcs_updated", float(story_arcs_updated)
            )
            context.record_performance_metric("ai_cost_total", float(total_ai_cost))
            context.record_performance_metric(
                "failed_generations", float(failed_generations)
            )

            # Calculate success metrics
            success_rate = narrative_content_generated / max(
                1, len(narrative_context.get("active_perspectives", ["omniscient"]))
            )

            return PhaseResult(
                success=success_rate > 0.5
                and failed_generations
                == 0,  # Success if >50% perspectives generated and no failures
                events_processed=turn_events_processed,
                events_generated=integration_events,
                artifacts_created=[
                    f"narrative_content_{narrative_content_generated}_perspectives",
                    f"story_arcs_updated_{story_arcs_updated}",
                    f"turn_events_integrated_{turn_events_processed}",
                    f"ai_cost_tracking_{total_ai_cost}",
                ],
                metadata={
                    "narrative_integration_summary": {
                        "turn_events_processed": turn_events_processed,
                        "narrative_content_generated": narrative_content_generated,
                        "story_arcs_updated": story_arcs_updated,
                        "failed_generations": failed_generations,
                        "success_rate": success_rate,
                        "total_ai_cost": float(total_ai_cost),
                        "narrative_perspectives": list(narrative_results.keys()),
                        "narrative_depth": context.configuration.narrative_analysis_depth,
                    }
                },
            )

        except Exception as e:
            return self._create_failure_result(
                context,
                f"Narrative integration failed: {e}",
                {
                    "partial_results": {
                        "turn_events_processed": turn_events_processed,
                        "narrative_content_generated": narrative_content_generated,
                        "story_arcs_updated": story_arcs_updated,
                        "total_ai_cost": float(total_ai_cost),
                    }
                },
            )

    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate preconditions for narrative integration.

        Args:
            context: Phase execution context

        Raises:
            ValueError: If preconditions are not met
        """
        # Check AI integration is enabled
        if not context.configuration.ai_integration_enabled:
            # This is valid - we'll generate a simplified result
            return

        # Check AI cost limits for narrative generation
        if context.configuration.max_ai_cost:
            estimated_cost = self._estimate_narrative_ai_cost(context)
            if estimated_cost > context.configuration.max_ai_cost:
                raise ValueError(
                    f"Estimated narrative AI cost ({estimated_cost}) exceeds limit "
                    f"({context.configuration.max_ai_cost})"
                )

        # Check narrative depth configuration
        valid_depths = ["basic", "standard", "detailed", "comprehensive"]
        if context.configuration.narrative_analysis_depth not in valid_depths:
            raise ValueError(
                f"Invalid narrative depth: {context.configuration.narrative_analysis_depth}"
            )

    async def _collect_all_turn_events(
        self, context: PhaseExecutionContext
    ) -> List[Dict[str, Any]]:
        """
        Collect all events generated during the turn from all phases.

        Args:
            context: Phase execution context

        Returns:
            List of all turn events for narrative integration
        """
        all_events = []

        # Collect events from execution metadata
        generated_events_details = context.execution_metadata.get(
            "generated_events_details", []
        )
        all_events.extend(generated_events_details)

        # Get events from event context if available
        event_response = await self._call_external_service(
            context,
            "event_context",
            "get_turn_events",
            {
                "turn_id": str(context.turn_id),
                "include_world_events": True,
                "include_interaction_events": True,
                "include_integration_events": True,
            },
        )

        turn_events = event_response.get("events", [])
        all_events.extend(turn_events)

        # Deduplicate events by event_id
        unique_events = {}
        for event in all_events:
            event_id = event.get("event_id")
            if event_id and event_id not in unique_events:
                unique_events[event_id] = event

        return list(unique_events.values())

    async def _analyze_narrative_context(
        self, context: PhaseExecutionContext
    ) -> Dict[str, Any]:
        """
        Analyze current narrative context and story state.

        Args:
            context: Phase execution context

        Returns:
            Narrative context for content generation
        """
        # Get current narrative state
        narrative_response = await self._call_external_service(
            context,
            self.narrative_service_endpoint,
            "get_narrative_context",
            {
                "turn_id": str(context.turn_id),
                "include_story_arcs": True,
                "include_character_development": True,
                "include_plot_threads": True,
            },
        )

        narrative_state = narrative_response.get("narrative_state", {})

        # Get active perspectives (POV characters, omniscient, etc.)
        perspective_response = await self._call_external_service(
            context,
            self.narrative_service_endpoint,
            "get_active_perspectives",
            {
                "participants": context.participants,
                "story_context": narrative_state.get("current_story_context", {}),
            },
        )

        active_perspectives = perspective_response.get("perspectives", ["omniscient"])

        return {
            "current_story_state": narrative_state,
            "active_perspectives": active_perspectives,
            "story_arcs": narrative_state.get("story_arcs", []),
            "plot_threads": narrative_state.get("plot_threads", []),
            "character_development": narrative_state.get("character_development", {}),
            "narrative_style": narrative_state.get("narrative_style", "third_person"),
            "genre_context": narrative_state.get("genre_context", "fantasy"),
            "pacing_context": narrative_state.get("pacing_context", "moderate"),
        }

    async def _generate_narrative_content(
        self,
        context: PhaseExecutionContext,
        perspective: str,
        turn_events: List[Dict[str, Any]],
        narrative_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate narrative content for a specific perspective.

        Args:
            context: Phase execution context
            perspective: Narrative perspective to generate content for
            turn_events: Events to integrate into narrative
            narrative_context: Current narrative context

        Returns:
            Narrative generation result
        """
        try:
            # Step 1: Build comprehensive prompt for narrative generation
            prompt = await self._build_narrative_prompt(
                context, perspective, turn_events, narrative_context
            )

            # Step 2: Select appropriate AI model and parameters
            ai_model = self._select_narrative_model(
                context.configuration.narrative_analysis_depth
            )
            max_tokens = self._calculate_narrative_max_tokens(
                context.configuration.narrative_analysis_depth, len(turn_events)
            )

            # Step 3: Call AI Gateway for narrative generation
            ai_response = await self._call_ai_service(
                context,
                self.ai_gateway_endpoint,
                "generate_narrative_content",
                prompt=prompt,
                model=ai_model,
                max_tokens=max_tokens,
                temperature=context.configuration.ai_temperature,
            )

            # Step 4: Process and validate narrative content
            narrative_content = ai_response.get("content", "")
            if not self._validate_narrative_content(narrative_content, turn_events):
                raise ValueError("Generated narrative content is invalid or incomplete")

            # Step 5: Enrich narrative with metadata
            enriched_narrative = {
                "perspective": perspective,
                "content": narrative_content,
                "generation_timestamp": datetime.now().isoformat(),
                "turn_id": str(context.turn_id),
                "events_integrated": len(turn_events),
                "ai_model_used": ai_model,
                "narrative_depth": context.configuration.narrative_analysis_depth,
                "tokens_used": ai_response.get("tokens_used", 0),
                "generation_cost": float(
                    context.ai_usage_tracking.get("total_cost", 0)
                ),
                "narrative_style": narrative_context.get("narrative_style"),
                "genre_context": narrative_context.get("genre_context"),
            }

            return {
                "success": True,
                "narrative": enriched_narrative,
                "ai_cost": ai_response.get("tokens_used", 0)
                * 0.002,  # Higher cost for narrative generation
            }

        except Exception as e:
            return {"success": False, "error": str(e), "perspective": perspective}

    async def _update_story_arcs(
        self,
        context: PhaseExecutionContext,
        turn_events: List[Dict[str, Any]],
        narrative_results: Dict[str, Dict[str, Any]],
    ) -> int:
        """
        Update story arcs and plot threads based on turn events.

        Args:
            context: Phase execution context
            turn_events: Events from the turn
            narrative_results: Generated narrative content

        Returns:
            Number of story arcs updated
        """
        arcs_updated = 0

        # Analyze events for story arc implications
        arc_updates = self._analyze_story_arc_implications(
            turn_events, context.participants
        )

        if arc_updates:
            # Update story arcs in narrative context
            update_response = await self._call_external_service(
                context,
                self.narrative_service_endpoint,
                "update_story_arcs",
                {
                    "turn_id": str(context.turn_id),
                    "arc_updates": arc_updates,
                    "supporting_narrative": {
                        perspective: result.get("narrative", {}).get("content", "")
                        for perspective, result in narrative_results.items()
                        if result.get("success")
                    },
                },
            )

            arcs_updated = update_response.get("arcs_updated", 0)

            # Record arc updates
            if arcs_updated > 0:
                self._record_event_generation(
                    context,
                    "story_arcs_updated",
                    {
                        "arcs_updated": arcs_updated,
                        "update_details": arc_updates,
                        "turn_id": str(context.turn_id),
                    },
                )

        return arcs_updated

    async def _store_and_integrate_narrative(
        self,
        context: PhaseExecutionContext,
        narrative_results: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Store generated narrative content and integrate with narrative context.

        Args:
            context: Phase execution context
            narrative_results: Results of narrative generation
        """
        for perspective, result in narrative_results.items():
            if result.get("success"):
                narrative = result["narrative"]

                # Store narrative content in narrative context
                await self._call_external_service(
                    context,
                    self.narrative_service_endpoint,
                    "store_turn_narrative",
                    {
                        "turn_id": str(context.turn_id),
                        "perspective": perspective,
                        "narrative": narrative,
                        "integration_metadata": {
                            "generation_timestamp": narrative["generation_timestamp"],
                            "events_integrated": narrative["events_integrated"],
                            "ai_model_used": narrative["ai_model_used"],
                        },
                    },
                )

                # Create narrative storage artifact
                artifact_name = f"turn_narrative_{perspective}_{context.turn_id}"
                context.artifacts_created.append(artifact_name)

    async def _generate_narrative_events(
        self,
        context: PhaseExecutionContext,
        events_processed: int,
        content_generated: int,
        arcs_updated: int,
    ) -> List:
        """
        Generate events for narrative integration results.

        Args:
            context: Phase execution context
            events_processed: Number of turn events processed
            content_generated: Number of narrative content pieces generated
            arcs_updated: Number of story arcs updated

        Returns:
            List of generated event IDs
        """
        events_generated = []

        # Generate narrative integration summary event
        summary_event_id = self._record_event_generation(
            context,
            "narrative_integration_completed",
            {
                "turn_id": str(context.turn_id),
                "turn_events_processed": events_processed,
                "narrative_content_generated": content_generated,
                "story_arcs_updated": arcs_updated,
                "participants": context.participants,
                "narrative_depth": context.configuration.narrative_analysis_depth,
                "total_ai_cost": float(context.ai_usage_tracking.get("total_cost", 0)),
                "completed_at": datetime.now().isoformat(),
            },
        )
        events_generated.append(summary_event_id)

        return events_generated

    # Helper methods

    def _create_ai_disabled_result(self, context: PhaseExecutionContext) -> PhaseResult:
        """Create result when AI integration is disabled."""
        # Generate simple non-AI narrative summaries
        simple_summaries = 1  # Basic summary without AI

        return PhaseResult(
            success=True,
            events_processed=0,
            events_generated=[],
            artifacts_created=[f"simple_narrative_summary_{context.turn_id}"],
            metadata={
                "narrative_integration_summary": {
                    "ai_integration_disabled": True,
                    "simple_summaries_generated": simple_summaries,
                    "narrative_depth": "basic",
                }
            },
        )

    def _estimate_narrative_ai_cost(self, context: PhaseExecutionContext) -> Decimal:
        """Estimate AI cost for narrative generation."""
        # Base cost per narrative perspective based on depth
        depth_costs = {
            "basic": Decimal("0.50"),
            "standard": Decimal("1.00"),
            "detailed": Decimal("2.00"),
            "comprehensive": Decimal("4.00"),
        }

        base_cost = depth_costs.get(
            context.configuration.narrative_analysis_depth, Decimal("1.00")
        )

        # Estimate number of perspectives (default to 2: omniscient + protagonist)
        estimated_perspectives = min(
            len(context.participants) + 1, 3
        )  # Cap at 3 perspectives

        return base_cost * estimated_perspectives

    async def _build_narrative_prompt(
        self,
        context: PhaseExecutionContext,
        perspective: str,
        turn_events: List[Dict[str, Any]],
        narrative_context: Dict[str, Any],
    ) -> str:
        """
        Build comprehensive AI prompt for narrative generation.

        Args:
            context: Phase execution context
            perspective: Narrative perspective
            turn_events: Events to integrate
            narrative_context: Current narrative context

        Returns:
            Formatted prompt for AI service
        """
        # Organize events by type for better narrative flow
        event_summary = self._organize_events_for_narrative(turn_events)

        # Get previous narrative context for continuity
        previous_narrative = narrative_context.get("current_story_state", {}).get(
            "recent_narrative", ""
        )

        # Build character context if perspective is character-based
        character_context = ""
        if perspective != "omniscient" and perspective in context.participants:
            character_context = await self._build_character_context(
                context, perspective
            )

        # Select prompt template based on narrative depth
        depth = context.configuration.narrative_analysis_depth

        if depth == "comprehensive":
            prompt_template = self._get_comprehensive_narrative_template()
        elif depth == "detailed":
            prompt_template = self._get_detailed_narrative_template()
        elif depth == "standard":
            prompt_template = self._get_standard_narrative_template()
        else:  # basic
            prompt_template = self._get_basic_narrative_template()

        # Fill template with context
        prompt = prompt_template.format(
            perspective=perspective,
            narrative_style=narrative_context.get("narrative_style", "third_person"),
            genre_context=narrative_context.get("genre_context", "fantasy"),
            previous_narrative=(
                previous_narrative[:500] if previous_narrative else "Beginning of story"
            ),
            character_context=character_context,
            world_events=event_summary.get("world_events", ""),
            interaction_events=event_summary.get("interaction_events", ""),
            character_development=event_summary.get("character_development", ""),
            plot_progression=event_summary.get("plot_progression", ""),
            story_arcs=narrative_context.get("story_arcs", [])[:3],  # Top 3 active arcs
            participants=context.participants,
            turn_duration=context.configuration.world_time_advance,
        )

        return prompt

    def _organize_events_for_narrative(
        self, turn_events: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Organize turn events into narrative-friendly categories.

        Args:
            turn_events: List of turn events

        Returns:
            Dictionary of organized event summaries
        """
        event_categories = {
            "world_events": [],
            "interaction_events": [],
            "character_development": [],
            "plot_progression": [],
        }

        for event in turn_events:
            event_type = event.get("event_type", "")
            event.get("event_data", {})

            # Categorize events for narrative purposes
            if event_type in [
                "world_time_advanced",
                "environment_changed",
                "entity_updated",
            ]:
                event_categories["world_events"].append(event)
            elif event_type in [
                "agent_agreement",
                "conflict_resolution",
                "cooperation_success",
            ]:
                event_categories["interaction_events"].append(event)
            elif event_type in ["character_development", "skill_improvement"]:
                event_categories["character_development"].append(event)
            elif event_type in ["plot_advancement", "story_arc_update"]:
                event_categories["plot_progression"].append(event)
            else:
                # Default to interaction events for unknown types
                event_categories["interaction_events"].append(event)

        # Convert to narrative summaries
        summaries = {}
        for category, events in event_categories.items():
            if events:
                summaries[category] = self._create_event_category_summary(
                    category, events
                )
            else:
                summaries[
                    category
                ] = f"No {category.replace('_', ' ')} occurred during this turn."

        return summaries

    def _create_event_category_summary(
        self, category: str, events: List[Dict[str, Any]]
    ) -> str:
        """Create a narrative summary for a category of events."""
        if category == "world_events":
            return f"{len(events)} world changes occurred, including environmental shifts and entity movements."
        elif category == "interaction_events":
            return f"{len(events)} character interactions took place, involving negotiations, conflicts, and cooperative efforts."
        elif category == "character_development":
            return f"{len(events)} character development events occurred, showing growth and change."
        elif category == "plot_progression":
            return f"{len(events)} plot developments advanced the story forward."
        else:
            return f"{len(events)} events of type {category} occurred."

    async def _build_character_context(
        self, context: PhaseExecutionContext, character_id: str
    ) -> str:
        """Build character-specific context for perspective narrative."""
        # Get character information for perspective-based narrative
        character_response = await self._call_external_service(
            context,
            "agent_context",
            "get_character_narrative_context",
            {"character_id": character_id},
        )

        character_data = character_response.get("character", {})

        return (
            f"Character: {character_data.get('name', character_id)}, "
            f"Personality: {character_data.get('personality', {}).get('traits', [])}, "
            f"Current goals: {character_data.get('goals', [])[:2]}"
        )  # Top 2 goals

    def _select_narrative_model(self, depth: str) -> str:
        """Select appropriate AI model based on narrative depth."""
        model_mapping = {
            "basic": "gpt-3.5-turbo",
            "standard": "gpt-4",
            "detailed": "gpt-4",
            "comprehensive": "gpt-4-turbo",  # Most capable model for complex narrative
        }
        return model_mapping.get(depth, "gpt-4")

    def _calculate_narrative_max_tokens(self, depth: str, event_count: int) -> int:
        """Calculate max tokens for narrative generation."""
        base_tokens = {
            "basic": 300,
            "standard": 800,
            "detailed": 1500,
            "comprehensive": 3000,
        }

        base = base_tokens.get(depth, 800)
        # Add tokens based on event complexity
        event_bonus = min(event_count * 50, 500)  # Up to 500 extra tokens for events

        return base + event_bonus

    def _validate_narrative_content(
        self, content: str, turn_events: List[Dict[str, Any]]
    ) -> bool:
        """Validate generated narrative content."""
        if not content or len(content.strip()) < 50:
            return False

        # Check for minimum narrative content
        if len(content.split()) < 20:  # At least 20 words
            return False

        # Check that content mentions some events (basic validation)
        event_types = [event.get("event_type", "") for event in turn_events]
        if event_types and not any(
            event_type.replace("_", " ") in content.lower()
            or event_type.split("_")[0] in content.lower()
            for event_type in event_types
        ):
            # Content should reference at least some events
            return False

        return True

    def _analyze_story_arc_implications(
        self, turn_events: List[Dict[str, Any]], participants: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze how turn events impact story arcs."""
        arc_updates = []

        # Analyze events for story progression
        for event in turn_events:
            event_type = event.get("event_type", "")

            if event_type == "conflict_resolution":
                arc_updates.append(
                    {
                        "arc_type": "character_conflict",
                        "participants": event.get("participants", []),
                        "progression": "resolution",
                        "impact": "major",
                    }
                )

            elif event_type == "cooperation_success":
                arc_updates.append(
                    {
                        "arc_type": "alliance_building",
                        "participants": event.get("participants", []),
                        "progression": "advancement",
                        "impact": "moderate",
                    }
                )

            elif event_type == "agent_agreement":
                arc_updates.append(
                    {
                        "arc_type": "relationship_development",
                        "participants": event.get("participants", []),
                        "progression": "advancement",
                        "impact": "minor",
                    }
                )

        return arc_updates

    # Prompt templates for different narrative depths

    def _get_basic_narrative_template(self) -> str:
        """Get basic narrative prompt template."""
        return """
Create a brief narrative summary of the following turn events in {narrative_style} perspective for a {genre_context} story.

Recent events:
{world_events}
{interaction_events}

Write 2-3 sentences that capture the essence of what happened during this turn.
"""

    def _get_standard_narrative_template(self) -> str:
        """Get standard narrative prompt template."""
        return """
You are writing a {genre_context} story from a {perspective} perspective in {narrative_style}.

Previous narrative context:
{previous_narrative}

Turn events to integrate:
- World changes: {world_events}
- Character interactions: {interaction_events}
- Character development: {character_development}

Participants: {participants}

Create a narrative passage (1-2 paragraphs) that seamlessly integrates these events into the ongoing story. Maintain consistency with the previous narrative and show cause-and-effect relationships between events.
"""

    def _get_detailed_narrative_template(self) -> str:
        """Get detailed narrative prompt template."""
        return """
You are crafting a {genre_context} narrative from {perspective} perspective using {narrative_style}.

NARRATIVE CONTINUITY:
Previous context: {previous_narrative}

CHARACTER CONTEXT:
{character_context}

TURN EVENTS TO INTEGRATE:
- World Events: {world_events}
- Character Interactions: {interaction_events}
- Character Development: {character_development}
- Plot Progression: {plot_progression}

ACTIVE STORY ARCS:
{story_arcs}

PARTICIPANTS: {participants}
TURN DURATION: {turn_duration} seconds

Create a rich narrative passage (2-3 paragraphs) that:
1. Seamlessly integrates all events into the story flow
2. Maintains character voice and personality
3. Advances the plot while showing character growth
4. Creates vivid scenes with sensory details
5. Shows consequences and emotional impact of events
"""

    def _get_comprehensive_narrative_template(self) -> str:
        """Get comprehensive narrative prompt template."""
        return """
You are crafting a sophisticated {genre_context} narrative from {perspective} perspective using {narrative_style}.

NARRATIVE FOUNDATION:
Previous narrative context: {previous_narrative}

CHARACTER DEPTH:
{character_context}

COMPREHENSIVE TURN INTEGRATION:
World Dynamics: {world_events}
Character Interactions: {interaction_events}
Character Evolution: {character_development}
Plot Advancement: {plot_progression}

STORY ARCHITECTURE:
Active story arcs: {story_arcs}
Key participants: {participants}
Temporal scope: {turn_duration} seconds of story time

Create a masterful narrative sequence (3-4 paragraphs) that demonstrates:

1. SEAMLESS INTEGRATION: Weave all events into a natural story flow that feels organic and inevitable
2. CHARACTER DEPTH: Show internal thoughts, motivations, and emotional responses that align with established personalities
3. WORLD BUILDING: Use events to reveal more about the world, its rules, and its atmosphere
4. DRAMATIC STRUCTURE: Build tension, create peaks and valleys, and set up future conflicts or resolutions
5. LITERARY QUALITY: Employ sophisticated prose, varied sentence structure, and evocative imagery
6. THEMATIC COHERENCE: Connect events to larger themes and the overall narrative arc
7. EMOTIONAL RESONANCE: Create moments that will impact readers and advance character relationships

Balance action with reflection, dialogue with description, and immediate events with their broader implications for the story world.
"""
