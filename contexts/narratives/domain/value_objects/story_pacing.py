#!/usr/bin/env python3
"""
Story Pacing Value Object

This module defines value objects for controlling narrative rhythm,
timing, and pacing within story structures.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime, timezone


class PacingType(Enum):
    """Types of story pacing patterns."""
    STEADY = "steady"                    # Consistent pace throughout
    ACCELERATING = "accelerating"        # Gradually increasing pace
    DECELERATING = "decelerating"        # Gradually decreasing pace
    EPISODIC = "episodic"               # Alternating fast and slow
    CRESCENDO = "crescendo"             # Building to climactic peak
    PLATEAU = "plateau"                 # High intensity sustained
    WAVE = "wave"                       # Multiple peaks and valleys
    EXPLOSIVE_START = "explosive_start"  # Fast beginning, then levels off
    SLOW_BURN = "slow_burn"             # Gradual buildup to explosion
    STACCATO = "staccato"               # Sharp, punctuated moments


class PacingIntensity(Enum):
    """Intensity levels for pacing."""
    GLACIAL = "glacial"          # Extremely slow, contemplative
    SLOW = "slow"                # Deliberate, reflective
    MODERATE = "moderate"        # Balanced, comfortable
    BRISK = "brisk"             # Quick, engaging
    FAST = "fast"               # Rapid, exciting
    BREAKNECK = "breakneck"     # Extremely fast, overwhelming


@dataclass(frozen=True)
class StoryPacing:
    """
    Represents pacing control for narrative segments.
    
    Story pacing controls the rhythm and tempo of narrative events,
    managing reader engagement and emotional response through timing.
    """
    
    pacing_id: str
    pacing_type: PacingType
    base_intensity: PacingIntensity
    
    # Segment definition
    start_sequence: int
    end_sequence: int
    segment_name: str = ""
    segment_description: str = ""
    
    # Pacing parameters
    event_density: Decimal = Decimal('5.0')      # Events per unit time (1-10)
    dialogue_ratio: Decimal = Decimal('0.3')     # Proportion of dialogue (0-1)
    action_ratio: Decimal = Decimal('0.4')       # Proportion of action (0-1)
    reflection_ratio: Decimal = Decimal('0.3')   # Proportion of reflection (0-1)
    
    # Temporal control
    scene_transitions: int = 0                    # Number of scene breaks
    time_jumps: int = 0                          # Number of temporal jumps
    average_scene_length: Optional[int] = None    # Average scene duration
    
    # Tension management
    tension_curve: List[Decimal] = None          # Tension levels throughout segment
    emotional_peaks: List[int] = None            # Sequence positions of peaks
    rest_periods: List[int] = None              # Positions of low-intensity moments
    
    # Reader engagement
    revelation_frequency: Decimal = Decimal('0.1') # Major reveals per sequence
    cliffhanger_intensity: Decimal = Decimal('0.0') # End-of-segment suspense
    curiosity_hooks: int = 0                     # Questions raised for reader
    
    # Style considerations
    sentence_complexity: Decimal = Decimal('5.0') # 1-10, simple to complex
    paragraph_length: Decimal = Decimal('5.0')   # 1-10, short to long
    vocabulary_density: Decimal = Decimal('5.0') # 1-10, simple to rich
    
    # Metadata
    target_reading_time: Optional[int] = None    # Minutes
    emotional_target: str = ""                   # Desired emotional response
    pacing_notes: str = ""
    creation_timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values and validate constraints."""
        # Set default values for mutable fields
        if self.tension_curve is None:
            object.__setattr__(self, 'tension_curve', [])
        
        if self.emotional_peaks is None:
            object.__setattr__(self, 'emotional_peaks', [])
        
        if self.rest_periods is None:
            object.__setattr__(self, 'rest_periods', [])
        
        if self.creation_timestamp is None:
            object.__setattr__(self, 'creation_timestamp', datetime.now(timezone.utc))
        
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        # Validate constraints
        self._validate_constraints()
    
    def _validate_constraints(self):
        """Validate business rules and constraints."""
        if not self.pacing_id or not self.pacing_id.strip():
            raise ValueError("Pacing ID cannot be empty")
        
        if self.start_sequence < 0 or self.end_sequence < 0:
            raise ValueError("Sequence numbers must be non-negative")
        
        if self.start_sequence >= self.end_sequence:
            raise ValueError("Start sequence must be before end sequence")
        
        # Validate ratio values (0-1)
        ratio_total = self.dialogue_ratio + self.action_ratio + self.reflection_ratio
        if not (Decimal('0.9') <= ratio_total <= Decimal('1.1')):
            raise ValueError("Dialogue, action, and reflection ratios should sum to approximately 1.0")
        
        for ratio_name, ratio_value in [
            ("dialogue_ratio", self.dialogue_ratio),
            ("action_ratio", self.action_ratio),
            ("reflection_ratio", self.reflection_ratio)
        ]:
            if not (Decimal('0') <= ratio_value <= Decimal('1')):
                raise ValueError(f"{ratio_name} must be between 0 and 1")
        
        # Validate scale values (1-10)
        for scale_name, scale_value in [
            ("event_density", self.event_density),
            ("sentence_complexity", self.sentence_complexity),
            ("paragraph_length", self.paragraph_length),
            ("vocabulary_density", self.vocabulary_density)
        ]:
            if not (Decimal('1') <= scale_value <= Decimal('10')):
                raise ValueError(f"{scale_name} must be between 1 and 10")
        
        # Validate other decimal values
        if not (Decimal('0') <= self.revelation_frequency <= Decimal('1')):
            raise ValueError("Revelation frequency must be between 0 and 1")
        
        if not (Decimal('0') <= self.cliffhanger_intensity <= Decimal('10')):
            raise ValueError("Cliffhanger intensity must be between 0 and 10")
        
        # Validate counts
        if self.scene_transitions < 0 or self.time_jumps < 0 or self.curiosity_hooks < 0:
            raise ValueError("Scene transitions, time jumps, and curiosity hooks must be non-negative")
        
        # Validate tension curve
        for tension_value in self.tension_curve:
            if not (Decimal('0') <= tension_value <= Decimal('10')):
                raise ValueError("Tension curve values must be between 0 and 10")
        
        # Validate peak and rest positions
        sequence_range = range(self.start_sequence, self.end_sequence + 1)
        for peak_pos in self.emotional_peaks:
            if peak_pos not in sequence_range:
                raise ValueError(f"Emotional peak position {peak_pos} outside segment range")
        
        for rest_pos in self.rest_periods:
            if rest_pos not in sequence_range:
                raise ValueError(f"Rest period position {rest_pos} outside segment range")
        
        # String length constraints
        if len(self.pacing_id) > 100:
            raise ValueError("Pacing ID too long (max 100 characters)")
        
        if len(self.segment_name) > 200:
            raise ValueError("Segment name too long (max 200 characters)")
    
    @property
    def segment_length(self) -> int:
        """Get the length of this pacing segment in sequences."""
        return self.end_sequence - self.start_sequence + 1
    
    @property
    def has_peaks(self) -> bool:
        """Check if this segment has defined emotional peaks."""
        return bool(self.emotional_peaks)
    
    @property
    def has_rest_periods(self) -> bool:
        """Check if this segment has defined rest periods."""
        return bool(self.rest_periods)
    
    @property
    def has_tension_curve(self) -> bool:
        """Check if this segment has a defined tension curve."""
        return bool(self.tension_curve)
    
    @property
    def is_high_intensity(self) -> bool:
        """Check if this is a high-intensity pacing segment."""
        return self.base_intensity in [PacingIntensity.FAST, PacingIntensity.BREAKNECK]
    
    @property
    def is_low_intensity(self) -> bool:
        """Check if this is a low-intensity pacing segment."""
        return self.base_intensity in [PacingIntensity.GLACIAL, PacingIntensity.SLOW]
    
    @property
    def average_tension(self) -> Decimal:
        """Calculate average tension level across the segment."""
        if not self.tension_curve:
            return Decimal('5.0')  # Default middle tension
        
        return sum(self.tension_curve) / Decimal(len(self.tension_curve))
    
    @property
    def peak_tension(self) -> Decimal:
        """Get the highest tension level in this segment."""
        if not self.tension_curve:
            return Decimal('5.0')
        
        return max(self.tension_curve)
    
    @property
    def tension_variance(self) -> Decimal:
        """Calculate the variance in tension levels (measure of volatility)."""
        if not self.tension_curve or len(self.tension_curve) < 2:
            return Decimal('0')
        
        avg_tension = self.average_tension
        variance = sum((t - avg_tension) ** 2 for t in self.tension_curve) / Decimal(len(self.tension_curve))
        return variance
    
    @property
    def pacing_complexity_score(self) -> Decimal:
        """
        Calculate overall pacing complexity.
        
        Based on number of transitions, peaks, and stylistic elements.
        """
        base_complexity = Decimal('0')
        
        # Add complexity for structural elements
        base_complexity += Decimal(str(self.scene_transitions * 0.5))
        base_complexity += Decimal(str(self.time_jumps * 1.0))
        base_complexity += Decimal(str(len(self.emotional_peaks) * 0.8))
        base_complexity += Decimal(str(len(self.rest_periods) * 0.3))
        
        # Add complexity for stylistic variation
        style_variance = abs(self.sentence_complexity - Decimal('5')) + \
                        abs(self.paragraph_length - Decimal('5')) + \
                        abs(self.vocabulary_density - Decimal('5'))
        base_complexity += style_variance * Decimal('0.2')
        
        # Add complexity for tension variation
        base_complexity += self.tension_variance * Decimal('0.5')
        
        return min(base_complexity, Decimal('10'))  # Cap at 10
    
    @property
    def engagement_score(self) -> Decimal:
        """
        Calculate reader engagement score.
        
        Based on pacing elements that typically increase engagement.
        """
        engagement = Decimal('0')
        
        # Base engagement from intensity
        intensity_scores = {
            PacingIntensity.GLACIAL: Decimal('2'),
            PacingIntensity.SLOW: Decimal('4'),
            PacingIntensity.MODERATE: Decimal('6'),
            PacingIntensity.BRISK: Decimal('7'),
            PacingIntensity.FAST: Decimal('8'),
            PacingIntensity.BREAKNECK: Decimal('6')  # Can be overwhelming
        }
        engagement += intensity_scores[self.base_intensity]
        
        # Add engagement from revelations and hooks
        engagement += self.revelation_frequency * Decimal('20')
        engagement += self.cliffhanger_intensity * Decimal('0.3')
        engagement += Decimal(str(self.curiosity_hooks * 0.2))
        
        # Add engagement from balanced content mix
        content_balance = Decimal('1') - abs(self.action_ratio - Decimal('0.4'))
        engagement += content_balance * Decimal('2')
        
        return min(engagement, Decimal('10'))
    
    def contains_sequence(self, sequence_number: int) -> bool:
        """Check if a sequence number falls within this pacing segment."""
        return self.start_sequence <= sequence_number <= self.end_sequence
    
    def get_tension_at_sequence(self, sequence_number: int) -> Optional[Decimal]:
        """Get tension level at a specific sequence, if defined."""
        if not self.contains_sequence(sequence_number) or not self.tension_curve:
            return None
        
        # Map sequence to tension curve index
        relative_position = sequence_number - self.start_sequence
        curve_length = len(self.tension_curve)
        
        if curve_length == 1:
            return self.tension_curve[0]
        
        # Interpolate position in curve
        curve_position = (relative_position / (self.segment_length - 1)) * (curve_length - 1)
        index = int(curve_position)
        
        if index >= curve_length - 1:
            return self.tension_curve[-1]
        
        # Linear interpolation between curve points
        weight = curve_position - index
        return (self.tension_curve[index] * (Decimal('1') - Decimal(str(weight)))) + \
               (self.tension_curve[index + 1] * Decimal(str(weight)))
    
    def is_emotional_peak(self, sequence_number: int) -> bool:
        """Check if a sequence is marked as an emotional peak."""
        return sequence_number in self.emotional_peaks
    
    def is_rest_period(self, sequence_number: int) -> bool:
        """Check if a sequence is marked as a rest period."""
        return sequence_number in self.rest_periods
    
    def get_pacing_context(self) -> Dict[str, Any]:
        """
        Get contextual information about this pacing segment.
        
        Returns:
            Dictionary containing pacing context for analysis
        """
        return {
            'pacing_id': self.pacing_id,
            'pacing_type': self.pacing_type.value,
            'base_intensity': self.base_intensity.value,
            'segment_length': self.segment_length,
            'segment_range': [self.start_sequence, self.end_sequence],
            'is_high_intensity': self.is_high_intensity,
            'is_low_intensity': self.is_low_intensity,
            'complexity_score': float(self.pacing_complexity_score),
            'engagement_score': float(self.engagement_score),
            'average_tension': float(self.average_tension) if self.has_tension_curve else None,
            'peak_tension': float(self.peak_tension) if self.has_tension_curve else None,
            'tension_variance': float(self.tension_variance),
            'content_distribution': {
                'dialogue': float(self.dialogue_ratio),
                'action': float(self.action_ratio),
                'reflection': float(self.reflection_ratio)
            },
            'structural_elements': {
                'scene_transitions': self.scene_transitions,
                'time_jumps': self.time_jumps,
                'emotional_peaks': len(self.emotional_peaks),
                'rest_periods': len(self.rest_periods),
                'curiosity_hooks': self.curiosity_hooks
            }
        }
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"StoryPacing('{self.segment_name or self.pacing_id}', {self.pacing_type.value}, {self.base_intensity.value})"
    
    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"StoryPacing(id='{self.pacing_id}', "
            f"type={self.pacing_type.value}, "
            f"intensity={self.base_intensity.value}, "
            f"range=[{self.start_sequence}, {self.end_sequence}])"
        )