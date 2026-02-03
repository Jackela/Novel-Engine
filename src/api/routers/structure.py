"""Structure router for narrative outline management.

Provides CRUD endpoints for managing Story, Chapter, and Scene entities.
This router enables the Outliner UI to create, read, update, delete,
and reorder narrative structure elements.

Why this router:
    The Structure API serves as the backend for the narrative outliner sidebar,
    allowing users to organize their story hierarchy before or during writing.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    BeatCreateRequest,
    BeatListResponse,
    BeatResponse,
    BeatUpdateRequest,
    ChapterCreateRequest,
    ChapterListResponse,
    ChapterResponse,
    ChapterUpdateRequest,
    MoveChapterRequest,
    MoveSceneRequest,
    ReorderBeatsRequest,
    SceneCreateRequest,
    SceneListResponse,
    SceneResponse,
    SceneUpdateRequest,
    StoryCreateRequest,
    StoryListResponse,
    StoryResponse,
    StoryUpdateRequest,
)
from src.contexts.narrative.application.ports.narrative_repository_port import (
    INarrativeRepository,
)
from src.contexts.narrative.domain import (
    Chapter,
    Scene,
    Story,
)
from src.contexts.narrative.domain.entities.beat import Beat, BeatType
from src.contexts.narrative.infrastructure.repositories.in_memory_narrative_repository import (
    InMemoryNarrativeRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/structure", tags=["structure"])

# Module-level repository instance for development/testing
# In production, this would be injected via dependency injection
_repository: Optional[INarrativeRepository] = None


def get_repository() -> INarrativeRepository:
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


def _story_to_response(story: Story) -> StoryResponse:
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


def _chapter_to_response(chapter: Chapter, scene_count: int = 0) -> ChapterResponse:
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


def _scene_to_response(scene: Scene) -> SceneResponse:
    """Convert a Scene entity to a response model."""
    return SceneResponse(
        id=str(scene.id),
        chapter_id=str(scene.chapter_id),
        title=scene.title,
        summary=scene.summary,
        location=scene.location,
        order_index=scene.order_index,
        status=scene.status.value,
        beat_count=len(scene.beats),
        created_at=scene.created_at.isoformat(),
        updated_at=scene.updated_at.isoformat(),
    )


def _beat_to_response(beat: Beat) -> BeatResponse:
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


# ============ Story Endpoints ============


@router.post("/stories", response_model=StoryResponse, status_code=201)
async def create_story(
    request: StoryCreateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> StoryResponse:
    """Create a new story.

    Args:
        request: Story creation data.
        repo: Narrative repository (injected).

    Returns:
        The created story.

    Raises:
        HTTPException: If story creation fails.
    """
    try:
        story = Story(title=request.title, summary=request.summary)
        repo.save(story)
        logger.info("Created story: %s", story.id)
        return _story_to_response(story)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stories", response_model=StoryListResponse)
async def list_stories(
    repo: INarrativeRepository = Depends(get_repository),
) -> StoryListResponse:
    """List all stories.

    Returns:
        List of all stories sorted by creation time.
    """
    stories = repo.list_all()
    return StoryListResponse(stories=[_story_to_response(s) for s in stories])


@router.get("/stories/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> StoryResponse:
    """Get a story by ID.

    Args:
        story_id: UUID of the story.
        repo: Narrative repository (injected).

    Returns:
        The requested story.

    Raises:
        HTTPException: If story not found.
    """
    uuid = _parse_uuid(story_id, "story_id")
    story = repo.get_by_id(uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")
    return _story_to_response(story)


@router.patch("/stories/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: str,
    request: StoryUpdateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> StoryResponse:
    """Update a story's properties.

    Args:
        story_id: UUID of the story.
        request: Fields to update.
        repo: Narrative repository (injected).

    Returns:
        The updated story.

    Raises:
        HTTPException: If story not found or update fails.
    """
    uuid = _parse_uuid(story_id, "story_id")
    story = repo.get_by_id(uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    try:
        if request.title is not None:
            story.update_title(request.title)
        if request.summary is not None:
            story.update_summary(request.summary)
        if request.status is not None:
            if request.status == "published":
                story.publish()
            elif request.status == "draft":
                story.unpublish()
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be 'draft' or 'published'",
                )

        repo.save(story)
        logger.info("Updated story: %s", story.id)
        return _story_to_response(story)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/stories/{story_id}", status_code=204)
async def delete_story(
    story_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> None:
    """Delete a story and all its contents.

    Args:
        story_id: UUID of the story.
        repo: Narrative repository (injected).

    Raises:
        HTTPException: If story not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    if not repo.delete(story_uuid):
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")
    logger.info("Deleted story: %s", story_uuid)


# ============ Chapter Endpoints ============


@router.post(
    "/stories/{story_id}/chapters", response_model=ChapterResponse, status_code=201
)
async def create_chapter(
    story_id: str,
    request: ChapterCreateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterResponse:
    """Create a new chapter in a story.

    Args:
        story_id: UUID of the parent story.
        request: Chapter creation data.
        repo: Narrative repository (injected).

    Returns:
        The created chapter.

    Raises:
        HTTPException: If story not found or chapter creation fails.
    """
    uuid = _parse_uuid(story_id, "story_id")
    story = repo.get_by_id(uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    try:
        # Determine order_index
        order_index = request.order_index
        if order_index is None:
            order_index = story.chapter_count

        chapter = Chapter(
            title=request.title,
            story_id=uuid,
            summary=request.summary,
            order_index=order_index,
        )
        story.add_chapter(chapter)
        repo.save(story)
        logger.info("Created chapter: %s in story: %s", chapter.id, uuid)
        return _chapter_to_response(chapter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stories/{story_id}/chapters", response_model=ChapterListResponse)
async def list_chapters(
    story_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterListResponse:
    """List all chapters in a story.

    Args:
        story_id: UUID of the story.
        repo: Narrative repository (injected).

    Returns:
        List of chapters sorted by order_index.

    Raises:
        HTTPException: If story not found.
    """
    uuid = _parse_uuid(story_id, "story_id")
    story = repo.get_by_id(uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    return ChapterListResponse(
        story_id=story_id,
        chapters=[_chapter_to_response(c) for c in story.chapters],
    )


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}", response_model=ChapterResponse
)
async def get_chapter(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterResponse:
    """Get a chapter by ID.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter.
        repo: Narrative repository (injected).

    Returns:
        The requested chapter.

    Raises:
        HTTPException: If story or chapter not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    return _chapter_to_response(chapter)


@router.patch(
    "/stories/{story_id}/chapters/{chapter_id}", response_model=ChapterResponse
)
async def update_chapter(
    story_id: str,
    chapter_id: str,
    request: ChapterUpdateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterResponse:
    """Update a chapter's properties.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter.
        request: Fields to update.
        repo: Narrative repository (injected).

    Returns:
        The updated chapter.

    Raises:
        HTTPException: If story/chapter not found or update fails.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    try:
        if request.title is not None:
            chapter.update_title(request.title)
        if request.summary is not None:
            chapter.update_summary(request.summary)
        if request.status is not None:
            if request.status == "published":
                chapter.publish()
            elif request.status == "draft":
                chapter.unpublish()
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be 'draft' or 'published'",
                )

        repo.save(story)
        logger.info("Updated chapter: %s", chapter_uuid)
        return _chapter_to_response(chapter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/stories/{story_id}/chapters/{chapter_id}", status_code=204)
async def delete_chapter(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> None:
    """Delete a chapter from a story.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter.
        repo: Narrative repository (injected).

    Raises:
        HTTPException: If story or chapter not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    removed = story.remove_chapter(chapter_uuid)
    if removed is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    repo.save(story)
    logger.info("Deleted chapter: %s", chapter_uuid)


@router.post(
    "/stories/{story_id}/chapters/{chapter_id}/move", response_model=ChapterResponse
)
async def move_chapter(
    story_id: str,
    chapter_id: str,
    request: MoveChapterRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterResponse:
    """Move a chapter to a new position within the story.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter.
        request: New position data.
        repo: Narrative repository (injected).

    Returns:
        The moved chapter with updated order_index.

    Raises:
        HTTPException: If story/chapter not found or move fails.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    try:
        chapter.move_to_position(request.new_order_index)
        repo.save(story)
        # chapter_uuid is already a validated UUID from _parse_uuid
        safe_position = int(request.new_order_index)
        logger.info(
            "Moved chapter to position",
            extra={"chapter_id": str(chapter_uuid), "position": safe_position},
        )
        return _chapter_to_response(chapter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Scene Endpoints ============


@router.post(
    "/stories/{story_id}/chapters/{chapter_id}/scenes",
    response_model=SceneResponse,
    status_code=201,
)
async def create_scene(
    story_id: str,
    chapter_id: str,
    request: SceneCreateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneResponse:
    """Create a new scene in a chapter.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        request: Scene creation data.
        repo: Narrative repository (injected).

    Returns:
        The created scene.

    Raises:
        HTTPException: If story/chapter not found or scene creation fails.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    try:
        # Determine order_index (Scenes are stored in a separate structure)
        # For MVP, we'll track scenes in a module-level dict
        order_index = request.order_index if request.order_index is not None else 0

        scene = Scene(
            title=request.title,
            chapter_id=chapter_uuid,
            summary=request.summary,
            location=request.location,
            order_index=order_index,
        )

        # Store scene (for MVP, using module-level storage)
        _store_scene(scene)

        repo.save(story)
        logger.info("Created scene: %s in chapter: %s", scene.id, chapter_uuid)
        return _scene_to_response(scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/scenes",
    response_model=SceneListResponse,
)
async def list_scenes(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneListResponse:
    """List all scenes in a chapter.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        repo: Narrative repository (injected).

    Returns:
        List of scenes sorted by order_index.

    Raises:
        HTTPException: If story or chapter not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    # Get scenes from module-level storage
    scenes = _get_scenes_by_chapter(chapter_uuid)

    return SceneListResponse(
        chapter_id=chapter_id,
        scenes=[_scene_to_response(s) for s in scenes],
    )


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}",
    response_model=SceneResponse,
)
async def get_scene(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneResponse:
    """Get a scene by ID.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        repo: Narrative repository (injected).

    Returns:
        The requested scene.

    Raises:
        HTTPException: If story, chapter, or scene not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    scene = _get_scene(scene_uuid)
    if scene is None or scene.chapter_id != chapter_uuid:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    return _scene_to_response(scene)


@router.patch(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}",
    response_model=SceneResponse,
)
async def update_scene(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    request: SceneUpdateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneResponse:
    """Update a scene's properties.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        request: Fields to update.
        repo: Narrative repository (injected).

    Returns:
        The updated scene.

    Raises:
        HTTPException: If not found or update fails.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    scene = _get_scene(scene_uuid)
    if scene is None or scene.chapter_id != chapter_uuid:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    try:
        if request.title is not None:
            scene.update_title(request.title)
        if request.summary is not None:
            scene.update_summary(request.summary)
        if request.location is not None:
            scene.update_location(request.location)
        if request.status is not None:
            valid_statuses = ["draft", "generating", "review", "published"]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be one of {valid_statuses}",
                )
            if request.status == "published":
                scene.publish()
            elif request.status == "draft":
                scene.unpublish()
            elif request.status == "generating":
                scene.start_generation()
            elif request.status == "review":
                scene.complete_generation()

        _store_scene(scene)
        logger.info("Updated scene: %s", scene_uuid)
        return _scene_to_response(scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}", status_code=204
)
async def delete_scene(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> None:
    """Delete a scene from a chapter.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        repo: Narrative repository (injected).

    Raises:
        HTTPException: If not found.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    if not _delete_scene(scene_uuid):
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    logger.info("Deleted scene: %s", scene_uuid)


@router.post(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}/move",
    response_model=SceneResponse,
)
async def move_scene(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    request: MoveSceneRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneResponse:
    """Move a scene to a new position, optionally to a different chapter.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the current chapter.
        scene_id: UUID of the scene.
        request: Move destination data.
        repo: Narrative repository (injected).

    Returns:
        The moved scene with updated position.

    Raises:
        HTTPException: If not found or move fails.
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    # Validate source chapter exists
    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    scene = _get_scene(scene_uuid)
    if scene is None or scene.chapter_id != chapter_uuid:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    try:
        # If moving to a different chapter
        if request.target_chapter_id is not None:
            target_uuid = _parse_uuid(request.target_chapter_id, "target_chapter_id")
            target_chapter = story.get_chapter(target_uuid)
            if target_chapter is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Target chapter not found: {request.target_chapter_id}",
                )
            # Update scene's chapter reference
            scene.chapter_id = target_uuid

        scene.move_to_position(request.new_order_index)
        _store_scene(scene)
        # scene_uuid is already a validated UUID from _parse_uuid
        safe_position = int(request.new_order_index)
        logger.info(
            "Moved scene to position",
            extra={"scene_id": str(scene_uuid), "position": safe_position},
        )
        return _scene_to_response(scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Beat Endpoints (DIR-042) ============


def _get_scene_for_beat_ops(scene_id: UUID) -> Scene:
    """Get a scene from storage, raising HTTPException if not found.

    Why this helper:
        Beat operations need to work directly with scenes. This helper
        simplifies the repeated pattern of fetching and validating scenes.
    """
    scene = _get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    return scene


@router.post(
    "/scenes/{scene_id}/beats",
    response_model=BeatResponse,
    status_code=201,
)
async def create_beat(
    scene_id: str,
    request: BeatCreateRequest,
) -> BeatResponse:
    """Create a new beat in a scene.

    Args:
        scene_id: UUID of the parent scene.
        request: Beat creation data.

    Returns:
        The created beat.

    Raises:
        HTTPException: If scene not found or beat creation fails.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    try:
        # Validate beat_type
        valid_types = [t.value for t in BeatType]
        if request.beat_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid beat_type: {request.beat_type}. Must be one of {valid_types}",
            )

        # Determine order_index
        order_index = request.order_index
        if order_index is None:
            order_index = len(scene.beats)

        beat = Beat(
            scene_id=scene_uuid,
            content=request.content,
            beat_type=BeatType(request.beat_type),
            mood_shift=request.mood_shift,
            order_index=order_index,
        )
        scene.add_beat(beat)
        _store_scene(scene)

        logger.info("Created beat: %s in scene: %s", beat.id, scene_uuid)
        return _beat_to_response(beat)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/scenes/{scene_id}/beats",
    response_model=BeatListResponse,
)
async def list_beats(
    scene_id: str,
) -> BeatListResponse:
    """List all beats in a scene.

    Args:
        scene_id: UUID of the scene.

    Returns:
        List of beats sorted by order_index.

    Raises:
        HTTPException: If scene not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    return BeatListResponse(
        scene_id=scene_id,
        beats=[_beat_to_response(b) for b in scene.beats],
    )


@router.get(
    "/scenes/{scene_id}/beats/{beat_id}",
    response_model=BeatResponse,
)
async def get_beat(
    scene_id: str,
    beat_id: str,
) -> BeatResponse:
    """Get a beat by ID.

    Args:
        scene_id: UUID of the parent scene.
        beat_id: UUID of the beat.

    Returns:
        The requested beat.

    Raises:
        HTTPException: If scene or beat not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    beat_uuid = _parse_uuid(beat_id, "beat_id")

    scene = _get_scene_for_beat_ops(scene_uuid)
    beat = scene.get_beat(beat_uuid)
    if beat is None:
        raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

    return _beat_to_response(beat)


@router.patch(
    "/scenes/{scene_id}/beats/{beat_id}",
    response_model=BeatResponse,
)
async def update_beat(
    scene_id: str,
    beat_id: str,
    request: BeatUpdateRequest,
) -> BeatResponse:
    """Update a beat's properties.

    Args:
        scene_id: UUID of the parent scene.
        beat_id: UUID of the beat.
        request: Fields to update.

    Returns:
        The updated beat.

    Raises:
        HTTPException: If not found or update fails.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    beat_uuid = _parse_uuid(beat_id, "beat_id")

    scene = _get_scene_for_beat_ops(scene_uuid)
    beat = scene.get_beat(beat_uuid)
    if beat is None:
        raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

    try:
        if request.content is not None:
            beat.update_content(request.content)
        if request.beat_type is not None:
            valid_types = [t.value for t in BeatType]
            if request.beat_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid beat_type: {request.beat_type}. Must be one of {valid_types}",
                )
            beat.change_type(BeatType(request.beat_type))
        if request.mood_shift is not None:
            beat.update_mood_shift(request.mood_shift)

        _store_scene(scene)
        logger.info("Updated beat: %s", beat_uuid)
        return _beat_to_response(beat)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/scenes/{scene_id}/beats/{beat_id}",
    status_code=204,
)
async def delete_beat(
    scene_id: str,
    beat_id: str,
) -> None:
    """Delete a beat from a scene.

    Args:
        scene_id: UUID of the parent scene.
        beat_id: UUID of the beat.

    Raises:
        HTTPException: If not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    beat_uuid = _parse_uuid(beat_id, "beat_id")

    scene = _get_scene_for_beat_ops(scene_uuid)
    if not scene.remove_beat(beat_uuid):
        raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

    _store_scene(scene)
    logger.info("Deleted beat: %s", beat_uuid)


@router.post(
    "/scenes/{scene_id}/beats/reorder",
    response_model=BeatListResponse,
)
async def reorder_beats(
    scene_id: str,
    request: ReorderBeatsRequest,
) -> BeatListResponse:
    """Reorder beats within a scene.

    Args:
        scene_id: UUID of the scene.
        request: List of beat IDs in desired order.

    Returns:
        Updated list of beats in new order.

    Raises:
        HTTPException: If scene not found or beat IDs don't match.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    try:
        # Parse and validate all beat UUIDs
        beat_uuids = [_parse_uuid(bid, "beat_id") for bid in request.beat_ids]
        scene.reorder_beats(beat_uuids)
        _store_scene(scene)

        logger.info("Reordered beats in scene: %s", scene_uuid)
        return BeatListResponse(
            scene_id=scene_id,
            beats=[_beat_to_response(b) for b in scene.beats],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Scene Storage (MVP In-Memory) ============
# Note: In production, scenes would be stored in the repository alongside stories.
# For MVP, we use module-level storage to avoid modifying the repository interface.

_scenes: dict[UUID, Scene] = {}


def _store_scene(scene: Scene) -> None:
    """Store a scene in the in-memory storage."""
    from copy import deepcopy

    _scenes[scene.id] = deepcopy(scene)


def _get_scene(scene_id: UUID) -> Optional[Scene]:
    """Get a scene by ID from storage."""
    from copy import deepcopy

    scene = _scenes.get(scene_id)
    return deepcopy(scene) if scene else None


def _get_scenes_by_chapter(chapter_id: UUID) -> list[Scene]:
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
