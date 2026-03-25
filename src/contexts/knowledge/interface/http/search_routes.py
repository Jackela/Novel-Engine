"""
Search Routes

Routes for semantic search operations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.interface.http.error_handlers import (
    ResultErrorHandler,
    handle_knowledge_errors,
)

router = APIRouter()


# Request/Response Models


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    document_id: str
    title: str
    content_preview: str
    relevance_score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


# Routes


@router.post(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=SearchResponse,
    summary="Semantic search",
)
@handle_knowledge_errors
async def semantic_search(
    knowledge_base_id: str,
    request: SearchRequest,
    service: KnowledgeApplicationService = Depends(),
):
    """Perform semantic search on a knowledge base."""
    result = await service.semantic_search(
        knowledge_base_id=knowledge_base_id,
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )

    results = ResultErrorHandler.handle_or_return(result)
    search_results = []

    for r in results:
        doc = r.get("document", {})
        search_results.append(
            SearchResult(
                document_id=doc.get("id", ""),
                title=doc.get("title", ""),
                content_preview=doc.get("content_preview", ""),
                relevance_score=r.get("relevance_score", 0.0),
                metadata=doc.get("metadata", {}),
            )
        )

    return SearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Global semantic search",
)
@handle_knowledge_errors
async def global_search(
    request: SearchRequest,
    knowledge_base_ids: Optional[List[str]] = Query(default=None),
    service: KnowledgeApplicationService = Depends(),
):
    """
    Perform semantic search across multiple knowledge bases.

    If no knowledge_base_ids are provided, searches across all
    accessible knowledge bases.
    """
    # For now, only support single KB search
    # TODO: Implement multi-KB search aggregation

    if not knowledge_base_ids:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one knowledge_base_id is required",
        )

    # Use first KB for now
    result = await service.semantic_search(
        knowledge_base_id=knowledge_base_ids[0],
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )

    results = ResultErrorHandler.handle_or_return(result)
    search_results = []

    for r in results:
        doc = r.get("document", {})
        search_results.append(
            SearchResult(
                document_id=doc.get("id", ""),
                title=doc.get("title", ""),
                content_preview=doc.get("content_preview", ""),
                relevance_score=r.get("relevance_score", 0.0),
                metadata=doc.get("metadata", {}),
            )
        )

    return SearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )
