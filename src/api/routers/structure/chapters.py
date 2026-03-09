"""Chapter endpoints for structure router."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    ChapterCreateRequest,
    ChapterHealthReportResponse,
    ChapterListResponse,
    ChapterPacingResponse,
    ChapterResponse,
    ChapterUpdateRequest,
    HealthWarningResponse,
    MoveChapterRequest,
    PacingIssueResponse,
    PhaseDistributionResponse,
    ScenePacingMetricsResponse,
    TensionArcShapeResponse,
    WordCountEstimateResponse,
)
from src.contexts.narrative.application.ports.narrative_repository_port import (
    INarrativeRepository,
)
from src.contexts.narrative.application.services.chapter_analysis_service import (
    ChapterAnalysisService,
)
from src.contexts.narrative.application.services.pacing_service import PacingService
from src.contexts.narrative.domain import Chapter

from .common import (
    _chapter_to_response,
    _get_scenes_by_chapter,
    _parse_uuid,
    get_repository,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


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
        safe_position = int(request.new_order_index)
        logger.info(
            "Moved chapter to position",
            extra={"chapter_id": str(chapter_uuid), "position": safe_position},
        )
        return _chapter_to_response(chapter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    """
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    scenes = _get_scenes_by_chapter(chapter_uuid)

    pacing_service = PacingService()
    result = pacing_service.calculate_chapter_pacing(chapter_uuid, scenes)

    if result.is_error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate chapter pacing: {result.error}",
        )

    report = result.value
    assert report is not None

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


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/health",
    response_model=ChapterHealthReportResponse,
)
async def get_chapter_health(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> ChapterHealthReportResponse:
    """Get structural health analysis for a chapter."""
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    scenes = _get_scenes_by_chapter(chapter_uuid)

    analysis_service = ChapterAnalysisService()
    report = analysis_service.analyze_chapter_structure(chapter_uuid, scenes)

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
