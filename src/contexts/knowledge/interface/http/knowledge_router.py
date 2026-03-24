"""
Knowledge API Router

FastAPI routes for knowledge base and RAG operations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.domain.entities.document import Document
from src.contexts.knowledge.interface.http.error_handlers import (
    ResultErrorHandler,
    handle_knowledge_errors,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ============ Request/Response Models ============


class DocumentUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    content_type: str = Field(default="text")
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    content: str
    content_type: str
    source: Optional[str]
    tags: List[str]
    word_count: int
    chunk_count: int
    is_indexed: bool
    indexed_at: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


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


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    project_id: Optional[str] = None
    is_public: bool = False


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    description: Optional[str]
    project_id: Optional[str]
    document_count: int
    indexed_count: int
    is_public: bool
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int


# ============ Routes ============


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base",
)
@handle_knowledge_errors
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    owner_id: str = "current_user",  # TODO: Get from auth
    service: KnowledgeApplicationService = Depends(),
):
    """Create a new knowledge base for storing documents."""
    result = await service.create_knowledge_base(
        name=request.name,
        owner_id=owner_id,
        description=request.description,
        project_id=request.project_id,
        is_public=request.is_public,
    )

    kb: KnowledgeBase = ResultErrorHandler.handle_or_return(result)
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


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
@handle_knowledge_errors
async def upload_document(
    knowledge_base_id: str,
    request: DocumentUploadRequest,
    auto_index: bool = Query(default=True, description="Auto-index after upload"),
    service: KnowledgeApplicationService = Depends(),
):
    """Upload a document to a knowledge base."""
    result = await service.upload_document(
        knowledge_base_id=knowledge_base_id,
        title=request.title,
        content=request.content,
        content_type=request.content_type,
        source=request.source,
        tags=request.tags,
        auto_index=auto_index,
    )

    doc: Document = ResultErrorHandler.handle_or_return(result)
    return DocumentResponse(
        id=str(doc.id),
        knowledge_base_id=doc.knowledge_base_id,
        title=doc.title,
        content=doc.content,
        content_type=doc.content_type,
        source=doc.source,
        tags=doc.tags,
        word_count=doc.word_count,
        chunk_count=doc.chunk_count,
        is_indexed=doc.is_indexed,
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        metadata=doc.metadata,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents",
)
@handle_knowledge_errors
async def list_documents(
    knowledge_base_id: str,
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: KnowledgeApplicationService = Depends(),
):
    """List documents in a knowledge base."""
    result = await service.list_documents(
        knowledge_base_id=knowledge_base_id,
        tags=tags,
        limit=limit,
        offset=offset,
    )

    documents = ResultErrorHandler.handle_or_return(result)
    return DocumentListResponse(
        documents=[doc.to_dict() for doc in documents],
        total=len(documents),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document",
)
@handle_knowledge_errors
async def get_document(
    knowledge_base_id: str,
    document_id: str,
    service: KnowledgeApplicationService = Depends(),
):
    """Get a document by ID."""
    result = await service.get_document(
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )

    doc: Document = ResultErrorHandler.handle_or_return(result)
    return DocumentResponse(
        id=str(doc.id),
        knowledge_base_id=doc.knowledge_base_id,
        title=doc.title,
        content=doc.content,
        content_type=doc.content_type,
        source=doc.source,
        tags=doc.tags,
        word_count=doc.word_count,
        chunk_count=doc.chunk_count,
        is_indexed=doc.is_indexed,
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        metadata=doc.metadata,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
@handle_knowledge_errors
async def delete_document(
    knowledge_base_id: str,
    document_id: str,
    service: KnowledgeApplicationService = Depends(),
):
    """Delete a document from a knowledge base."""
    result = await service.delete_document(
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )

    ResultErrorHandler.handle_or_return(result)
    return None


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


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/index",
    response_model=DocumentResponse,
    summary="Index a document",
)
@handle_knowledge_errors
async def index_document(
    knowledge_base_id: str,
    document_id: str,
    service: KnowledgeApplicationService = Depends(),
):
    """Manually index a document for semantic search."""
    result = await service.index_document(
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )

    doc: Document = ResultErrorHandler.handle_or_return(result)
    return DocumentResponse(
        id=str(doc.id),
        knowledge_base_id=doc.knowledge_base_id,
        title=doc.title,
        content=doc.content,
        content_type=doc.content_type,
        source=doc.source,
        tags=doc.tags,
        word_count=doc.word_count,
        chunk_count=doc.chunk_count,
        is_indexed=doc.is_indexed,
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        metadata=doc.metadata,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.get(
    "/knowledge-bases/{knowledge_base_id}/stats",
    response_model=Dict[str, Any],
    summary="Get knowledge base statistics",
)
@handle_knowledge_errors
async def get_knowledge_base_stats(
    knowledge_base_id: str,
    service: KnowledgeApplicationService = Depends(),
):
    """Get statistics for a knowledge base."""
    result = await service.get_knowledge_base_stats(knowledge_base_id)

    return ResultErrorHandler.handle_or_return(result)
