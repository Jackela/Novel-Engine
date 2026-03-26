"""Routes for knowledge base management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.apps.api.dependencies import (
    CurrentUser,
    get_current_user,
    get_knowledge_service,
)
from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.interface.http.error_handlers import (
    ResultErrorHandler,
    handle_knowledge_errors,
)

router = APIRouter()


# Request/Response Models


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    project_id: str | None = None
    is_public: bool = False


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    description: str | None
    project_id: str | None
    document_count: int
    indexed_count: int
    is_public: bool
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    documents: list[dict[str, Any]]
    total: int


# Routes


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base",
)
@handle_knowledge_errors
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeApplicationService = Depends(get_knowledge_service),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base for storing documents."""
    result = await service.create_knowledge_base(
        name=request.name,
        owner_id=current_user.user_id,
        description=request.description,
        project_id=request.project_id,
        is_public=request.is_public,
    )

    kb = ResultErrorHandler.handle(result)
    return KnowledgeBaseResponse(
        id=str(kb.id),
        name=kb.name,
        owner_id=kb.owner_id,
        description=kb.description,
        project_id=kb.project_id,
        document_count=kb.document_count,
        indexed_count=kb.indexed_count,
        is_public=kb.is_public,
        created_at=kb.created_at.isoformat(),
        updated_at=kb.updated_at.isoformat(),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents",
)
@handle_knowledge_errors
async def list_documents(
    knowledge_base_id: str,
    tags: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: KnowledgeApplicationService = Depends(get_knowledge_service),
) -> DocumentListResponse:
    """List documents in a knowledge base."""
    result = await service.list_documents(
        knowledge_base_id=knowledge_base_id,
        tags=tags,
        limit=limit,
        offset=offset,
    )

    documents = ResultErrorHandler.handle(result)
    return DocumentListResponse(
        documents=[doc.to_dict() for doc in documents],
        total=len(documents),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/stats",
    response_model=dict[str, Any],
    summary="Get knowledge base statistics",
)
@handle_knowledge_errors
async def get_knowledge_base_stats(
    knowledge_base_id: str,
    service: KnowledgeApplicationService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    """Get statistics for a knowledge base."""
    result = await service.get_knowledge_base_stats(knowledge_base_id)

    return ResultErrorHandler.handle(result)
