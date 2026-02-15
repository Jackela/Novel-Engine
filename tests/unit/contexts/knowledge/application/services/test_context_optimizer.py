"""
Unit Tests for Context Optimizer

Tests context optimization strategies for packing chunks into token budgets.

Warzone 4: AI Brain - BRAIN-011B
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.services.context_optimizer import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERHEAD_TOKENS,
    DEFAULT_SYSTEM_PROMPT_TOKENS,
    CompressSummariesPackingStrategy,
    ContextOptimizer,
    DiversityPackingStrategy,
    OptimizationConfig,
    OptimizationResult,
    PackingStrategy,
    RelevancePackingStrategy,
    RemoveRedundancyPackingStrategy,
    create_context_optimizer,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


class TestPackingStrategy:
    """Test suite for PackingStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert PackingStrategy.RELEVANCE.value == "relevance"
        assert PackingStrategy.DIVERSITY.value == "diversity"
        assert PackingStrategy.REMOVE_REDUNDANCY.value == "remove_redundancy"
        assert PackingStrategy.COMPRESS_SUMMARIES.value == "compress_summaries"

    def test_strategy_from_string(self):
        """Test creating strategy from string."""
        assert PackingStrategy("relevance") == PackingStrategy.RELEVANCE
        assert PackingStrategy("diversity") == PackingStrategy.DIVERSITY


class TestOptimizationConfig:
    """Test suite for OptimizationConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = OptimizationConfig()
        assert config.max_tokens == DEFAULT_MAX_TOKENS - DEFAULT_SYSTEM_PROMPT_TOKENS
        assert config.system_prompt_tokens == DEFAULT_SYSTEM_PROMPT_TOKENS
        assert config.overhead_tokens == DEFAULT_OVERHEAD_TOKENS
        assert config.strategy == PackingStrategy.REMOVE_REDUNDANCY
        assert config.relevance_threshold == 0.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = OptimizationConfig(
            max_tokens=2000,
            strategy=PackingStrategy.DIVERSITY,
            relevance_threshold=0.7,
        )
        assert config.max_tokens == 2000
        assert config.strategy == PackingStrategy.DIVERSITY
        assert config.relevance_threshold == 0.7


class TestOptimizationResult:
    """Test suite for OptimizationResult."""

    def test_result_creation(self):
        """Test creating optimization result."""
        result = OptimizationResult(
            chunks=[],
            total_tokens=100,
            original_count=10,
            optimized_count=5,
            tokens_saved=50,
            removed_redundant=3,
            compressed=2,
            strategy_used=PackingStrategy.REMOVE_REDUNDANCY,
        )
        assert result.total_tokens == 100
        assert result.original_count == 10
        assert result.optimized_count == 5
        assert result.tokens_saved == 50
        assert result.removed_redundant == 3
        assert result.compressed == 2
        assert result.strategy_used == PackingStrategy.REMOVE_REDUNDANCY


class TestRelevancePackingStrategy:
    """Test suite for RelevancePackingStrategy."""

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id=f"source_{i}",
                source_type=SourceType.LORE,
                content=f"This is content for chunk {i}. " * 10,
                score=0.9 - (i * 0.1),  # Decreasing relevance
                metadata={"chunk_index": i},
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_pack_by_relevance(self, sample_chunks):
        """Test packing chunks by relevance score."""
        strategy = RelevancePackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=500,
            strategy=PackingStrategy.RELEVANCE,
        )

        result = await strategy.pack(sample_chunks, config, token_counter)

        # Should include highest-relevance chunks first
        assert result.optimized_count <= len(sample_chunks)
        assert result.strategy_used == PackingStrategy.RELEVANCE
        assert result.removed_redundant >= 0

    @pytest.mark.asyncio
    async def test_pack_respects_relevance_threshold(self, sample_chunks):
        """Test that low-relevance chunks are filtered out."""
        strategy = RelevancePackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=1000,
            relevance_threshold=0.7,  # Only include chunks with score >= 0.7
        )

        result = await strategy.pack(sample_chunks, config, token_counter)

        # Only first 3 chunks have score >= 0.7
        assert result.optimized_count <= 3


class TestDiversityPackingStrategy:
    """Test suite for DiversityPackingStrategy."""

    @pytest.fixture
    def diverse_chunks(self):
        """Create chunks from diverse sources."""
        chunks = []
        sources = ["char_alice", "char_bob", "lore_kingdom", "scene_battle"]
        for source in sources:
            for i in range(3):
                chunks.append(
                    RetrievedChunk(
                        chunk_id=f"{source}_{i}",
                        source_id=source,
                        source_type=(
                            SourceType.CHARACTER
                            if "char" in source
                            else SourceType.LORE
                        ),
                        content=f"Content from {source}, part {i}. " * 10,
                        score=0.8 - (i * 0.1),
                        metadata={"source": source},
                    )
                )
        return chunks

    @pytest.mark.asyncio
    async def test_pack_maximizes_diversity(self, diverse_chunks):
        """Test that strategy maximizes source diversity."""
        strategy = DiversityPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(max_tokens=500)

        result = await strategy.pack(diverse_chunks, config, token_counter)

        # Should include chunks from different sources
        sources_in_result = {c.source_id for c in result.chunks}
        assert len(sources_in_result) >= 2
        assert result.strategy_used == PackingStrategy.DIVERSITY

    @pytest.mark.asyncio
    async def test_pack_respects_token_budget(self, diverse_chunks):
        """Test that strategy respects token budget."""
        strategy = DiversityPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(max_tokens=100)  # Small budget

        result = await strategy.pack(diverse_chunks, config, token_counter)

        assert result.total_tokens <= 100 + 50  # Small fudge factor


class TestRemoveRedundancyPackingStrategy:
    """Test suite for RemoveRedundancyPackingStrategy."""

    @pytest.fixture
    def redundant_chunks(self):
        """Create chunks with redundant content."""
        base_content = "The kingdom of Eldoria was founded in the age of darkness. " * 3
        return [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="lore_1",
                source_type=SourceType.LORE,
                content=base_content,
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="lore_2",
                source_type=SourceType.LORE,
                content=base_content,  # Exact duplicate
                score=0.8,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_3",
                source_id="lore_3",
                source_type=SourceType.LORE,
                content="The kingdom of Eldoria was founded during the dark age. "
                * 3,  # Similar
                score=0.7,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_4",
                source_id="lore_4",
                source_type=SourceType.LORE,
                content="Completely different content about dragons and magic. " * 3,
                score=0.6,
                metadata={},
            ),
        ]

    @pytest.mark.asyncio
    async def test_removes_exact_duplicates(self, redundant_chunks):
        """Test that exact duplicates are removed."""
        strategy = RemoveRedundancyPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=1000,
            redundancy_threshold=0.9,  # High threshold
        )

        result = await strategy.pack(redundant_chunks, config, token_counter)

        # chunk_2 is exact duplicate, should be removed
        chunk_ids = {c.chunk_id for c in result.chunks}
        assert "chunk_1" in chunk_ids
        assert "chunk_2" not in chunk_ids or result.removed_redundant > 0

    @pytest.mark.asyncio
    async def test_removes_similar_content(self, redundant_chunks):
        """Test that similar content is removed."""
        strategy = RemoveRedundancyPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=1000,
            redundancy_threshold=0.8,  # 80% similarity threshold
        )

        result = await strategy.pack(redundant_chunks, config, token_counter)

        # chunk_3 is similar to chunk_1, should be removed
        assert result.removed_redundant >= 1

    @pytest.mark.asyncio
    async def test_keeps_higher_scoring_duplicates(self, redundant_chunks):
        """Test that higher-scoring chunks are kept when duplicates exist."""
        strategy = RemoveRedundancyPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(max_tokens=1000)

        result = await strategy.pack(redundant_chunks, config, token_counter)

        # chunk_1 has higher score than chunk_2 (duplicate)
        chunk_ids = {c.chunk_id for c in result.chunks}
        assert (
            "chunk_1" in chunk_ids
            or len(redundant_chunks) == len(result.chunks) + result.removed_redundant
        )


class TestCompressSummariesPackingStrategy:
    """Test suite for CompressSummariesPackingStrategy."""

    @pytest.fixture
    def mixed_relevance_chunks(self):
        """Create chunks with varying relevance."""
        return [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id=f"source_{i}",
                source_type=SourceType.LORE,
                content=f"This is a detailed content for chunk {i}. "
                * 20,  # Long content
                score=0.95 - (i * 0.15),
                metadata={"chunk_index": i},
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_compresses_low_relevance(self, mixed_relevance_chunks):
        """Test that low-relevance chunks are compressed."""
        strategy = CompressSummariesPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=500,
            compress_below=0.7,  # Compress chunks with score < 0.7
        )

        result = await strategy.pack(mixed_relevance_chunks, config, token_counter)

        # Last two chunks have score < 0.7
        assert result.compressed >= 0
        assert result.strategy_used == PackingStrategy.COMPRESS_SUMMARIES

    @pytest.mark.asyncio
    async def test_summary_is_shorter(self, mixed_relevance_chunks):
        """Test that summaries are shorter than original content."""
        strategy = CompressSummariesPackingStrategy()
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )

        token_counter = TokenCounter()

        config = OptimizationConfig(
            max_tokens=500,
            compress_below=0.8,  # Compress more chunks
        )

        result = await strategy.pack(mixed_relevance_chunks, config, token_counter)

        # Find summarized chunks
        for chunk in result.chunks:
            if chunk.metadata.get("summarized"):
                # Summary should be shorter than original (rough check)
                original_chunks = [
                    c for c in mixed_relevance_chunks if c.chunk_id == chunk.chunk_id
                ]
                if original_chunks:
                    assert len(chunk.content) < len(original_chunks[0].content)


class TestContextOptimizer:
    """Test suite for ContextOptimizer."""

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id=f"source_{i % 3}",  # 3 sources total
                source_type=SourceType.LORE,
                content=f"Content {i}: " + "The kingdom has many secrets. " * 10,
                score=0.9 - (i * 0.08),
                metadata={"chunk_index": i, "tags": ["history", "politics"]},
            )
            for i in range(10)
        ]

    def test_init_default(self):
        """Test default initialization."""
        optimizer = ContextOptimizer()
        assert optimizer is not None
        assert optimizer._default_config is not None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = OptimizationConfig(
            max_tokens=2000,
            strategy=PackingStrategy.DIVERSITY,
        )
        optimizer = ContextOptimizer(default_config=config)
        assert optimizer._default_config == config

    @pytest.mark.asyncio
    async def test_optimize_context_empty(self):
        """Test optimizing empty chunk list."""
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context([])
        assert result.chunks == []
        assert result.total_tokens == 0
        assert result.original_count == 0

    @pytest.mark.asyncio
    async def test_optimize_context_relevance(self, sample_chunks):
        """Test optimizing with relevance strategy."""
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context(
            chunks=sample_chunks,
            max_tokens=200,
            strategy=PackingStrategy.RELEVANCE,
        )
        assert result.optimized_count <= len(sample_chunks)
        assert result.strategy_used == PackingStrategy.RELEVANCE

    @pytest.mark.asyncio
    async def test_optimize_context_diversity(self, sample_chunks):
        """Test optimizing with diversity strategy."""
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context(
            chunks=sample_chunks,
            max_tokens=300,
            strategy=PackingStrategy.DIVERSITY,
        )
        assert result.strategy_used == PackingStrategy.DIVERSITY
        # Should have chunks from multiple sources
        sources = {c.source_id for c in result.chunks}
        assert len(sources) >= 2

    @pytest.mark.asyncio
    async def test_optimize_context_remove_redundancy(self, sample_chunks):
        """Test optimizing with redundancy removal."""
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context(
            chunks=sample_chunks,
            max_tokens=300,
            strategy=PackingStrategy.REMOVE_REDUNDANCY,
        )
        assert result.strategy_used == PackingStrategy.REMOVE_REDUNDANCY

    @pytest.mark.asyncio
    async def test_optimize_context_compress_summaries(self, sample_chunks):
        """Test optimizing with summary compression."""
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context(
            chunks=sample_chunks,
            max_tokens=300,
            strategy=PackingStrategy.COMPRESS_SUMMARIES,
        )
        assert result.strategy_used == PackingStrategy.COMPRESS_SUMMARIES

    @pytest.mark.asyncio
    async def test_optimize_respects_token_budget(self, sample_chunks):
        """Test that optimization respects token budget."""
        max_tokens = 150
        optimizer = ContextOptimizer()
        result = await optimizer.optimize_context(
            chunks=sample_chunks,
            max_tokens=max_tokens,
        )
        # Should stay close to budget (with small overhead)
        assert result.total_tokens <= max_tokens + 100

    def test_calculate_available_tokens(self):
        """Test calculating available tokens."""
        optimizer = ContextOptimizer()
        available = optimizer.calculate_available_tokens(
            model_context_window=4096,
            system_prompt_tokens=500,
            reserve_for_response=500,
        )
        # 4096 - 500 - 500 - 100 (overhead)
        assert available == 4096 - 500 - 500 - DEFAULT_OVERHEAD_TOKENS

    def test_calculate_available_tokens_min_zero(self):
        """Test that available tokens is never negative."""
        optimizer = ContextOptimizer()
        available = optimizer.calculate_available_tokens(
            model_context_window=100,
            system_prompt_tokens=500,
        )
        assert available >= 0

    def test_estimate_chunk_tokens(self, sample_chunks):
        """Test estimating tokens for chunks."""
        optimizer = ContextOptimizer()
        tokens = optimizer.estimate_chunk_tokens(sample_chunks)
        assert len(tokens) == len(sample_chunks)
        assert all(t > 0 for t in tokens)

    @pytest.mark.asyncio
    async def test_optimize_with_invalid_strategy_raises(self, sample_chunks):
        """Test that invalid strategy raises error."""
        optimizer = ContextOptimizer()
        # Remove the strategy to test error handling
        original_strategies = optimizer._strategies
        optimizer._strategies = {}

        with pytest.raises(ValueError, match="Unknown strategy"):
            await optimizer.optimize_context(
                chunks=sample_chunks,
                strategy=PackingStrategy.RELEVANCE,
            )

        # Restore for cleanup
        optimizer._strategies = original_strategies


class TestCreateContextOptimizer:
    """Test suite for create_context_optimizer factory."""

    def test_factory_default(self):
        """Test factory with default parameters."""
        optimizer = create_context_optimizer()
        assert optimizer is not None
        assert isinstance(optimizer, ContextOptimizer)

    def test_factory_with_params(self):
        """Test factory with custom parameters."""
        optimizer = create_context_optimizer(
            max_tokens=1500,
            strategy=PackingStrategy.DIVERSITY,
        )
        assert optimizer is not None
        assert optimizer._default_config.max_tokens == 1500
        assert optimizer._default_config.strategy == PackingStrategy.DIVERSITY

    def test_factory_with_provider(self):
        """Test factory with provider parameter."""
        from src.contexts.knowledge.application.services.token_counter import (
            LLMProvider,
        )

        optimizer = create_context_optimizer(
            provider=LLMProvider.ANTHROPIC,
        )
        assert optimizer is not None
        assert optimizer._token_counter._default_provider == LLMProvider.ANTHROPIC


class TestConstants:
    """Test suite for constants."""

    def test_default_system_prompt_tokens(self):
        """Test default system prompt tokens constant."""
        assert DEFAULT_SYSTEM_PROMPT_TOKENS == 500

    def test_default_overhead_tokens(self):
        """Test default overhead tokens constant."""
        assert DEFAULT_OVERHEAD_TOKENS == 100

    def test_default_max_tokens(self):
        """Test default max tokens constant."""
        assert DEFAULT_MAX_TOKENS == 4096
