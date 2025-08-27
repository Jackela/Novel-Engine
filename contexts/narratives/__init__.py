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

Key Application Services:
- NarrativeArcApplicationService: High-level orchestration and public interface
"""

# Domain Layer Exports
from .domain.aggregates.narrative_arc import NarrativeArc
from .domain.value_objects.narrative_id import NarrativeId
from .domain.value_objects.plot_point import PlotPoint, PlotPointType, PlotPointImportance
from .domain.value_objects.narrative_theme import NarrativeTheme, ThemeType, ThemeIntensity
from .domain.value_objects.story_pacing import StoryPacing, PacingType, PacingIntensity
from .domain.value_objects.narrative_context import NarrativeContext
from .domain.value_objects.causal_node import CausalNode, CausalRelationType, CausalStrength
from .domain.services.causal_graph_service import CausalGraphService
from .domain.services.narrative_flow_service import NarrativeFlowService

# Application Layer Exports
from .application.services.narrative_arc_application_service import NarrativeArcApplicationService

# Infrastructure Layer Exports
from .infrastructure.repositories.narrative_arc_repository import (
    NarrativeArcRepository, 
    INarrativeArcRepository
)

__all__ = [
    # Domain Layer
    'NarrativeArc',
    'NarrativeId',
    'PlotPoint', 'PlotPointType', 'PlotPointImportance',
    'NarrativeTheme', 'ThemeType', 'ThemeIntensity',
    'StoryPacing', 'PacingType', 'PacingIntensity',
    'NarrativeContext',
    'CausalNode', 'CausalRelationType', 'CausalStrength',
    'CausalGraphService',
    'NarrativeFlowService',
    
    # Application Layer
    'NarrativeArcApplicationService',
    
    # Infrastructure Layer
    'NarrativeArcRepository',
    'INarrativeArcRepository'
]

__version__ = "1.0.0"
__context_name__ = "narratives"
__description__ = "Narrative Domain Context with Story Generation and Management"