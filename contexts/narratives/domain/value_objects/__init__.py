#!/usr/bin/env python3
"""
Narrative Value Objects Package

This package contains immutable value objects that represent fundamental
concepts within the Narrative domain.

Key Value Objects:
- NarrativeId: Unique identifier for narrative elements
- PlotPoint: Represents key moments in story progression
- NarrativeTheme: Core themes and motifs in stories
- CausalNode: Nodes in cause-and-effect relationships
- StoryPacing: Controls narrative rhythm and timing
"""

from .narrative_id import NarrativeId
from .plot_point import PlotPoint, PlotPointType, PlotPointImportance
from .narrative_theme import NarrativeTheme, ThemeType, ThemeIntensity
from .causal_node import CausalNode, CausalRelationType, CausalStrength
from .story_pacing import StoryPacing, PacingType, PacingIntensity
from .narrative_context import NarrativeContext

__all__ = [
    'NarrativeId',
    'PlotPoint',
    'PlotPointType', 
    'PlotPointImportance',
    'NarrativeTheme',
    'ThemeType',
    'ThemeIntensity', 
    'CausalNode',
    'CausalRelationType',
    'CausalStrength',
    'StoryPacing',
    'PacingType',
    'PacingIntensity',
    'NarrativeContext'
]

__version__ = "1.0.0"