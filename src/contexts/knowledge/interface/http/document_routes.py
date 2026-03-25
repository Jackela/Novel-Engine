"""
Document Routes

Routes for document management.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.domain.entities.document import Document
from src.contexts.knowledge.interface.http.error_handlers import (
    ResultErrorHandler,
    handle_knowledge_errors,
)

router = APIRouter()


# Request/Response Models


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
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


# Routes


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
