"""
Application Services Module

Services in the knowledge context that orchestrate business logic.
"""

from .bm25_retriever import (
    DEFAULT_B,
    DEFAULT_K1,
    BM25IndexStats,
    BM25Result,
    BM25Retriever,
    IndexedDocument,
    tokenize,
)
from .budget_alert_service import (
    AlertHandler,
    BudgetAlertService,
    BudgetAlertServiceConfig,
    create_budget_alert_service,
)
from .citation_formatter import (
    ChunkCitation,
    CitationFormat,
    CitationFormatter,
    CitationFormatterConfig,
    SourceReference,
)
from .context_optimizer import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERHEAD_TOKENS,
    DEFAULT_SYSTEM_PROMPT_TOKENS,
    ChunkPriority,
    CompressSummariesPackingStrategy,
    ContextOptimizer,
    DiversityPackingStrategy,
    IPackingStrategy,
    OptimizationConfig,
    OptimizationResult,
    OptimizedChunk,
    PackingStrategy,
    RelevancePackingStrategy,
    RemoveRedundancyPackingStrategy,
    create_context_optimizer,
)
from .context_window_manager import (
    DEFAULT_CONTEXT_WINDOWS,
    ContextWindowConfig,
    ContextWindowManager,
    ManagedContext,
    PruningStrategy,
    create_context_window_manager,
)
from .context_window_manager import ChatMessage as ContextWindowChatMessage
from .coreference_resolution_service import (
    DEFAULT_COREF_MAX_TOKENS,
    DEFAULT_COREF_TEMPERATURE,
    DEFAULT_MAX_REFERENCES,
    DEFAULT_WINDOW_SIZE,
    CoreferenceConfig,
    CoreferenceResolutionError,
    CoreferenceResolutionService,
    CoreferenceResult,
    ResolvedReference,
)
from .embedding_cache_service import (
    CacheEntry,
    CacheKey,
    CacheStats,
    EmbeddingCacheService,
)
from .entity_extraction_service import DEFAULT_MAX_TOKENS as DEFAULT_ENTITY_MAX_TOKENS
from .entity_extraction_service import DEFAULT_TEMPERATURE as DEFAULT_ENTITY_TEMPERATURE
from .entity_extraction_service import (
    EntityExtractionError,
    EntityExtractionService,
    ExtractionConfig,
)
from .graph_retrieval_service import (
    GraphEnhancedChunk,
    GraphEntityContext,
    GraphExplanation,
    GraphExplanationStep,
    GraphRetrievalConfig,
    GraphRetrievalResult,
    GraphRetrievalService,
)
from .hybrid_retriever import (
    DEFAULT_BM25_WEIGHT,
    DEFAULT_RRF_ALPHA,
    DEFAULT_RRF_K,
    DEFAULT_VECTOR_WEIGHT,
    FusionMetadata,
    HybridConfig,
    HybridResult,
    HybridRetriever,
)
from .knowledge_ingestion_service import (
    DEFAULT_COLLECTION,
    BatchIngestionResult,
    IngestionProgress,
    IngestionResult,
    KnowledgeIngestionService,
    RetrievedChunk,
    SourceChunk,
)
from .model_registry import (
    ModelLookupResult,
    ModelRegistry,
    ModelRegistryConfig,
    ModelRegistryConfigFile,
    create_model_registry,
)
from .multi_hop_retriever import (
    DEFAULT_HOP_K,
    DEFAULT_MAX_HOPS,
    ExplainConfig,
    HopConfig,
    HopResult,
    HopStatus,
    MultiHopConfig,
    MultiHopResult,
    MultiHopRetriever,
    QueryDecomposer,
    ReasoningStep,
)
from .multi_hop_retriever import DEFAULT_TEMPERATURE as DEFAULT_MULTIHOP_TEMPERATURE
from .prompt_formatter import (
    FormattedPrompt,
    PromptFormat,
    PromptFormatter,
    PromptModelFamily,
    PromptRequest,
    create_prompt_formatter,
)
from .query_aware_retrieval_service import (
    DEFAULT_MAX_CONCURRENT,
    QueryAwareConfig,
    QueryAwareMetrics,
    QueryAwareRetrievalResult,
    QueryAwareRetrievalService,
)
from .query_rewriter import (
    DEFAULT_INCLUDE_ORIGINAL,
    DEFAULT_MAX_VARIANTS,
    DEFAULT_STRATEGY,
    DEFAULT_TEMPERATURE,
    QueryRewriter,
    RewriteConfig,
    RewriteResult,
    RewriteStrategy,
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
from .rerank_service import (
    DEFAULT_TOP_K,
    FailingReranker,
    MockReranker,
    RerankConfig,
    RerankService,
    RerankServiceResult,
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
from .smart_tagging_service import DEFAULT_MAX_TOKENS as DEFAULT_TAGGING_MAX_TOKENS
from .smart_tagging_service import DEFAULT_TEMPERATURE as DEFAULT_TAGGING_TEMPERATURE
from .smart_tagging_service import (
    GeneratedTag,
    SmartTaggingError,
    SmartTaggingService,
    TagCategory,
    TaggingConfig,
    TaggingResult,
)
from .token_counter import (
    TIKTOKEN_AVAILABLE,
    LLMProvider,
    ModelFamily,
    TokenCounter,
    TokenCountResult,
    create_token_counter,
)
from .token_tracker import (
    TokenAwareConfig,
    TokenTracker,
    TokenTrackerConfig,
    TrackingContext,
    create_token_tracker,
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
    "DEFAULT_ENTITY_TEMPERATURE",
    "DEFAULT_ENTITY_MAX_TOKENS",
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
    # Prompt Formatter
    "PromptFormatter",
    "PromptRequest",
    "FormattedPrompt",
    "PromptFormat",
    "PromptModelFamily",
    "create_prompt_formatter",
]
