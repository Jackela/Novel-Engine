#!/usr/bin/env python3
"""
AI Intelligence Module - Novel Engine Integration
================================================

Integration module for Novel Engine's AI intelligence systems that provides
unified access to all advanced AI capabilities including agent coordination,
story quality analysis, analytics, recommendations, and export features.

This module serves as the main entry point for all AI intelligence functionality
and ensures proper integration with the existing Novel Engine framework.
"""

from .agent_coordination_engine import (
    AgentContext,
    AgentCoordinationEngine,
    ConsistencyLevel,
    CoordinationMetrics,
    CoordinationPriority,
    CoordinationTask,
)
from .ai_orchestrator import (
    AIIntelligenceOrchestrator,
    AIPerformanceMetrics,
    AISystemConfig,
    IntelligenceInsight,
    IntelligenceLevel,
    OrchestratorStatus,
    SystemPriority,
)
from .analytics_platform import (
    AnalyticsEvent,
    AnalyticsPlatform,
    CharacterAnalytics,
    EngagementLevel,
    MetricType,
)
from .analytics_platform import SystemMetrics as AnalyticsSystemMetrics
from .analytics_platform import (
    TimeWindow,
    UserEngagement,
)
from .export_integration_engine import (
    ExportFormat,
    ExportIntegrationEngine,
    ExportRequest,
    ExportResult,
    IntegrationType,
    ShareConfiguration,
    ShareMode,
    StoryVersion,
    VersionAction,
)
from .recommendation_engine import (
    ConfidenceLevel,
    PreferenceType,
    Recommendation,
    RecommendationEngine,
    RecommendationType,
    UserPreference,
    UserProfile,
)
from .story_quality_engine import (
    GenreTemplate,
    QualityDimension,
    QualityLevel,
    QualityScore,
    StoryGenre,
    StoryQualityEngine,
    StoryQualityReport,
)

# Version information
__version__ = "1.0.0"
__author__ = "Novel Engine AI Intelligence Team"

# Export all public classes and functions
__all__ = [
    # Agent Coordination
    "AgentCoordinationEngine",
    "AgentContext",
    "CoordinationTask",
    "CoordinationMetrics",
    "CoordinationPriority",
    "ConsistencyLevel",
    # Story Quality
    "StoryQualityEngine",
    "QualityScore",
    "StoryQualityReport",
    "QualityDimension",
    "QualityLevel",
    "StoryGenre",
    "GenreTemplate",
    # Analytics Platform
    "AnalyticsPlatform",
    "AnalyticsEvent",
    "UserEngagement",
    "CharacterAnalytics",
    "AnalyticsSystemMetrics",
    "MetricType",
    "TimeWindow",
    "EngagementLevel",
    # Recommendation Engine
    "RecommendationEngine",
    "UserPreference",
    "Recommendation",
    "UserProfile",
    "RecommendationType",
    "PreferenceType",
    "ConfidenceLevel",
    # Export Integration
    "ExportIntegrationEngine",
    "ExportRequest",
    "ExportResult",
    "ShareConfiguration",
    "StoryVersion",
    "ExportFormat",
    "ShareMode",
    "IntegrationType",
    "VersionAction",
    # AI Orchestrator
    "AIIntelligenceOrchestrator",
    "AISystemConfig",
    "AIPerformanceMetrics",
    "IntelligenceInsight",
    "OrchestratorStatus",
    "IntelligenceLevel",
    "SystemPriority",
]

# Module metadata
INTELLIGENCE_SYSTEMS = [
    "agent_coordination_engine",
    "story_quality_engine",
    "analytics_platform",
    "recommendation_engine",
    "export_integration_engine",
    "ai_orchestrator",
]

SUPPORTED_FEATURES = [
    "multi_agent_coordination",
    "character_consistency_validation",
    "story_quality_analysis",
    "real_time_analytics",
    "user_engagement_tracking",
    "personalized_recommendations",
    "adaptive_story_generation",
    "multi_format_export",
    "version_control",
    "intelligent_orchestration",
]


def get_module_info():
    """Get information about the AI intelligence module."""
    return {
        "version": __version__,
        "author": __author__,
        "systems": INTELLIGENCE_SYSTEMS,
        "features": SUPPORTED_FEATURES,
        "description": "Novel Engine AI Intelligence Framework",
    }
