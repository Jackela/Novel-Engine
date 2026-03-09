"""Scene endpoints for structure router."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    LinkSceneToPlotlineRequest,
    ManualSmartTagsUpdateRequest,
    MoveSceneRequest,
    SceneCreateRequest,
    SceneListResponse,
    ScenePlotlinesResponse,
    SceneResponse,
    SceneUpdateRequest,
    SetScenePlotlinesRequest,
    SmartTagsResponse,
    UnlinkSceneFromPlotlineRequest,
)
from src.contexts.narrative.application.ports.narrative_repository_port import (
    INarrativeRepository,
)
from src.contexts.narrative.domain.entities.scene import Scene, StoryPhase

from .common import (
    _delete_scene,
    _get_plotline,
    _get_scene,
    _get_scenes_by_chapter,
    _parse_uuid,
    _scene_to_response,
    _store_scene,
    get_repository,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


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
    """Create a new scene in a chapter."""
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

    try:
        order_index = request.order_index if request.order_index is not None else 0

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

        _store_scene(scene)
        repo.save(story)
        logger.info("Created scene: %s in chapter: %s", scene.id, chapter_uuid)
        return _scene_to_response(scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/stories/{story_id}/chapters/{chapter_id}/scenes", response_model=SceneListResponse
)
async def list_scenes(
    story_id: str,
    chapter_id: str,
    repo: INarrativeRepository = Depends(get_repository),
) -> SceneListResponse:
    """List all scenes in a chapter."""
    story_uuid = _parse_uuid(story_id, "story_id")
    chapter_uuid = _parse_uuid(chapter_id, "chapter_id")

    story = repo.get_by_id(story_uuid)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")

    chapter = story.get_chapter(chapter_uuid)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

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
    """Get a scene by ID."""
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
    """Update a scene's properties."""
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
    """Delete a scene from a chapter."""
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
    """Get smart tags for a scene."""
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
    """Update manual smart tags for a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)

    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    existing_manual = scene.get_manual_smart_tags_for_category(request.category)

    if request.replace:
        scene.set_manual_smart_tags(request.category, request.tags)
    else:
        combined = existing_manual + request.tags
        seen: set[str] = set()
        unique: list[str] = []
        for tag in combined:
            normalized = tag.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(tag)
        scene.set_manual_smart_tags(request.category, unique)

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
    """Delete manual smart tags for a specific category."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)

    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    scene.clear_manual_smart_tags(category)
    _store_scene(scene)
    logger.info(
        "cleared_manual_smart_tags: category=%s scene_uuid=%s",
        category,
        str(scene_uuid),
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
    """Move a scene to a new position, optionally to a different chapter."""
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
        if request.target_chapter_id is not None:
            target_uuid = _parse_uuid(request.target_chapter_id, "target_chapter_id")
            target_chapter = story.get_chapter(target_uuid)
            if target_chapter is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Target chapter not found: {request.target_chapter_id}",
                )
            scene.chapter_id = target_uuid

        scene.move_to_position(request.new_order_index)
        _store_scene(scene)
        safe_position = int(request.new_order_index)
        logger.info(
            "Moved scene to position",
            extra={"scene_id": str(scene_uuid), "position": safe_position},
        )
        return _scene_to_response(scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Plotline link endpoints on scenes


@router.post("/scenes/{scene_id}/plotlines", response_model=ScenePlotlinesResponse)
async def link_scene_to_plotline(
    scene_id: str,
    request: LinkSceneToPlotlineRequest,
) -> ScenePlotlinesResponse:
    """Link a scene to a plotline."""
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


@router.delete("/scenes/{scene_id}/plotlines", response_model=ScenePlotlinesResponse)
async def unlink_scene_from_plotline(
    scene_id: str,
    request: UnlinkSceneFromPlotlineRequest,
) -> ScenePlotlinesResponse:
    """Unlink a scene from a plotline."""
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


@router.put("/scenes/{scene_id}/plotlines", response_model=ScenePlotlinesResponse)
async def set_scene_plotlines(
    scene_id: str,
    request: SetScenePlotlinesRequest,
) -> ScenePlotlinesResponse:
    """Set all plotlines for a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    from uuid import UUID

    plotline_uuids: list[Any] = []
    for pid_str in request.plotline_ids:
        try:
            pid = UUID(pid_str)
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


@router.get("/scenes/{scene_id}/plotlines", response_model=ScenePlotlinesResponse)
async def get_scene_plotlines(
    scene_id: str,
) -> ScenePlotlinesResponse:
    """Get all plotlines for a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    return ScenePlotlinesResponse(
        scene_id=scene_id,
        plotline_ids=[str(pid) for pid in scene.plotline_ids],
    )
