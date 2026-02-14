"""Narrative Domain Entities Package.

This package contains the core domain entities for story structure:
- Story: The root aggregate for a novel
- Chapter: A container for scenes within a story
- Scene: A dramatic unit within a chapter
- Beat: The atomic unit of narrative
- Conflict: Dramatic tension driver within a scene
- Plotline: A narrative thread running through multiple scenes
- Foreshadowing: Chekhov's Gun enforcement (setup/payoff tracking)
"""

from .beat import Beat, BeatType
from .chapter import Chapter, ChapterStatus
from .conflict import Conflict, ConflictStakes, ConflictType, ResolutionStatus
from .foreshadowing import Foreshadowing, ForeshadowingStatus
from .plotline import Plotline, PlotlineStatus
from .scene import Scene, SceneStatus, StoryPhase
from .story import Story, StoryStatus

__all__ = [
    "Story",
    "StoryStatus",
    "Chapter",
    "ChapterStatus",
    "Scene",
    "SceneStatus",
    "StoryPhase",
    "Beat",
    "BeatType",
    "Conflict",
    "ConflictType",
    "ConflictStakes",
    "ResolutionStatus",
    "Plotline",
    "PlotlineStatus",
    "Foreshadowing",
    "ForeshadowingStatus",
]
