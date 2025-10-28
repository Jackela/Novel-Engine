#!/usr/bin/env python3
"""
Context Integrator
=================

Integrates structured character context from ContextLoaderService with existing
character data loaded by CharacterInterpreter. This component bridges the new
Context Engineering Framework with the existing PersonaAgent architecture.

Provides a hybrid approach where:
- Existing character_data from CharacterInterpreter remains unchanged
- New structured context adds enhanced decision-making capabilities
- Graceful fallback ensures system continues without context loading
"""

import logging
from typing import Any, Dict

# Import context models
from contexts.character.domain.value_objects.context_models import (
    CharacterContext,
    MemoryContext,
    ObjectivesContext,
    ProfileContext,
    StatsContext,
)

# Configure logging
logger = logging.getLogger(__name__)


class ContextIntegrator:
    """
    Integrates structured context with existing character data.

    This class merges new CharacterContext data with existing PersonaAgent
    character_data, creating enhanced data structures for improved decision-making
    while maintaining full backward compatibility.
    """

    def merge_contexts(
        self, existing_data: Dict[str, Any], new_context: CharacterContext
    ) -> Dict[str, Any]:
        """
        Merge new structured context with existing character data.

        Args:
            existing_data: Current character_data from CharacterInterpreter
            new_context: Structured context from ContextLoaderService

        Returns:
            Enhanced character_data with integrated context
        """
        try:
            # Start with existing data (preserve all current functionality)
            merged_data = existing_data.copy()

            # Add structured context data (additive enhancement)
            merged_data["enhanced_context"] = new_context
            merged_data["context_load_success"] = new_context.load_success
            merged_data["context_timestamp"] = new_context.load_timestamp.isoformat()
            merged_data["context_warnings"] = new_context.validation_warnings

            # Integrate specific contexts
            if new_context.memory_context:
                merged_data["memory_context"] = new_context.memory_context
                self._integrate_memory_data(merged_data, new_context.memory_context)

            if new_context.objectives_context:
                merged_data["objectives_context"] = new_context.objectives_context
                self._integrate_objectives_data(
                    merged_data, new_context.objectives_context
                )

            if new_context.profile_context:
                merged_data["profile_context"] = new_context.profile_context
                self._integrate_profile_data(merged_data, new_context.profile_context)

            if new_context.stats_context:
                merged_data["stats_context"] = new_context.stats_context
                self._integrate_stats_data(merged_data, new_context.stats_context)

            logger.info(
                f"Context integration completed for {new_context.character_name}"
            )
            return merged_data

        except Exception as e:
            logger.error(f"Error during context integration: {e}")
            # Return original data on integration failure
            return existing_data

    def _integrate_memory_data(
        self, merged_data: Dict, memory_context: MemoryContext
    ) -> None:
        """Integrate memory context into decision-making data structures."""
        try:
            # Add behavioral triggers to decision weights
            if "behavioral_triggers" not in merged_data:
                merged_data["behavioral_triggers"] = {}

            for trigger in memory_context.behavioral_triggers:
                merged_data["behavioral_triggers"][trigger.trigger_name] = {
                    "conditions": trigger.trigger_conditions,
                    "response": trigger.behavioral_response,
                    "overrides": trigger.override_conditions,
                    "memory_origin": trigger.memory_origin,
                }

            # Add relationship trust scores
            if "enhanced_relationships" not in merged_data:
                merged_data["enhanced_relationships"] = {}

            for relationship in memory_context.relationships:
                merged_data["enhanced_relationships"][relationship.character_name] = {
                    "trust_level": relationship.trust_level.score,
                    "relationship_type": relationship.relationship_type.value,
                    "emotional_dynamics": relationship.emotional_dynamics,
                    "conflict_points": relationship.conflict_points,
                    "shared_experiences": relationship.shared_experiences,
                    "memory_foundation": relationship.memory_foundation,
                }

            # Add formative events for decision context
            if "formative_events" not in merged_data:
                merged_data["formative_events"] = {}

            for event in memory_context.formative_events:
                merged_data["formative_events"][event.event_name] = {
                    "age": event.age,
                    "description": event.description,
                    "memory_type": event.memory_type.value,
                    "emotional_impact": event.emotional_impact,
                    "decision_influence": event.decision_influence,
                    "trigger_phrases": event.trigger_phrases,
                    "key_lesson": event.key_lesson,
                }

        except Exception as e:
            logger.warning(f"Error integrating memory data: {e}")

    def _integrate_objectives_data(
        self, merged_data: Dict, objectives_context: ObjectivesContext
    ) -> None:
        """Integrate objectives context for decision prioritization."""
        try:
            if "active_objectives" not in merged_data:
                merged_data["active_objectives"] = {}

            # Add core objectives with highest weight
            for objective in objectives_context.core_objectives:
                if objective.status.value == "active":
                    merged_data["active_objectives"][objective.name] = {
                        "priority": objective.priority
                        * 2.0,  # Core objectives get double weight
                        "tier": "core",
                        "success_metrics": objective.success_metrics,
                        "timeline": objective.timeline,
                        "motivation_source": objective.motivation_source,
                        "risk_factors": objective.risk_factors,
                    }

            # Add strategic objectives
            for objective in objectives_context.strategic_objectives:
                if objective.status.value == "active":
                    merged_data["active_objectives"][objective.name] = {
                        "priority": objective.priority
                        * 1.5,  # Strategic gets 1.5x weight
                        "tier": "strategic",
                        "success_metrics": objective.success_metrics,
                        "timeline": objective.timeline,
                        "motivation_source": objective.motivation_source,
                        "risk_factors": objective.risk_factors,
                    }

            # Add tactical objectives
            for objective in objectives_context.tactical_objectives:
                if objective.status.value == "active":
                    merged_data["active_objectives"][objective.name] = {
                        "priority": objective.priority,  # Normal weight
                        "tier": "tactical",
                        "success_metrics": objective.success_metrics,
                        "timeline": objective.timeline,
                        "motivation_source": objective.motivation_source,
                        "risk_factors": objective.risk_factors,
                    }

            # Add resource allocation data
            if objectives_context.resource_allocation:
                merged_data["resource_allocation"] = {
                    "time_energy_percentages": objectives_context.resource_allocation.time_energy_percentages,
                    "success_thresholds": objectives_context.resource_allocation.success_thresholds,
                }

            # Add current focus
            if objectives_context.current_focus:
                merged_data["current_focus"] = objectives_context.current_focus

        except Exception as e:
            logger.warning(f"Error integrating objectives data: {e}")

    def _integrate_profile_data(
        self, merged_data: Dict, profile_context: ProfileContext
    ) -> None:
        """Integrate profile context for personality-driven decisions."""
        try:
            # Enhanced emotional drives
            if "emotional_drives" not in merged_data:
                merged_data["emotional_drives"] = {}

            for drive in profile_context.emotional_drives:
                weight = {"Dominant": 1.0, "Core": 0.8, "Emerging": 0.5}.get(
                    drive.dominance_level, 0.5
                )
                merged_data["emotional_drives"][drive.name] = {
                    "weight": weight,
                    "foundation": drive.foundation,
                    "positive_expression": drive.positive_expression,
                    "negative_expression": drive.negative_expression,
                    "triggers": drive.trigger_events,
                    "soothing_behaviors": drive.soothing_behaviors,
                    "dominance_level": drive.dominance_level,
                }

            # Enhanced personality trait scores
            if "enhanced_personality" not in merged_data:
                merged_data["enhanced_personality"] = {}

            for trait in profile_context.personality_traits:
                merged_data["enhanced_personality"][trait.name] = {
                    "score": trait.score,
                    "emotional_foundation": trait.emotional_foundation,
                    "positive_expression": trait.positive_expression,
                    "negative_expression": trait.negative_expression,
                    "triggers": trait.emotional_triggers,
                }

            # Enhanced character background
            merged_data.update(
                {
                    "enhanced_background": {
                        "background_summary": profile_context.background_summary,
                        "key_life_phases": profile_context.key_life_phases,
                        "physical_description": profile_context.physical_description,
                        "distinguishing_features": profile_context.distinguishing_features,
                    },
                    "enhanced_capabilities": {
                        "core_skills": profile_context.core_skills,
                        "specializations": profile_context.specializations,
                        "equipment": profile_context.equipment,
                        "resources": profile_context.resources,
                    },
                }
            )

        except Exception as e:
            logger.warning(f"Error integrating profile data: {e}")

    def _integrate_stats_data(
        self, merged_data: Dict, stats_context: StatsContext
    ) -> None:
        """Integrate stats context for quantitative decision support."""
        try:
            # Update combat capabilities
            if (
                hasattr(stats_context.combat_stats, "primary_stats")
                and stats_context.combat_stats.primary_stats
            ):
                merged_data[
                    "enhanced_combat_stats"
                ] = stats_context.combat_stats.primary_stats

            # Update psychological profile
            if (
                hasattr(stats_context.psychological_profile, "traits")
                and stats_context.psychological_profile.traits
            ):
                if "enhanced_psychological_traits" not in merged_data:
                    merged_data["enhanced_psychological_traits"] = {}
                merged_data["enhanced_psychological_traits"].update(
                    stats_context.psychological_profile.traits
                )

            # Update relationship data
            if stats_context.relationships:
                if "quantified_relationships" not in merged_data:
                    merged_data["quantified_relationships"] = {}

                for rel_type, rel_list in stats_context.relationships.items():
                    for relationship in rel_list:
                        merged_data["quantified_relationships"][relationship.name] = {
                            "trust_level": relationship.trust_level,
                            "relationship_type": relationship.relationship_type,
                            "category": rel_type,
                        }

            # Add equipment and additional data
            if stats_context.equipment:
                merged_data["enhanced_equipment"] = stats_context.equipment

            if stats_context.objectives:
                if "yaml_objectives" not in merged_data:
                    merged_data["yaml_objectives"] = {}
                merged_data["yaml_objectives"].update(stats_context.objectives)

        except Exception as e:
            logger.warning(f"Error integrating stats data: {e}")

    def get_integration_summary(self, merged_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of context integration results."""
        try:
            enhanced_context = merged_data.get("enhanced_context")
            if not enhanced_context:
                return {"integration_status": "no_context", "components": []}

            components_integrated = []
            if "memory_context" in merged_data:
                components_integrated.append("memory")
            if "objectives_context" in merged_data:
                components_integrated.append("objectives")
            if "profile_context" in merged_data:
                components_integrated.append("profile")
            if "stats_context" in merged_data:
                components_integrated.append("stats")

            return {
                "integration_status": (
                    "success"
                    if merged_data.get("context_load_success", False)
                    else "partial"
                ),
                "components": components_integrated,
                "character_name": (
                    enhanced_context.character_name
                    if hasattr(enhanced_context, "character_name")
                    else "Unknown"
                ),
                "context_timestamp": merged_data.get("context_timestamp"),
                "warnings_count": len(merged_data.get("context_warnings", [])),
                "behavioral_triggers_count": len(
                    merged_data.get("behavioral_triggers", {})
                ),
                "active_objectives_count": len(
                    merged_data.get("active_objectives", {})
                ),
                "enhanced_relationships_count": len(
                    merged_data.get("enhanced_relationships", {})
                ),
            }

        except Exception as e:
            logger.error(f"Error generating integration summary: {e}")
            return {"integration_status": "error", "error": str(e)}
