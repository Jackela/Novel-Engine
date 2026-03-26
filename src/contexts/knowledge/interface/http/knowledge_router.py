"""
Knowledge API Router

FastAPI routes for knowledge base and RAG operations.
Main router that combines all knowledge-related routes.
"""

from fastapi import APIRouter

from .document_routes import router as document_router
from .knowledge_base_routes import router as kb_router
from .search_routes import router as search_router

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Include all sub-routers
router.include_router(kb_router)
router.include_router(document_router)
router.include_router(search_router)

# Re-export for backward compatibility
from .document_routes import (
    DocumentResponse,
    DocumentUploadRequest,
)
from .knowledge_base_routes import (
    DocumentListResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
)
from .search_routes import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)

__all__ = [
    "router",
    "DocumentResponse",
    "DocumentUploadRequest",
    "DocumentListResponse",
    "KnowledgeBaseCreateRequest",
    "KnowledgeBaseResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
]
