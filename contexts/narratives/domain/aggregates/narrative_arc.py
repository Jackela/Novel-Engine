#!/usr/bin/env python3
"""
Narrative Arc Aggregate Root

This module defines the NarrativeArc aggregate root, which serves as the
main aggregate for managing story arcs and narrative structures within
the Narrative bounded context.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone
from uuid import UUID
from decimal import Decimal

from ..value_objects.narrative_id import NarrativeId
from ..value_objects.plot_point import PlotPoint
from ..value_objects.narrative_theme import NarrativeTheme
from ..value_objects.story_pacing import StoryPacing
from ..value_objects.narrative_context import NarrativeContext
from ..entities.narrative_thread import NarrativeThread
from ..events.narrative_events import (
    NarrativeEvent, NarrativeArcCreated, NarrativeArcUpdated,
    PlotPointAdded, ThemeIntroduced, PacingAdjusted
)


@dataclass
class NarrativeArc:
    """
    Narrative Arc Aggregate Root.
    
    The main aggregate for managing story arcs, plot points, themes,
    pacing, and overall narrative structure. Enforces narrative
    consistency and business rules.
    """
    
    # Identity (required fields without defaults)
    arc_id: NarrativeId
    arc_name: str
    arc_type: str  # main, subplot, character_arc, flashback, etc.
    
    # Optional/defaulted fields
    description: str = ""
    
    # Arc structure and progression
    plot_points: Dict[str, PlotPoint] = field(default_factory=dict)
    plot_sequence: List[str] = field(default_factory=list)  # Ordered plot point IDs
    
    # Thematic elements
    themes: Dict[str, NarrativeTheme] = field(default_factory=dict)
    theme_development: Dict[str, List[int]] = field(default_factory=dict)  # Theme -> sequences
    
    # Pacing and flow
    pacing_segments: Dict[str, StoryPacing] = field(default_factory=dict)
    pacing_sequence: List[str] = field(default_factory=list)  # Ordered pacing segment IDs
    
    # Context and setting
    narrative_contexts: Dict[str, NarrativeContext] = field(default_factory=dict)
    active_contexts: Set[str] = field(default_factory=set)  # Currently active context IDs
    
    # Character involvement
    primary_characters: Set[UUID] = field(default_factory=set)
    supporting_characters: Set[UUID] = field(default_factory=set)
    character_arcs: Dict[UUID, str] = field(default_factory=dict)  # Character -> arc notes
    
    # Arc metrics and properties
    target_length: Optional[int] = None  # Target number of sequences
    current_length: int = 0
    completion_percentage: Decimal = field(default_factory=lambda: Decimal('0.0'))
    complexity_score: Decimal = field(default_factory=lambda: Decimal('5.0'))
    
    # Arc status and lifecycle
    status: str = "planning"  # planning, active, paused, completed, archived
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    
    # Quality metrics
    narrative_coherence: Decimal = field(default_factory=lambda: Decimal('5.0'))  # 1-10
    thematic_consistency: Decimal = field(default_factory=lambda: Decimal('5.0'))  # 1-10
    pacing_effectiveness: Decimal = field(default_factory=lambda: Decimal('5.0'))   # 1-10
    
    # Relationships
    parent_arc_id: Optional[NarrativeId] = None
    child_arc_ids: Set[NarrativeId] = field(default_factory=set)
    related_threads: Set[NarrativeId] = field(default_factory=set)  # NarrativeThread IDs
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[UUID] = None
    tags: Set[str] = field(default_factory=set)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Domain events
    _uncommitted_events: List[NarrativeEvent] = field(default_factory=list, init=False, repr=False)
    _version: int = field(default=1, init=False)
    
    def __post_init__(self):
        """Initialize aggregate and raise creation event."""
        if not self._uncommitted_events:  # Only on initial creation
            event = NarrativeArcCreated(
                event_id=f"arc_created_{self.arc_id}",
                narrative_id=self.arc_id,
                occurred_at=self.created_at,
                arc_name=self.arc_name,
                arc_type=self.arc_type,
                expected_length=self.target_length
            )
            self._add_event(event)
    
    def _add_event(self, event: NarrativeEvent) -> None:
        """Add a domain event to the uncommitted events list."""
        self._uncommitted_events.append(event)
    
    def get_uncommitted_events(self) -> List[NarrativeEvent]:
        """Get all uncommitted domain events."""
        return self._uncommitted_events.copy()
    
    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events (called after persistence)."""
        self._uncommitted_events.clear()
    
    def _update_timestamp_and_version(self) -> None:
        """Update modification timestamp and version."""
        self.updated_at = datetime.now(timezone.utc)
        self._version += 1
    
    # Plot Point Management
    
    def add_plot_point(self, plot_point: PlotPoint) -> None:
        """
        Add a plot point to the narrative arc.
        
        Args:
            plot_point: PlotPoint value object to add
            
        Raises:
            ValueError: If plot point already exists or sequence conflicts
        """
        if plot_point.plot_point_id in self.plot_points:
            raise ValueError(f"Plot point {plot_point.plot_point_id} already exists")
        
        # Check for sequence conflicts
        for existing_id, existing_plot in self.plot_points.items():
            if existing_plot.sequence_order == plot_point.sequence_order:
                raise ValueError(f"Sequence {plot_point.sequence_order} already occupied by {existing_id}")
        
        self.plot_points[plot_point.plot_point_id] = plot_point
        self._insert_plot_point_in_sequence(plot_point.plot_point_id, plot_point.sequence_order)
        self._update_arc_length()
        self._update_timestamp_and_version()
        
        # Raise domain event
        event = PlotPointAdded(
            event_id=f"plot_added_{plot_point.plot_point_id}",
            narrative_id=self.arc_id,
            occurred_at=datetime.now(timezone.utc),
            plot_point_id=plot_point.plot_point_id,
            plot_point_type=plot_point.plot_point_type.value,
            sequence_order=plot_point.sequence_order,
            importance_level=plot_point.importance.value,
            character_ids=list(plot_point.involved_characters)
        )
        self._add_event(event)
    
    def _insert_plot_point_in_sequence(self, plot_point_id: str, sequence_order: int) -> None:
        """Insert plot point ID in correct sequence position."""
        # Find correct insertion position
        insert_pos = 0
        for i, existing_id in enumerate(self.plot_sequence):
            existing_plot = self.plot_points[existing_id]
            if existing_plot.sequence_order < sequence_order:
                insert_pos = i + 1
            else:
                break
        
        self.plot_sequence.insert(insert_pos, plot_point_id)
    
    def remove_plot_point(self, plot_point_id: str) -> Optional[PlotPoint]:
        """Remove a plot point from the arc."""
        if plot_point_id not in self.plot_points:
            return None
        
        removed_plot = self.plot_points.pop(plot_point_id)
        self.plot_sequence.remove(plot_point_id)
        self._update_arc_length()
        self._update_timestamp_and_version()
        
        return removed_plot
    
    def get_plot_point(self, plot_point_id: str) -> Optional[PlotPoint]:
        """Get a plot point by ID."""
        return self.plot_points.get(plot_point_id)
    
    def get_plot_points_in_sequence(self) -> List[PlotPoint]:
        """Get all plot points in sequence order."""
        return [self.plot_points[pid] for pid in self.plot_sequence]
    
    # Theme Management
    
    def add_theme(self, theme: NarrativeTheme) -> None:
        """Add a theme to the narrative arc."""
        if theme.theme_id in self.themes:
            raise ValueError(f"Theme {theme.theme_id} already exists")
        
        self.themes[theme.theme_id] = theme
        self.theme_development[theme.theme_id] = []
        
        if theme.introduction_sequence is not None:
            self.theme_development[theme.theme_id].append(theme.introduction_sequence)
        
        self._update_timestamp_and_version()
        
        # Raise domain event
        event = ThemeIntroduced(
            event_id=f"theme_added_{theme.theme_id}",
            narrative_id=self.arc_id,
            occurred_at=datetime.now(timezone.utc),
            theme_id=theme.theme_id,
            theme_type=theme.theme_type.value,
            theme_name=theme.name,
            intensity_level=theme.intensity.value,
            introduction_sequence=theme.introduction_sequence or 0,
            symbolic_elements=list(theme.symbolic_elements)
        )
        self._add_event(event)
    
    def develop_theme_at_sequence(self, theme_id: str, sequence: int) -> None:
        """Mark theme development at a specific sequence."""
        if theme_id not in self.themes:
            raise ValueError(f"Theme {theme_id} not found")
        
        if sequence not in self.theme_development[theme_id]:
            self.theme_development[theme_id].append(sequence)
            self.theme_development[theme_id].sort()
            self._update_timestamp_and_version()
    
    def get_themes_at_sequence(self, sequence: int) -> List[NarrativeTheme]:
        """Get all themes active at a specific sequence."""
        active_themes = []
        for theme_id, theme in self.themes.items():
            development_sequences = self.theme_development.get(theme_id, [])
            
            # Check if theme is active at this sequence
            is_active = False
            if theme.introduction_sequence is not None and sequence >= theme.introduction_sequence:
                if theme.resolution_sequence is None or sequence <= theme.resolution_sequence:
                    is_active = True
            elif sequence in development_sequences:
                is_active = True
            
            if is_active:
                active_themes.append(theme)
        
        return active_themes
    
    # Pacing Management
    
    def add_pacing_segment(self, pacing: StoryPacing) -> None:
        """Add a pacing segment to the arc."""
        if pacing.pacing_id in self.pacing_segments:
            raise ValueError(f"Pacing segment {pacing.pacing_id} already exists")
        
        # Check for sequence overlaps
        for existing_pacing in self.pacing_segments.values():
            if self._sequences_overlap(pacing, existing_pacing):
                raise ValueError(f"Pacing segment overlaps with existing segment")
        
        self.pacing_segments[pacing.pacing_id] = pacing
        self._insert_pacing_in_sequence(pacing.pacing_id)
        self._update_timestamp_and_version()
        
        # Raise domain event
        event = PacingAdjusted(
            event_id=f"pacing_added_{pacing.pacing_id}",
            narrative_id=self.arc_id,
            occurred_at=datetime.now(timezone.utc),
            pacing_segment_id=pacing.pacing_id,
            previous_pacing_type="none",
            new_pacing_type=pacing.pacing_type.value,
            previous_intensity="moderate",
            new_intensity=pacing.base_intensity.value,
            affected_sequences=list(range(pacing.start_sequence, pacing.end_sequence + 1))
        )
        self._add_event(event)
    
    def _sequences_overlap(self, pacing1: StoryPacing, pacing2: StoryPacing) -> bool:
        """Check if two pacing segments overlap in sequence range."""
        return not (pacing1.end_sequence < pacing2.start_sequence or 
                   pacing2.end_sequence < pacing1.start_sequence)
    
    def _insert_pacing_in_sequence(self, pacing_id: str) -> None:
        """Insert pacing segment in correct sequence position."""
        pacing = self.pacing_segments[pacing_id]
        insert_pos = 0
        
        for i, existing_id in enumerate(self.pacing_sequence):
            existing_pacing = self.pacing_segments[existing_id]
            if existing_pacing.start_sequence < pacing.start_sequence:
                insert_pos = i + 1
            else:
                break
        
        self.pacing_sequence.insert(insert_pos, pacing_id)
    
    def get_pacing_at_sequence(self, sequence: int) -> Optional[StoryPacing]:
        """Get the pacing segment active at a specific sequence."""
        for pacing in self.pacing_segments.values():
            if pacing.contains_sequence(sequence):
                return pacing
        return None
    
    # Context Management
    
    def add_narrative_context(self, context: NarrativeContext) -> None:
        """Add a narrative context to the arc."""
        if context.context_id in self.narrative_contexts:
            raise ValueError(f"Context {context.context_id} already exists")
        
        self.narrative_contexts[context.context_id] = context
        
        # Auto-activate if persistent or currently applicable
        if context.is_persistent or self._context_applies_now(context):
            self.active_contexts.add(context.context_id)
        
        self._update_timestamp_and_version()
    
    def _context_applies_now(self, context: NarrativeContext) -> bool:
        """Check if context should be active based on current arc state."""
        if not context.has_sequence_range:
            return context.is_persistent
        
        # For now, assume current sequence is the latest plot point sequence
        current_seq = max((pp.sequence_order for pp in self.plot_points.values()), default=0)
        return context.applies_at_sequence(current_seq)
    
    def activate_context(self, context_id: str) -> None:
        """Activate a narrative context."""
        if context_id not in self.narrative_contexts:
            raise ValueError(f"Context {context_id} not found")
        
        self.active_contexts.add(context_id)
        self._update_timestamp_and_version()
    
    def deactivate_context(self, context_id: str) -> None:
        """Deactivate a narrative context."""
        self.active_contexts.discard(context_id)
        self._update_timestamp_and_version()
    
    def get_active_contexts(self) -> List[NarrativeContext]:
        """Get all currently active narrative contexts."""
        return [self.narrative_contexts[cid] for cid in self.active_contexts 
                if cid in self.narrative_contexts]
    
    # Character Management
    
    def add_primary_character(self, character_id: UUID) -> None:
        """Add a primary character to the arc."""
        self.primary_characters.add(character_id)
        # Remove from supporting if present
        self.supporting_characters.discard(character_id)
        self._update_timestamp_and_version()
    
    def add_supporting_character(self, character_id: UUID) -> None:
        """Add a supporting character to the arc."""
        # Only add if not already primary
        if character_id not in self.primary_characters:
            self.supporting_characters.add(character_id)
            self._update_timestamp_and_version()
    
    # Arc State Management
    
    def start_arc(self, start_sequence: int) -> None:
        """Start the narrative arc at a specific sequence."""
        if self.status != "planning":
            raise ValueError(f"Cannot start arc in {self.status} status")
        
        self.status = "active"
        self.start_sequence = start_sequence
        self._update_timestamp_and_version()
    
    def complete_arc(self, end_sequence: int) -> None:
        """Complete the narrative arc."""
        if self.status not in ["active", "paused"]:
            raise ValueError(f"Cannot complete arc in {self.status} status")
        
        self.status = "completed"
        self.end_sequence = end_sequence
        self.completion_percentage = Decimal('1.0')
        self._update_arc_length()
        self._update_timestamp_and_version()
    
    def _update_arc_length(self) -> None:
        """Update current arc length based on plot points."""
        if self.plot_points:
            sequences = [pp.sequence_order for pp in self.plot_points.values()]
            self.current_length = max(sequences) - min(sequences) + 1
            
            if self.target_length and self.target_length > 0:
                progress = min(Decimal('1.0'), Decimal(str(self.current_length)) / Decimal(str(self.target_length)))
                self.completion_percentage = progress
    
    # Analysis and Metrics
    
    def calculate_narrative_coherence(self) -> Decimal:
        """Calculate narrative coherence score based on plot point connections."""
        if len(self.plot_points) < 2:
            return Decimal('10.0')  # Single or no plot points are perfectly coherent
        
        coherence_score = Decimal('5.0')  # Base score
        
        # Check sequence ordering
        sequences = [pp.sequence_order for pp in self.plot_points.values()]
        if sequences == sorted(sequences):
            coherence_score += Decimal('2.0')  # Bonus for proper ordering
        
        # Check for prerequisite fulfillment
        coherence_penalties = Decimal('0')
        for plot_point in self.plot_points.values():
            for prereq in plot_point.prerequisite_events:
                if prereq not in self.plot_points:
                    coherence_penalties += Decimal('0.5')
        
        coherence_score = max(Decimal('1.0'), coherence_score - coherence_penalties)
        self.narrative_coherence = min(Decimal('10.0'), coherence_score)
        
        return self.narrative_coherence
    
    def get_arc_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the narrative arc."""
        return {
            'arc_id': str(self.arc_id),
            'name': self.arc_name,
            'type': self.arc_type,
            'status': self.status,
            'completion_percentage': float(self.completion_percentage),
            'sequence_range': [self.start_sequence, self.end_sequence],
            'current_length': self.current_length,
            'target_length': self.target_length,
            'plot_points_count': len(self.plot_points),
            'themes_count': len(self.themes),
            'pacing_segments_count': len(self.pacing_segments),
            'active_contexts_count': len(self.active_contexts),
            'primary_characters_count': len(self.primary_characters),
            'supporting_characters_count': len(self.supporting_characters),
            'complexity_score': float(self.complexity_score),
            'coherence_score': float(self.narrative_coherence),
            'thematic_consistency': float(self.thematic_consistency),
            'pacing_effectiveness': float(self.pacing_effectiveness),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self._version
        }
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"NarrativeArc('{self.arc_name}', {self.arc_type}, {self.status}, {len(self.plot_points)} plots)"
    
    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"NarrativeArc(id={self.arc_id}, "
            f"name='{self.arc_name}', "
            f"type='{self.arc_type}', "
            f"status='{self.status}', "
            f"plots={len(self.plot_points)}, "
            f"themes={len(self.themes)}, "
            f"version={self._version})"
        )