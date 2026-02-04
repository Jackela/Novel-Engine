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

from .hybrid_retriever import (
    HybridRetriever,
    HybridConfig,
    HybridResult,
    FusionMetadata,
    DEFAULT_VECTOR_WEIGHT,
    DEFAULT_BM25_WEIGHT,
    DEFAULT_RRF_K,
    DEFAULT_RRF_ALPHA,
)

from .query_rewriter import (
    QueryRewriter,
    RewriteStrategy,
    RewriteConfig,
    RewriteResult,
    DEFAULT_STRATEGY,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_VARIANTS,
    DEFAULT_INCLUDE_ORIGINAL,
)

from .query_aware_retrieval_service import (
    QueryAwareRetrievalService,
    QueryAwareConfig,
    QueryAwareRetrievalResult,
    QueryAwareMetrics,
    DEFAULT_MAX_CONCURRENT,
)

from .rerank_service import (
    RerankService,
    RerankConfig,
    RerankServiceResult,
    MockReranker,
    FailingReranker,
    DEFAULT_TOP_K,
)

from .token_counter import (
    TokenCounter,
    LLMProvider,
    ModelFamily,
    TokenCountResult,
    create_token_counter,
    TIKTOKEN_AVAILABLE,
)

from .context_optimizer import (
    ContextOptimizer,
    PackingStrategy,
    OptimizationConfig,
    OptimizationResult,
    ChunkPriority,
    OptimizedChunk,
    IPackingStrategy,
    RelevancePackingStrategy,
    DiversityPackingStrategy,
    RemoveRedundancyPackingStrategy,
    CompressSummariesPackingStrategy,
    create_context_optimizer,
    DEFAULT_SYSTEM_PROMPT_TOKENS,
    DEFAULT_OVERHEAD_TOKENS,
    DEFAULT_MAX_TOKENS,
)

from .citation_formatter import (
    CitationFormatter,
    CitationFormatterConfig,
    SourceReference,
    ChunkCitation,
    CitationFormat,
)

from .multi_hop_retriever import (
    MultiHopRetriever,
    QueryDecomposer,
    MultiHopConfig,
    HopConfig,
    MultiHopResult,
    HopResult,
    HopStatus,
    DEFAULT_MAX_HOPS,
    DEFAULT_HOP_K,
    DEFAULT_TEMPERATURE as DEFAULT_MULTIHOP_TEMPERATURE,
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
    # Hybrid Retriever
    "HybridRetriever",
    "HybridConfig",
    "HybridResult",
    "FusionMetadata",
    "DEFAULT_VECTOR_WEIGHT",
    "DEFAULT_BM25_WEIGHT",
    "DEFAULT_RRF_K",
    "DEFAULT_RRF_ALPHA",
    # Query Rewriter
    "QueryRewriter",
    "RewriteStrategy",
    "RewriteConfig",
    "RewriteResult",
    "DEFAULT_STRATEGY",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_VARIANTS",
    "DEFAULT_INCLUDE_ORIGINAL",
    # Query-Aware Retrieval Service
    "QueryAwareRetrievalService",
    "QueryAwareConfig",
    "QueryAwareRetrievalResult",
    "QueryAwareMetrics",
    "DEFAULT_MAX_CONCURRENT",
    # Rerank Service
    "RerankService",
    "RerankConfig",
    "RerankServiceResult",
    "MockReranker",
    "FailingReranker",
    "DEFAULT_TOP_K",
    # Token Counter
    "TokenCounter",
    "LLMProvider",
    "ModelFamily",
    "TokenCountResult",
    "create_token_counter",
    "TIKTOKEN_AVAILABLE",
    # Context Optimizer
    "ContextOptimizer",
    "PackingStrategy",
    "OptimizationConfig",
    "OptimizationResult",
    "ChunkPriority",
    "OptimizedChunk",
    "IPackingStrategy",
    "RelevancePackingStrategy",
    "DiversityPackingStrategy",
    "RemoveRedundancyPackingStrategy",
    "CompressSummariesPackingStrategy",
    "create_context_optimizer",
    "DEFAULT_SYSTEM_PROMPT_TOKENS",
    "DEFAULT_OVERHEAD_TOKENS",
    "DEFAULT_MAX_TOKENS",
    # Citation Formatter
    "CitationFormatter",
    "CitationFormatterConfig",
    "SourceReference",
    "ChunkCitation",
    "CitationFormat",
    # Multi-Hop Retriever
    "MultiHopRetriever",
    "QueryDecomposer",
    "MultiHopConfig",
    "HopConfig",
    "MultiHopResult",
    "HopResult",
    "HopStatus",
    "DEFAULT_MAX_HOPS",
    "DEFAULT_HOP_K",
    "DEFAULT_MULTIHOP_TEMPERATURE",
]
