"""Story workflow routes for the canonical API."""

# mypy: disable-error-code=misc

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from src.apps.api.dependencies import (
    WorkspacePrincipal,
    get_workspace_principal,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.types import StoryGenre
from src.contexts.narrative.infrastructure.runtime import get_story_workflow_service
from src.shared.application.result import Failure, Success

router = APIRouter(prefix="/story", tags=["story"])


class StoryCreateRequest(BaseModel):
    """Request payload for creating a story draft."""

    model_config = ConfigDict(extra="allow")

    title: str = Field(..., min_length=1, max_length=200)
    genre: StoryGenre
    premise: str = Field(..., min_length=10, max_length=5000)
    target_chapters: int = Field(default=12, ge=1, le=Story.MAX_CHAPTERS)
    target_audience: str | None = Field(default=None, max_length=120)
    themes: list[str] = Field(default_factory=list)
    tone: str = Field(default="commercial web fiction", max_length=200)


class StoryPipelineRequest(StoryCreateRequest):
    """Request payload for the full generation pipeline."""

    publish: bool = Field(default=True)


class StoryDraftRequest(BaseModel):
    """Request payload for chapter drafting."""

    target_chapters: int | None = Field(
        default=None,
        ge=1,
        le=Story.MAX_CHAPTERS,
    )


class StoryRunRequest(BaseModel):
    """Request payload for executing a run against an existing story."""

    operation: Literal[
        "blueprint",
        "outline",
        "draft",
        "review",
        "revise",
        "export",
        "publish",
        "pipeline",
    ] = Field(default="pipeline")
    target_chapters: int | None = Field(
        default=None,
        ge=1,
        le=Story.MAX_CHAPTERS,
    )
    publish: bool = Field(default=False)


def _failure_status(code: str) -> int:
    failure_statuses: dict[str, int] = {
        "NOT_FOUND": int(status.HTTP_404_NOT_FOUND),
        "VALIDATION_ERROR": int(status.HTTP_400_BAD_REQUEST),
        "MISSING_BLUEPRINT": int(status.HTTP_400_BAD_REQUEST),
        "MISSING_OUTLINE": int(status.HTTP_400_BAD_REQUEST),
        "GENERATION_ERROR": int(status.HTTP_502_BAD_GATEWAY),
        "QUALITY_GATE_FAILED": int(status.HTTP_422_UNPROCESSABLE_ENTITY),
        "CONFIG_ERROR": int(status.HTTP_500_INTERNAL_SERVER_ERROR),
        "INTERNAL_ERROR": int(status.HTTP_500_INTERNAL_SERVER_ERROR),
    }
    return failure_statuses.get(code, status.HTTP_400_BAD_REQUEST)


def _unwrap(result: Success[dict[str, Any]] | Failure) -> dict[str, Any]:
    if isinstance(result, Failure):
        detail = result.value
        code = detail.get("code", "ERROR") if isinstance(detail, dict) else "ERROR"
        raise HTTPException(status_code=_failure_status(code), detail=detail)
    payload = result.value
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story workflow returned an invalid payload",
        )
    return payload


def _require_principal(
    principal: WorkspacePrincipal | None,
) -> WorkspacePrincipal:
    if principal is not None:
        return principal
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication or guest workspace is required",
    )


def _requested_author_id(payload: StoryCreateRequest) -> str | None:
    author_id = payload.model_extra.get("author_id") if payload.model_extra else None
    if isinstance(author_id, str) and author_id.strip():
        return author_id.strip()
    return None


def _resolve_author_id(
    payload: StoryCreateRequest,
    principal: WorkspacePrincipal | None,
) -> str:
    resolved_principal = _require_principal(principal)
    requested_author_id = _requested_author_id(payload)
    if (
        requested_author_id is not None
        and requested_author_id != resolved_principal.workspace_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="author_id cannot be set for another workspace",
        )
    return resolved_principal.workspace_id


async def _authorize_story_access(
    *,
    story_id: str,
    principal: WorkspacePrincipal | None,
    service: StoryWorkflowService,
) -> dict[str, Any]:
    resolved_principal = _require_principal(principal)
    payload = _unwrap(await service.get_story(story_id))
    story = payload.get("story")
    if not isinstance(story, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story workflow returned an invalid story payload",
        )
    if story.get("author_id") != resolved_principal.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return payload


@router.get("")
async def list_stories(
    author_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """List stories owned by the current principal."""
    resolved_principal = _require_principal(principal)
    if author_id is not None and author_id.strip() != resolved_principal.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="author_id cannot be set for another workspace",
        )

    result = await service.list_stories(
        limit=limit,
        offset=offset,
        author_id=resolved_principal.workspace_id,
    )
    return _unwrap(result)


@router.get("/{story_id}")
async def get_story(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Return a single story snapshot."""
    return await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )


@router.get("/{story_id}/workspace")
async def get_story_workspace(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Return the aggregated author workspace payload for a story."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.get_story_workspace(story_id))


@router.get("/{story_id}/runs")
async def get_story_runs(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Return run history and append-only events for a story."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.get_story_runs(story_id))


@router.get("/{story_id}/runs/{run_id}")
async def get_story_run(
    story_id: str,
    run_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Return a single run with its scoped events and artifacts."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.get_story_run(story_id, run_id))


@router.get("/{story_id}/artifacts")
async def get_story_artifacts(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Return current artifacts and append-only artifact history for a story."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.get_story_artifacts(story_id))


@router.post("")
async def create_story(
    payload: StoryCreateRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Create a new draft story."""
    author_id = _resolve_author_id(payload, principal)
    result = await service.create_story(
        title=payload.title,
        genre=payload.genre,
        author_id=author_id,
        premise=payload.premise,
        target_chapters=payload.target_chapters,
        target_audience=payload.target_audience,
        themes=payload.themes,
        tone=payload.tone,
    )
    return _unwrap(result)


@router.post("/{story_id}/blueprint")
async def generate_blueprint(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Generate the world and character bible."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.generate_blueprint(story_id))


@router.post("/{story_id}/outline")
async def generate_outline(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Generate the chapter outline."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.generate_outline(story_id))


@router.post("/{story_id}/draft")
async def draft_story(
    story_id: str,
    payload: StoryDraftRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Draft missing chapters and scenes."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(
        await service.draft_story(
            story_id,
            target_chapters=payload.target_chapters,
        )
    )


@router.post("/{story_id}/review")
async def review_story(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Run the story quality review."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.review_story(story_id))


@router.post("/{story_id}/revise")
async def revise_story(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Run the revision pass and repair continuity issues."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.revise_story(story_id))


@router.post("/{story_id}/export")
async def export_story(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Export a serialisable story snapshot."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.export_story(story_id))


@router.post("/{story_id}/publish")
async def publish_story(
    story_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Publish the story if it passes the quality gate."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(await service.publish_story(story_id))


@router.post("/{story_id}/runs")
async def execute_story_run(
    story_id: str,
    payload: StoryRunRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Execute a workflow run against an existing story."""
    await _authorize_story_access(
        story_id=story_id,
        principal=principal,
        service=service,
    )
    return _unwrap(
        await service.execute_story_run(
            story_id,
            operation=payload.operation,
            target_chapters=payload.target_chapters,
            publish=payload.publish,
        )
    )


@router.post("/pipeline")
async def run_pipeline(
    payload: StoryPipelineRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
    service: StoryWorkflowService = Depends(get_story_workflow_service),
) -> dict[str, Any]:
    """Run the full long-form story generation pipeline."""
    author_id = _resolve_author_id(payload, principal)
    result = await service.run_pipeline(
        title=payload.title,
        genre=payload.genre,
        author_id=author_id,
        premise=payload.premise,
        target_chapters=payload.target_chapters,
        target_audience=payload.target_audience,
        themes=payload.themes,
        tone=payload.tone,
        publish=payload.publish,
    )
    return _unwrap(result)
