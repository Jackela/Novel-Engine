"""
Application Services Module

Services in the knowledge context that orchestrate business logic.
"""

from .knowledge_ingestion_service import (
    BatchIngestionResult,
    DEFAULT_COLLECTION,
    IngestionProgress,
    IngestionResult,
    KnowledgeIngestionService,
    RetrievedChunk,
    SourceChunk,
)

from .retrieval_service import (
    DEFAULT_DEDUPLICATION_SIMILARITY,
    DEFAULT_RELEVANCE_THRESHOLD,
    FormattedContext,
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
    RetrievalService,
)

from .rag_integration_service import (
    DEFAULT_CONTEXT_TOKEN_LIMIT,
    DEFAULT_ENABLED,
    DEFAULT_MAX_CHUNKS,
    EnrichedPrompt,
    RAGConfig,
    RAGIntegrationService,
    RAGMetrics,
)

from .bm25_retriever import (
    BM25Retriever,
    BM25Result,
    IndexedDocument,
    BM25IndexStats,
    tokenize,
    DEFAULT_K1,
    DEFAULT_B,
)

__all__ = [
    # Knowledge Ingestion Service
    "KnowledgeIngestionService",
    "IngestionProgress",
    "IngestionResult",
    "BatchIngestionResult",
    "SourceChunk",
    "RetrievedChunk",
    "DEFAULT_COLLECTION",
    # Retrieval Service
    "RetrievalService",
    "RetrievalFilter",
    "RetrievalOptions",
    "FormattedContext",
    "RetrievalResult",
    "DEFAULT_RELEVANCE_THRESHOLD",
    "DEFAULT_DEDUPLICATION_SIMILARITY",
    # RAG Integration Service
    "RAGIntegrationService",
    "RAGConfig",
    "EnrichedPrompt",
    "RAGMetrics",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_CONTEXT_TOKEN_LIMIT",
    "DEFAULT_ENABLED",
    # BM25 Retriever
    "BM25Retriever",
    "BM25Result",
    "IndexedDocument",
    "BM25IndexStats",
    "tokenize",
    "DEFAULT_K1",
    "DEFAULT_B",
]
