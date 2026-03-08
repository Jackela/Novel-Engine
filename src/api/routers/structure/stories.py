"""Story endpoints for structure router."""

from __future__ import annotations

import structlog

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    StoryCreateRequest,
    StoryListResponse,
    StoryResponse,
    StoryUpdateRequest,
)
from src.contexts.narrative.application.ports.narrative_repository_port import (
    INarrativeRepository,
)
from src.contexts.narrative.domain import Story

from .common import _parse_uuid, _story_to_response, get_repository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/stories")


@router.post("", response_model=StoryResponse, status_code=201)
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


@router.get("", response_model=StoryListResponse)
async def list_stories(
    repo: INarrativeRepository = Depends(get_repository),
) -> StoryListResponse:
    """List all stories.

    Returns:
        List of all stories sorted by creation time.
    """
    stories = repo.list_all()
    return StoryListResponse(stories=[_story_to_response(s) for s in stories])


@router.get("/{story_id}", response_model=StoryResponse)
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


@router.patch("/{story_id}", response_model=StoryResponse)
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


@router.delete("/{story_id}", status_code=204)
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
