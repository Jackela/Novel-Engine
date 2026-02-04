"""
Context Optimizer Service

Optimizes retrieved context chunks to maximize information density within token budget.
Implements strategies for redundancy removal, relevance prioritization, and compression.

Constitution Compliance:
- Article II (Hexagonal): Application service for context optimization
- Article V (SOLID): SRP - context optimization only

Warzone 4: AI Brain - BRAIN-011B
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
import hashlib

import structlog

from .token_counter import TokenCounter, LLMProvider
from ..services.knowledge_ingestion_service import RetrievedChunk

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


# Default optimization settings
DEFAULT_SYSTEM_PROMPT_TOKENS = 500  # Reserve space for system prompt
DEFAULT_OVERHEAD_TOKENS = 100  # Additional overhead for formatting
DEFAULT_MAX_TOKENS = 4096  # Default context window (smaller models)
DEFAULT_RElevance_THRESHOLD = 0.5  # Minimum relevance score


class PackingStrategy(str, Enum):
    """Strategies for packing context chunks into token budget.

    Why Enum:
        Type-safe strategy selection with string compatibility.
    """

    RELEVANCE = "relevance"  # Prioritize by relevance score only
    DIVERSITY = "diversity"  # Maximize source diversity
    REMOVE_REDUNDANCY = "remove_redundancy"  # Remove similar content
    COMPRESS_SUMMARIES = "compress_summaries"  # Use summaries for low-relevance chunks


@dataclass(frozen=True, slots=True)
class ChunkPriority:
    """
    Priority score for a chunk during optimization.

    Attributes:
        chunk: The chunk being prioritized
        priority: Combined priority score (higher = more important)
        relevance: Original relevance score
        diversity_score: Score for source diversity
        redundancy_penalty: Penalty for redundant content
    """

    chunk: RetrievedChunk
    priority: float
    relevance: float
    diversity_score: float
    redundancy_penalty: float


@dataclass(frozen=True, slots=True)
class OptimizationConfig:
    """
    Configuration for context optimization.

    Attributes:
        max_tokens: Maximum tokens for context (excluding system prompt)
        system_prompt_tokens: Reserved tokens for system prompt
        overhead_tokens: Additional overhead for formatting
        strategy: Primary packing strategy to use
        relevance_threshold: Minimum relevance score to include
        diversity_weight: Weight for diversity scoring (0.0-1.0)
        redundancy_threshold: Similarity threshold for redundancy detection
        compress_below: Relevance score below which to use summaries
    """

    max_tokens: int = DEFAULT_MAX_TOKENS - DEFAULT_SYSTEM_PROMPT_TOKENS
    system_prompt_tokens: int = DEFAULT_SYSTEM_PROMPT_TOKENS
    overhead_tokens: int = DEFAULT_OVERHEAD_TOKENS
    strategy: PackingStrategy = PackingStrategy.REMOVE_REDUNDANCY
    relevance_threshold: float = DEFAULT_RElevance_THRESHOLD
    diversity_weight: float = 0.3  # 30% weight to diversity
    redundancy_threshold: float = 0.8  # 80% similarity = redundant
    compress_below: float = 0.6  # Below 0.6 relevance, consider compression


@dataclass
class OptimizationResult:
    """
    Result of context optimization.

    Attributes:
        chunks: Optimized list of chunks
        total_tokens: Estimated token count
        original_count: Number of input chunks
        optimized_count: Number of chunks after optimization
        tokens_saved: Estimated tokens saved
        removed_redundant: Number of chunks removed as redundant
        compressed: Number of chunks compressed to summaries
        strategy_used: Strategy that was applied
    """

    chunks: list[RetrievedChunk]
    total_tokens: int
    original_count: int
    optimized_count: int
    tokens_saved: int
    removed_redundant: int
    compressed: int
    strategy_used: PackingStrategy


@dataclass
class OptimizedChunk:
    """
    A chunk that may have been optimized.

    Attributes:
        chunk: Original or modified chunk
        is_summary: Whether this is a compressed summary
        is_original: Whether content is unchanged
    """

    chunk: RetrievedChunk
    is_summary: bool = False
    is_original: bool = True


class IPackingStrategy(ABC):
    """
    Interface for context packing strategies.

    Each strategy defines how to select and arrange chunks
    to fit within a token budget.
    """

    @abstractmethod
    async def pack(
        self,
        chunks: list[RetrievedChunk],
        config: OptimizationConfig,
        token_counter: TokenCounter,
    ) -> OptimizationResult:
        """
        Pack chunks according to strategy.

        Args:
            chunks: Input chunks to pack
            config: Optimization configuration
            token_counter: Token counter for estimation

        Returns:
            OptimizationResult with packed chunks
        """
        pass


class RelevancePackingStrategy(IPackingStrategy):
    """
    Pack chunks by relevance score only.

    Simplest strategy: include highest-scoring chunks first
    until token budget is exhausted.
    """

    async def pack(
        self,
        chunks: list[RetrievedChunk],
        config: OptimizationConfig,
        token_counter: TokenCounter,
    ) -> OptimizationResult:
        """Pack by relevance score descending."""
        # Filter by threshold and sort by relevance
        filtered = [
            c for c in chunks
            if c.score >= config.relevance_threshold
        ]
        sorted_chunks = sorted(filtered, key=lambda c: c.score, reverse=True)

        # Pack until budget exhausted
        packed: list[RetrievedChunk] = []
        total_tokens = 0
        available_tokens = config.max_tokens - config.overhead_tokens

        for chunk in sorted_chunks:
            chunk_tokens = self._estimate_tokens(chunk.content, token_counter)
            if total_tokens + chunk_tokens > available_tokens:
                break
            packed.append(chunk)
            total_tokens += chunk_tokens

        return OptimizationResult(
            chunks=packed,
            total_tokens=total_tokens,
            original_count=len(chunks),
            optimized_count=len(packed),
            tokens_saved=0,
            removed_redundant=len(chunks) - len(packed),
            compressed=0,
            strategy_used=PackingStrategy.RELEVANCE,
        )

    def _estimate_tokens(self, text: str, token_counter: TokenCounter) -> int:
        """Estimate tokens for content."""
        return token_counter.count(text).token_count


class DiversityPackingStrategy(IPackingStrategy):
    """
    Pack chunks to maximize source diversity.

    Prioritizes chunks from different sources to provide
    broader context coverage.
    """

    async def pack(
        self,
        chunks: list[RetrievedChunk],
        config: OptimizationConfig,
        token_counter: TokenCounter,
    ) -> OptimizationResult:
        """Pack by source diversity."""
        # Filter by threshold
        filtered = [
            c for c in chunks
            if c.score >= config.relevance_threshold
        ]

        # Group by source
        sources: dict[str, list[RetrievedChunk]] = {}
        for chunk in filtered:
            key = f"{chunk.source_type.value}:{chunk.source_id}"
            if key not in sources:
                sources[key] = []
            sources[key].append(chunk)

        # Sort chunks within each source by relevance
        for source_chunks in sources.values():
            source_chunks.sort(key=lambda c: c.score, reverse=True)

        # Round-robin pick from sources to maximize diversity
        packed: list[RetrievedChunk] = []
        total_tokens = 0
        available_tokens = config.max_tokens - config.overhead_tokens
        source_keys = list(sources.keys())
        indices = {k: 0 for k in source_keys}

        # Keep picking until exhausted
        while True:
            added_any = False
            for source_key in source_keys:
                idx = indices[source_key]
                if idx >= len(sources[source_key]):
                    continue

                chunk = sources[source_key][idx]
                chunk_tokens = token_counter.count(chunk.content).token_count

                if total_tokens + chunk_tokens > available_tokens:
                    continue

                packed.append(chunk)
                total_tokens += chunk_tokens
                indices[source_key] = idx + 1
                added_any = True

            if not added_any:
                break

        return OptimizationResult(
            chunks=packed,
            total_tokens=total_tokens,
            original_count=len(chunks),
            optimized_count=len(packed),
            tokens_saved=0,
            removed_redundant=len(chunks) - len(packed),
            compressed=0,
            strategy_used=PackingStrategy.DIVERSITY,
        )


class RemoveRedundancyPackingStrategy(IPackingStrategy):
    """
    Pack chunks while removing redundant content.

    Uses content similarity to detect and remove redundant chunks,
    keeping the highest-scoring version.
    """

    async def pack(
        self,
        chunks: list[RetrievedChunk],
        config: OptimizationConfig,
        token_counter: TokenCounter,
    ) -> OptimizationResult:
        """Pack with redundancy removal."""
        # Filter by threshold and sort by relevance
        filtered = [
            c for c in chunks
            if c.score >= config.relevance_threshold
        ]
        sorted_chunks = sorted(filtered, key=lambda c: c.score, reverse=True)

        # Remove redundant chunks
        deduplicated: list[RetrievedChunk] = []
        seen_hashes: set[str] = set()

        for chunk in sorted_chunks:
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()

            # Check for exact duplicate
            if content_hash in seen_hashes:
                continue

            # Check for similar content
            is_redundant = False
            for existing in deduplicated:
                similarity = self._content_similarity(chunk.content, existing.content)
                if similarity >= config.redundancy_threshold:
                    is_redundant = True
                    break

            if not is_redundant:
                deduplicated.append(chunk)
                seen_hashes.add(content_hash)

        # Pack until budget exhausted
        packed: list[RetrievedChunk] = []
        total_tokens = 0
        available_tokens = config.max_tokens - config.overhead_tokens
        redundant_removed = len(sorted_chunks) - len(deduplicated)

        for chunk in deduplicated:
            chunk_tokens = token_counter.count(chunk.content).token_count
            if total_tokens + chunk_tokens > available_tokens:
                break
            packed.append(chunk)
            total_tokens += chunk_tokens

        # Estimate tokens saved from redundancy removal
        tokens_saved = redundant_removed * 100  # Rough estimate

        return OptimizationResult(
            chunks=packed,
            total_tokens=total_tokens,
            original_count=len(chunks),
            optimized_count=len(packed),
            tokens_saved=tokens_saved,
            removed_redundant=redundant_removed + (len(deduplicated) - len(packed)),
            compressed=0,
            strategy_used=PackingStrategy.REMOVE_REDUNDANCY,
        )

    def _content_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        text1_normalized = " ".join(text1.lower().split())
        text2_normalized = " ".join(text2.lower().split())
        return SequenceMatcher(None, text1_normalized, text2_normalized).ratio()


class CompressSummariesPackingStrategy(IPackingStrategy):
    """
    Pack chunks with compression for low-relevance content.

    High-relevance chunks are included as-is.
    Low-relevance chunks are compressed to brief summaries.
    """

    async def pack(
        self,
        chunks: list[RetrievedChunk],
        config: OptimizationConfig,
        token_counter: TokenCounter,
    ) -> OptimizationResult:
        """Pack with compression for low-relevance chunks."""
        # Filter by threshold
        filtered = [
            c for c in chunks
            if c.score >= config.relevance_threshold
        ]

        # Sort by relevance
        sorted_chunks = sorted(filtered, key=lambda c: c.score, reverse=True)

        high_relevance: list[RetrievedChunk] = []
        low_relevance: list[RetrievedChunk] = []

        for chunk in sorted_chunks:
            if chunk.score >= config.compress_below:
                high_relevance.append(chunk)
            else:
                low_relevance.append(chunk)

        # Add high-relevance chunks as-is
        packed: list[RetrievedChunk] = []
        total_tokens = 0
        available_tokens = config.max_tokens - config.overhead_tokens

        for chunk in high_relevance:
            chunk_tokens = token_counter.count(chunk.content).token_count
            if total_tokens + chunk_tokens > available_tokens:
                break
            packed.append(chunk)
            total_tokens += chunk_tokens

        # Add compressed versions of low-relevance chunks
        compressed_count = 0
        for chunk in low_relevance:
            summary = self._create_summary(chunk)
            summary_tokens = token_counter.count(summary).token_count

            if total_tokens + summary_tokens > available_tokens:
                break

            # Create a modified chunk with summary
            summarized_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                content=summary,
                score=chunk.score,
                metadata={**chunk.metadata, "summarized": True},
            )
            packed.append(summarized_chunk)
            total_tokens += summary_tokens
            compressed_count += 1

        return OptimizationResult(
            chunks=packed,
            total_tokens=total_tokens,
            original_count=len(chunks),
            optimized_count=len(packed),
            tokens_saved=compressed_count * 50,  # Rough estimate
            removed_redundant=len(chunks) - len(packed) - compressed_count,
            compressed=compressed_count,
            strategy_used=PackingStrategy.COMPRESS_SUMMARIES,
        )

    def _create_summary(self, chunk: RetrievedChunk) -> str:
        """Create a brief summary of chunk content."""
        # Take first sentence and last sentence if available
        sentences = chunk.content.split(". ")
        if len(sentences) <= 2:
            # Too short to summarize, truncate instead
            words = chunk.content.split()[:15]
            return " ".join(words) + "..."

        # First and last sentence
        first = sentences[0].strip()
        last = sentences[-1].strip() if sentences[-1] else sentences[-2].strip()
        return f"{first} [...] {last}"


class ContextOptimizer:
    """
    Service for optimizing RAG context within token budgets.

    Implements multiple packing strategies:
    - RELEVANCE: Prioritize high-scoring chunks
    - DIVERSITY: Maximize source diversity
    - REMOVE_REDUNDANCY: Remove similar content
    - COMPRESS_SUMMARIES: Compress low-relevance chunks

    Constitution Compliance:
        - Article II (Hexagonal): Application service
        - Article V (SOLID): SRP - context optimization only

    Example:
        >>> optimizer = ContextOptimizer()
        >>> result = await optimizer.optimize_context(
        ...     chunks=retrieved_chunks,
        ...     max_tokens=2000,
        ...     strategy=PackingStrategy.REMOVE_REDUNDANCY,
        ... )
        >>> print(f"Included {result.optimized_count} chunks")
    """

    def __init__(
        self,
        token_counter: TokenCounter | None = None,
        default_config: OptimizationConfig | None = None,
    ):
        """
        Initialize the context optimizer.

        Args:
            token_counter: Token counter for estimation (creates default if None)
            default_config: Default optimization configuration
        """
        self._token_counter = token_counter or TokenCounter()
        self._default_config = default_config or OptimizationConfig()

        # Strategy registry
        self._strategies: dict[PackingStrategy, IPackingStrategy] = {
            PackingStrategy.RELEVANCE: RelevancePackingStrategy(),
            PackingStrategy.DIVERSITY: DiversityPackingStrategy(),
            PackingStrategy.REMOVE_REDUNDANCY: RemoveRedundancyPackingStrategy(),
            PackingStrategy.COMPRESS_SUMMARIES: CompressSummariesPackingStrategy(),
        }

    async def optimize_context(
        self,
        chunks: list[RetrievedChunk],
        max_tokens: int | None = None,
        strategy: PackingStrategy | None = None,
        config: OptimizationConfig | None = None,
    ) -> OptimizationResult:
        """
        Optimize context chunks to fit within token budget.

        Args:
            chunks: Retrieved chunks to optimize
            max_tokens: Maximum tokens (overrides config)
            strategy: Packing strategy to use (overrides config)
            config: Full optimization config (uses default if None)

        Returns:
            OptimizationResult with optimized chunks

        Raises:
            ValueError: If chunks is empty or strategy is invalid

        Example:
            >>> result = await optimizer.optimize_context(
            ...     chunks=chunks,
            ...     max_tokens=2000,
            ...     strategy=PackingStrategy.DIVERSITY,
            ... )
            >>> for chunk in result.chunks:
            ...     print(f"{chunk.source_id}: {chunk.score}")
        """
        if not chunks:
            return OptimizationResult(
                chunks=[],
                total_tokens=0,
                original_count=0,
                optimized_count=0,
                tokens_saved=0,
                removed_redundant=0,
                compressed=0,
                strategy_used=strategy or PackingStrategy.RELEVANCE,
            )

        # Resolve configuration
        opt_config = self._resolve_config(config, max_tokens, strategy)

        logger.debug(
            "context_optimization_start",
            chunk_count=len(chunks),
            max_tokens=opt_config.max_tokens,
            strategy=opt_config.strategy.value,
        )

        # Get strategy and execute
        packer = self._strategies.get(opt_config.strategy)
        if not packer:
            raise ValueError(f"Unknown strategy: {opt_config.strategy}")

        result = await packer.pack(chunks, opt_config, self._token_counter)

        logger.info(
            "context_optimization_complete",
            original_count=result.original_count,
            optimized_count=result.optimized_count,
            total_tokens=result.total_tokens,
            tokens_saved=result.tokens_saved,
            strategy_used=result.strategy_used.value,
        )

        return result

    def calculate_available_tokens(
        self,
        model_context_window: int,
        system_prompt_tokens: int | None = None,
        reserve_for_response: int = 500,
    ) -> int:
        """
        Calculate available tokens for context.

        Args:
            model_context_window: Total context window for model
            system_prompt_tokens: Tokens used by system prompt
            reserve_for_response: Reserve tokens for LLM response

        Returns:
            Available tokens for context chunks
        """
        system = system_prompt_tokens or self._default_config.system_prompt_tokens
        overhead = self._default_config.overhead_tokens
        available = model_context_window - system - reserve_for_response - overhead
        return max(0, available)

    def estimate_chunk_tokens(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[int]:
        """
        Estimate token count for each chunk.

        Args:
            chunks: Chunks to count

        Returns:
            List of token counts in same order
        """
        return [
            self._token_counter.count(chunk.content).token_count
            for chunk in chunks
        ]

    def _resolve_config(
        self,
        config: OptimizationConfig | None,
        max_tokens: int | None,
        strategy: PackingStrategy | None,
    ) -> OptimizationConfig:
        """Resolve final configuration from defaults and overrides."""
        base = config or self._default_config

        if max_tokens is not None and strategy is not None:
            return OptimizationConfig(
                max_tokens=max_tokens,
                strategy=strategy,
                system_prompt_tokens=base.system_prompt_tokens,
                overhead_tokens=base.overhead_tokens,
                relevance_threshold=base.relevance_threshold,
                diversity_weight=base.diversity_weight,
                redundancy_threshold=base.redundancy_threshold,
                compress_below=base.compress_below,
            )
        elif max_tokens is not None:
            return OptimizationConfig(
                max_tokens=max_tokens,
                strategy=base.strategy,
                system_prompt_tokens=base.system_prompt_tokens,
                overhead_tokens=base.overhead_tokens,
                relevance_threshold=base.relevance_threshold,
                diversity_weight=base.diversity_weight,
                redundancy_threshold=base.redundancy_threshold,
                compress_below=base.compress_below,
            )
        elif strategy is not None:
            return OptimizationConfig(
                max_tokens=base.max_tokens,
                strategy=strategy,
                system_prompt_tokens=base.system_prompt_tokens,
                overhead_tokens=base.overhead_tokens,
                relevance_threshold=base.relevance_threshold,
                diversity_weight=base.diversity_weight,
                redundancy_threshold=base.redundancy_threshold,
                compress_below=base.compress_below,
            )

        return base


def create_context_optimizer(
    max_tokens: int | None = None,
    strategy: PackingStrategy = PackingStrategy.REMOVE_REDUNDANCY,
    provider: LLMProvider = LLMProvider.OPENAI,
) -> ContextOptimizer:
    """
    Factory function to create a configured ContextOptimizer.

    Args:
        max_tokens: Default maximum tokens for context
        strategy: Default packing strategy
        provider: LLM provider for token counting

    Returns:
        Configured ContextOptimizer instance

    Example:
        >>> optimizer = create_context_optimizer(
        ...     max_tokens=2000,
        ...     strategy=PackingStrategy.DIVERSITY,
        ... )
        >>> result = await optimizer.optimize_context(chunks)
    """
    token_counter = TokenCounter(default_provider=provider)
    config = OptimizationConfig(
        max_tokens=max_tokens or (DEFAULT_MAX_TOKENS - DEFAULT_SYSTEM_PROMPT_TOKENS),
        strategy=strategy,
    )
    return ContextOptimizer(token_counter=token_counter, default_config=config)


__all__ = [
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
]
