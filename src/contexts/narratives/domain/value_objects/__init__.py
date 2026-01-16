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

from .causal_node import CausalNode, CausalRelationType, CausalStrength
from .narrative_context import NarrativeContext
from .narrative_id import NarrativeId
from .narrative_theme import NarrativeTheme, ThemeIntensity, ThemeType
from .narrative_v2_models import (
    NarrativeGuidance,
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)
from .plot_point import PlotPoint, PlotPointImportance, PlotPointType
from .story_pacing import PacingIntensity, PacingType, StoryPacing

__all__ = [
    "NarrativeId",
    "PlotPoint",
    "PlotPointType",
    "PlotPointImportance",
    "NarrativeTheme",
    "ThemeType",
    "ThemeIntensity",
    "CausalNode",
    "CausalRelationType",
    "CausalStrength",
    "StoryPacing",
    "PacingType",
    "PacingIntensity",
    "NarrativeContext",
    "StoryArcPhase",
    "StoryArcState",
    "NarrativeGuidance",
    "PacingAdjustment",
]

__version__ = "1.0.0"
