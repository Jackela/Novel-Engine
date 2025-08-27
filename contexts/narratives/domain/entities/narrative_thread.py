#!/usr/bin/env python3
"""
Narrative Thread Entity

This module defines the NarrativeThread entity, which represents
continuous story threads that span multiple narrative arcs.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from uuid import UUID
from decimal import Decimal

from .story_element import StoryElement
from ..value_objects.narrative_id import NarrativeId


@dataclass
class NarrativeThread(StoryElement):
    """
    Entity representing a continuous narrative thread.
    
    Narrative threads are ongoing story elements that can span
    multiple arcs, maintaining continuity and providing structure
    to complex narratives.
    """
    
    # Thread-specific properties
    thread_type: str = "main"  # main, subplot, character_arc, theme_arc
    priority_level: str = "medium"  # low, medium, high, critical
    
    # Thread progression
    current_arc_id: Optional[NarrativeId] = None
    participating_arc_ids: Set[NarrativeId] = field(default_factory=set)
    completed_arc_ids: Set[NarrativeId] = field(default_factory=set)
    
    # Thread structure
    key_moments: List[Dict[str, Any]] = field(default_factory=list)
    turning_points: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_elements: Set[str] = field(default_factory=set)
    
    # Character involvement
    primary_characters: Set[UUID] = field(default_factory=set)
    supporting_characters: Set[UUID] = field(default_factory=set)
    
    # Thematic elements
    central_themes: Set[str] = field(default_factory=set)
    supporting_themes: Set[str] = field(default_factory=set)
    
    # Thread metrics
    complexity_score: Decimal = field(default_factory=lambda: Decimal('5.0'))
    resolution_progress: Decimal = field(default_factory=lambda: Decimal('0.0'))  # 0-1
    reader_engagement: Decimal = field(default_factory=lambda: Decimal('5.0'))   # 1-10
    
    # Timeline and pacing
    estimated_total_length: Optional[int] = None
    current_sequence_position: int = 0
    pacing_notes: str = ""
    
    def __post_init__(self):
        """Initialize thread-specific defaults."""
        if not hasattr(self, 'element_type') or not self.element_type:
            self.element_type = "narrative_thread"
    
    def add_to_arc(self, arc_id: NarrativeId) -> None:
        """Add this thread to a narrative arc."""
        self.participating_arc_ids.add(arc_id)
        if self.current_arc_id is None:
            self.current_arc_id = arc_id
        self.update_element()
    
    def complete_arc(self, arc_id: NarrativeId) -> None:
        """Mark an arc as completed for this thread."""
        if arc_id in self.participating_arc_ids:
            self.participating_arc_ids.discard(arc_id)
            self.completed_arc_ids.add(arc_id)
            
            # Update current arc if needed
            if self.current_arc_id == arc_id:
                self.current_arc_id = next(iter(self.participating_arc_ids), None)
            
            self.update_element()
    
    def add_key_moment(self, 
                      sequence: int, 
                      description: str, 
                      significance: str = "moderate",
                      **metadata) -> None:
        """Add a key moment to this thread."""
        moment = {
            'sequence': sequence,
            'description': description,
            'significance': significance,
            'timestamp': datetime.now(timezone.utc),
            'metadata': metadata
        }
        self.key_moments.append(moment)
        self.key_moments.sort(key=lambda x: x['sequence'])
        self.update_element()
    
    def add_turning_point(self,
                         sequence: int,
                         description: str,
                         impact_level: str = "moderate",
                         affected_elements: List[str] = None,
                         **metadata) -> None:
        """Add a turning point to this thread."""
        turning_point = {
            'sequence': sequence,
            'description': description,
            'impact_level': impact_level,
            'affected_elements': affected_elements or [],
            'timestamp': datetime.now(timezone.utc),
            'metadata': metadata
        }
        self.turning_points.append(turning_point)
        self.turning_points.sort(key=lambda x: x['sequence'])
        self.update_element()
    
    def add_primary_character(self, character_id: UUID) -> None:
        """Add a primary character to this thread."""
        self.primary_characters.add(character_id)
        # Remove from supporting if present
        self.supporting_characters.discard(character_id)
        self.update_element()
    
    def add_supporting_character(self, character_id: UUID) -> None:
        """Add a supporting character to this thread."""
        # Only add if not already a primary character
        if character_id not in self.primary_characters:
            self.supporting_characters.add(character_id)
            self.update_element()
    
    def remove_character(self, character_id: UUID) -> None:
        """Remove a character from this thread."""
        self.primary_characters.discard(character_id)
        self.supporting_characters.discard(character_id)
        self.update_element()
    
    def add_central_theme(self, theme: str) -> None:
        """Add a central theme to this thread."""
        self.central_themes.add(theme)
        # Remove from supporting if present
        self.supporting_themes.discard(theme)
        self.update_element()
    
    def add_supporting_theme(self, theme: str) -> None:
        """Add a supporting theme to this thread."""
        # Only add if not already a central theme
        if theme not in self.central_themes:
            self.supporting_themes.add(theme)
            self.update_element()
    
    def resolve_element(self, element: str) -> None:
        """Mark an unresolved element as resolved."""
        self.unresolved_elements.discard(element)
        self.update_element()
        self._recalculate_resolution_progress()
    
    def add_unresolved_element(self, element: str) -> None:
        """Add an unresolved element to track."""
        self.unresolved_elements.add(element)
        self.update_element()
        self._recalculate_resolution_progress()
    
    def update_complexity_score(self, score: Decimal) -> None:
        """Update the complexity score for this thread."""
        if not (Decimal('1') <= score <= Decimal('10')):
            raise ValueError("Complexity score must be between 1 and 10")
        self.complexity_score = score
        self.update_element()
    
    def update_engagement_score(self, score: Decimal) -> None:
        """Update the reader engagement score."""
        if not (Decimal('1') <= score <= Decimal('10')):
            raise ValueError("Engagement score must be between 1 and 10")
        self.reader_engagement = score
        self.update_element()
    
    def advance_sequence_position(self, new_position: int) -> None:
        """Update the current sequence position."""
        if new_position < self.current_sequence_position:
            raise ValueError("Sequence position cannot move backward")
        self.current_sequence_position = new_position
        self.update_element()
    
    def _recalculate_resolution_progress(self) -> None:
        """Recalculate resolution progress based on resolved elements."""
        if not hasattr(self, '_total_elements_count'):
            # Estimate total elements from current state
            total_elements = len(self.unresolved_elements) + len(self.key_moments) + len(self.central_themes)
            if total_elements == 0:
                self.resolution_progress = Decimal('0')
                return
        
        # Simple heuristic: progress based on resolved vs total elements
        resolved_count = len(self.key_moments) + len(self.completed_arc_ids)
        total_count = resolved_count + len(self.unresolved_elements) + len(self.participating_arc_ids)
        
        if total_count > 0:
            self.resolution_progress = Decimal(str(resolved_count)) / Decimal(str(total_count))
        else:
            self.resolution_progress = Decimal('0')
    
    @property
    def is_active_thread(self) -> bool:
        """Check if this thread is currently active."""
        return self.is_active and self.current_arc_id is not None
    
    @property
    def has_unresolved_elements(self) -> bool:
        """Check if thread has unresolved elements."""
        return bool(self.unresolved_elements)
    
    @property
    def total_character_count(self) -> int:
        """Get total number of characters involved in thread."""
        return len(self.primary_characters) + len(self.supporting_characters)
    
    @property
    def total_arc_count(self) -> int:
        """Get total number of arcs this thread spans."""
        return len(self.participating_arc_ids) + len(self.completed_arc_ids)
    
    @property
    def is_nearly_complete(self) -> bool:
        """Check if thread is nearly complete (>80% resolution)."""
        return self.resolution_progress >= Decimal('0.8')
    
    @property
    def thread_summary(self) -> Dict[str, Any]:
        """Get a summary of this narrative thread."""
        return {
            'thread_id': str(self.element_id),
            'name': self.name,
            'type': self.thread_type,
            'priority': self.priority_level,
            'status': self.status,
            'is_active': self.is_active_thread,
            'current_arc': str(self.current_arc_id) if self.current_arc_id else None,
            'total_arcs': self.total_arc_count,
            'completed_arcs': len(self.completed_arc_ids),
            'resolution_progress': float(self.resolution_progress),
            'complexity_score': float(self.complexity_score),
            'engagement_score': float(self.reader_engagement),
            'character_count': self.total_character_count,
            'key_moments_count': len(self.key_moments),
            'turning_points_count': len(self.turning_points),
            'unresolved_elements_count': len(self.unresolved_elements),
            'central_themes': list(self.central_themes),
            'current_sequence': self.current_sequence_position
        }
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"NarrativeThread('{self.name}', {self.thread_type}, progress={float(self.resolution_progress):.1%})"
    
    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"NarrativeThread(id={self.element_id}, "
            f"type='{self.thread_type}', "
            f"name='{self.name}', "
            f"arcs={self.total_arc_count}, "
            f"progress={float(self.resolution_progress):.2f})"
        )