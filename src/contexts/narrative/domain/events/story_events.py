"""Story domain events.

This module defines all domain events related to the Story aggregate.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.shared.domain.base.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class StoryCreated(DomainEvent):
    """Event fired when a new story is created."""

    event_type: str = "story.created"
    title: str = ""
    genre: str = ""
    author_id: str = ""
    target_audience: Optional[str] = None
    themes: List[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class StoryPublished(DomainEvent):
    """Event fired when a story is published."""

    event_type: str = "story.published"


@dataclass(frozen=True, kw_only=True)
class StoryCompleted(DomainEvent):
    """Event fired when a story is marked as completed."""

    event_type: str = "story.completed"
    final_chapter_id: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class ChapterAdded(DomainEvent):
    """Event fired when a chapter is added to a story."""

    event_type: str = "story.chapter_added"
    chapter_id: str = ""
    chapter_number: int = 0
    title: str = ""


@dataclass(frozen=True, kw_only=True)
class StoryUpdated(DomainEvent):
    """Event fired when story metadata is updated."""

    event_type: str = "story.updated"
    changes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class StoryDeleted(DomainEvent):
    """Event fired when a story is deleted."""

    event_type: str = "story.deleted"
    author_id: str = ""
