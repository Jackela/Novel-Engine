#!/usr/bin/env python3
"""
Narrative Domain Entities Package

This package contains domain entities for the Narrative bounded context.
Entities have identity and can change over time while maintaining their identity.

Key Domain Entities:
- StoryElement: Base entity for narrative elements with identity
- NarrativeThread: Continuous story thread across multiple arcs
- CharacterArc: Character development arc within narrative
- Subplot: Secondary story line within main narrative
"""

from .story_element import StoryElement
from .narrative_thread import NarrativeThread

__all__ = [
    'StoryElement',
    'NarrativeThread'
]

__version__ = "1.0.0"