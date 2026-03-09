"""Common utilities and storage for structure routers.

This module provides shared functionality used across all structure
router modules, including repository access, UUID parsing, and
in-memory storage for MVP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

import structlog
from fastapi import HTTPException

if TYPE_CHECKING:
    from src.contexts.narrative.application.ports.narrative_repository_port import (
        INarrativeRepository,
    )
    from src.contexts.narrative.domain import Chapter, Scene, Story
    from src.contexts.narrative.domain.entities.beat import Beat
    from src.contexts.narrative.domain.entities.conflict import Conflict
    from src.contexts.narrative.domain.entities.foreshadowing import Foreshadowing
    from src.contexts.narrative.domain.entities.plotline import Plotline

from src.api.schemas import (
    BeatResponse,
    ChapterResponse,
    ConflictResponse,
    ForeshadowingResponse,
    PlotlineResponse,
    SceneResponse,
    StoryResponse,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_narrative_repository import (
    InMemoryNarrativeRepository,
)

logger = structlog.get_logger(__name__)

# Module-level repository instance for development/testing
_repository: Optional[INarrativeRepository] = None

# In-Memory storage for MVP (production would use database)
_scenes: dict[UUID, "Scene"] = {}
_conflicts: dict[UUID, "Conflict"] = {}
_plotlines: dict[UUID, "Plotline"] = {}
_foreshadowings: dict[UUID, "Foreshadowing"] = {}


def get_repository() -> "INarrativeRepository":
    """Dependency that provides the narrative repository.

    Why this pattern:
        Centralizes repository access and enables easy swapping between
        in-memory (testing) and persistent (production) implementations.
    """
    global _repository
    if _repository is None:
        _repository = InMemoryNarrativeRepository()
    return _repository


def _parse_uuid(value: str, field_name: str = "id") -> UUID:
    """Parse and validate a UUID string.

    Args:
        value: String to parse as UUID.
        field_name: Name of the field for error messages.

    Returns:
        Parsed UUID.

    Raises:
        HTTPException: If the string is not a valid UUID.
    """
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {value}")


# ============ Response Converters ============


def _story_to_response(story: "Story") -> StoryResponse:
    """Convert a Story entity to a response model.

    Why this conversion:
        Separates the internal domain model from the API contract,
        allowing them to evolve independently.
    """
    return StoryResponse(
        id=str(story.id),
        title=story.title,
        summary=story.summary,
        status=story.status.value,
        chapter_count=story.chapter_count,
        created_at=story.created_at.isoformat(),
        updated_at=story.updated_at.isoformat(),
    )


def _chapter_to_response(chapter: "Chapter", scene_count: int = 0) -> ChapterResponse:
    """Convert a Chapter entity to a response model."""
    return ChapterResponse(
        id=str(chapter.id),
        story_id=str(chapter.story_id),
        title=chapter.title,
        summary=chapter.summary,
        order_index=chapter.order_index,
        status=chapter.status.value,
        scene_count=scene_count,
        created_at=chapter.created_at.isoformat(),
        updated_at=chapter.updated_at.isoformat(),
    )


def _scene_to_response(scene: "Scene") -> SceneResponse:
    """Convert a Scene entity to a response model."""
    return SceneResponse(
        id=str(scene.id),
        chapter_id=str(scene.chapter_id),
        title=scene.title,
        summary=scene.summary,
        location=scene.location,
        order_index=scene.order_index,
        status=scene.status.value,
        story_phase=scene.story_phase.value,
        beat_count=len(scene.beats),
        metadata=scene.metadata.copy(),
        created_at=scene.created_at.isoformat(),
        updated_at=scene.updated_at.isoformat(),
    )


def _beat_to_response(beat: "Beat") -> BeatResponse:
    """Convert a Beat entity to a response model."""
    return BeatResponse(
        id=str(beat.id),
        scene_id=str(beat.scene_id),
        content=beat.content,
        beat_type=beat.beat_type.value,
        mood_shift=beat.mood_shift,
        order_index=beat.order_index,
        created_at=beat.created_at.isoformat(),
        updated_at=beat.updated_at.isoformat(),
    )


def _conflict_to_response(conflict: "Conflict") -> ConflictResponse:
    """Convert a Conflict entity to a response model."""
    return ConflictResponse(
        id=str(conflict.id),
        scene_id=str(conflict.scene_id),
        conflict_type=conflict.conflict_type.value,
        stakes=conflict.stakes.value,
        description=conflict.description,
        resolution_status=conflict.resolution_status.value,
        created_at=conflict.created_at.isoformat(),
        updated_at=conflict.updated_at.isoformat(),
    )


def _plotline_to_response(
    plotline: "Plotline", scene_count: int = 0
) -> PlotlineResponse:
    """Convert a Plotline entity to a response model.

    Args:
        plotline: The plotline entity.
        scene_count: Number of scenes linked to this plotline.

    Returns:
        A PlotlineResponse with scene count included.
    """
    return PlotlineResponse(
        id=str(plotline.id),
        name=plotline.name,
        color=plotline.color,
        description=plotline.description,
        status=plotline.status.value,
        scene_count=scene_count,
        created_at=plotline.created_at.isoformat(),
        updated_at=plotline.updated_at.isoformat(),
    )


def _foreshadowing_to_response(
    foreshadowing: "Foreshadowing",
) -> ForeshadowingResponse:
    """Convert a Foreshadowing entity to a response model."""
    return ForeshadowingResponse(
        id=str(foreshadowing.id),
        setup_scene_id=str(foreshadowing.setup_scene_id),
        payoff_scene_id=(
            str(foreshadowing.payoff_scene_id)
            if foreshadowing.payoff_scene_id
            else None
        ),
        description=foreshadowing.description,
        status=foreshadowing.status.value,
        created_at=foreshadowing.created_at.isoformat(),
        updated_at=foreshadowing.updated_at.isoformat(),
    )


# ============ Scene Storage ============


def _store_scene(scene: "Scene") -> None:
    """Store a scene in the in-memory storage."""
    from copy import deepcopy

    _scenes[scene.id] = deepcopy(scene)


def _get_scene(scene_id: UUID) -> Optional["Scene"]:
    """Get a scene by ID from storage."""
    from copy import deepcopy

    scene = _scenes.get(scene_id)
    return deepcopy(scene) if scene else None


def _list_scenes() -> list["Scene"]:
    """Get all scenes from storage in deterministic order."""
    from copy import deepcopy

    scenes = [deepcopy(scene) for scene in _scenes.values()]
    return sorted(scenes, key=lambda scene: (scene.chapter_id, scene.order_index))


def _get_scenes_by_chapter(chapter_id: UUID) -> list["Scene"]:
    """Get all scenes for a chapter, sorted by order_index."""
    from copy import deepcopy

    scenes = [deepcopy(s) for s in _scenes.values() if s.chapter_id == chapter_id]
    return sorted(scenes, key=lambda s: s.order_index)


def _delete_scene(scene_id: UUID) -> bool:
    """Delete a scene from storage. Returns True if deleted."""
    if scene_id in _scenes:
        del _scenes[scene_id]
        return True
    return False


def reset_scene_storage() -> None:
    """Reset scene storage. Useful for testing."""
    _scenes.clear()


# ============ Conflict Storage ============


def _store_conflict(conflict: "Conflict") -> None:
    """Store a conflict in the in-memory storage."""
    from copy import deepcopy

    _conflicts[conflict.id] = deepcopy(conflict)


def _get_conflict(conflict_id: UUID) -> Optional["Conflict"]:
    """Get a conflict by ID from storage."""
    from copy import deepcopy

    conflict = _conflicts.get(conflict_id)
    return deepcopy(conflict) if conflict else None


def _get_conflicts_by_scene(scene_id: UUID) -> list["Conflict"]:
    """Get all conflicts for a scene."""
    from copy import deepcopy

    conflicts = [deepcopy(c) for c in _conflicts.values() if c.scene_id == scene_id]
    return sorted(conflicts, key=lambda c: c.created_at)


def _delete_conflict(conflict_id: UUID) -> bool:
    """Delete a conflict from storage. Returns True if deleted."""
    if conflict_id in _conflicts:
        del _conflicts[conflict_id]
        return True
    return False


def reset_conflict_storage() -> None:
    """Reset conflict storage. Useful for testing."""
    _conflicts.clear()


# ============ Plotline Storage ============


def _store_plotline(plotline: "Plotline") -> None:
    """Store a plotline in the in-memory storage."""
    from copy import deepcopy

    _plotlines[plotline.id] = deepcopy(plotline)


def _get_plotline(plotline_id: UUID) -> Optional["Plotline"]:
    """Get a plotline by ID from storage."""
    from copy import deepcopy

    plotline = _plotlines.get(plotline_id)
    return deepcopy(plotline) if plotline else None


def _list_plotlines() -> list["Plotline"]:
    """Get all plotlines from storage."""
    plotlines = list(_plotlines.values())
    return sorted(plotlines, key=lambda p: p.created_at, reverse=True)


def _delete_plotline(plotline_id: UUID) -> bool:
    """Delete a plotline from storage. Returns True if deleted."""
    if plotline_id in _plotlines:
        del _plotlines[plotline_id]
        return True
    return False


def reset_plotline_storage() -> None:
    """Reset plotline storage. Useful for testing."""
    _plotlines.clear()


def _count_scenes_for_plotline(plotline_id: UUID) -> int:
    """Count the number of scenes linked to a plotline."""
    count = 0
    for scene in _list_scenes():
        if plotline_id in scene.plotline_ids:
            count += 1
    return count


# ============ Foreshadowing Storage ============


def _store_foreshadowing(foreshadowing: "Foreshadowing") -> None:
    """Store a foreshadowing in the in-memory storage."""
    from copy import deepcopy

    _foreshadowings[foreshadowing.id] = deepcopy(foreshadowing)


def _get_foreshadowing(foreshadowing_id: UUID) -> Optional["Foreshadowing"]:
    """Get a foreshadowing by ID from storage."""
    from copy import deepcopy

    foreshadowing = _foreshadowings.get(foreshadowing_id)
    return deepcopy(foreshadowing) if foreshadowing else None


def _list_foreshadowings() -> list["Foreshadowing"]:
    """Get all foreshadowings from storage."""
    foreshadowings = list(_foreshadowings.values())
    return sorted(foreshadowings, key=lambda f: f.created_at, reverse=True)


def _delete_foreshadowing(foreshadowing_id: UUID) -> bool:
    """Delete a foreshadowing from storage. Returns True if deleted."""
    if foreshadowing_id in _foreshadowings:
        del _foreshadowings[foreshadowing_id]
        return True
    return False


def reset_foreshadowing_storage() -> None:
    """Reset foreshadowing storage. Useful for testing."""
    _foreshadowings.clear()
