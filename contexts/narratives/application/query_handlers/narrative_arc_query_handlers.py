#!/usr/bin/env python3
"""
Narrative Arc Query Handlers

This module implements query handlers for narrative arc read operations.
Handlers coordinate between the application layer and domain/infrastructure layers.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ...domain.services.causal_graph_service import CausalGraphService
from ...domain.services.narrative_flow_service import NarrativeFlowService
from ...domain.value_objects.narrative_id import NarrativeId
from ...infrastructure.repositories.narrative_arc_repository import (
    NarrativeArcRepository,
)
from ..queries.narrative_arc_queries import (
    GetArcMetricsQuery,
    GetArcSummaryQuery,
    GetCausalAnalysisQuery,
    GetNarrativeArcQuery,
    GetNarrativeArcsByTypeQuery,
    GetNarrativeFlowAnalysisQuery,
    GetPlotPointQuery,
    GetPlotPointsByTypeQuery,
    GetPlotPointsInSequenceQuery,
    GetThemeQuery,
    GetThemesAtSequenceQuery,
    SearchNarrativeArcsQuery,
)

logger = logging.getLogger(__name__)


class NarrativeArcQueryHandler:
    """
    Query handler for narrative arc read operations.

    Processes queries and returns appropriate data without modifying state.
    """

    def __init__(
        self,
        repository: NarrativeArcRepository,
        flow_service: Optional[NarrativeFlowService] = None,
        causal_service: Optional[CausalGraphService] = None,
    ):
        """
        Initialize query handler.

        Args:
            repository: Repository for narrative arc data access
            flow_service: Service for narrative flow analysis
            causal_service: Service for causal relationship analysis
        """
        self.repository = repository
        self.flow_service = flow_service or NarrativeFlowService()
        self.causal_service = causal_service or CausalGraphService()

    def handle_get_narrative_arc(
        self, query: GetNarrativeArcQuery
    ) -> Optional[Dict[str, Any]]:
        """Handle get narrative arc query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return None

            result = {
                "arc_id": str(arc.arc_id),
                "arc_name": arc.arc_name,
                "arc_type": arc.arc_type,
                "description": arc.description,
                "status": arc.status,
                "created_at": arc.created_at.isoformat(),
                "updated_at": arc.updated_at.isoformat(),
                "version": arc._version,
            }

            if query.include_details:
                result.update(
                    {
                        "target_length": arc.target_length,
                        "current_length": arc.current_length,
                        "completion_percentage": float(
                            arc.completion_percentage
                        ),
                        "complexity_score": float(arc.complexity_score),
                        "narrative_coherence": float(arc.narrative_coherence),
                        "thematic_consistency": float(
                            arc.thematic_consistency
                        ),
                        "pacing_effectiveness": float(
                            arc.pacing_effectiveness
                        ),
                        "sequence_range": [
                            arc.start_sequence,
                            arc.end_sequence,
                        ],
                        "plot_points_count": len(arc.plot_points),
                        "themes_count": len(arc.themes),
                        "pacing_segments_count": len(arc.pacing_segments),
                        "contexts_count": len(arc.narrative_contexts),
                        "active_contexts_count": len(arc.active_contexts),
                        "primary_characters": [
                            str(cid) for cid in arc.primary_characters
                        ],
                        "supporting_characters": [
                            str(cid) for cid in arc.supporting_characters
                        ],
                        "tags": list(arc.tags),
                        "notes": arc.notes,
                        "metadata": arc.metadata,
                    }
                )

            if query.include_events:
                result["uncommitted_events"] = [
                    {
                        "event_id": event.event_id,
                        "event_type": event.__class__.__name__,
                        "occurred_at": event.occurred_at.isoformat(),
                        "narrative_id": str(event.narrative_id),
                    }
                    for event in arc.get_uncommitted_events()
                ]

            logger.debug(f"Retrieved narrative arc: {query.arc_id}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to get narrative arc {query.arc_id}: {str(e)}"
            )
            raise

    def handle_get_narrative_arcs_by_type(
        self, query: GetNarrativeArcsByTypeQuery
    ) -> List[Dict[str, Any]]:
        """Handle get narrative arcs by type query."""
        try:
            arcs = self.repository.get_by_type(
                arc_type=query.arc_type,
                status=query.status,
                limit=query.limit,
                offset=query.offset,
            )

            result = []
            for arc in arcs:
                result.append(
                    {
                        "arc_id": str(arc.arc_id),
                        "arc_name": arc.arc_name,
                        "arc_type": arc.arc_type,
                        "status": arc.status,
                        "completion_percentage": float(
                            arc.completion_percentage
                        ),
                        "plot_points_count": len(arc.plot_points),
                        "created_at": arc.created_at.isoformat(),
                        "updated_at": arc.updated_at.isoformat(),
                    }
                )

            logger.debug(
                f"Retrieved {len(result)} narrative arcs of type {query.arc_type}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get narrative arcs by type: {str(e)}")
            raise

    def handle_search_narrative_arcs(
        self, query: SearchNarrativeArcsQuery
    ) -> Dict[str, Any]:
        """Handle search narrative arcs query."""
        try:
            arcs, total_count = self.repository.search(
                search_term=query.search_term,
                arc_types=query.arc_types,
                statuses=query.statuses,
                character_ids=query.character_ids,
                theme_ids=query.theme_ids,
                tags=query.tags,
                created_by=query.created_by,
                min_complexity=query.min_complexity,
                max_complexity=query.max_complexity,
                min_completion=query.min_completion,
                max_completion=query.max_completion,
                limit=query.limit,
                offset=query.offset,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
            )

            results = []
            for arc in arcs:
                results.append(
                    {
                        "arc_id": str(arc.arc_id),
                        "arc_name": arc.arc_name,
                        "arc_type": arc.arc_type,
                        "status": arc.status,
                        "description": (
                            arc.description[:200] + "..."
                            if len(arc.description) > 200
                            else arc.description
                        ),
                        "completion_percentage": float(
                            arc.completion_percentage
                        ),
                        "complexity_score": float(arc.complexity_score),
                        "plot_points_count": len(arc.plot_points),
                        "themes_count": len(arc.themes),
                        "primary_characters_count": len(
                            arc.primary_characters
                        ),
                        "tags": list(arc.tags),
                        "created_at": arc.created_at.isoformat(),
                        "updated_at": arc.updated_at.isoformat(),
                    }
                )

            result = {
                "arcs": results,
                "total_count": total_count,
                "limit": query.limit,
                "offset": query.offset,
                "has_more": (query.offset or 0) + len(results) < total_count,
            }

            logger.debug(
                f"Search returned {len(results)} of {total_count} narrative arcs"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to search narrative arcs: {str(e)}")
            raise

    def handle_get_plot_point(
        self, query: GetPlotPointQuery
    ) -> Optional[Dict[str, Any]]:
        """Handle get plot point query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return None

            plot_point = arc.get_plot_point(query.plot_point_id)
            if not plot_point:
                return None

            return {
                "plot_point_id": plot_point.plot_point_id,
                "plot_point_type": plot_point.plot_point_type.value,
                "importance": plot_point.importance.value,
                "title": plot_point.title,
                "description": plot_point.description,
                "sequence_order": plot_point.sequence_order,
                "emotional_intensity": float(plot_point.emotional_intensity),
                "dramatic_tension": float(plot_point.dramatic_tension),
                "story_significance": float(plot_point.story_significance),
                "involved_characters": [
                    str(cid) for cid in plot_point.involved_characters
                ],
                "prerequisite_events": list(plot_point.prerequisite_events),
                "consequence_events": list(plot_point.consequence_events),
                "location": plot_point.location,
                "time_context": plot_point.time_context,
                "pov_character": (
                    str(plot_point.pov_character)
                    if plot_point.pov_character
                    else None
                ),
                "outcome": plot_point.outcome,
                "conflict_type": plot_point.conflict_type,
                "thematic_relevance": {
                    k: float(v)
                    for k, v in plot_point.thematic_relevance.items()
                },
                "tags": list(plot_point.tags),
                "notes": plot_point.notes,
                "overall_impact_score": float(plot_point.overall_impact_score),
            }

        except Exception as e:
            logger.error(f"Failed to get plot point: {str(e)}")
            raise

    def handle_get_plot_points_in_sequence(
        self, query: GetPlotPointsInSequenceQuery
    ) -> List[Dict[str, Any]]:
        """Handle get plot points in sequence query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return []

            plot_points = arc.get_plot_points_in_sequence()

            # Filter by sequence range if specified
            if (
                query.start_sequence is not None
                or query.end_sequence is not None
            ):
                filtered_points = []
                for pp in plot_points:
                    if (
                        query.start_sequence is not None
                        and pp.sequence_order < query.start_sequence
                    ):
                        continue
                    if (
                        query.end_sequence is not None
                        and pp.sequence_order > query.end_sequence
                    ):
                        continue
                    filtered_points.append(pp)
                plot_points = filtered_points

            results = []
            for plot_point in plot_points:
                results.append(
                    {
                        "plot_point_id": plot_point.plot_point_id,
                        "title": plot_point.title,
                        "plot_point_type": plot_point.plot_point_type.value,
                        "importance": plot_point.importance.value,
                        "sequence_order": plot_point.sequence_order,
                        "emotional_intensity": float(
                            plot_point.emotional_intensity
                        ),
                        "dramatic_tension": float(plot_point.dramatic_tension),
                        "story_significance": float(
                            plot_point.story_significance
                        ),
                        "involved_characters": [
                            str(cid) for cid in plot_point.involved_characters
                        ],
                        "outcome": plot_point.outcome,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to get plot points in sequence: {str(e)}")
            raise

    def handle_get_plot_points_by_type(
        self, query: GetPlotPointsByTypeQuery
    ) -> List[Dict[str, Any]]:
        """Handle get plot points by type query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return []

            results = []
            for plot_point in arc.plot_points.values():
                if plot_point.plot_point_type.value in query.plot_point_types:
                    plot_data = {
                        "plot_point_id": plot_point.plot_point_id,
                        "title": plot_point.title,
                        "plot_point_type": plot_point.plot_point_type.value,
                        "importance": plot_point.importance.value,
                        "sequence_order": plot_point.sequence_order,
                    }

                    if query.include_details:
                        plot_data.update(
                            {
                                "description": plot_point.description,
                                "emotional_intensity": float(
                                    plot_point.emotional_intensity
                                ),
                                "dramatic_tension": float(
                                    plot_point.dramatic_tension
                                ),
                                "story_significance": float(
                                    plot_point.story_significance
                                ),
                                "involved_characters": [
                                    str(cid)
                                    for cid in plot_point.involved_characters
                                ],
                                "outcome": plot_point.outcome,
                                "conflict_type": plot_point.conflict_type,
                                "location": plot_point.location,
                                "time_context": plot_point.time_context,
                            }
                        )

                    results.append(plot_data)

            # Sort by sequence order
            results.sort(key=lambda x: x["sequence_order"])
            return results

        except Exception as e:
            logger.error(f"Failed to get plot points by type: {str(e)}")
            raise

    def handle_get_theme(
        self, query: GetThemeQuery
    ) -> Optional[Dict[str, Any]]:
        """Handle get theme query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return None

            theme = arc.themes.get(query.theme_id)
            if not theme:
                return None

            return {
                "theme_id": theme.theme_id,
                "theme_type": theme.theme_type.value,
                "intensity": theme.intensity.value,
                "name": theme.name,
                "description": theme.description,
                "moral_complexity": float(theme.moral_complexity),
                "emotional_resonance": float(theme.emotional_resonance),
                "universal_appeal": float(theme.universal_appeal),
                "cultural_significance": float(theme.cultural_significance),
                "development_potential": float(theme.development_potential),
                "symbolic_elements": list(theme.symbolic_elements),
                "introduction_sequence": theme.introduction_sequence,
                "resolution_sequence": theme.resolution_sequence,
                "tags": list(theme.tags),
                "notes": theme.notes,
                "overall_significance_score": float(
                    theme.overall_significance_score
                ),
                "development_sequences": arc.theme_development.get(
                    query.theme_id, []
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get theme: {str(e)}")
            raise

    def handle_get_themes_at_sequence(
        self, query: GetThemesAtSequenceQuery
    ) -> List[Dict[str, Any]]:
        """Handle get themes at sequence query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                return []

            active_themes = arc.get_themes_at_sequence(query.sequence)

            results = []
            for theme in active_themes:
                results.append(
                    {
                        "theme_id": theme.theme_id,
                        "name": theme.name,
                        "theme_type": theme.theme_type.value,
                        "intensity": theme.intensity.value,
                        "emotional_resonance": float(
                            theme.emotional_resonance
                        ),
                        "introduction_sequence": theme.introduction_sequence,
                        "is_active": True,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to get themes at sequence: {str(e)}")
            raise

    def handle_get_arc_metrics(
        self, query: GetArcMetricsQuery
    ) -> Dict[str, Any]:
        """Handle get arc metrics query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {query.arc_id} not found")

            metrics = {
                "arc_id": query.arc_id,
                "complexity_score": float(arc.complexity_score),
                "completion_percentage": float(arc.completion_percentage),
                "current_length": arc.current_length,
                "target_length": arc.target_length,
            }

            if query.include_coherence:
                coherence = arc.calculate_narrative_coherence()
                metrics.update(
                    {
                        "narrative_coherence": float(coherence),
                        "thematic_consistency": float(
                            arc.thematic_consistency
                        ),
                        "pacing_effectiveness": float(
                            arc.pacing_effectiveness
                        ),
                    }
                )

            if query.include_flow_analysis and self.flow_service:
                flow_analysis = self.flow_service.analyze_narrative_flow(arc)
                metrics["flow_analysis"] = {
                    "pacing_score": float(flow_analysis.pacing_score),
                    "climax_positioning": float(
                        flow_analysis.climax_positioning
                    ),
                    "resolution_quality": float(
                        flow_analysis.resolution_quality
                    ),
                    "narrative_momentum": float(
                        flow_analysis.narrative_momentum
                    ),
                    "flow_consistency": float(flow_analysis.flow_consistency),
                }

            if query.include_causal_analysis and self.causal_service:
                # Add plot points to causal service
                for plot_point in arc.plot_points.values():
                    if (
                        plot_point.plot_point_id
                        not in self.causal_service.nodes
                    ):
                        from ...domain.value_objects.causal_node import (
                            CausalNode,
                        )

                        causal_node = CausalNode(
                            node_id=plot_point.plot_point_id,
                            sequence_order=plot_point.sequence_order,
                            narrative_importance=plot_point.overall_impact_score,
                        )
                        self.causal_service.add_node(causal_node)

                causal_analysis = (
                    self.causal_service.analyze_narrative_causality()
                )
                metrics["causal_analysis"] = {
                    "graph_complexity": float(
                        causal_analysis.graph_complexity
                    ),
                    "consistency_score": float(
                        causal_analysis.consistency_score
                    ),
                    "narrative_flow_score": float(
                        causal_analysis.narrative_flow_score
                    ),
                    "root_causes_count": len(causal_analysis.root_causes),
                    "terminal_effects_count": len(
                        causal_analysis.terminal_effects
                    ),
                    "critical_nodes_count": len(
                        causal_analysis.critical_nodes
                    ),
                    "feedback_loops_count": len(
                        causal_analysis.feedback_loops
                    ),
                }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get arc metrics: {str(e)}")
            raise

    def handle_get_arc_summary(
        self, query: GetArcSummaryQuery
    ) -> Dict[str, Any]:
        """Handle get arc summary query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {query.arc_id} not found")

            summary = arc.get_arc_summary()

            if query.include_statistics:
                # Add statistical information
                plot_types_distribution = {}
                for plot_point in arc.plot_points.values():
                    plot_type = plot_point.plot_point_type.value
                    plot_types_distribution[plot_type] = (
                        plot_types_distribution.get(plot_type, 0) + 1
                    )

                theme_types_distribution = {}
                for theme in arc.themes.values():
                    theme_type = theme.theme_type.value
                    theme_types_distribution[theme_type] = (
                        theme_types_distribution.get(theme_type, 0) + 1
                    )

                summary["statistics"] = {
                    "plot_types_distribution": plot_types_distribution,
                    "theme_types_distribution": theme_types_distribution,
                    "average_emotional_intensity": float(
                        sum(
                            pp.emotional_intensity
                            for pp in arc.plot_points.values()
                        )
                        / len(arc.plot_points)
                        if arc.plot_points
                        else Decimal("0")
                    ),
                    "average_dramatic_tension": float(
                        sum(
                            pp.dramatic_tension
                            for pp in arc.plot_points.values()
                        )
                        / len(arc.plot_points)
                        if arc.plot_points
                        else Decimal("0")
                    ),
                }

            if query.include_progression:
                # Add progression information
                plot_points = arc.get_plot_points_in_sequence()
                progression = []
                for pp in plot_points:
                    progression.append(
                        {
                            "sequence": pp.sequence_order,
                            "plot_point_id": pp.plot_point_id,
                            "title": pp.title,
                            "type": pp.plot_point_type.value,
                            "importance": pp.importance.value,
                            "dramatic_tension": float(pp.dramatic_tension),
                        }
                    )

                summary["progression"] = progression

            return summary

        except Exception as e:
            logger.error(f"Failed to get arc summary: {str(e)}")
            raise

    def handle_get_narrative_flow_analysis(
        self, query: GetNarrativeFlowAnalysisQuery
    ) -> Dict[str, Any]:
        """Handle narrative flow analysis query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {query.arc_id} not found")

            analysis = self.flow_service.analyze_narrative_flow(arc)

            result = {
                "arc_id": query.arc_id,
                "pacing_score": float(analysis.pacing_score),
                "climax_positioning": float(analysis.climax_positioning),
                "resolution_quality": float(analysis.resolution_quality),
                "narrative_momentum": float(analysis.narrative_momentum),
                "flow_consistency": float(analysis.flow_consistency),
            }

            if query.include_tension_progression:
                result["tension_progression"] = [
                    float(t) for t in analysis.tension_progression
                ]

            if query.include_recommendations:
                result["recommendations"] = analysis.recommended_adjustments

            return result

        except Exception as e:
            logger.error(f"Failed to get narrative flow analysis: {str(e)}")
            raise

    def handle_get_causal_analysis(
        self, query: GetCausalAnalysisQuery
    ) -> Dict[str, Any]:
        """Handle causal analysis query."""
        try:
            arc = self.repository.get_by_id(NarrativeId(query.arc_id))
            if not arc:
                raise ValueError(f"Narrative arc {query.arc_id} not found")

            # Add plot points to causal service if not already present
            for plot_point in arc.plot_points.values():
                if plot_point.plot_point_id not in self.causal_service.nodes:
                    from ...domain.value_objects.causal_node import CausalNode

                    causal_node = CausalNode(
                        node_id=plot_point.plot_point_id,
                        sequence_order=plot_point.sequence_order,
                        narrative_importance=plot_point.overall_impact_score,
                    )
                    self.causal_service.add_node(causal_node)

            analysis = self.causal_service.analyze_narrative_causality()

            result = {
                "arc_id": query.arc_id,
                "root_causes": analysis.root_causes,
                "terminal_effects": analysis.terminal_effects,
                "critical_nodes": analysis.critical_nodes,
                "graph_complexity": float(analysis.graph_complexity),
                "consistency_score": float(analysis.consistency_score),
                "narrative_flow_score": float(analysis.narrative_flow_score),
                "summary": self.causal_service.get_graph_summary(),
            }

            if query.include_loops:
                result["feedback_loops"] = analysis.feedback_loops

            if query.include_paths:
                longest_chains = []
                for chain in analysis.longest_chains:
                    longest_chains.append(
                        {
                            "nodes": chain.nodes,
                            "path_length": chain.path_length,
                            "total_strength": float(chain.total_strength),
                            "average_strength": float(chain.average_strength),
                            "relationship_types": [
                                rt.value for rt in chain.relationship_types
                            ],
                        }
                    )
                result["longest_chains"] = longest_chains

            return result

        except Exception as e:
            logger.error(f"Failed to get causal analysis: {str(e)}")
            raise
