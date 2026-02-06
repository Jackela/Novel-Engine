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
    ExplainConfig,
    MultiHopResult,
    HopResult,
    HopStatus,
    ReasoningStep,
    DEFAULT_MAX_HOPS,
    DEFAULT_HOP_K,
    DEFAULT_TEMPERATURE as DEFAULT_MULTIHOP_TEMPERATURE,
)

from .model_registry import (
    ModelRegistry,
    ModelRegistryConfig,
    ModelLookupResult,
    ModelRegistryConfigFile,
    create_model_registry,
)

from .entity_extraction_service import (
    EntityExtractionService,
    ExtractionConfig,
    EntityExtractionError,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
)

from .coreference_resolution_service import (
    CoreferenceResolutionService,
    CoreferenceConfig,
    CoreferenceResult,
    ResolvedReference,
    CoreferenceResolutionError,
    DEFAULT_COREF_TEMPERATURE,
    DEFAULT_COREF_MAX_TOKENS,
    DEFAULT_MAX_REFERENCES,
    DEFAULT_WINDOW_SIZE,
)

from .graph_retrieval_service import (
    GraphEntityContext,
    GraphEnhancedChunk,
    GraphRetrievalConfig,
    GraphRetrievalResult,
    GraphRetrievalService,
    GraphExplanationStep,
    GraphExplanation,
)

from .token_tracker import (
    TokenTracker,
    TrackingContext,
    TokenTrackerConfig,
    TokenAwareConfig,
    create_token_tracker,
)

from .budget_alert_service import (
    BudgetAlertService,
    BudgetAlertServiceConfig,
    AlertHandler,
    create_budget_alert_service,
)

from .smart_tagging_service import (
    SmartTaggingService,
    TagCategory,
    GeneratedTag,
    TaggingResult,
    TaggingConfig,
    SmartTaggingError,
    DEFAULT_TEMPERATURE as DEFAULT_TAGGING_TEMPERATURE,
    DEFAULT_MAX_TOKENS as DEFAULT_TAGGING_MAX_TOKENS,
)

from .embedding_cache_service import (
    EmbeddingCacheService,
    CacheKey,
    CacheEntry,
    CacheStats,
)

from .context_window_manager import (
    ContextWindowManager,
    ContextWindowConfig,
    ManagedContext,
    ChatMessage as ContextWindowChatMessage,
    PruningStrategy,
    create_context_window_manager,
    DEFAULT_CONTEXT_WINDOWS,
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
    "ExplainConfig",
    "MultiHopResult",
    "HopResult",
    "HopStatus",
    "ReasoningStep",
    "DEFAULT_MAX_HOPS",
    "DEFAULT_HOP_K",
    "DEFAULT_MULTIHOP_TEMPERATURE",
    # Model Registry
    "ModelRegistry",
    "ModelRegistryConfig",
    "ModelLookupResult",
    "ModelRegistryConfigFile",
    "create_model_registry",
    # Entity Extraction
    "EntityExtractionService",
    "ExtractionConfig",
    "EntityExtractionError",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    # Co-reference Resolution
    "CoreferenceResolutionService",
    "CoreferenceConfig",
    "CoreferenceResult",
    "ResolvedReference",
    "CoreferenceResolutionError",
    "DEFAULT_COREF_TEMPERATURE",
    "DEFAULT_COREF_MAX_TOKENS",
    "DEFAULT_MAX_REFERENCES",
    "DEFAULT_WINDOW_SIZE",
    # Graph Retrieval Service
    "GraphRetrievalService",
    "GraphEntityContext",
    "GraphEnhancedChunk",
    "GraphRetrievalConfig",
    "GraphRetrievalResult",
    "GraphExplanationStep",
    "GraphExplanation",
    # Token Tracker
    "TokenTracker",
    "TrackingContext",
    "TokenTrackerConfig",
    "TokenAwareConfig",
    "create_token_tracker",
    # Budget Alert Service
    "BudgetAlertService",
    "BudgetAlertServiceConfig",
    "AlertHandler",
    "create_budget_alert_service",
    # Smart Tagging Service
    "SmartTaggingService",
    "TagCategory",
    "GeneratedTag",
    "TaggingResult",
    "TaggingConfig",
    "SmartTaggingError",
    "DEFAULT_TAGGING_TEMPERATURE",
    "DEFAULT_TAGGING_MAX_TOKENS",
    # Embedding Cache Service
    "EmbeddingCacheService",
    "CacheKey",
    "CacheEntry",
    "CacheStats",
    # Context Window Manager
    "ContextWindowManager",
    "ContextWindowConfig",
    "ManagedContext",
    "ContextWindowChatMessage",
    "PruningStrategy",
    "create_context_window_manager",
    "DEFAULT_CONTEXT_WINDOWS",
]
