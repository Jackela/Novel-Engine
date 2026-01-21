"""
Narrative Bounded Context

This package implements the Narrative bounded context for the Novel Engine,
following Domain-Driven Design (DDD) principles with CQRS and Event Sourcing patterns.

The Narrative context manages story arcs, plot points, themes, pacing, and causal relationships
within narrative structures, providing sophisticated tools for story analysis and optimization.

Architecture Layers:
- Domain: Core business logic, entities, value objects, and domain services
- Application: CQRS implementation with commands, queries, and application services
- Infrastructure: Data persistence, external integrations, and technical concerns

Key Aggregates:
- NarrativeArc: Main aggregate root managing story arcs and narrative structures

Key Domain Services:
- CausalGraphService: Manages cause-and-effect relationships in narratives
- NarrativeFlowService: Analyzes and optimizes story flow and pacing
- StoryArcManager: Tracks narrative arc progression and milestones
- PacingManager: Balances tension and rhythm across turns
- NarrativePlanningEngine: Plans arc evolution and story beats

Key Application Services:
- NarrativeArcApplicationService: High-level orchestration and public interface
"""

# Application Layer Exports
from .application.services.narrative_arc_application_service import (
    NarrativeArcApplicationService,
)

# Domain Layer Exports
from .domain.aggregates.narrative_arc import NarrativeArc
from .domain.services.causal_graph_service import CausalGraphService
from .domain.services.narrative_flow_service import NarrativeFlowService
from .domain.services.narrative_planning_engine import NarrativePlanningEngine
from .domain.services.pacing_manager import PacingManager
from .domain.services.story_arc_manager import StoryArcManager
from .domain.value_objects.causal_node import (
    CausalNode,
    CausalRelationType,
    CausalStrength,
)
from .domain.value_objects.narrative_models import (
    NarrativeGuidance,
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)
from .domain.value_objects.narrative_context import NarrativeContext
from .domain.value_objects.narrative_id import NarrativeId
from .domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)
from .domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)
from .domain.value_objects.story_pacing import PacingIntensity, PacingType, StoryPacing

# Infrastructure Layer Exports
from .infrastructure.repositories.narrative_arc_repository import (
    INarrativeArcRepository,
    NarrativeArcRepository,
)

__all__ = [
    # Domain Layer
    "NarrativeArc",
    "NarrativeId",
    "PlotPoint",
    "PlotPointType",
    "PlotPointImportance",
    "NarrativeTheme",
    "ThemeType",
    "ThemeIntensity",
    "StoryPacing",
    "PacingType",
    "PacingIntensity",
    "NarrativeContext",
    "StoryArcPhase",
    "StoryArcState",
    "NarrativeGuidance",
    "PacingAdjustment",
    "CausalNode",
    "CausalRelationType",
    "CausalStrength",
    "CausalGraphService",
    "NarrativeFlowService",
    "NarrativePlanningEngine",
    "PacingManager",
    "StoryArcManager",
    # Application Layer
    "NarrativeArcApplicationService",
    # Infrastructure Layer
    "NarrativeArcRepository",
    "INarrativeArcRepository",
]

__version__ = "1.0.0"
__context_name__ = "narratives"
__description__ = "Narrative Domain Context with Story Generation and Management"
