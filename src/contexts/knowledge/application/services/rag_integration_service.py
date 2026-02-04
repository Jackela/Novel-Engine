"""
RAG Integration Service

Warzone 4: AI Brain - BRAIN-007A

Integration wrapper that combines RAG retrieval with LLM generation.
This service provides a clean interface for enriching prompts with
retrieved context from the knowledge base.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating domain and infrastructure
- Article V (SOLID): SRP - RAG integration and prompt enrichment only
- Article III (TDD): Tested via mock dependencies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from ..ports.i_vector_store import VectorStoreError
from .retrieval_service import (
    RetrievalService,
    RetrievalFilter,
    RetrievalOptions,
    FormattedContext,
    DEFAULT_RELEVANCE_THRESHOLD,
)

if TYPE_CHECKING:
    from ..ports.i_embedding_service import IEmbeddingService
    from ..ports.i_vector_store import IVectorStore


logger = structlog.get_logger()


# Default configuration values
DEFAULT_MAX_CHUNKS = 5
DEFAULT_CONTEXT_TOKEN_LIMIT = 4000
DEFAULT_ENABLED = True


@dataclass(frozen=True, slots=True)
class RAGConfig:
    """
    Configuration for RAG integration.

    Why frozen:
        Immutable snapshot ensures configuration doesn't change during operation.

    Attributes:
        max_chunks: Maximum number of chunks to retrieve
        score_threshold: Minimum relevance score (0.0 - 1.0)
        context_token_limit: Maximum tokens for retrieved context
        enabled: Whether RAG is enabled
        include_sources: Whether to include source citations
    """

    max_chunks: int = DEFAULT_MAX_CHUNKS
    score_threshold: float = DEFAULT_RELEVANCE_THRESHOLD
    context_token_limit: int | None = DEFAULT_CONTEXT_TOKEN_LIMIT
    enabled: bool = DEFAULT_ENABLED
    include_sources: bool = True


@dataclass
class EnrichedPrompt:
    """
    Result of prompt enrichment with RAG context.

    Attributes:
        prompt: The enriched prompt with context injected
        context: The formatted context that was added
        chunks_retrieved: Number of chunks retrieved
        sources: List of source references
        tokens_added: Estimated tokens added to prompt
    """

    prompt: str
    context: FormattedContext
    chunks_retrieved: int
    sources: list[str]
    tokens_added: int


@dataclass
class RAGMetrics:
    """
    Metrics for RAG operations.

    Attributes:
        queries_total: Total number of RAG queries
        chunks_retrieved_total: Total chunks retrieved
        avg_chunks_per_query: Average chunks per query
        tokens_added_total: Total tokens added to prompts
        failed_queries: Number of failed queries
    """

    queries_total: int = 0
    chunks_retrieved_total: int = 0
    tokens_added_total: int = 0
    failed_queries: int = 0

    @property
    def avg_chunks_per_query(self) -> float:
        """Calculate average chunks per query."""
        if self.queries_total == 0:
            return 0.0
        return self.chunks_retrieved_total / self.queries_total


class RAGIntegrationService:
    """
    Service for integrating RAG retrieval with LLM generation.

    This service provides a high-level interface for:
    - Enriching prompts with retrieved context
    - Configurable retrieval behavior
    - Metrics tracking for RAG operations

    The service coordinates between RetrievalService and the prompt construction
    logic, providing a clean abstraction layer for LLM integration.

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - RAG integration and prompt enrichment
        - Article III (TDD): Tested via mock dependencies

    Example:
        >>> service = RAGIntegrationService(
        ...     retrieval_service=retrieval_svc,
        ...     config=RAGConfig(max_chunks=5),
        ... )
        >>> result = await service.enrich_prompt(
        ...     query="brave warrior",
        ...     base_prompt="Generate a scene about a warrior",
        ... )
        >>> print(result.prompt)  # Contains enriched prompt with context
        >>> print(result.chunks_retrieved)  # Number of chunks added
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        config: RAGConfig | None = None,
    ):
        """
        Initialize the RAG integration service.

        Args:
            retrieval_service: Service for retrieving relevant context
            config: Optional configuration (uses defaults if None)
        """
        self._retrieval_service = retrieval_service
        self._config = config or RAGConfig()
        self._metrics = RAGMetrics()

    @classmethod
    def create(
        cls,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        config: RAGConfig | None = None,
    ) -> RAGIntegrationService:
        """
        Factory method to create the service with dependencies.

        Convenience method for creating the service with all required dependencies.

        Args:
            embedding_service: Service for generating query embeddings
            vector_store: Vector storage backend
            config: Optional RAG configuration

        Returns:
            Configured RAGIntegrationService instance

        Example:
            >>> service = RAGIntegrationService.create(
            ...     embedding_service=embedding_svc,
            ...     vector_store=chromadb_store,
            ...     config=RAGConfig(max_chunks=10),
            ... )
        """
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        return cls(retrieval_service=retrieval_service, config=config)

    async def enrich_prompt(
        self,
        query: str,
        base_prompt: str,
        filters: RetrievalFilter | None = None,
        config_override: RAGConfig | None = None,
    ) -> EnrichedPrompt:
        """
        Enrich a prompt with relevant context from the knowledge base.

        This method:
        1. Retrieves relevant chunks using the query
        2. Formats the retrieved context
        3. Injects the context into the base prompt

        Args:
            query: Search query for context retrieval
            base_prompt: The base prompt to enrich
            filters: Optional filters for retrieval (source_type, tags, dates)
            config_override: Optional config override for this call

        Returns:
            EnrichedPrompt with the enriched prompt and metadata

        Raises:
            ValueError: If query or base_prompt is empty
            VectorStoreError: If vector retrieval fails
            EmbeddingError: If query embedding fails

        Example:
            >>> result = await service.enrich_prompt(
            ...     query="brave warrior with a sword",
            ...     base_prompt="Write a scene introduction.",
            ... )
            >>> print(result.prompt)
            >>> # Relevant Context:\\n
            >>> # [1] CHARACTER:arthur (part 1/1)\\n
            >>> # Sir Arthur is known for his exceptional bravery...\\n
            >>> # \\nWrite a scene introduction.
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        if not base_prompt:
            raise ValueError("base_prompt cannot be empty")

        # Use override config or default
        config = config_override or self._config

        # Track metrics
        self._metrics.queries_total += 1

        # If RAG is disabled, return base prompt as-is
        if not config.enabled:
            logger.debug(
                "rag_disabled",
                query=query,
            )
            return EnrichedPrompt(
                prompt=base_prompt,
                context=FormattedContext(text="", sources=[], total_tokens=0, chunk_count=0),
                chunks_retrieved=0,
                sources=[],
                tokens_added=0,
            )

        try:
            # Step 1: Retrieve relevant context
            retrieval_options = RetrievalOptions(
                k=config.max_chunks,
                min_score=config.score_threshold,
            )

            retrieval_result = await self._retrieval_service.retrieve_relevant(
                query=query,
                k=config.max_chunks,
                filters=filters,
                options=retrieval_options,
            )

            # Step 2: Format context
            formatted_context = self._retrieval_service.format_context(
                result=retrieval_result,
                max_tokens=config.context_token_limit,
                include_sources=config.include_sources,
            )

            # Step 3: Build enriched prompt
            enriched_prompt = self._build_enriched_prompt(
                base_prompt=base_prompt,
                context=formatted_context,
            )

            # Step 4: Update metrics
            self._metrics.chunks_retrieved_total += len(retrieval_result.chunks)
            self._metrics.tokens_added_total += formatted_context.total_tokens

            logger.info(
                "rag_enrichment_complete",
                query=query,
                chunks_retrieved=len(retrieval_result.chunks),
                tokens_added=formatted_context.total_tokens,
                sources=formatted_context.sources,
            )

            return EnrichedPrompt(
                prompt=enriched_prompt,
                context=formatted_context,
                chunks_retrieved=len(retrieval_result.chunks),
                sources=formatted_context.sources,
                tokens_added=formatted_context.total_tokens,
            )

        except (VectorStoreError, Exception) as e:
            self._metrics.failed_queries += 1
            logger.error(
                "rag_enrichment_failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _build_enriched_prompt(
        self,
        base_prompt: str,
        context: FormattedContext,
    ) -> str:
        """
        Build an enriched prompt by injecting context.

        Args:
            base_prompt: The original prompt
            context: Formatted context to inject

        Returns:
            Enriched prompt string
        """
        if not context.text or context.chunk_count == 0:
            # No context to add, return base prompt
            return base_prompt

        # Build the enriched prompt with context section
        enriched = f"""Relevant Context:
{context.text}

---

{base_prompt}"""

        return enriched

    def get_metrics(self) -> RAGMetrics:
        """
        Get current RAG operation metrics.

        Returns:
            Copy of current metrics
        """
        return RAGMetrics(
            queries_total=self._metrics.queries_total,
            chunks_retrieved_total=self._metrics.chunks_retrieved_total,
            tokens_added_total=self._metrics.tokens_added_total,
            failed_queries=self._metrics.failed_queries,
        )

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._metrics = RAGMetrics()

    def update_config(self, config: RAGConfig) -> None:
        """
        Update the service configuration.

        Args:
            config: New configuration to apply
        """
        self._config = config
        logger.debug(
            "rag_config_updated",
            max_chunks=config.max_chunks,
            score_threshold=config.score_threshold,
            enabled=config.enabled,
        )

    def get_config(self) -> RAGConfig:
        """
        Get the current configuration.

        Returns:
            Copy of current config
        """
        return self._config


__all__ = [
    "RAGIntegrationService",
    "RAGConfig",
    "EnrichedPrompt",
    "RAGMetrics",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_CONTEXT_TOKEN_LIMIT",
    "DEFAULT_ENABLED",
]
