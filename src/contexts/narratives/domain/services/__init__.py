"""
Service layer components for the narrative V2 domain.

Exports orchestration utilities such as the StoryArcManager that coordinate
value objects into higher-level behaviours.
"""

from .story_arc_manager import StoryArcManager

__all__ = ["StoryArcManager"]

