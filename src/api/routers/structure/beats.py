"""Beat endpoints for structure router."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    BeatCreateRequest,
    BeatListResponse,
    BeatResponse,
    BeatSuggestionRequest,
    BeatSuggestionResponse,
    BeatUpdateRequest,
    CritiqueSceneRequest,
    CritiqueSceneResponse,
    ReorderBeatsRequest,
)
from src.contexts.narrative.domain.entities.beat import Beat, BeatType

from .common import _beat_to_response, _get_scene, _parse_uuid, _store_scene

if TYPE_CHECKING:
    from src.contexts.world.infrastructure.generators.llm_world_generator import (
        LLMWorldGenerator,
    )

logger = structlog.get_logger(__name__)

router = APIRouter()


def _get_scene_for_beat_ops(scene_id: str) -> "Beat":
    """Get a scene from storage, raising HTTPException if not found."""
    from uuid import UUID

    scene_uuid = UUID(scene_id) if isinstance(scene_id, str) else scene_id
    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    return scene


@router.post("/scenes/{scene_id}/beats", response_model=BeatResponse, status_code=201)
async def create_beat(
    scene_id: str,
    request: BeatCreateRequest,
) -> BeatResponse:
    """Create a new beat in a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    try:
        valid_types = [t.value for t in BeatType]
        if request.beat_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid beat_type: {request.beat_type}. Must be one of {valid_types}",
            )

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


@router.get("/scenes/{scene_id}/beats", response_model=BeatListResponse)
async def list_beats(
    scene_id: str,
) -> BeatListResponse:
    """List all beats in a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    return BeatListResponse(
        scene_id=scene_id,
        beats=[_beat_to_response(b) for b in scene.beats],
    )


@router.get("/scenes/{scene_id}/beats/{beat_id}", response_model=BeatResponse)
async def get_beat(
    scene_id: str,
    beat_id: str,
) -> BeatResponse:
    """Get a beat by ID."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    beat_uuid = _parse_uuid(beat_id, "beat_id")

    scene = _get_scene_for_beat_ops(scene_uuid)
    beat = scene.get_beat(beat_uuid)
    if beat is None:
        raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

    return _beat_to_response(beat)


@router.patch("/scenes/{scene_id}/beats/{beat_id}", response_model=BeatResponse)
async def update_beat(
    scene_id: str,
    beat_id: str,
    request: BeatUpdateRequest,
) -> BeatResponse:
    """Update a beat's properties."""
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


@router.delete("/scenes/{scene_id}/beats/{beat_id}", status_code=204)
async def delete_beat(
    scene_id: str,
    beat_id: str,
) -> None:
    """Delete a beat from a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    beat_uuid = _parse_uuid(beat_id, "beat_id")

    scene = _get_scene_for_beat_ops(scene_uuid)
    if not scene.remove_beat(beat_uuid):
        raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

    _store_scene(scene)
    logger.info("Deleted beat: %s", beat_uuid)


@router.post("/scenes/{scene_id}/beats/reorder", response_model=BeatListResponse)
async def reorder_beats(
    scene_id: str,
    request: ReorderBeatsRequest,
) -> BeatListResponse:
    """Reorder beats within a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene_for_beat_ops(scene_uuid)

    try:
        from uuid import UUID

        beat_uuids = [UUID(bid) for bid in request.beat_ids]
        scene.reorder_beats(beat_uuids)
        _store_scene(scene)

        logger.info("Reordered beats in scene: %s", scene_uuid)
        return BeatListResponse(
            scene_id=scene_id,
            beats=[_beat_to_response(b) for b in scene.beats],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _get_llm_generator(request: Request) -> "LLMWorldGenerator":
    """Get or create the LLM World Generator from app state."""
    from src.contexts.world.infrastructure.generators.llm_world_generator import (
        LLMWorldGenerator,
    )

    generator = getattr(request.app.state, "llm_world_generator", None)
    if generator is None:
        generator = LLMWorldGenerator()
        request.app.state.llm_world_generator = generator
    return generator


@router.post("/scenes/{scene_id}/suggest-beats", response_model=BeatSuggestionResponse)
async def suggest_beats(
    scene_id: str,
    request: Request,
    payload: BeatSuggestionRequest,
) -> BeatSuggestionResponse:
    """Generate AI beat suggestions for a scene."""
    log_extra = {"scene_id": scene_id, "num_current_beats": len(payload.current_beats)}
    logger.info("Generating beat suggestions: %s", log_extra)

    try:
        generator = _get_llm_generator(request)
        result = await generator.suggest_next_beats(
            current_beats=payload.current_beats,
            scene_context=payload.scene_context,
            mood_target=payload.mood_target,
        )

        if result.is_error():
            logger.warning("Beat suggestion generation failed: %s", result.error)
            return BeatSuggestionResponse(
                scene_id=scene_id,
                suggestions=[],
                error=str(result.error),
            )

        logger.info(
            "Beat suggestions generated successfully: num_suggestions=%d",
            len(result.suggestions),
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
        logger.error("Beat suggestion endpoint error: %s", str(e))
        return BeatSuggestionResponse(
            scene_id=scene_id,
            suggestions=[],
            error=str(e),
        )


@router.post("/scenes/{scene_id}/critique", response_model=CritiqueSceneResponse)
async def critique_scene(
    scene_id: str,
    request: Request,
    payload: CritiqueSceneRequest,
) -> CritiqueSceneResponse:
    """Analyze scene writing quality using AI."""
    log_extra = {"scene_id": scene_id, "text_length": len(payload.scene_text)}
    logger.info("Generating scene critique: %s", log_extra)

    try:
        generator = _get_llm_generator(request)
        result = generator.critique_scene(
            scene_text=payload.scene_text,
            scene_goals=payload.scene_goals,
        )

        if result.is_error():
            logger.warning("Scene critique generation failed: %s", result.error)
            return CritiqueSceneResponse(
                overall_score=1,
                category_scores=[],
                highlights=[],
                summary="Critique failed.",
                error=str(result.error),
            )

        logger.info(
            "Scene critique generated successfully: overall_score=%d num_categories=%d",
            result.overall_score,
            len(result.category_scores),
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
        logger.error("Scene critique endpoint error: %s", str(e))
        return CritiqueSceneResponse(
            overall_score=1,
            category_scores=[],
            highlights=[],
            summary="An error occurred during critique.",
            error=str(e),
        )
