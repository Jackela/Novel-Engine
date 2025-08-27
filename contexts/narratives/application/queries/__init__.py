#!/usr/bin/env python3
"""
Narrative Application Queries

This package contains query objects for narrative read operations in the CQRS pattern.
Queries represent requests for information without changing state.
"""

from .narrative_arc_queries import (
    GetNarrativeArcQuery,
    GetNarrativeArcsByTypeQuery,
    SearchNarrativeArcsQuery,
    GetPlotPointQuery,
    GetPlotPointsInSequenceQuery,
    GetPlotPointsByTypeQuery,
    GetThemeQuery,
    GetThemesAtSequenceQuery,
    GetThemesByTypeQuery,
    GetPacingSegmentQuery,
    GetPacingAtSequenceQuery,
    GetNarrativeContextQuery,
    GetActiveContextsQuery,
    GetCharactersInArcQuery,
    GetArcsByCharacterQuery,
    GetArcMetricsQuery,
    GetArcSummaryQuery,
    GetRelatedArcsQuery,
    GetNarrativeFlowAnalysisQuery,
    GetSequenceOptimizationQuery,
    GetCausalAnalysisQuery,
    GetCausalPathsQuery,
    GetNodeInfluenceQuery,
    GetArcTimelineQuery,
    GetProgressionAnalysisQuery,
    GetCompletionAnalysisQuery,
    GetArcStatisticsQuery,
    GetCrossArcAnalysisQuery,
    GetNarrativeHealthQuery
)

__all__ = [
    'GetNarrativeArcQuery',
    'GetNarrativeArcsByTypeQuery',
    'SearchNarrativeArcsQuery',
    'GetPlotPointQuery',
    'GetPlotPointsInSequenceQuery',
    'GetPlotPointsByTypeQuery',
    'GetThemeQuery',
    'GetThemesAtSequenceQuery',
    'GetThemesByTypeQuery',
    'GetPacingSegmentQuery',
    'GetPacingAtSequenceQuery',
    'GetNarrativeContextQuery',
    'GetActiveContextsQuery',
    'GetCharactersInArcQuery',
    'GetArcsByCharacterQuery',
    'GetArcMetricsQuery',
    'GetArcSummaryQuery',
    'GetRelatedArcsQuery',
    'GetNarrativeFlowAnalysisQuery',
    'GetSequenceOptimizationQuery',
    'GetCausalAnalysisQuery',
    'GetCausalPathsQuery',
    'GetNodeInfluenceQuery',
    'GetArcTimelineQuery',
    'GetProgressionAnalysisQuery',
    'GetCompletionAnalysisQuery',
    'GetArcStatisticsQuery',
    'GetCrossArcAnalysisQuery',
    'GetNarrativeHealthQuery'
]

__version__ = "1.0.0"