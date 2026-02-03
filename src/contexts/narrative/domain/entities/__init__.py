"""Narrative Domain Entities Package.

This package contains the core domain entities for story structure:
- Story: The root aggregate for a novel
- Chapter: A container for scenes within a story
- Scene: A dramatic unit within a chapter
- Beat: The atomic unit of narrative
- Conflict: Dramatic tension driver within a scene
- Plotline: A narrative thread running through multiple scenes
"""

from .story import Story, StoryStatus
from .chapter import Chapter, ChapterStatus
from .scene import Scene, SceneStatus
from .beat import Beat, BeatType
from .conflict import Conflict, ConflictType, ConflictStakes, ResolutionStatus
from .plotline import Plotline, PlotlineStatus

__all__ = [
    "Story",
    "StoryStatus",
    "Chapter",
    "ChapterStatus",
    "Scene",
    "SceneStatus",
    "Beat",
    "BeatType",
    "Conflict",
    "ConflictType",
    "ConflictStakes",
    "ResolutionStatus",
    "Plotline",
    "PlotlineStatus",
]
