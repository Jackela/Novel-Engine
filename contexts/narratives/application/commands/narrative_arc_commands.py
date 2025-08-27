#!/usr/bin/env python3
"""
Narrative Arc Application Commands

This module defines commands for narrative arc operations in the CQRS pattern.
Commands represent intent to change state and are processed by command handlers.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Set, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime


@dataclass(frozen=True)
class CreateNarrativeArcCommand:
    """Command to create a new narrative arc."""
    arc_name: str
    arc_type: str
    description: str = ""
    target_length: Optional[int] = None
    primary_characters: Optional[Set[UUID]] = None
    created_by: Optional[UUID] = None
    tags: Optional[Set[str]] = None
    notes: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class UpdateNarrativeArcCommand:
    """Command to update narrative arc properties."""
    arc_id: str
    arc_name: Optional[str] = None
    arc_type: Optional[str] = None
    description: Optional[str] = None
    target_length: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[Set[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AddPlotPointCommand:
    """Command to add a plot point to a narrative arc."""
    arc_id: str
    plot_point_id: str
    plot_point_type: str
    importance: str
    title: str
    description: str
    sequence_order: int
    emotional_intensity: Decimal = Decimal('5.0')
    dramatic_tension: Decimal = Decimal('5.0')
    story_significance: Decimal = Decimal('5.0')
    involved_characters: Optional[Set[UUID]] = None
    prerequisite_events: Optional[Set[str]] = None
    consequence_events: Optional[Set[str]] = None
    location: Optional[str] = None
    time_context: Optional[str] = None
    pov_character: Optional[UUID] = None
    outcome: Optional[str] = None
    conflict_type: Optional[str] = None
    thematic_relevance: Optional[Dict[str, Decimal]] = None
    tags: Optional[Set[str]] = None
    notes: str = ""


@dataclass(frozen=True)
class UpdatePlotPointCommand:
    """Command to update a plot point."""
    arc_id: str
    plot_point_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    sequence_order: Optional[int] = None
    emotional_intensity: Optional[Decimal] = None
    dramatic_tension: Optional[Decimal] = None
    story_significance: Optional[Decimal] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class RemovePlotPointCommand:
    """Command to remove a plot point from a narrative arc."""
    arc_id: str
    plot_point_id: str


@dataclass(frozen=True)
class AddThemeCommand:
    """Command to add a theme to a narrative arc."""
    arc_id: str
    theme_id: str
    theme_type: str
    intensity: str
    name: str
    description: str
    moral_complexity: Decimal = Decimal('5.0')
    emotional_resonance: Decimal = Decimal('5.0')
    universal_appeal: Decimal = Decimal('5.0')
    cultural_significance: Decimal = Decimal('5.0')
    development_potential: Decimal = Decimal('5.0')
    symbolic_elements: Optional[Set[str]] = None
    introduction_sequence: Optional[int] = None
    resolution_sequence: Optional[int] = None
    tags: Optional[Set[str]] = None
    notes: str = ""


@dataclass(frozen=True)
class DevelopThemeCommand:
    """Command to develop a theme at a specific sequence."""
    arc_id: str
    theme_id: str
    sequence: int
    development_notes: str = ""


@dataclass(frozen=True)
class AddPacingSegmentCommand:
    """Command to add a pacing segment to a narrative arc."""
    arc_id: str
    pacing_id: str
    pacing_type: str
    base_intensity: str
    start_sequence: int
    end_sequence: int
    event_density: Decimal = Decimal('5.0')
    tension_curve: Optional[List[Decimal]] = None
    dialogue_ratio: Decimal = Decimal('0.4')
    action_ratio: Decimal = Decimal('0.3')
    reflection_ratio: Decimal = Decimal('0.3')
    description_density: Decimal = Decimal('5.0')
    character_focus: Optional[Set[UUID]] = None
    narrative_techniques: Optional[Set[str]] = None
    reader_engagement_target: Optional[str] = None
    tags: Optional[Set[str]] = None
    notes: str = ""


@dataclass(frozen=True)
class AddNarrativeContextCommand:
    """Command to add a narrative context to an arc."""
    arc_id: str
    context_id: str
    context_type: str
    name: str
    description: str
    importance: Decimal = Decimal('5.0')
    is_persistent: bool = False
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    location: Optional[str] = None
    time_period: Optional[str] = None
    mood: Optional[str] = None
    atmosphere: Optional[str] = None
    social_context: Optional[str] = None
    cultural_context: Optional[str] = None
    affected_characters: Optional[Set[UUID]] = None
    related_themes: Optional[Set[str]] = None
    tags: Optional[Set[str]] = None
    notes: str = ""


@dataclass(frozen=True)
class ActivateContextCommand:
    """Command to activate a narrative context."""
    arc_id: str
    context_id: str


@dataclass(frozen=True)
class DeactivateContextCommand:
    """Command to deactivate a narrative context."""
    arc_id: str
    context_id: str


@dataclass(frozen=True)
class AddCharacterToArcCommand:
    """Command to add a character to a narrative arc."""
    arc_id: str
    character_id: UUID
    role: str  # primary, supporting
    character_arc_notes: str = ""


@dataclass(frozen=True)
class StartNarrativeArcCommand:
    """Command to start a narrative arc."""
    arc_id: str
    start_sequence: int


@dataclass(frozen=True)
class CompleteNarrativeArcCommand:
    """Command to complete a narrative arc."""
    arc_id: str
    end_sequence: int


@dataclass(frozen=True)
class AnalyzeNarrativeFlowCommand:
    """Command to analyze narrative flow of an arc."""
    arc_id: str
    include_recommendations: bool = True


@dataclass(frozen=True)
class OptimizeSequenceCommand:
    """Command to optimize plot point sequence."""
    arc_id: str
    preserve_critical_order: bool = True
    optimization_criteria: Optional[List[str]] = None


@dataclass(frozen=True)
class EstablishCausalLinkCommand:
    """Command to establish causal relationship between plot points."""
    arc_id: str
    cause_id: str
    effect_id: str
    relationship_type: str = "direct_cause"
    strength: str = "moderate"
    certainty: Decimal = Decimal('0.8')
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class RemoveCausalLinkCommand:
    """Command to remove causal relationship."""
    arc_id: str
    cause_id: str
    effect_id: str


@dataclass(frozen=True)
class AnalyzeCausalityCommand:
    """Command to analyze causality in narrative arc."""
    arc_id: str
    include_paths: bool = True
    max_path_depth: int = 5