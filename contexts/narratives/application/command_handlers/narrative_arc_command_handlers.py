#!/usr/bin/env python3
"""
Narrative Arc Command Handlers

This module implements command handlers for narrative arc operations.
Handlers coordinate between the application layer and domain layer.
"""

import logging
from typing import Any, Dict, Optional

from ...domain.aggregates.narrative_arc import NarrativeArc
from ...domain.services.causal_graph_service import CausalGraphService
from ...domain.services.narrative_flow_service import NarrativeFlowService
from ...domain.value_objects.causal_node import (
    CausalNode,
    CausalRelationType,
    CausalStrength,
)
from ...domain.value_objects.narrative_context import NarrativeContext
from ...domain.value_objects.narrative_id import NarrativeId
from ...domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)
from ...domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)
from ...domain.value_objects.story_pacing import (
    PacingIntensity,
    PacingType,
    StoryPacing,
)
from ...infrastructure.repositories.narrative_arc_repository import (
    NarrativeArcRepository,
)
from ..commands.narrative_arc_commands import (
    ActivateContextCommand,
    AddCharacterToArcCommand,
    AddNarrativeContextCommand,
    AddPacingSegmentCommand,
    AddPlotPointCommand,
    AddThemeCommand,
    AnalyzeCausalityCommand,
    AnalyzeNarrativeFlowCommand,
    CompleteNarrativeArcCommand,
    CreateNarrativeArcCommand,
    DeactivateContextCommand,
    DevelopThemeCommand,
    EstablishCausalLinkCommand,
    OptimizeSequenceCommand,
    RemoveCausalLinkCommand,
    RemovePlotPointCommand,
    StartNarrativeArcCommand,
    UpdateNarrativeArcCommand,
    UpdatePlotPointCommand,
)

logger = logging.getLogger(__name__)


class NarrativeArcCommandHandler:
    """
    Command handler for narrative arc operations.

    Coordinates between application commands and domain logic.
    """

    def __init__(
        self,
        repository: NarrativeArcRepository,
        flow_service: Optional[NarrativeFlowService] = None,
        causal_service: Optional[CausalGraphService] = None,
    ):
        """
        Initialize command handler.

        Args:
            repository: Repository for narrative arc persistence
            flow_service: Service for narrative flow analysis
            causal_service: Service for causal relationship management
        """
        self.repository = repository
        self.flow_service = flow_service or NarrativeFlowService()
        self.causal_service = causal_service or CausalGraphService()

    def handle_create_narrative_arc(self, command: CreateNarrativeArcCommand) -> str:
        """
        Handle narrative arc creation.

        Args:
            command: CreateNarrativeArcCommand with arc details

        Returns:
            ID of the created narrative arc
        """
        try:
            arc_id = NarrativeId.generate()

            arc = NarrativeArc(
                arc_id=arc_id,
                arc_name=command.arc_name,
                arc_type=command.arc_type,
                description=command.description,
                target_length=command.target_length,
                primary_characters=command.primary_characters or set(),
                created_by=command.created_by,
                tags=command.tags or set(),
                notes=command.notes,
                metadata=command.metadata or {},
            )

            self.repository.save(arc)
            logger.info(f"Created narrative arc: {arc_id}")

            return str(arc_id)

        except Exception as e:
            logger.error(f"Failed to create narrative arc: {str(e)}")
            raise

    def handle_update_narrative_arc(self, command: UpdateNarrativeArcCommand) -> None:
        """Handle narrative arc updates."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            # Update fields if provided
            if command.arc_name is not None:
                arc.arc_name = command.arc_name
            if command.arc_type is not None:
                arc.arc_type = command.arc_type
            if command.description is not None:
                arc.description = command.description
            if command.target_length is not None:
                arc.target_length = command.target_length
            if command.notes is not None:
                arc.notes = command.notes
            if command.tags is not None:
                arc.tags = command.tags
            if command.metadata is not None:
                arc.metadata.update(command.metadata)

            arc._update_timestamp_and_version()
            self.repository.save(arc)

            logger.info(f"Updated narrative arc: {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to update narrative arc {command.arc_id}: {str(e)}")
            raise

    def handle_add_plot_point(self, command: AddPlotPointCommand) -> None:
        """Handle plot point addition."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            plot_point = PlotPoint(
                plot_point_id=command.plot_point_id,
                plot_point_type=PlotPointType(command.plot_point_type),
                importance=PlotPointImportance(command.importance),
                title=command.title,
                description=command.description,
                sequence_order=command.sequence_order,
                emotional_intensity=command.emotional_intensity,
                dramatic_tension=command.dramatic_tension,
                story_significance=command.story_significance,
                involved_characters=command.involved_characters or set(),
                prerequisite_events=command.prerequisite_events or set(),
                consequence_events=command.consequence_events or set(),
                location=command.location,
                time_context=command.time_context,
                pov_character=command.pov_character,
                outcome=command.outcome,
                conflict_type=command.conflict_type,
                thematic_relevance=command.thematic_relevance or {},
                tags=command.tags or set(),
                notes=command.notes,
            )

            arc.add_plot_point(plot_point)
            self.repository.save(arc)

            # Add to causal graph if service available
            if self.causal_service and plot_point.has_causal_relationships:
                causal_node = CausalNode(
                    node_id=plot_point.plot_point_id,
                    sequence_order=plot_point.sequence_order,
                    narrative_importance=plot_point.overall_impact_score,
                )
                self.causal_service.add_node(causal_node)

            logger.info(f"Added plot point {command.plot_point_id} to arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to add plot point: {str(e)}")
            raise

    def handle_update_plot_point(self, command: UpdatePlotPointCommand) -> None:
        """Handle plot point updates."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            plot_point = arc.get_plot_point(command.plot_point_id)
            if not plot_point:
                raise ValueError(f"Plot point {command.plot_point_id} not found")

            # Create updated plot point with new values
            updated_plot = PlotPoint(
                plot_point_id=plot_point.plot_point_id,
                plot_point_type=plot_point.plot_point_type,
                importance=plot_point.importance,
                title=command.title if command.title is not None else plot_point.title,
                description=(
                    command.description
                    if command.description is not None
                    else plot_point.description
                ),
                sequence_order=(
                    command.sequence_order
                    if command.sequence_order is not None
                    else plot_point.sequence_order
                ),
                emotional_intensity=(
                    command.emotional_intensity
                    if command.emotional_intensity is not None
                    else plot_point.emotional_intensity
                ),
                dramatic_tension=(
                    command.dramatic_tension
                    if command.dramatic_tension is not None
                    else plot_point.dramatic_tension
                ),
                story_significance=(
                    command.story_significance
                    if command.story_significance is not None
                    else plot_point.story_significance
                ),
                involved_characters=plot_point.involved_characters,
                prerequisite_events=plot_point.prerequisite_events,
                consequence_events=plot_point.consequence_events,
                location=plot_point.location,
                time_context=plot_point.time_context,
                pov_character=plot_point.pov_character,
                outcome=(command.outcome if command.outcome is not None else plot_point.outcome),
                conflict_type=plot_point.conflict_type,
                thematic_relevance=plot_point.thematic_relevance,
                tags=plot_point.tags,
                notes=command.notes if command.notes is not None else plot_point.notes,
            )

            # Replace plot point
            arc.remove_plot_point(command.plot_point_id)
            arc.add_plot_point(updated_plot)

            self.repository.save(arc)

            logger.info(f"Updated plot point {command.plot_point_id} in arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to update plot point: {str(e)}")
            raise

    def handle_remove_plot_point(self, command: RemovePlotPointCommand) -> None:
        """Handle plot point removal."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            removed_plot = arc.remove_plot_point(command.plot_point_id)
            if not removed_plot:
                raise ValueError(f"Plot point {command.plot_point_id} not found")

            self.repository.save(arc)

            # Remove from causal graph if service available
            if self.causal_service:
                self.causal_service.remove_node(command.plot_point_id)

            logger.info(f"Removed plot point {command.plot_point_id} from arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to remove plot point: {str(e)}")
            raise

    def handle_add_theme(self, command: AddThemeCommand) -> None:
        """Handle theme addition."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            theme = NarrativeTheme(
                theme_id=command.theme_id,
                theme_type=ThemeType(command.theme_type),
                intensity=ThemeIntensity(command.intensity),
                name=command.name,
                description=command.description,
                moral_complexity=command.moral_complexity,
                emotional_resonance=command.emotional_resonance,
                universal_appeal=command.universal_appeal,
                cultural_significance=command.cultural_significance,
                development_potential=command.development_potential,
                symbolic_elements=command.symbolic_elements or set(),
                introduction_sequence=command.introduction_sequence,
                resolution_sequence=command.resolution_sequence,
                tags=command.tags or set(),
                notes=command.notes,
            )

            arc.add_theme(theme)
            self.repository.save(arc)

            logger.info(f"Added theme {command.theme_id} to arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to add theme: {str(e)}")
            raise

    def handle_develop_theme(self, command: DevelopThemeCommand) -> None:
        """Handle theme development."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            arc.develop_theme_at_sequence(command.theme_id, command.sequence)
            self.repository.save(arc)

            logger.info(f"Developed theme {command.theme_id} at sequence {command.sequence}")

        except Exception as e:
            logger.error(f"Failed to develop theme: {str(e)}")
            raise

    def handle_add_pacing_segment(self, command: AddPacingSegmentCommand) -> None:
        """Handle pacing segment addition."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            pacing = StoryPacing(
                pacing_id=command.pacing_id,
                pacing_type=PacingType(command.pacing_type),
                base_intensity=PacingIntensity(command.base_intensity),
                start_sequence=command.start_sequence,
                end_sequence=command.end_sequence,
                event_density=command.event_density,
                tension_curve=command.tension_curve or [],
                dialogue_ratio=command.dialogue_ratio,
                action_ratio=command.action_ratio,
                reflection_ratio=command.reflection_ratio,
                description_density=command.description_density,
                character_focus=command.character_focus or set(),
                narrative_techniques=command.narrative_techniques or set(),
                reader_engagement_target=command.reader_engagement_target,
                tags=command.tags or set(),
                notes=command.notes,
            )

            arc.add_pacing_segment(pacing)
            self.repository.save(arc)

            logger.info(f"Added pacing segment {command.pacing_id} to arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to add pacing segment: {str(e)}")
            raise

    def handle_add_narrative_context(self, command: AddNarrativeContextCommand) -> None:
        """Handle narrative context addition."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            context = NarrativeContext(
                context_id=command.context_id,
                context_type=command.context_type,
                name=command.name,
                description=command.description,
                importance=command.importance,
                is_persistent=command.is_persistent,
                start_sequence=command.start_sequence,
                end_sequence=command.end_sequence,
                location=command.location,
                time_period=command.time_period,
                mood=command.mood,
                atmosphere=command.atmosphere,
                social_context=command.social_context,
                cultural_context=command.cultural_context,
                affected_characters=command.affected_characters or set(),
                related_themes=command.related_themes or set(),
                tags=command.tags or set(),
                notes=command.notes,
            )

            arc.add_narrative_context(context)
            self.repository.save(arc)

            logger.info(f"Added context {command.context_id} to arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to add narrative context: {str(e)}")
            raise

    def handle_activate_context(self, command: ActivateContextCommand) -> None:
        """Handle context activation."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            arc.activate_context(command.context_id)
            self.repository.save(arc)

            logger.info(f"Activated context {command.context_id} in arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to activate context: {str(e)}")
            raise

    def handle_deactivate_context(self, command: DeactivateContextCommand) -> None:
        """Handle context deactivation."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            arc.deactivate_context(command.context_id)
            self.repository.save(arc)

            logger.info(f"Deactivated context {command.context_id} in arc {command.arc_id}")

        except Exception as e:
            logger.error(f"Failed to deactivate context: {str(e)}")
            raise

    def handle_add_character_to_arc(self, command: AddCharacterToArcCommand) -> None:
        """Handle character addition to arc."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            if command.role.lower() == "primary":
                arc.add_primary_character(command.character_id)
            elif command.role.lower() == "supporting":
                arc.add_supporting_character(command.character_id)
            else:
                raise ValueError(f"Invalid character role: {command.role}")

            # Add character arc notes if provided
            if command.character_arc_notes:
                arc.character_arcs[command.character_id] = command.character_arc_notes

            self.repository.save(arc)

            logger.info(
                f"Added {command.role} character {command.character_id} to arc {command.arc_id}"
            )

        except Exception as e:
            logger.error(f"Failed to add character to arc: {str(e)}")
            raise

    def handle_start_narrative_arc(self, command: StartNarrativeArcCommand) -> None:
        """Handle narrative arc start."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            arc.start_arc(command.start_sequence)
            self.repository.save(arc)

            logger.info(
                f"Started narrative arc {command.arc_id} at sequence {command.start_sequence}"
            )

        except Exception as e:
            logger.error(f"Failed to start narrative arc: {str(e)}")
            raise

    def handle_complete_narrative_arc(self, command: CompleteNarrativeArcCommand) -> None:
        """Handle narrative arc completion."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            arc.complete_arc(command.end_sequence)
            self.repository.save(arc)

            logger.info(
                f"Completed narrative arc {command.arc_id} at sequence {command.end_sequence}"
            )

        except Exception as e:
            logger.error(f"Failed to complete narrative arc: {str(e)}")
            raise

    def handle_analyze_narrative_flow(self, command: AnalyzeNarrativeFlowCommand) -> Dict[str, Any]:
        """Handle narrative flow analysis."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            analysis = self.flow_service.analyze_narrative_flow(arc)

            result = {
                "arc_id": command.arc_id,
                "pacing_score": float(analysis.pacing_score),
                "tension_progression": [float(t) for t in analysis.tension_progression],
                "climax_positioning": float(analysis.climax_positioning),
                "resolution_quality": float(analysis.resolution_quality),
                "narrative_momentum": float(analysis.narrative_momentum),
                "flow_consistency": float(analysis.flow_consistency),
            }

            if command.include_recommendations:
                result["recommendations"] = analysis.recommended_adjustments

            logger.info(f"Analyzed narrative flow for arc {command.arc_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to analyze narrative flow: {str(e)}")
            raise

    def handle_optimize_sequence(self, command: OptimizeSequenceCommand) -> Dict[str, Any]:
        """Handle sequence optimization."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            optimization = self.flow_service.optimize_sequence_order(arc)

            result = {
                "arc_id": command.arc_id,
                "original_sequence": optimization.original_sequence,
                "optimized_sequence": optimization.optimized_sequence,
                "improvement_score": float(optimization.improvement_score),
                "changes_made": optimization.changes_made,
                "rationale": optimization.rationale,
            }

            logger.info(f"Optimized sequence for arc {command.arc_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to optimize sequence: {str(e)}")
            raise

    def handle_establish_causal_link(self, command: EstablishCausalLinkCommand) -> None:
        """Handle causal link establishment."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            # Ensure both plot points exist
            if command.cause_id not in arc.plot_points:
                raise ValueError(f"Cause plot point {command.cause_id} not found")
            if command.effect_id not in arc.plot_points:
                raise ValueError(f"Effect plot point {command.effect_id} not found")

            success = self.causal_service.establish_causal_link(
                cause_id=command.cause_id,
                effect_id=command.effect_id,
                relationship_type=CausalRelationType(command.relationship_type),
                strength=CausalStrength(command.strength),
                certainty=command.certainty,
                metadata=command.metadata,
            )

            if not success:
                raise ValueError("Failed to establish causal link")

            logger.info(f"Established causal link: {command.cause_id} -> {command.effect_id}")

        except Exception as e:
            logger.error(f"Failed to establish causal link: {str(e)}")
            raise

    def handle_remove_causal_link(self, command: RemoveCausalLinkCommand) -> None:
        """Handle causal link removal."""
        try:
            success = self.causal_service.remove_causal_link(
                cause_id=command.cause_id, effect_id=command.effect_id
            )

            if not success:
                raise ValueError("Failed to remove causal link")

            logger.info(f"Removed causal link: {command.cause_id} -> {command.effect_id}")

        except Exception as e:
            logger.error(f"Failed to remove causal link: {str(e)}")
            raise

    def handle_analyze_causality(self, command: AnalyzeCausalityCommand) -> Dict[str, Any]:
        """Handle causality analysis."""
        try:
            arc = self.repository.get_by_id(NarrativeId(command.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {command.arc_id} not found")

            # Add plot points to causal service if not already present
            for plot_point in arc.plot_points.values():
                if plot_point.plot_point_id not in self.causal_service.nodes:
                    causal_node = CausalNode(
                        node_id=plot_point.plot_point_id,
                        sequence_order=plot_point.sequence_order,
                        narrative_importance=plot_point.overall_impact_score,
                    )
                    self.causal_service.add_node(causal_node)

            analysis = self.causal_service.analyze_narrative_causality()

            result = {
                "arc_id": command.arc_id,
                "root_causes": analysis.root_causes,
                "terminal_effects": analysis.terminal_effects,
                "critical_nodes": analysis.critical_nodes,
                "feedback_loops": analysis.feedback_loops,
                "graph_complexity": float(analysis.graph_complexity),
                "consistency_score": float(analysis.consistency_score),
                "narrative_flow_score": float(analysis.narrative_flow_score),
            }

            if command.include_paths:
                longest_chains = []
                for chain in analysis.longest_chains:
                    longest_chains.append(
                        {
                            "nodes": chain.nodes,
                            "path_length": chain.path_length,
                            "total_strength": float(chain.total_strength),
                            "average_strength": float(chain.average_strength),
                            "relationship_types": [rt.value for rt in chain.relationship_types],
                        }
                    )
                result["longest_chains"] = longest_chains

            logger.info(f"Analyzed causality for arc {command.arc_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to analyze causality: {str(e)}")
            raise
