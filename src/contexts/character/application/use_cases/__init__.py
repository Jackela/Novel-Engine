"""Character use cases package.

This package contains use cases for character memory management,
including storing, recalling, and summarizing character memories.
"""

from __future__ import annotations

from .recall_character_memories import (
    RecallCharacterMemoriesRequest,
    RecallCharacterMemoriesResponse,
    RecallCharacterMemoriesUseCase,
)
from .remember_character_event import (
    RememberCharacterEventRequest,
    RememberCharacterEventResponse,
    RememberCharacterEventUseCase,
)
from .summarize_character_arc import (
    SummarizeCharacterArcRequest,
    SummarizeCharacterArcResponse,
    SummarizeCharacterArcUseCase,
)

__all__ = [
    # Remember
    "RememberCharacterEventRequest",
    "RememberCharacterEventResponse",
    "RememberCharacterEventUseCase",
    # Recall
    "RecallCharacterMemoriesRequest",
    "RecallCharacterMemoriesResponse",
    "RecallCharacterMemoriesUseCase",
    # Summarize
    "SummarizeCharacterArcRequest",
    "SummarizeCharacterArcResponse",
    "SummarizeCharacterArcUseCase",
]
