#!/usr/bin/env python3
"""
Interaction Query Objects

This module implements query objects for the Interaction bounded context,
following CQRS principles to encapsulate read operations and their
required parameters.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass(frozen=True)
class InteractionQuery:
    """Base class for all interaction queries."""

    query_id: UUID
    timestamp: datetime
    requested_by: UUID

    def __post_init__(self):
        """Validate base query data."""
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")


# Session Queries


@dataclass(frozen=True)
class GetNegotiationSessionQuery(InteractionQuery):
    """Query to get a specific negotiation session."""

    session_id: UUID
    include_parties: bool = True
    include_proposals: bool = True
    include_responses: bool = True
    include_events: bool = False


@dataclass(frozen=True)
class ListNegotiationSessionsQuery(InteractionQuery):
    """Query to list negotiation sessions with filters."""

    created_by: Optional[UUID] = None
    session_type: Optional[str] = None
    status_filter: Optional[str] = None  # active, completed, terminated
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    participant_id: Optional[UUID] = None
    negotiation_domain: Optional[str] = None
    priority_level: Optional[str] = None
    limit: int = 50
    offset: int = 0
    order_by: str = "created_at"
    order_direction: str = "desc"

    def __post_init__(self):
        super().__post_init__()
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.order_by not in [
            "created_at",
            "session_name",
            "status",
            "priority_level",
        ]:
            raise ValueError(
                "order_by must be one of: created_at, session_name, status, priority_level"
            )
        if self.order_direction not in ["asc", "desc"]:
            raise ValueError("order_direction must be 'asc' or 'desc'")


@dataclass(frozen=True)
class GetSessionSummaryQuery(InteractionQuery):
    """Query to get a comprehensive summary of a negotiation session."""

    session_id: UUID
    include_analytics: bool = True
    include_timeline: bool = True
    include_party_details: bool = True
    summary_depth: str = "standard"  # basic, standard, detailed

    def __post_init__(self):
        super().__post_init__()
        if self.summary_depth not in ["basic", "standard", "detailed"]:
            raise ValueError("summary_depth must be one of: basic, standard, detailed")


@dataclass(frozen=True)
class GetSessionTimelineQuery(InteractionQuery):
    """Query to get the timeline of events for a negotiation session."""

    session_id: UUID
    event_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_system_events: bool = False
    group_by_phase: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")


# Party Queries


@dataclass(frozen=True)
class GetSessionPartiesQuery(InteractionQuery):
    """Query to get parties in a negotiation session."""

    session_id: UUID
    include_capabilities: bool = True
    include_preferences: bool = True
    include_activity_summary: bool = False
    role_filter: Optional[str] = None
    authority_filter: Optional[str] = None


@dataclass(frozen=True)
class GetPartyDetailsQuery(InteractionQuery):
    """Query to get detailed information about a specific party."""

    session_id: UUID
    party_id: UUID
    include_negotiation_history: bool = True
    include_performance_metrics: bool = True
    include_compatibility_analysis: bool = False


@dataclass(frozen=True)
class GetPartyCompatibilityQuery(InteractionQuery):
    """Query to get compatibility analysis between parties."""

    session_id: UUID
    party_ids: Optional[List[UUID]] = None  # If None, analyze all parties
    compatibility_factors: Optional[List[str]] = None
    include_recommendations: bool = True
    matrix_format: bool = True


# Proposal Queries


@dataclass(frozen=True)
class GetSessionProposalsQuery(InteractionQuery):
    """Query to get proposals in a negotiation session."""

    session_id: UUID
    proposal_status: str = "active"  # active, withdrawn, expired, all
    include_terms: bool = True
    include_responses: bool = False
    include_viability_analysis: bool = False
    submitted_by: Optional[UUID] = None
    proposal_type: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.proposal_status not in ["active", "withdrawn", "expired", "all"]:
            raise ValueError(
                "proposal_status must be one of: active, withdrawn, expired, all"
            )


@dataclass(frozen=True)
class GetProposalDetailsQuery(InteractionQuery):
    """Query to get detailed information about a specific proposal."""

    session_id: UUID
    proposal_id: UUID
    include_viability_analysis: bool = True
    include_response_summary: bool = True
    include_optimization_suggestions: bool = False
    analysis_depth: str = "standard"

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_depth not in ["basic", "standard", "comprehensive"]:
            raise ValueError(
                "analysis_depth must be one of: basic, standard, comprehensive"
            )


@dataclass(frozen=True)
class GetProposalResponsesQuery(InteractionQuery):
    """Query to get responses to a specific proposal."""

    session_id: UUID
    proposal_id: UUID
    responding_party_id: Optional[UUID] = None
    response_type_filter: Optional[str] = None
    include_term_responses: bool = True
    include_analysis: bool = False


# Analysis Queries


@dataclass(frozen=True)
class GetNegotiationAnalyticsQuery(InteractionQuery):
    """Query to get comprehensive analytics for a negotiation session."""

    session_id: UUID
    analytics_types: List[str] = None  # momentum, conflicts, viability, compatibility
    time_window_hours: int = 168  # 1 week default
    include_trends: bool = True
    include_predictions: bool = False
    granularity: str = "hour"  # hour, day, phase

    def __post_init__(self):
        super().__post_init__()
        if self.time_window_hours <= 0:
            raise ValueError("time_window_hours must be positive")
        if self.granularity not in ["hour", "day", "phase"]:
            raise ValueError("granularity must be one of: hour, day, phase")
        if self.analytics_types is None:
            self.analytics_types = [
                "momentum",
                "conflicts",
                "viability",
                "compatibility",
            ]


@dataclass(frozen=True)
class GetMomentumAnalysisQuery(InteractionQuery):
    """Query to get negotiation momentum analysis."""

    session_id: UUID
    analysis_window_hours: int = 24
    include_predictions: bool = True
    include_contributing_factors: bool = True
    momentum_factors: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_window_hours <= 0:
            raise ValueError("analysis_window_hours must be positive")


@dataclass(frozen=True)
class GetConflictAnalysisQuery(InteractionQuery):
    """Query to get conflict analysis for a negotiation session."""

    session_id: UUID
    conflict_types: Optional[List[str]] = None
    severity_threshold: str = "medium"
    include_resolution_suggestions: bool = True
    include_historical_conflicts: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.severity_threshold not in ["low", "medium", "high", "critical"]:
            raise ValueError(
                "severity_threshold must be one of: low, medium, high, critical"
            )


@dataclass(frozen=True)
class GetStrategyRecommendationsQuery(InteractionQuery):
    """Query to get negotiation strategy recommendations."""

    session_id: UUID
    target_outcome: Optional[str] = None
    strategy_focus: str = "balanced"
    include_tactics: bool = True
    include_risk_assessment: bool = True
    timeline_constraints: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.strategy_focus not in [
            "aggressive",
            "balanced",
            "conservative",
            "collaborative",
        ]:
            raise ValueError(
                "strategy_focus must be one of: aggressive, balanced, conservative, collaborative"
            )


# Performance and Reporting Queries


@dataclass(frozen=True)
class GetSessionPerformanceQuery(InteractionQuery):
    """Query to get performance metrics for a negotiation session."""

    session_id: UUID
    metrics_types: List[
        str
    ] = None  # efficiency, effectiveness, engagement, satisfaction
    include_benchmarks: bool = True
    include_party_performance: bool = True
    performance_period: Optional[str] = None  # overall, recent, phase-specific

    def __post_init__(self):
        super().__post_init__()
        if self.metrics_types is None:
            self.metrics_types = ["efficiency", "effectiveness", "engagement"]
        if self.performance_period is not None and self.performance_period not in [
            "overall",
            "recent",
            "phase-specific",
        ]:
            raise ValueError(
                "performance_period must be one of: overall, recent, phase-specific"
            )


@dataclass(frozen=True)
class GenerateSessionReportQuery(InteractionQuery):
    """Query to generate a comprehensive session report."""

    session_id: UUID
    report_type: str = "comprehensive"
    include_analytics: bool = True
    include_recommendations: bool = True
    target_audience: str = "technical"
    export_format: str = "json"
    sections: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.report_type not in [
            "summary",
            "comprehensive",
            "analytical",
            "executive",
        ]:
            raise ValueError(
                "report_type must be one of: summary, comprehensive, analytical, executive"
            )
        if self.target_audience not in [
            "technical",
            "business",
            "executive",
            "general",
        ]:
            raise ValueError(
                "target_audience must be one of: technical, business, executive, general"
            )
        if self.export_format not in ["json", "pdf", "html", "csv"]:
            raise ValueError("export_format must be one of: json, pdf, html, csv")


# Search and Filter Queries


@dataclass(frozen=True)
class SearchNegotiationSessionsQuery(InteractionQuery):
    """Query to search negotiation sessions with flexible criteria."""

    search_term: Optional[str] = None
    filters: Dict[str, Any] = None
    search_fields: List[str] = None  # session_name, session_type, party_names, etc.
    full_text_search: bool = False
    fuzzy_matching: bool = False
    limit: int = 50
    offset: int = 0

    def __post_init__(self):
        super().__post_init__()
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.search_fields is None:
            self.search_fields = ["session_name", "session_type"]
        if self.filters is None:
            self.filters = {}


@dataclass(frozen=True)
class SearchProposalsQuery(InteractionQuery):
    """Query to search proposals across sessions."""

    search_term: Optional[str] = None
    session_id: Optional[UUID] = None
    proposal_type: Optional[str] = None
    submitted_by: Optional[UUID] = None
    date_range: Optional[Dict[str, datetime]] = None
    terms_filter: Optional[Dict[str, Any]] = None
    viability_threshold: Optional[float] = None
    limit: int = 50
    offset: int = 0

    def __post_init__(self):
        super().__post_init__()
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.viability_threshold is not None and not (
            0 <= self.viability_threshold <= 100
        ):
            raise ValueError("viability_threshold must be between 0 and 100")


# Historical and Trend Queries


@dataclass(frozen=True)
class GetNegotiationTrendsQuery(InteractionQuery):
    """Query to get negotiation trends over time."""

    time_period: str = "last_30_days"  # last_7_days, last_30_days, last_90_days, custom
    custom_start_date: Optional[datetime] = None
    custom_end_date: Optional[datetime] = None
    trend_metrics: List[str] = None  # success_rate, avg_duration, party_satisfaction
    group_by: str = "week"  # day, week, month
    filters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.time_period not in [
            "last_7_days",
            "last_30_days",
            "last_90_days",
            "custom",
        ]:
            raise ValueError(
                "time_period must be one of: last_7_days, last_30_days, last_90_days, custom"
            )
        if self.time_period == "custom":
            if not self.custom_start_date or not self.custom_end_date:
                raise ValueError(
                    "custom_start_date and custom_end_date required for custom time_period"
                )
            if self.custom_start_date >= self.custom_end_date:
                raise ValueError("custom_start_date must be before custom_end_date")
        if self.group_by not in ["day", "week", "month"]:
            raise ValueError("group_by must be one of: day, week, month")
        if self.trend_metrics is None:
            self.trend_metrics = ["success_rate", "avg_duration", "completion_rate"]


@dataclass(frozen=True)
class GetHistoricalAnalysisQuery(InteractionQuery):
    """Query to get historical analysis of negotiation patterns."""

    analysis_type: str = "success_factors"
    time_range: Dict[str, datetime] = None
    include_patterns: bool = True
    include_benchmarks: bool = True
    pattern_types: Optional[List[str]] = None
    min_sample_size: int = 10

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_type not in [
            "success_factors",
            "failure_patterns",
            "duration_analysis",
            "party_behavior",
            "proposal_effectiveness",
        ]:
            raise ValueError(
                "analysis_type must be one of: success_factors, failure_patterns, duration_analysis, party_behavior, proposal_effectiveness"
            )
        if self.min_sample_size <= 0:
            raise ValueError("min_sample_size must be positive")


# Real-time and Monitoring Queries


@dataclass(frozen=True)
class GetActiveSessionsQuery(InteractionQuery):
    """Query to get currently active negotiation sessions."""

    priority_filter: Optional[str] = None
    timeout_warning_threshold: int = 24  # hours
    include_health_status: bool = True
    include_alerts: bool = True
    sort_by_urgency: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.timeout_warning_threshold <= 0:
            raise ValueError("timeout_warning_threshold must be positive")


@dataclass(frozen=True)
class GetSessionHealthQuery(InteractionQuery):
    """Query to get health status and alerts for a session."""

    session_id: UUID
    include_recommendations: bool = True
    include_trend_analysis: bool = False
    health_check_depth: str = "standard"
    alert_threshold: str = "medium"

    def __post_init__(self):
        super().__post_init__()
        if self.health_check_depth not in ["basic", "standard", "comprehensive"]:
            raise ValueError(
                "health_check_depth must be one of: basic, standard, comprehensive"
            )
        if self.alert_threshold not in ["low", "medium", "high", "critical"]:
            raise ValueError(
                "alert_threshold must be one of: low, medium, high, critical"
            )


@dataclass(frozen=True)
class GetNotificationsQuery(InteractionQuery):
    """Query to get notifications and alerts for a user."""

    notification_types: Optional[List[str]] = None
    severity_filter: Optional[str] = None
    session_id: Optional[UUID] = None
    unread_only: bool = False
    limit: int = 50
    offset: int = 0

    def __post_init__(self):
        super().__post_init__()
        if self.limit <= 0 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.severity_filter is not None and self.severity_filter not in [
            "low",
            "medium",
            "high",
            "critical",
        ]:
            raise ValueError(
                "severity_filter must be one of: low, medium, high, critical"
            )
