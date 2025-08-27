#!/usr/bin/env python3
"""
Narrative Arc Application Queries

This module defines queries for narrative arc read operations in the CQRS pattern.
Queries represent requests for information without changing state.
"""

from dataclasses import dataclass
from typing import Optional, List, Set, Dict, Any
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True)
class GetNarrativeArcQuery:
    """Query to get a narrative arc by ID."""
    arc_id: str
    include_details: bool = True
    include_events: bool = False


@dataclass(frozen=True)
class GetNarrativeArcsByTypeQuery:
    """Query to get narrative arcs by type."""
    arc_type: str
    status: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


@dataclass(frozen=True)
class SearchNarrativeArcsQuery:
    """Query to search narrative arcs."""
    search_term: Optional[str] = None
    arc_types: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    character_ids: Optional[List[UUID]] = None
    theme_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_by: Optional[UUID] = None
    min_complexity: Optional[Decimal] = None
    max_complexity: Optional[Decimal] = None
    min_completion: Optional[Decimal] = None
    max_completion: Optional[Decimal] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    sort_by: Optional[str] = "updated_at"
    sort_order: str = "desc"


@dataclass(frozen=True)
class GetPlotPointQuery:
    """Query to get a specific plot point."""
    arc_id: str
    plot_point_id: str


@dataclass(frozen=True)
class GetPlotPointsInSequenceQuery:
    """Query to get plot points in sequence order."""
    arc_id: str
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None


@dataclass(frozen=True)
class GetPlotPointsByTypeQuery:
    """Query to get plot points by type."""
    arc_id: str
    plot_point_types: List[str]
    include_details: bool = True


@dataclass(frozen=True)
class GetThemeQuery:
    """Query to get a specific theme."""
    arc_id: str
    theme_id: str


@dataclass(frozen=True)
class GetThemesAtSequenceQuery:
    """Query to get themes active at a specific sequence."""
    arc_id: str
    sequence: int


@dataclass(frozen=True)
class GetThemesByTypeQuery:
    """Query to get themes by type."""
    arc_id: str
    theme_types: List[str]


@dataclass(frozen=True)
class GetPacingSegmentQuery:
    """Query to get a specific pacing segment."""
    arc_id: str
    pacing_id: str


@dataclass(frozen=True)
class GetPacingAtSequenceQuery:
    """Query to get pacing segment at a specific sequence."""
    arc_id: str
    sequence: int


@dataclass(frozen=True)
class GetNarrativeContextQuery:
    """Query to get a specific narrative context."""
    arc_id: str
    context_id: str


@dataclass(frozen=True)
class GetActiveContextsQuery:
    """Query to get all active narrative contexts."""
    arc_id: str
    at_sequence: Optional[int] = None


@dataclass(frozen=True)
class GetCharactersInArcQuery:
    """Query to get characters involved in an arc."""
    arc_id: str
    role: Optional[str] = None  # primary, supporting, or None for all


@dataclass(frozen=True)
class GetArcsByCharacterQuery:
    """Query to get arcs containing a specific character."""
    character_id: UUID
    role: Optional[str] = None
    status: Optional[str] = None


@dataclass(frozen=True)
class GetArcMetricsQuery:
    """Query to get narrative arc metrics and analysis."""
    arc_id: str
    include_coherence: bool = True
    include_flow_analysis: bool = False
    include_causal_analysis: bool = False


@dataclass(frozen=True)
class GetArcSummaryQuery:
    """Query to get a comprehensive arc summary."""
    arc_id: str
    include_statistics: bool = True
    include_progression: bool = True


@dataclass(frozen=True)
class GetRelatedArcsQuery:
    """Query to get arcs related to a specific arc."""
    arc_id: str
    include_parent: bool = True
    include_children: bool = True
    include_threads: bool = True


@dataclass(frozen=True)
class GetNarrativeFlowAnalysisQuery:
    """Query to get narrative flow analysis."""
    arc_id: str
    include_recommendations: bool = True
    include_tension_progression: bool = True


@dataclass(frozen=True)
class GetSequenceOptimizationQuery:
    """Query to get sequence optimization suggestions."""
    arc_id: str
    optimization_criteria: Optional[List[str]] = None
    preserve_critical_order: bool = True


@dataclass(frozen=True)
class GetCausalAnalysisQuery:
    """Query to get causal relationship analysis."""
    arc_id: str
    include_paths: bool = True
    include_loops: bool = True
    max_path_depth: int = 5


@dataclass(frozen=True)
class GetCausalPathsQuery:
    """Query to get causal paths between plot points."""
    arc_id: str
    start_node: str
    end_node: str
    max_depth: int = 5


@dataclass(frozen=True)
class GetNodeInfluenceQuery:
    """Query to get influence score of a plot point."""
    arc_id: str
    node_id: str


@dataclass(frozen=True)
class GetArcTimelineQuery:
    """Query to get arc timeline with all elements."""
    arc_id: str
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    include_plot_points: bool = True
    include_themes: bool = True
    include_pacing: bool = True
    include_contexts: bool = True


@dataclass(frozen=True)
class GetProgressionAnalysisQuery:
    """Query to analyze arc progression and development."""
    arc_id: str
    analyze_character_development: bool = True
    analyze_theme_development: bool = True
    analyze_tension_buildup: bool = True


@dataclass(frozen=True)
class GetCompletionAnalysisQuery:
    """Query to analyze arc completion readiness."""
    arc_id: str
    check_plot_resolution: bool = True
    check_theme_resolution: bool = True
    check_character_arcs: bool = True


@dataclass(frozen=True)
class GetArcStatisticsQuery:
    """Query to get statistical information about an arc."""
    arc_id: str
    include_distribution_metrics: bool = True
    include_complexity_metrics: bool = True
    include_engagement_metrics: bool = False


@dataclass(frozen=True)
class GetCrossArcAnalysisQuery:
    """Query to analyze relationships between multiple arcs."""
    arc_ids: List[str]
    analyze_character_overlap: bool = True
    analyze_theme_consistency: bool = True
    analyze_timeline_conflicts: bool = True


@dataclass(frozen=True)
class GetNarrativeHealthQuery:
    """Query to get overall narrative health assessment."""
    arc_id: str
    check_structural_integrity: bool = True
    check_pacing_balance: bool = True
    check_thematic_coherence: bool = True
    check_character_consistency: bool = True