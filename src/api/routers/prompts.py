"""
Prompt Management API Router

Warzone 4: AI Brain - BRAIN-015
REST API for managing prompt templates.

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from src.api.schemas import (
    PromptCreateRequest,
    PromptDetailResponse,
    PromptListResponse,
    PromptModelConfig,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptSummary,
    PromptUpdateRequest,
    PromptVariableValue,
)
from src.api.services.prompt_router_service import PromptRouterService
from src.contexts.knowledge.application.ports.i_prompt_repository import (
    PromptNotFoundError,
    PromptRepositoryError,
    PromptValidationError,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prompts"])


def get_prompt_repository(request: Request) -> InMemoryPromptRepository:
    """
    Get or create the prompt repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The prompt repository instance
    """
    repository = getattr(request.app.state, "prompt_repository", None)
    if repository is None:
        repository = InMemoryPromptRepository()
        request.app.state.prompt_repository = repository
        logger.info("Initialized InMemoryPromptRepository")
    return repository


def get_prompt_service(
    repository: InMemoryPromptRepository = Depends(get_prompt_repository),
) -> PromptRouterService:
    """
    Get the prompt router service.

    Why: Dependency injection for testability.

    Args:
        repository: The prompt repository

    Returns:
        PromptRouterService instance
    """
    return PromptRouterService(repository)


# ==================== Query/List Endpoints ====================


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    request: Request,
    response: Response,
    tags: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptListResponse:
    """
    List all prompt templates with optional filtering.

    Why: Provides discovery and browsing of available prompts.

    Args:
        request: FastAPI request
        response: FastAPI response (for cache headers)
        tags: Comma-separated filter by tags
        model: Filter by model name
        limit: Maximum number of results
        offset: Number of results to skip
        service: Prompt router service

    Returns:
        List of prompt summaries
    """
    try:
        # Parse tags filter
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        # Build model filter tags
        if model:
            model_tags = [f"model:{model}"]
            tag_list = (tag_list or []) + model_tags

        prompts = await service.list_prompts(
            tags=tag_list,
            limit=limit,
            offset=offset,
        )

        total = await service.count_prompts()

        return PromptListResponse(
            prompts=[service.to_summary(p) for p in prompts],
            total=total,
            limit=limit,
            offset=offset,
        )

    except PromptRepositoryError as e:
        logger.error(f"Failed to list prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts/search", response_model=PromptListResponse)
async def search_prompts(
    query: str,
    request: Request,
    limit: int = 20,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptListResponse:
    """
    Search prompt templates by name or description.

    Why: Enables quick lookup of specific prompts.

    Args:
        query: Search query string
        request: FastAPI request
        limit: Maximum number of results
        service: Prompt router service

    Returns:
        List of matching prompt summaries
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        prompts = await service.search_prompts(query.strip(), limit=limit)

        return PromptListResponse(
            prompts=[service.to_summary(p) for p in prompts],
            total=len(prompts),
            limit=limit,
            offset=0,
        )

    except PromptRepositoryError as e:
        logger.error(f"Failed to search prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts/tags", response_model=dict[str, list[str]])
async def list_prompt_tags(
    service: PromptRouterService = Depends(get_prompt_service),
) -> dict[str, list[str]]:
    """
    List all unique tags across all prompt templates.

    Why: Provides tag values for filtering UI.

    Args:
        service: Prompt router service

    Returns:
        Dictionary with tag categories and their values
    """
    try:
        return await service.get_all_tags()
    except PromptRepositoryError as e:
        logger.error(f"Failed to list tags: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts/health", response_model=dict[str, Any])
async def prompts_health(
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> dict[str, Any]:
    """
    Health check for the prompt management system.

    Why: Verify repository is accessible and count templates.

    NOTE: This route must be defined BEFORE /prompts/{prompt_id}
          to avoid 'health' being captured as a prompt_id.

    Args:
        request: FastAPI request
        service: Prompt router service

    Returns:
        Health status information
    """
    try:
        count = await service.count_prompts()
        return {
            "status": "healthy",
            "repository_type": "InMemoryPromptRepository",
            "total_prompts": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except PromptRepositoryError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ==================== CRUD Endpoints ====================


@router.post("/prompts", response_model=PromptDetailResponse, status_code=201)
async def create_prompt(
    payload: PromptCreateRequest,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptDetailResponse:
    """
    Create a new prompt template.

    Why: Allows users to define custom prompts.

    Args:
        payload: Prompt creation request
        request: FastAPI request
        service: Prompt router service

    Returns:
        Created prompt detail
    """
    try:
        # Build variable definitions
        variables = tuple(
            VariableDefinition(
                name=v.name,
                type=VariableType(v.type),
                default_value=v.default_value,
                description=v.description or "",
                required=v.required,
            )
            for v in (payload.variables or [])
        )

        # Build model config - use defaults when None is provided
        model_config = ModelConfig(
            provider=payload.model_provider or "openai",
            model_name=payload.model_name or "gpt-4",
            temperature=payload.temperature if payload.temperature is not None else 0.7,
            max_tokens=payload.max_tokens if payload.max_tokens is not None else 1000,
            top_p=payload.top_p if payload.top_p is not None else 1.0,
            frequency_penalty=payload.frequency_penalty if payload.frequency_penalty is not None else 0.0,
            presence_penalty=payload.presence_penalty if payload.presence_penalty is not None else 0.0,
        )

        # Create template
        template = PromptTemplate(
            id=str(uuid4()),
            name=payload.name,
            content=payload.content,
            variables=variables,
            model_config=model_config,
            tags=tuple(payload.tags or []),
            description=payload.description or "",
        )

        template_id = await service.save_prompt(template)

        # Fetch the saved template
        saved = await service.get_prompt_by_id(template_id)

        return service.to_detail(saved)

    except (ValueError, PromptValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to create prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt(
    prompt_id: str,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptDetailResponse:
    """
    Get a specific prompt template by ID.

    Why: Retrieve full prompt details for editing or viewing.

    Args:
        prompt_id: Prompt template ID
        request: FastAPI request
        service: Prompt router service

    Returns:
        Prompt detail response
    """
    try:
        template = await service.get_prompt_by_id(prompt_id)
        return service.to_detail(template)

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to get prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/prompts/{prompt_id}", response_model=PromptDetailResponse)
async def update_prompt(
    prompt_id: str,
    payload: PromptUpdateRequest,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptDetailResponse:
    """
    Update a prompt template (creates a new version).

    Why: Version tracking allows safe modifications and rollback.

    Args:
        prompt_id: ID of the prompt to update
        payload: Update request fields
        request: FastAPI request
        service: Prompt router service

    Returns:
        New version of the prompt
    """
    try:
        # Get existing template
        existing = await service.get_prompt_by_id(prompt_id)

        # Build updated variables
        variables = existing.variables
        if payload.variables is not None:
            variables = tuple(
                VariableDefinition(
                    name=v.name,
                    type=VariableType(v.type),
                    default_value=v.default_value,
                    description=v.description or "",
                    required=v.required,
                )
                for v in payload.variables
            )

        # Build updated model config
        model_config = existing.model_config
        if any(
            [
                payload.model_provider is not None,
                payload.model_name is not None,
                payload.temperature is not None,
                payload.max_tokens is not None,
                payload.top_p is not None,
                payload.frequency_penalty is not None,
                payload.presence_penalty is not None,
            ]
        ):
            model_config = ModelConfig(
                provider=payload.model_provider or existing.model_config.provider,
                model_name=payload.model_name or existing.model_config.model_name,
                temperature=payload.temperature
                if payload.temperature is not None
                else existing.model_config.temperature,
                max_tokens=payload.max_tokens
                if payload.max_tokens is not None
                else existing.model_config.max_tokens,
                top_p=payload.top_p
                if payload.top_p is not None
                else existing.model_config.top_p,
                frequency_penalty=payload.frequency_penalty
                if payload.frequency_penalty is not None
                else existing.model_config.frequency_penalty,
                presence_penalty=payload.presence_penalty
                if payload.presence_penalty is not None
                else existing.model_config.presence_penalty,
            )

        # Create new version
        new_template = existing.create_new_version(
            content=payload.content if payload.content is not None else None,
            variables=variables,
            model_config=model_config,
            name=payload.name if payload.name is not None else None,
            description=payload.description
            if payload.description is not None
            else None,
            tags=tuple(payload.tags) if payload.tags is not None else None,
        )

        new_id = await service.save_prompt(new_template)

        # Fetch the saved template
        saved = await service.get_prompt_by_id(new_id)

        return service.to_detail(saved)

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, PromptValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to update prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/prompts/{prompt_id}", status_code=204, response_class=Response)
async def delete_prompt(
    prompt_id: str,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> Response:
    """
    Archive (soft delete) a prompt template.

    Why: Soft delete preserves history and allows recovery.

    Args:
        prompt_id: ID of the prompt to delete
        request: FastAPI request
        service: Prompt router service

    Returns:
        204 No Content on success
    """
    try:
        deleted = await service.delete_prompt(prompt_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

        return Response(status_code=204)

    except HTTPException:
        raise
    except PromptRepositoryError as e:
        logger.error(f"Failed to delete prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Render Endpoint ====================


@router.post(
    "/prompts/{prompt_id}/render",
    response_model=PromptRenderResponse,
)
async def render_prompt(
    prompt_id: str,
    payload: PromptRenderRequest,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptRenderResponse:
    """
    Render a prompt template with variable values.

    Why: Preview the rendered prompt before using it.

    Args:
        prompt_id: ID of the prompt to render
        payload: Variable values for rendering
        request: FastAPI request
        service: Prompt router service

    Returns:
        Rendered prompt content with metadata
    """
    try:
        result = await service.render_prompt(
            prompt_id=prompt_id,
            variables={v.name: v.value for v in (payload.variables or [])},
            strict=payload.strict,
        )

        return PromptRenderResponse(
            rendered=result["rendered"],
            variables_used=result["variables_used"],
            variables_missing=result.get("variables_missing", []),
            template_id=prompt_id,
            template_name=result["template_name"],
            token_count=result.get("token_count"),
            llm_config=result.get("llm_config"),
        )

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to render prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Version History ====================


@router.get("/prompts/{prompt_id}/versions", response_model=PromptListResponse)
async def get_prompt_versions(
    prompt_id: str,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptListResponse:
    """
    Get all versions of a prompt template.

    Why: Version history enables audit trail and rollback.

    Args:
        prompt_id: ID of any version of the prompt
        request: FastAPI request
        service: Prompt router service

    Returns:
        List of all versions of the prompt
    """
    try:
        # Verify the prompt exists
        await service.get_prompt_by_id(prompt_id)

        versions = await service.get_version_history(prompt_id)

        return PromptListResponse(
            prompts=[service.to_summary(v) for v in versions],
            total=len(versions),
            limit=len(versions),
            offset=0,
        )

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to get version history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/prompts/{prompt_id}/rollback/{version}", response_model=PromptDetailResponse)
async def rollback_prompt(
    prompt_id: str,
    version: int,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> PromptDetailResponse:
    """
    Rollback a prompt to a specific version.

    Why: Restore previous versions by creating a new version with the target content.

    Args:
        prompt_id: ID of the current prompt version
        version: Target version number to rollback to
        request: FastAPI request
        service: Prompt router service

    Returns:
        New PromptTemplate created from the target version
    """
    try:
        rolled_back = await service.rollback_to_version(prompt_id, version)
        return service.to_detail(rolled_back)

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to rollback prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts/{prompt_id}/compare", response_model=dict[str, Any])
async def compare_prompt_versions(
    prompt_id: str,
    version_a: int,
    version_b: int,
    request: Request,
    service: PromptRouterService = Depends(get_prompt_service),
) -> dict[str, Any]:
    """
    Compare two versions of a prompt template.

    Why: View differences between versions for review and debugging.

    Args:
        prompt_id: ID of any version of the prompt
        version_a: First version number to compare
        version_b: Second version number to compare
        request: FastAPI request
        service: Prompt router service

    Returns:
        Comparison result with diffs
    """
    try:
        return await service.compare_versions(prompt_id, version_a, version_b)

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PromptRepositoryError as e:
        logger.error(f"Failed to compare versions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = ["router"]
