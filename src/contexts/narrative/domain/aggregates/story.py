"""
Story Aggregate Root

The Story is the main aggregate root for the narrative context.
It contains chapters, manages the narrative flow, and enforces business rules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, cast

from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.events.story_events import (
    ChapterAdded,
    StoryCompleted,
    StoryCreated,
    StoryPublished,
)
from src.contexts.narrative.domain.types import StoryStatus
from src.shared.domain.base.aggregate import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Story(AggregateRoot):
    """
    A story is the main aggregate root for the narrative.

    AI注意:
    - Stories contain chapters, which contain scenes
    - Stories have a lifecycle: draft -> active -> completed
    - Long-form stories need a materially higher chapter cap than the old demo
    - Only one chapter can be active at a time
    """

    MAX_CHAPTERS: ClassVar[int] = 120

    title: str
    genre: str
    author_id: str
    status: StoryStatus = field(default="draft")
    chapters: List[Chapter] = field(default_factory=list)
    current_chapter_id: Optional[str] = None
    target_audience: Optional[str] = None
    themes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate story invariants."""
        super().__post_init__()

        if not self.title or len(self.title.strip()) == 0:
            raise ValueError("Story title cannot be empty")

        if len(self.title) > 200:
            raise ValueError("Story title cannot exceed 200 characters")

        if not self.author_id:
            raise ValueError("Story must have an author")

        # Validate genre
        valid_genres = {
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
        }
        if self.genre not in valid_genres:
            raise ValueError(f"Invalid genre: {self.genre}")

        # Emit creation event on first initialization
        if not self._domain_events:
            self.add_event(
                StoryCreated(
                    aggregate_id=str(self.id),
                    title=self.title,
                    genre=self.genre,
                    author_id=self.author_id,
                    target_audience=self.target_audience,
                    themes=self.themes,
                )
            )

    @property
    def chapter_count(self) -> int:
        """Return the number of chapters in this story."""
        return len(self.chapters)

    @property
    def current_chapter(self) -> Optional[Chapter]:
        """Get the currently active chapter."""
        if not self.current_chapter_id:
            return None

        for chapter in self.chapters:
            if str(chapter.id) == self.current_chapter_id:
                return chapter

        return None

    @property
    def is_published(self) -> bool:
        """Check if the story is published (active or completed)."""
        status_value = cast(str, self.status)
        return status_value == "active" or status_value == "completed"

    @property
    def is_completed(self) -> bool:
        """Check if the story is completed."""
        return cast(str, self.status) == "completed"

    def add_chapter(self, title: str, summary: Optional[str] = None) -> Chapter:
        """
        Add a new chapter to the story.

        Args:
            title: Chapter title
            summary: Optional chapter summary

        Returns:
            The newly created chapter

        Raises:
            ValueError: If maximum chapters reached or story is completed
        """
        if self.is_completed:
            raise ValueError("Cannot add chapters to a completed story")

        if len(self.chapters) >= self.MAX_CHAPTERS:
            raise ValueError(f"Story cannot have more than {self.MAX_CHAPTERS} chapters")

        chapter = Chapter(
            story_id=str(self.id),
            chapter_number=len(self.chapters) + 1,
            title=title,
            summary=summary,
        )

        self.chapters.append(chapter)
        self.current_chapter_id = str(chapter.id)
        self.updated_at = datetime.utcnow()

        # Emit event
        self.add_event(
            ChapterAdded(
                aggregate_id=str(self.id),
                chapter_id=str(chapter.id),
                chapter_number=chapter.chapter_number,
                title=title,
            )
        )

        return chapter

    def publish(self) -> None:
        """
        Publish the story, making it active.

        Raises:
            ValueError: If story doesn't meet publishing criteria
        """
        if self.status != "draft":
            raise ValueError("Only draft stories can be published")

        if len(self.chapters) == 0:
            raise ValueError("Story must have at least one chapter to be published")

        # Check first chapter has at least one scene
        first_chapter = self.chapters[0]
        if first_chapter.scene_count == 0:
            raise ValueError("First chapter must have at least one scene")

        if any(chapter.scene_count == 0 for chapter in self.chapters):
            raise ValueError(
                "Every chapter must have at least one scene before publishing"
            )

        self.status = "active"
        self.updated_at = datetime.utcnow()

        self.add_event(
            StoryPublished(
                aggregate_id=str(self.id),
            )
        )

    def complete(self) -> None:
        """
        Mark the story as completed.

        Raises:
            ValueError: If story is not active
        """
        if self.status != "active":
            raise ValueError("Only active stories can be completed")

        self.status = "completed"
        self.updated_at = datetime.utcnow()

        self.add_event(
            StoryCompleted(
                aggregate_id=str(self.id),
                final_chapter_id=self.current_chapter_id,
            )
        )

    def switch_chapter(self, chapter_number: int) -> Chapter:
        """
        Switch to a different chapter.

        Args:
            chapter_number: The chapter number to switch to

        Returns:
            The selected chapter
        """
        for chapter in self.chapters:
            if chapter.chapter_number == chapter_number:
                self.current_chapter_id = str(chapter.id)
                self.updated_at = datetime.utcnow()
                return chapter

        raise ValueError(f"Chapter {chapter_number} not found")

    def get_chapter(self, chapter_number: int) -> Optional[Chapter]:
        """Get a chapter by its number."""
        for chapter in self.chapters:
            if chapter.chapter_number == chapter_number:
                return chapter
        return None

    def update_metadata(self, key: str, value: Any) -> None:
        """Update story metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert story to dictionary for serialization."""
        return {
            "id": str(self.id),
            "title": self.title,
            "genre": self.genre,
            "author_id": self.author_id,
            "status": self.status,
            "chapters": [c.to_dict() for c in self.chapters],
            "chapter_count": self.chapter_count,
            "current_chapter_id": self.current_chapter_id,
            "target_audience": self.target_audience,
            "themes": self.themes,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
