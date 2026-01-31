"""Narrative Domain Layer.

This module contains the domain entities and value objects for the Narrative
bounded context. These represent the core building blocks for novel/story
structure: stories, chapters, scenes, and beats.

Why this structure:
    The domain layer is pure Python with no external dependencies. This allows
    the business rules to remain isolated and testable without infrastructure
    concerns. The hexagonal architecture principle guides this separation.
"""

from .entities.story import Story, StoryStatus
from .entities.chapter import Chapter, ChapterStatus
from .entities.scene import Scene, SceneStatus
from .entities.beat import Beat, BeatType

__all__ = [
    "Story",
    "StoryStatus",
    "Chapter",
    "ChapterStatus",
    "Scene",
    "SceneStatus",
    "Beat",
    "BeatType",
]
