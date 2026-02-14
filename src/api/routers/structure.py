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

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.schemas import (
    BeatCreateRequest,
    BeatListResponse,
    BeatResponse,
    BeatSuggestionRequest,
    BeatSuggestionResponse,
    BeatUpdateRequest,
    ChapterCreateRequest,
    ChapterHealthReportResponse,
    ChapterListResponse,
    ChapterPacingResponse,
    ChapterResponse,
    ChapterUpdateRequest,
    ConflictCreateRequest,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    CritiqueCategoryScoreResponse,
    CritiqueSceneRequest,
    CritiqueSceneResponse,
    ForeshadowingCreateRequest,
    ForeshadowingListResponse,
    ForeshadowingResponse,
    ForeshadowingUpdateRequest,
    HealthWarningResponse,
    LinkPayoffRequest,
    LinkSceneToPlotlineRequest,
    ManualSmartTagsUpdateRequest,
    MoveChapterRequest,
    MoveSceneRequest,
    PacingIssueResponse,
    PhaseDistributionResponse,
    PlotlineCreateRequest,
    PlotlineListResponse,
    PlotlineResponse,
    PlotlineUpdateRequest,
    ReorderBeatsRequest,
    SceneCreateRequest,
    SceneListResponse,
    ScenePacingMetricsResponse,
    ScenePlotlinesResponse,
    SceneResponse,
    SceneUpdateRequest,
    SetScenePlotlinesRequest,
    SmartTagsResponse,
    StoryCreateRequest,
    StoryListResponse,
    StoryResponse,
    StoryUpdateRequest,
    TensionArcShapeResponse,
    UnlinkSceneFromPlotlineRequest,
    WordCountEstimateResponse,
)
from src.contexts.narrative.application.ports.narrative_repository_port import (
    INarrativeRepository,
)
from src.contexts.narrative.application.services.chapter_analysis_service import (
    ChapterAnalysisService,
)
from src.contexts.narrative.application.services.pacing_service import PacingService
from src.contexts.narrative.domain import (
    Chapter,
    Scene,
    Story,
)
from src.contexts.narrative.domain.entities.beat import Beat, BeatType
from src.contexts.narrative.domain.entities.conflict import (
    Conflict,
    ConflictStakes,
    ConflictType,
    ResolutionStatus,
)
from src.contexts.narrative.domain.entities.foreshadowing import (
    Foreshadowing,
    ForeshadowingStatus,
)
from src.contexts.narrative.domain.entities.plotline import (
    Plotline,
    PlotlineStatus,
)
from src.contexts.narrative.domain.entities.scene import StoryPhase
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
        story_phase=scene.story_phase.value,
        beat_count=len(scene.beats),
        metadata=scene.metadata.copy(),
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


@router.get("/stories/{story_id}/chapters/{chapter_id}", response_model=ChapterResponse)
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

        # Parse story_phase
        story_phase = StoryPhase.SETUP
        if request.story_phase:
            try:
                story_phase = StoryPhase(request.story_phase)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid story_phase: {request.story_phase}. "
                    f"Must be one of: {[p.value for p in StoryPhase]}",
                )

        scene = Scene(
            title=request.title,
            chapter_id=chapter_uuid,
            summary=request.summary,
            location=request.location,
            order_index=order_index,
            story_phase=story_phase,
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
        if request.story_phase is not None:
            valid_phases = [p.value for p in StoryPhase]
            if request.story_phase not in valid_phases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid story_phase: {request.story_phase}. Must be one of {valid_phases}",
                )
            scene.update_story_phase(StoryPhase(request.story_phase))
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


# === Smart Tags Management Routes ===


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}/smart-tags",
    response_model=SmartTagsResponse,
)
async def get_scene_smart_tags(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> SmartTagsResponse:
    """Get smart tags for a scene.

    Returns both auto-generated and manual smart tags.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        repo: Narrative repository (injected).

    Returns:
        Smart tags response with auto, manual, and effective tags.

    Raises:
        HTTPException: If not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)

    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    return SmartTagsResponse(
        smart_tags=scene.get_smart_tags(),
        manual_smart_tags=scene.get_manual_smart_tags(),
        effective_tags=scene.get_effective_smart_tags(),
    )


@router.put(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}/smart-tags/manual",
    response_model=SmartTagsResponse,
)
async def update_scene_manual_smart_tags(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    request: ManualSmartTagsUpdateRequest,
    repo: INarrativeRepository = Depends(get_repository),
) -> SmartTagsResponse:
    """Update manual smart tags for a scene.

    Manual tags are never overridden by auto-tagging.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        request: Manual tags update request.
        repo: Narrative repository (injected).

    Returns:
        Updated smart tags response.

    Raises:
        HTTPException: If not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)

    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    # Get existing manual tags for this category
    existing_manual = scene.get_manual_smart_tags_for_category(request.category)

    if request.replace:
        # Replace entirely
        scene.set_manual_smart_tags(request.category, request.tags)
    else:
        # Append to existing
        combined = existing_manual + request.tags
        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for tag in combined:
            normalized = tag.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(tag)
        scene.set_manual_smart_tags(request.category, unique)

    # Store the updated scene
    _store_scene(scene)
    logger.info("Updated manual smart tags for scene: %s", scene_uuid)

    return SmartTagsResponse(
        smart_tags=scene.get_smart_tags(),
        manual_smart_tags=scene.get_manual_smart_tags(),
        effective_tags=scene.get_effective_smart_tags(),
    )


@router.delete(
    "/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}/smart-tags/manual/{category}",
    status_code=204,
)
async def delete_scene_manual_smart_tags(
    story_id: str,
    chapter_id: str,
    scene_id: str,
    category: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> None:
    """Delete manual smart tags for a specific category.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the parent chapter.
        scene_id: UUID of the scene.
        category: The tag category to clear.
        repo: Narrative repository (injected).

    Raises:
        HTTPException: If not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)

    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    scene.clear_manual_smart_tags(category)
    _store_scene(scene)
    logger.info(
        "Cleared manual smart tags for category %s in scene: %s", category, scene_uuid
    )


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


# ============ Beat Suggestion Endpoint (DIR-048) ============


def _get_llm_generator(request: Request):
    """Get or create the LLM World Generator from app state.

    Why this pattern:
        Centralizes generator access and enables lazy initialization.
        The generator is cached in app.state for reuse across requests.
    """
    from src.contexts.world.infrastructure.generators.llm_world_generator import (
        LLMWorldGenerator,
    )

    generator = getattr(request.app.state, "llm_world_generator", None)
    if generator is None:
        generator = LLMWorldGenerator()
        request.app.state.llm_world_generator = generator
    return generator


@router.post(
    "/scenes/{scene_id}/suggest-beats",
    response_model=BeatSuggestionResponse,
)
async def suggest_beats(
    scene_id: str,
    request: Request,
    payload: BeatSuggestionRequest,
) -> BeatSuggestionResponse:
    """Generate AI beat suggestions for a scene.

    Uses the LLM to suggest 3 possible next beats that could
    logically follow the current beat sequence, considering
    scene context and desired mood trajectory.

    Args:
        scene_id: UUID of the scene.
        payload: Current beats, scene context, and optional mood target.

    Returns:
        Three AI-generated beat suggestions with type, content,
        mood shift, and rationale.
    """
    log = logger.bind(scene_id=scene_id, num_current_beats=len(payload.current_beats))
    log.info("Generating beat suggestions")

    try:
        generator = _get_llm_generator(request)
        result = generator.suggest_next_beats(
            current_beats=payload.current_beats,
            scene_context=payload.scene_context,
            mood_target=payload.mood_target,
        )

        if result.is_error():
            log.warning("Beat suggestion generation failed", error=result.error)
            return BeatSuggestionResponse(
                scene_id=scene_id,
                suggestions=[],
                error=result.error,
            )

        log.info(
            "Beat suggestions generated successfully",
            num_suggestions=len(result.suggestions),
        )
        return BeatSuggestionResponse(
            scene_id=scene_id,
            suggestions=[
                {
                    "beat_type": s.beat_type,
                    "content": s.content,
                    "mood_shift": s.mood_shift,
                    "rationale": s.rationale,
                }
                for s in result.suggestions
            ],
        )
    except Exception as e:
        log.error("Beat suggestion endpoint error", error=str(e))
        return BeatSuggestionResponse(
            scene_id=scene_id,
            suggestions=[],
            error=str(e),
        )


# ============ Scene Critique Endpoint (DIR-058) ============


@router.post(
    "/scenes/{scene_id}/critique",
    response_model=CritiqueSceneResponse,
)
async def critique_scene(
    scene_id: str,
    request: Request,
    payload: CritiqueSceneRequest,
) -> CritiqueSceneResponse:
    """Analyze scene writing quality using AI.

    Provides AI-generated feedback on scene quality across multiple
    craft dimensions: pacing, narrative voice, showing vs. telling,
    and dialogue naturalism. Returns specific, actionable suggestions
    for improvement along with recognition of what works well.

    Args:
        scene_id: UUID of the scene (for logging, not used in lookup).
        payload: Scene text and optional writer's goals.

    Returns:
        CritiqueResult containing overall score (1-10), category-specific
        evaluations (pacing, voice, showing, dialogue), highlights of what
        works, summary assessment, and actionable suggestions.
    """
    log = logger.bind(scene_id=scene_id, text_length=len(payload.scene_text))
    log.info("Generating scene critique")

    try:
        generator = _get_llm_generator(request)
        result = generator.critique_scene(
            scene_text=payload.scene_text,
            scene_goals=payload.scene_goals,
        )

        if result.is_error():
            log.warning("Scene critique generation failed", error=result.error)
            return CritiqueSceneResponse(
                overall_score=1,
                category_scores=[],
                highlights=[],
                summary="Critique failed.",
                error=result.error,
            )

        log.info(
            "Scene critique generated successfully",
            overall_score=result.overall_score,
            num_categories=len(result.category_scores),
        )
        return CritiqueSceneResponse(
            overall_score=result.overall_score,
            category_scores=[
                {
                    "category": cat.category,
                    "score": cat.score,
                    "issues": cat.issues,
                    "suggestions": cat.suggestions,
                }
                for cat in result.category_scores
            ],
            highlights=result.highlights,
            summary=result.summary,
        )
    except Exception as e:
        log.error("Scene critique endpoint error", error=str(e))
        return CritiqueSceneResponse(
            overall_score=1,
            category_scores=[],
            highlights=[],
            summary="An error occurred during critique.",
            error=str(e),
        )


# ============ Pacing Endpoints (DIR-044) ============


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/pacing",
    response_model=ChapterPacingResponse,
)
async def get_chapter_pacing(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterPacingResponse:
    """Get pacing analysis for a chapter.

    Returns tension/energy metrics for each scene in the chapter,
    along with aggregate statistics and detected pacing issues.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter to analyze.
        repo: Narrative repository (injected).

    Returns:
        ChapterPacingResponse with scene-by-scene metrics and issues.

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

    # Get scenes for this chapter
    scenes = _get_scenes_by_chapter(chapter_uuid)

    # Use PacingService for analysis
    pacing_service = PacingService()
    report = pacing_service.calculate_chapter_pacing(chapter_uuid, scenes)

    # Convert to response models
    return ChapterPacingResponse(
        chapter_id=chapter_id,
        scene_metrics=[
            ScenePacingMetricsResponse(
                scene_id=str(m.scene_id),
                scene_title=m.scene_title,
                order_index=m.order_index,
                tension_level=m.tension_level,
                energy_level=m.energy_level,
            )
            for m in report.scene_metrics
        ],
        issues=[
            PacingIssueResponse(
                issue_type=issue.issue_type,
                description=issue.description,
                affected_scenes=[str(sid) for sid in issue.affected_scenes],
                severity=issue.severity,
                suggestion=issue.suggestion,
            )
            for issue in report.issues
        ],
        average_tension=report.average_tension,
        average_energy=report.average_energy,
        tension_range=list(report.tension_range),
        energy_range=list(report.energy_range),
    )


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


def _list_scenes() -> list[Scene]:
    """Get all scenes from storage in deterministic order."""
    from copy import deepcopy

    scenes = [deepcopy(scene) for scene in _scenes.values()]
    return sorted(scenes, key=lambda scene: (scene.chapter_id, scene.order_index))


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


# ============ Conflict Storage (MVP In-Memory) ============
# Note: In production, conflicts would be stored in a repository.
# For MVP, we use module-level storage similar to scenes.

_conflicts: dict[UUID, Conflict] = {}


def _store_conflict(conflict: Conflict) -> None:
    """Store a conflict in the in-memory storage."""
    from copy import deepcopy

    _conflicts[conflict.id] = deepcopy(conflict)


def _get_conflict(conflict_id: UUID) -> Optional[Conflict]:
    """Get a conflict by ID from storage."""
    from copy import deepcopy

    conflict = _conflicts.get(conflict_id)
    return deepcopy(conflict) if conflict else None


def _get_conflicts_by_scene(scene_id: UUID) -> list[Conflict]:
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


def _conflict_to_response(conflict: Conflict) -> ConflictResponse:
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


# ============ Conflict Endpoints (DIR-045) ============


@router.post(
    "/scenes/{scene_id}/conflicts",
    response_model=ConflictResponse,
    status_code=201,
)
async def create_conflict(
    scene_id: str,
    request: ConflictCreateRequest,
) -> ConflictResponse:
    """Create a new conflict in a scene.

    Args:
        scene_id: UUID of the parent scene.
        request: Conflict creation data.

    Returns:
        The created conflict.

    Raises:
        HTTPException: If scene not found or conflict creation fails.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    try:
        # Validate conflict_type
        valid_types = [t.value for t in ConflictType]
        if request.conflict_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid conflict_type: {request.conflict_type}. Must be one of {valid_types}",
            )

        # Validate stakes
        valid_stakes = [s.value for s in ConflictStakes]
        if request.stakes not in valid_stakes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stakes: {request.stakes}. Must be one of {valid_stakes}",
            )

        # Validate resolution_status
        valid_statuses = [s.value for s in ResolutionStatus]
        if request.resolution_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resolution_status: {request.resolution_status}. Must be one of {valid_statuses}",
            )

        conflict = Conflict(
            scene_id=scene_uuid,
            conflict_type=ConflictType(request.conflict_type),
            stakes=ConflictStakes(request.stakes),
            description=request.description,
            resolution_status=ResolutionStatus(request.resolution_status),
        )
        _store_conflict(conflict)

        logger.info("Created conflict: %s in scene: %s", conflict.id, scene_uuid)
        return _conflict_to_response(conflict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/scenes/{scene_id}/conflicts",
    response_model=ConflictListResponse,
)
async def list_conflicts(
    scene_id: str,
) -> ConflictListResponse:
    """List all conflicts in a scene.

    Args:
        scene_id: UUID of the scene.

    Returns:
        List of conflicts for the scene.

    Raises:
        HTTPException: If scene not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflicts = _get_conflicts_by_scene(scene_uuid)

    return ConflictListResponse(
        scene_id=scene_id,
        conflicts=[_conflict_to_response(c) for c in conflicts],
    )


@router.get(
    "/scenes/{scene_id}/conflicts/{conflict_id}",
    response_model=ConflictResponse,
)
async def get_conflict(
    scene_id: str,
    conflict_id: str,
) -> ConflictResponse:
    """Get a conflict by ID.

    Args:
        scene_id: UUID of the parent scene.
        conflict_id: UUID of the conflict.

    Returns:
        The requested conflict.

    Raises:
        HTTPException: If scene or conflict not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    return _conflict_to_response(conflict)


@router.patch(
    "/scenes/{scene_id}/conflicts/{conflict_id}",
    response_model=ConflictResponse,
)
async def update_conflict(
    scene_id: str,
    conflict_id: str,
    request: ConflictUpdateRequest,
) -> ConflictResponse:
    """Update a conflict's properties.

    Args:
        scene_id: UUID of the parent scene.
        conflict_id: UUID of the conflict.
        request: Fields to update.

    Returns:
        The updated conflict.

    Raises:
        HTTPException: If not found or update fails.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    try:
        if request.description is not None:
            conflict.update_description(request.description)

        if request.conflict_type is not None:
            valid_types = [t.value for t in ConflictType]
            if request.conflict_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid conflict_type: {request.conflict_type}. Must be one of {valid_types}",
                )
            conflict.update_conflict_type(ConflictType(request.conflict_type))

        if request.stakes is not None:
            valid_stakes = [s.value for s in ConflictStakes]
            if request.stakes not in valid_stakes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid stakes: {request.stakes}. Must be one of {valid_stakes}",
                )
            conflict.update_stakes(ConflictStakes(request.stakes))

        if request.resolution_status is not None:
            valid_statuses = [s.value for s in ResolutionStatus]
            if request.resolution_status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid resolution_status: {request.resolution_status}. Must be one of {valid_statuses}",
                )
            # Use the appropriate method based on new status
            if request.resolution_status == "escalating":
                conflict.escalate()
            elif request.resolution_status == "resolved":
                conflict.resolve()
            elif request.resolution_status == "unresolved":
                conflict.reopen()

        _store_conflict(conflict)
        logger.info("Updated conflict: %s", conflict_uuid)
        return _conflict_to_response(conflict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/scenes/{scene_id}/conflicts/{conflict_id}",
    status_code=204,
)
async def delete_conflict(
    scene_id: str,
    conflict_id: str,
) -> None:
    """Delete a conflict from a scene.

    Args:
        scene_id: UUID of the parent scene.
        conflict_id: UUID of the conflict.

    Raises:
        HTTPException: If not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    _delete_conflict(conflict_uuid)
    logger.info("Deleted conflict: %s", conflict_uuid)


# ============ Plotline Endpoints (DIR-049) ============

# Note: In production, plotlines would be stored in a repository.
# For MVP, we use module-level storage similar to conflicts.

_plotlines: dict[UUID, Plotline] = {}


def _store_plotline(plotline: Plotline) -> None:
    """Store a plotline in the in-memory storage."""
    from copy import deepcopy

    _plotlines[plotline.id] = deepcopy(plotline)


def _get_plotline(plotline_id: UUID) -> Optional[Plotline]:
    """Get a plotline by ID from storage."""
    from copy import deepcopy

    plotline = _plotlines.get(plotline_id)
    return deepcopy(plotline) if plotline else None


def _list_plotlines() -> list[Plotline]:
    """Get all plotlines from storage."""
    from copy import deepcopy

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


def _plotline_to_response(plotline: Plotline, scene_count: int = 0) -> PlotlineResponse:
    """Convert a Plotline entity to a response model.

    Args:
        plotline: The plotline entity.
        scene_count: Number of scenes linked to this plotline. Defaults to 0.

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


def _count_scenes_for_plotline(plotline_id: UUID) -> int:
    """Count the number of scenes linked to a plotline.

    Args:
        plotline_id: UUID of the plotline.

    Returns:
        Number of scenes that have this plotline in their plotline_ids list.
    """
    count = 0
    for scene in _list_scenes():
        if plotline_id in scene.plotline_ids:
            count += 1
    return count


# ============ Foreshadowing Storage (MVP In-Memory) ============
# Note: In production, foreshadowings would be stored in a repository.
# For MVP, we use module-level storage similar to plotlines.

_foreshadowings: dict[UUID, Foreshadowing] = {}


def _store_foreshadowing(foreshadowing: Foreshadowing) -> None:
    """Store a foreshadowing in the in-memory storage."""
    from copy import deepcopy

    _foreshadowings[foreshadowing.id] = deepcopy(foreshadowing)


def _get_foreshadowing(foreshadowing_id: UUID) -> Optional[Foreshadowing]:
    """Get a foreshadowing by ID from storage."""
    from copy import deepcopy

    foreshadowing = _foreshadowings.get(foreshadowing_id)
    return deepcopy(foreshadowing) if foreshadowing else None


def _list_foreshadowings() -> list[Foreshadowing]:
    """Get all foreshadowings from storage."""
    from copy import deepcopy

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


def _foreshadowing_to_response(foreshadowing: Foreshadowing) -> ForeshadowingResponse:
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


@router.post(
    "/plotlines",
    response_model=PlotlineResponse,
    status_code=201,
)
async def create_plotline(
    request: PlotlineCreateRequest,
) -> PlotlineResponse:
    """Create a new plotline.

    Args:
        request: Plotline creation data.

    Returns:
        The created plotline.

    Raises:
        HTTPException: If plotline creation fails.
    """
    try:
        # Validate status
        valid_statuses = [s.value for s in PlotlineStatus]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Must be one of {valid_statuses}",
            )

        plotline = Plotline(
            name=request.name,
            color=request.color,
            description=request.description,
            status=PlotlineStatus(request.status),
        )

        _store_plotline(plotline)
        logger.info("Created plotline: %s (%s)", plotline.id, plotline.name)

        return _plotline_to_response(plotline, scene_count=0)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create plotline: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create plotline: {str(e)}"
        )


@router.get(
    "/plotlines",
    response_model=PlotlineListResponse,
)
async def list_plotlines() -> PlotlineListResponse:
    """List all plotlines with scene counts.

    Returns:
        List of all plotlines with the number of scenes linked to each.
    """
    plotlines = _list_plotlines()
    scenes = _list_scenes()

    # Build a mapping of plotline_id -> scene count
    scene_counts: dict[UUID, int] = {}
    for scene in scenes:
        for plotline_id in scene.plotline_ids:
            scene_counts[plotline_id] = scene_counts.get(plotline_id, 0) + 1

    return PlotlineListResponse(
        plotlines=[
            _plotline_to_response(p, scene_count=scene_counts.get(p.id, 0))
            for p in plotlines
        ],
    )


@router.get(
    "/plotlines/{plotline_id}",
    response_model=PlotlineResponse,
)
async def get_plotline(
    plotline_id: str,
) -> PlotlineResponse:
    """Get a plotline by ID.

    Args:
        plotline_id: UUID of the plotline.

    Returns:
        The requested plotline.

    Raises:
        HTTPException: If plotline not found.
    """
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    plotline = _get_plotline(plotline_uuid)
    if plotline is None:
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    scene_count = _count_scenes_for_plotline(plotline_uuid)
    return _plotline_to_response(plotline, scene_count=scene_count)


@router.patch(
    "/plotlines/{plotline_id}",
    response_model=PlotlineResponse,
)
async def update_plotline(
    plotline_id: str,
    request: PlotlineUpdateRequest,
) -> PlotlineResponse:
    """Update a plotline's properties.

    Args:
        plotline_id: UUID of the plotline.
        request: Fields to update.

    Returns:
        The updated plotline.

    Raises:
        HTTPException: If not found or update fails.
    """
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    plotline = _get_plotline(plotline_uuid)
    if plotline is None:
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    try:
        if request.name is not None:
            plotline.update_name(request.name)

        if request.color is not None:
            plotline.update_color(request.color)

        if request.description is not None:
            plotline.update_description(request.description)

        if request.status is not None:
            valid_statuses = [s.value for s in PlotlineStatus]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be one of {valid_statuses}",
                )

            # Map status to appropriate method
            if request.status == "resolved":
                plotline.resolve()
            elif request.status == "abandoned":
                plotline.abandon()
            elif request.status == "active":
                plotline.reactivate()

        # Store the updated plotline
        _store_plotline(plotline)
        logger.info("Updated plotline: %s", plotline_uuid)

        scene_count = _count_scenes_for_plotline(plotline_uuid)
        return _plotline_to_response(plotline, scene_count=scene_count)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update plotline: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update plotline: {str(e)}"
        )


@router.delete(
    "/plotlines/{plotline_id}",
    status_code=204,
)
async def delete_plotline(
    plotline_id: str,
) -> None:
    """Delete a plotline.

    Args:
        plotline_id: UUID of the plotline.

    Raises:
        HTTPException: If not found.
    """
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    if not _delete_plotline(plotline_uuid):
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    logger.info("Deleted plotline: %s", plotline_uuid)


@router.post(
    "/scenes/{scene_id}/plotlines",
    response_model=ScenePlotlinesResponse,
)
async def link_scene_to_plotline(
    scene_id: str,
    request: LinkSceneToPlotlineRequest,
) -> ScenePlotlinesResponse:
    """Link a scene to a plotline.

    Args:
        scene_id: UUID of the scene.
        request: Request containing plotline_id to link.

    Returns:
        Updated list of plotline IDs for the scene.

    Raises:
        HTTPException: If scene or plotline not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    plotline_uuid = _parse_uuid(request.plotline_id, "plotline_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    plotline = _get_plotline(plotline_uuid)
    if plotline is None:
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {request.plotline_id}"
        )

    scene.add_plotline(plotline_uuid)
    _store_scene(scene)

    logger.info("Linked scene %s to plotline %s", scene_uuid, plotline_uuid)

    return ScenePlotlinesResponse(
        scene_id=scene_id,
        plotline_ids=[str(pid) for pid in scene.plotline_ids],
    )


@router.delete(
    "/scenes/{scene_id}/plotlines",
    response_model=ScenePlotlinesResponse,
)
async def unlink_scene_from_plotline(
    scene_id: str,
    request: UnlinkSceneFromPlotlineRequest,
) -> ScenePlotlinesResponse:
    """Unlink a scene from a plotline.

    Args:
        scene_id: UUID of the scene.
        request: Request containing plotline_id to unlink.

    Returns:
        Updated list of plotline IDs for the scene.

    Raises:
        HTTPException: If scene not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    plotline_uuid = _parse_uuid(request.plotline_id, "plotline_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    scene.remove_plotline(plotline_uuid)
    _store_scene(scene)

    logger.info("Unlinked scene %s from plotline %s", scene_uuid, plotline_uuid)

    return ScenePlotlinesResponse(
        scene_id=scene_id,
        plotline_ids=[str(pid) for pid in scene.plotline_ids],
    )


@router.put(
    "/scenes/{scene_id}/plotlines",
    response_model=ScenePlotlinesResponse,
)
async def set_scene_plotlines(
    scene_id: str,
    request: SetScenePlotlinesRequest,
) -> ScenePlotlinesResponse:
    """Set all plotlines for a scene.

    Args:
        scene_id: UUID of the scene.
        request: Request containing list of plotline IDs.

    Returns:
        Updated list of plotline IDs for the scene.

    Raises:
        HTTPException: If scene not found or plotline IDs invalid.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    # Validate all plotline IDs
    plotline_uuids = []
    for pid_str in request.plotline_ids:
        try:
            pid = UUID(pid_str)
            # Verify plotline exists
            if _get_plotline(pid) is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Plotline not found: {pid_str}",
                )
            plotline_uuids.append(pid)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plotline ID: {pid_str}",
            )

    scene.set_plotlines(plotline_uuids)
    _store_scene(scene)

    logger.info(
        "Set plotlines for scene %s: %d plotlines", scene_uuid, len(plotline_uuids)
    )

    return ScenePlotlinesResponse(
        scene_id=scene_id,
        plotline_ids=[str(pid) for pid in scene.plotline_ids],
    )


@router.get(
    "/scenes/{scene_id}/plotlines",
    response_model=ScenePlotlinesResponse,
)
async def get_scene_plotlines(
    scene_id: str,
) -> ScenePlotlinesResponse:
    """Get all plotlines for a scene.

    Args:
        scene_id: UUID of the scene.

    Returns:
        List of plotline IDs for the scene.

    Raises:
        HTTPException: If scene not found.
    """
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    return ScenePlotlinesResponse(
        scene_id=scene_id,
        plotline_ids=[str(pid) for pid in scene.plotline_ids],
    )


# ============ Foreshadowing Endpoints (DIR-052) ============


@router.post(
    "/foreshadowings",
    response_model=ForeshadowingResponse,
    status_code=201,
)
async def create_foreshadowing(
    request: ForeshadowingCreateRequest,
) -> ForeshadowingResponse:
    """Create a new foreshadowing.

    Args:
        request: Foreshadowing creation data.

    Returns:
        The created foreshadowing.

    Raises:
        HTTPException: If foreshadowing creation fails or setup scene not found.
    """
    setup_scene_uuid = _parse_uuid(request.setup_scene_id, "setup_scene_id")

    # Verify setup scene exists
    setup_scene = _get_scene(setup_scene_uuid)
    if setup_scene is None:
        raise HTTPException(
            status_code=404, detail=f"Setup scene not found: {request.setup_scene_id}"
        )

    try:
        # Validate status
        valid_statuses = [s.value for s in ForeshadowingStatus]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Must be one of: {valid_statuses}",
            )

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene_uuid,
            description=request.description,
            status=ForeshadowingStatus(request.status),
        )

        _store_foreshadowing(foreshadowing)
        logger.info(
            "Created foreshadowing %s for setup scene %s",
            foreshadowing.id,
            setup_scene_uuid,
        )

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create foreshadowing: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create foreshadowing: {str(e)}"
        )


@router.get(
    "/foreshadowings",
    response_model=ForeshadowingListResponse,
)
async def list_foreshadowings() -> ForeshadowingListResponse:
    """List all foreshadowings.

    Returns:
        List of all foreshadowings.
    """
    foreshadowings = _list_foreshadowings()

    return ForeshadowingListResponse(
        foreshadowings=[_foreshadowing_to_response(f) for f in foreshadowings],
    )


@router.get(
    "/foreshadowings/{foreshadowing_id}",
    response_model=ForeshadowingResponse,
)
async def get_foreshadowing(
    foreshadowing_id: str,
) -> ForeshadowingResponse:
    """Get a foreshadowing by ID.

    Args:
        foreshadowing_id: UUID of the foreshadowing.

    Returns:
        The foreshadowing.

    Raises:
        HTTPException: If foreshadowing not found.
    """
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    return _foreshadowing_to_response(foreshadowing)


@router.put(
    "/foreshadowings/{foreshadowing_id}",
    response_model=ForeshadowingResponse,
)
async def update_foreshadowing(
    foreshadowing_id: str,
    request: ForeshadowingUpdateRequest,
) -> ForeshadowingResponse:
    """Update a foreshadowing.

    Args:
        foreshadowing_id: UUID of the foreshadowing.
        request: Update data.

    Returns:
        The updated foreshadowing.

    Raises:
        HTTPException: If foreshadowing not found or update fails.
    """
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    try:
        # Update description if provided
        if request.description:
            foreshadowing.update_description(request.description)

        # Update status if provided
        if request.status:
            valid_statuses = [s.value for s in ForeshadowingStatus]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be one of: {valid_statuses}",
                )

            if request.status == ForeshadowingStatus.ABANDONED.value:
                foreshadowing.abandon()
            elif request.status == ForeshadowingStatus.PLANTED.value:
                foreshadowing.replant()

        # If payoff_scene_id is provided, validate and link it
        if request.payoff_scene_id:
            payoff_uuid = _parse_uuid(request.payoff_scene_id, "payoff_scene_id")

            # Verify payoff scene exists
            payoff_scene = _get_scene(payoff_uuid)
            if payoff_scene is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Payoff scene not found: {request.payoff_scene_id}",
                )

            # Link payoff with validation
            foreshadowing.link_payoff(payoff_uuid, _get_scene)

        _store_foreshadowing(foreshadowing)
        logger.info("Updated foreshadowing %s", foreshadowing_uuid)

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update foreshadowing %s: %s", foreshadowing_uuid, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update foreshadowing: {str(e)}"
        )


@router.post(
    "/foreshadowings/{foreshadowing_id}/link-payoff",
    response_model=ForeshadowingResponse,
)
async def link_payoff_to_foreshadowing(
    foreshadowing_id: str,
    request: LinkPayoffRequest,
) -> ForeshadowingResponse:
    """Link a payoff scene to a foreshadowing.

    This validates that the payoff scene comes after the setup scene.

    Args:
        foreshadowing_id: UUID of the foreshadowing.
        request: Request containing payoff_scene_id.

    Returns:
        The updated foreshadowing.

    Raises:
        HTTPException: If foreshadowing not found, payoff scene not found,
            or validation fails.
    """
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    payoff_uuid = _parse_uuid(request.payoff_scene_id, "payoff_scene_id")

    # Verify payoff scene exists
    payoff_scene = _get_scene(payoff_uuid)
    if payoff_scene is None:
        raise HTTPException(
            status_code=404, detail=f"Payoff scene not found: {request.payoff_scene_id}"
        )

    try:
        # Link payoff with validation
        foreshadowing.link_payoff(payoff_uuid, _get_scene)

        _store_foreshadowing(foreshadowing)
        logger.info(
            "Linked payoff scene %s to foreshadowing %s",
            payoff_uuid,
            foreshadowing_uuid,
        )

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to link payoff to foreshadowing %s: %s", foreshadowing_uuid, e
        )
        raise HTTPException(status_code=500, detail=f"Failed to link payoff: {str(e)}")


@router.delete(
    "/foreshadowings/{foreshadowing_id}",
    status_code=204,
)
async def delete_foreshadowing(
    foreshadowing_id: str,
) -> None:
    """Delete a foreshadowing.

    Args:
        foreshadowing_id: UUID of the foreshadowing.

    Raises:
        HTTPException: If foreshadowing not found.
    """
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    deleted = _delete_foreshadowing(foreshadowing_uuid)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    logger.info("Deleted foreshadowing %s", foreshadowing_uuid)


# ============ Chapter Analysis Endpoint (DIR-056) ============


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/health",
    response_model=ChapterHealthReportResponse,
)
async def get_chapter_health(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterHealthReportResponse:
    """Get structural health analysis for a chapter.

    Returns comprehensive chapter-level analysis including phase distribution,
    word count estimates, tension arc shape, and detected structural issues.

    Args:
        story_id: UUID of the parent story.
        chapter_id: UUID of the chapter to analyze.
        repo: Narrative repository (injected).

    Returns:
        ChapterHealthReportResponse with complete analysis.

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

    # Get scenes for this chapter
    scenes = _get_scenes_by_chapter(chapter_uuid)

    # Use ChapterAnalysisService for analysis
    analysis_service = ChapterAnalysisService()
    report = analysis_service.analyze_chapter_structure(chapter_uuid, scenes)

    # Convert to response models
    return ChapterHealthReportResponse(
        chapter_id=chapter_id,
        health_score=report.health_score.value,
        phase_distribution=PhaseDistributionResponse(
            setup=report.phase_distribution.setup,
            inciting_incident=report.phase_distribution.inciting_incident,
            rising_action=report.phase_distribution.rising_action,
            climax=report.phase_distribution.climax,
            resolution=report.phase_distribution.resolution,
        ),
        word_count=WordCountEstimateResponse(
            total_words=report.word_count.total_words,
            min_words=report.word_count.min_words,
            max_words=report.word_count.max_words,
            per_scene_average=report.word_count.per_scene_average,
        ),
        total_scenes=report.total_scenes,
        total_beats=report.total_beats,
        tension_arc=TensionArcShapeResponse(
            shape_type=report.tension_arc.shape_type,
            starts_at=report.tension_arc.starts_at,
            peaks_at=report.tension_arc.peaks_at,
            ends_at=report.tension_arc.ends_at,
            has_clear_climax=report.tension_arc.has_clear_climax,
            is_monotonic=report.tension_arc.is_monotonic,
        ),
        warnings=[
            HealthWarningResponse(
                category=w.category.value,
                title=w.title,
                description=w.description,
                severity=w.severity,
                affected_scenes=[str(sid) for sid in w.affected_scenes],
                recommendation=w.recommendation,
            )
            for w in report.warnings
        ],
        recommendations=report.recommendations,
    )
