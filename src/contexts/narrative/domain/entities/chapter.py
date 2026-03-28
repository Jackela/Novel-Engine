"""
Chapter Entity

Represents a chapter within a story. Chapters contain multiple scenes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.types import ChapterId, SceneType
from src.shared.domain.base.entity import Entity


@dataclass(kw_only=True, eq=False)
class Chapter(Entity[ChapterId]):
    """
    A chapter in a story.

    AI注意:
    - Chapters organize the narrative into major sections
    - Each chapter has multiple scenes
    - Chapter order determines narrative flow
    """

    story_id: str
    chapter_number: int
    title: str
    summary: Optional[str] = None
    scenes: List[Scene] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate chapter invariants.

        Required by Entity base class.
        """
        if not self.story_id:
            raise ValueError("Chapter must belong to a story")

        if self.chapter_number < 1:
            raise ValueError("Chapter number must be positive")

        if not self.title or len(self.title.strip()) == 0:
            raise ValueError("Chapter title cannot be empty")

        if len(self.title) > 200:
            raise ValueError("Chapter title cannot exceed 200 characters")

    @property
    def scene_count(self) -> int:
        """Return the number of scenes in this chapter."""
        return len(self.scenes)

    @property
    def is_first_chapter(self) -> bool:
        """Check if this is the first chapter."""
        return self.chapter_number == 1

    @property
    def current_scene(self) -> Optional[Scene]:
        """Get the current/active scene in this chapter."""
        if not self.scenes:
            return None
        # Return the last scene (most recent)
        return self.scenes[-1]

    def add_scene(
        self,
        content: str,
        scene_type: SceneType = "narrative",
        title: Optional[str] = None,
    ) -> Scene:
        """
        Add a new scene to this chapter.

        Args:
            content: Scene narrative content
            scene_type: Type of scene (narrative, dialogue, action, etc.)
            title: Optional scene title

        Returns:
            The newly created scene
        """
        if len(self.scenes) >= 20:
            raise ValueError("Chapter cannot have more than 20 scenes")

        scene = Scene(
            chapter_id=str(self.id),
            scene_number=len(self.scenes) + 1,
            title=title,
            content=content,
            scene_type=scene_type,
        )

        self.scenes.append(scene)
        self.updated_at = datetime.utcnow()

        return scene

    def get_scene(self, scene_number: int) -> Optional[Scene]:
        """Get a scene by its number."""
        for scene in self.scenes:
            if scene.scene_number == scene_number:
                return scene
        return None

    def reorder_scenes(self, new_order: List[int]) -> None:
        """
        Reorder scenes within this chapter.

        Args:
            new_order: List of scene numbers in desired order
        """
        if len(new_order) != len(self.scenes):
            raise ValueError("New order must include all scenes")

        scene_map = {s.scene_number: s for s in self.scenes}

        if set(new_order) != set(scene_map.keys()):
            raise ValueError("New order contains invalid scene numbers")

        self.scenes = [scene_map[num] for num in new_order]

        # Update scene numbers
        for i, scene in enumerate(self.scenes, 1):
            scene.scene_number = i

        self.updated_at = datetime.utcnow()

    def remove_scene(self, scene_number: int) -> None:
        """Remove a scene from this chapter."""
        self.scenes = [s for s in self.scenes if s.scene_number != scene_number]

        # Renumber remaining scenes
        for i, scene in enumerate(self.scenes, 1):
            scene.scene_number = i

        self.updated_at = datetime.utcnow()

    def update_title(self, new_title: str) -> None:
        """Update chapter title."""
        if not new_title or len(new_title.strip()) == 0:
            raise ValueError("Title cannot be empty")

        if len(new_title) > 200:
            raise ValueError("Title too long")

        self.title = new_title
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert chapter to dictionary for serialization."""
        return {
            "id": str(self.id),
            "story_id": self.story_id,
            "chapter_number": self.chapter_number,
            "title": self.title,
            "summary": self.summary,
            "scenes": [s.to_dict() for s in self.scenes],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
