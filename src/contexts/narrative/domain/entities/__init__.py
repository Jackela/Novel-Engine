"""Narrative Domain Entities Package.

This package contains the core domain entities for story structure:
- Story: The root aggregate for a novel
- Chapter: A container for scenes within a story
"""

from .story import Story, StoryStatus
from .chapter import Chapter, ChapterStatus

__all__ = [
    "Story",
    "StoryStatus",
    "Chapter",
    "ChapterStatus",
]
