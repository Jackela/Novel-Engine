"""Routes for semantic search operations."""

# mypy: disable-error-code=misc

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.apps.api.dependencies import get_knowledge_service
from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.interface.http.error_handlers import (
    ResultErrorHandler,
)

router = APIRouter()


# Request/Response Models


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] | None = None


class SearchResult(BaseModel):
    document_id: str
    title: str
    content_preview: str
    relevance_score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total_results: int


def _build_search_response(query: str, results: list[dict[str, Any]]) -> SearchResponse:
    search_results = [
        SearchResult(
            document_id=result.get("document", {}).get("id", ""),
            title=result.get("document", {}).get("title", ""),
            content_preview=result.get("document", {}).get("content_preview", ""),
            relevance_score=result.get("relevance_score", 0.0),
            metadata=result.get("document", {}).get("metadata", {}),
        )
        for result in results
    ]
    return SearchResponse(
        query=query,
        results=search_results,
        total_results=len(search_results),
    )


# Routes


@router.post(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=SearchResponse,
    summary="Semantic search",
)
async def semantic_search(
    knowledge_base_id: str,
    request: SearchRequest,
    service: KnowledgeApplicationService = Depends(get_knowledge_service),
) -> SearchResponse:
    """Perform semantic search on a knowledge base."""
    result = await service.semantic_search(
        knowledge_base_id=knowledge_base_id,
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )

    return _build_search_response(request.query, ResultErrorHandler.handle(result))


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across selected knowledge bases",
)
async def global_search(
    request: SearchRequest,
    knowledge_base_ids: list[str] | None = Query(default=None),
    service: KnowledgeApplicationService = Depends(get_knowledge_service),
) -> SearchResponse:
    """
    Perform semantic search across the provided knowledge bases.
    """
    if not knowledge_base_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one knowledge_base_id is required",
        )

    candidate_limit = request.top_k * len(knowledge_base_ids)
    best_results_by_document_id: dict[str, dict[str, Any]] = {}
    for knowledge_base_id in knowledge_base_ids:
        result = await service.semantic_search(
            knowledge_base_id=knowledge_base_id,
            query=request.query,
            top_k=candidate_limit,
            filters=request.filters,
        )
        for search_result in ResultErrorHandler.handle(result):
            document = search_result.get("document", {})
            document_id = document.get("id", "")
            if not document_id:
                continue

            current_best = best_results_by_document_id.get(document_id)
            if (
                current_best is None
                or search_result.get("relevance_score", 0.0)
                > current_best.get("relevance_score", 0.0)
            ):
                best_results_by_document_id[document_id] = search_result

    aggregated_results = sorted(
        best_results_by_document_id.values(),
        key=lambda result: result.get("relevance_score", 0.0),
        reverse=True,
    )
    return _build_search_response(request.query, aggregated_results[: request.top_k])
