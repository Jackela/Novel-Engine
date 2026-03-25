"""Type definitions for narrative context domain.

This module defines type aliases and constants used throughout
the narrative context domain layer.
"""

from typing import Literal, NewType
from uuid import UUID

# ID Types
StoryId = NewType("StoryId", UUID)
ChapterId = NewType("ChapterId", UUID)
SceneId = NewType("SceneId", UUID)

# Status Types
StoryStatus = Literal["draft", "active", "completed"]

# Genre Types
StoryGenre = Literal[
    "fantasy",
    "sci-fi",
    "mystery",
    "romance",
    "horror",
    "adventure",
    "historical",
    "thriller",
    "comedy",
    "drama",
]

# Scene Types
SceneType = Literal[
    "opening",
    "narrative",
    "dialogue",
    "action",
    "decision",
    "climax",
    "ending",
]
