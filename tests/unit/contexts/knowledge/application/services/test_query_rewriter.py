"""
Unit Tests for Query Rewriter Service

Warzone 4: AI Brain - BRAIN-009A

Tests for the query rewriting service that improves RAG retrieval
by generating query variants with synonym expansion and sub-query decomposition.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.contexts.knowledge.application.services.query_rewriter import (
    QueryRewriter,
    RewriteStrategy,
    RewriteConfig,
    RewriteResult,
    QueryRewriterCacheEntry,
    DEFAULT_STRATEGY,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_VARIANTS,
    DEFAULT_INCLUDE_ORIGINAL,
)
from src.contexts.knowledge.application.ports.i_llm_client import (
    ILLMClient,
    LLMRequest,
    LLMResponse,
    LLMError,
)
from src.contexts.knowledge.infrastructure.adapters.gemini_llm_client import (
    MockLLMClient,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        # Return different responses based on strategy in system prompt
        system = request.system_prompt.lower()
        if "decompose" in system:
            return LLMResponse(
                text='["main character goals", "hero motivation", "protagonist objectives"]',
                model="mock-model",
            )
        else:
            return LLMResponse(
                text='["main character motivation", "hero driving forces", "protagonist goals"]',
                model="mock-model",
            )

    client.generate = mock_generate
    return client


@pytest.fixture
def failing_llm_client():
    """Create a mock LLM client that always fails."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        raise LLMError("API error")

    client.generate = mock_generate
    return client


@pytest.fixture
def json_failing_llm_client():
    """Create a mock LLM client that returns invalid JSON."""
    client = AsyncMock(spec=ILLMClient)

    async def mock_generate(request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="This is not valid JSON at all\nJust plain text response",
            model="mock-model",
        )

    client.generate = mock_generate
    return client


@pytest.fixture
def default_config():
    """Create default rewrite configuration."""
    return RewriteConfig()


@pytest.fixture
def query_rewriter(mock_llm_client):
    """Create a QueryRewriter instance with mock LLM."""
    return QueryRewriter(llm_client=mock_llm_client)


class TestRewriteConfig:
    """Tests for RewriteConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RewriteConfig()

        assert config.strategy == DEFAULT_STRATEGY
        assert config.max_variants == DEFAULT_MAX_VARIANTS
        assert config.include_original == DEFAULT_INCLUDE_ORIGINAL
        assert config.temperature == DEFAULT_TEMPERATURE

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RewriteConfig(
            strategy=RewriteStrategy.DECOMPOSE,
            max_variants=5,
            include_original=False,
            temperature=0.5,
        )

        assert config.strategy == RewriteStrategy.DECOMPOSE
        assert config.max_variants == 5
        assert config.include_original is False
        assert config.temperature == 0.5

    def test_config_validation_max_variants_too_low(self):
        """Test validation rejects max_variants < 1."""
        with pytest.raises(ValueError, match="max_variants must be at least 1"):
            RewriteConfig(max_variants=0)

    def test_config_validation_max_variants_too_high(self):
        """Test validation rejects max_variants > 10."""
        with pytest.raises(ValueError, match="max_variants must not exceed 10"):
            RewriteConfig(max_variants=11)

    def test_config_validation_temperature_out_of_range(self):
        """Test validation rejects temperature outside 0-2."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            RewriteConfig(temperature=2.5)

    def test_config_frozen(self):
        """Test config is immutable (frozen dataclass)."""
        config = RewriteConfig()
        with pytest.raises(AttributeError):
            config.max_variants = 5


class TestRewriteResult:
    """Tests for RewriteResult value object."""

    def test_result_creation(self):
        """Test creating a rewrite result."""
        result = RewriteResult(
            original_query="protagonist motivation",
            variants=["protagonist motivation", "hero goals"],
            strategy=RewriteStrategy.SYNONYM,
            cached=False,
        )

        assert result.original_query == "protagonist motivation"
        assert len(result.variants) == 2
        assert result.strategy == RewriteStrategy.SYNONYM
        assert result.cached is False

    def test_result_frozen(self):
        """Test result is immutable (frozen dataclass)."""
        result = RewriteResult(
            original_query="test",
            variants=["test"],
            strategy=RewriteStrategy.SYNONYM,
        )
        with pytest.raises(AttributeError):
            result.variants = ["other"]


class TestQueryRewriter:
    """Tests for QueryRewriter service."""

    def test_initialization(self, mock_llm_client):
        """Test QueryRewriter initialization."""
        rewriter = QueryRewriter(llm_client=mock_llm_client)

        assert rewriter._llm == mock_llm_client
        assert rewriter._config.strategy == DEFAULT_STRATEGY
        assert rewriter._cache_enabled is True

    def test_initialization_with_custom_config(self, mock_llm_client):
        """Test initialization with custom config."""
        config = RewriteConfig(strategy=RewriteStrategy.DECOMPOSE, max_variants=2)
        rewriter = QueryRewriter(llm_client=mock_llm_client, default_config=config)

        assert rewriter._config.strategy == RewriteStrategy.DECOMPOSE
        assert rewriter._config.max_variants == 2

    def test_initialization_with_cache_disabled(self, mock_llm_client):
        """Test initialization with cache disabled."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=False)

        assert rewriter._cache_enabled is False

    @pytest.mark.asyncio
    async def test_rewrite_synonym_strategy(self, query_rewriter):
        """Test rewrite with synonym expansion strategy."""
        config = RewriteConfig(strategy=RewriteStrategy.SYNONYM, max_variants=3)
        result = await query_rewriter.rewrite("protagonist motivation", config)

        assert result.original_query == "protagonist motivation"
        assert result.strategy == RewriteStrategy.SYNONYM
        assert len(result.variants) >= 1
        assert "protagonist motivation" in result.variants
        # Check for expanded variants
        assert any("hero" in v.lower() or "main" in v.lower() for v in result.variants)

    @pytest.mark.asyncio
    async def test_rewrite_decompose_strategy(self, query_rewriter):
        """Test rewrite with query decomposition strategy."""
        config = RewriteConfig(strategy=RewriteStrategy.DECOMPOSE, max_variants=3)
        result = await query_rewriter.rewrite("protagonist motivation and goals", config)

        assert result.strategy == RewriteStrategy.DECOMPOSE
        assert len(result.variants) >= 1
        assert "protagonist motivation and goals" in result.variants

    @pytest.mark.asyncio
    async def test_rewrite_hybrid_strategy(self, query_rewriter):
        """Test rewrite with hybrid strategy."""
        config = RewriteConfig(strategy=RewriteStrategy.HYBRID, max_variants=5)
        result = await query_rewriter.rewrite("brave warrior seeks revenge", config)

        assert result.strategy == RewriteStrategy.HYBRID
        assert len(result.variants) >= 1

    @pytest.mark.asyncio
    async def test_rewrite_includes_original_by_default(self, query_rewriter):
        """Test that original query is included by default."""
        result = await query_rewriter.rewrite("test query")

        assert "test query" in result.variants
        assert result.variants[0] == "test query"

    @pytest.mark.asyncio
    async def test_rewrite_exclude_original(self, query_rewriter):
        """Test excluding original query from variants."""
        config = RewriteConfig(include_original=False)
        result = await query_rewriter.rewrite("test query", config)

        # Original should not be in variants
        assert "test query" not in result.variants

    @pytest.mark.asyncio
    async def test_rewrite_max_variants_limit(self, query_rewriter):
        """Test that max_variants limits the number of results."""
        config = RewriteConfig(max_variants=2, include_original=True)
        result = await query_rewriter.rewrite("test query", config)

        # Should have original + at most 2 more = max 3
        assert len(result.variants) <= 3

    @pytest.mark.asyncio
    async def test_rewrite_empty_query_raises_error(self, query_rewriter):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await query_rewriter.rewrite("")

    @pytest.mark.asyncio
    async def test_rewrite_whitespace_only_query_raises_error(self, query_rewriter):
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await query_rewriter.rewrite("   ")

    @pytest.mark.asyncio
    async def test_rewrite_removes_duplicate_variants(self, mock_llm_client):
        """Test that duplicate variants are removed."""
        # Set up mock to return duplicates
        async def mock_generate(request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text='["test query", "test query", "another variant", "test query"]',
                model="mock-model",
            )

        mock_llm_client.generate = mock_generate
        rewriter = QueryRewriter(llm_client=mock_llm_client)

        result = await rewriter.rewrite("test query")

        # Duplicates should be removed
        assert result.variants.count("test query") == 1

    @pytest.mark.asyncio
    async def test_rewrite_on_llm_error_returns_original(self, failing_llm_client):
        """Test graceful degradation when LLM fails."""
        rewriter = QueryRewriter(llm_client=failing_llm_client)
        result = await rewriter.rewrite("test query")

        # Should return original query on error
        assert result.variants == ["test query"]

    @pytest.mark.asyncio
    async def test_rewrite_on_llm_error_excludes_original_if_configured(self, failing_llm_client):
        """Test error handling when include_original=False."""
        rewriter = QueryRewriter(llm_client=failing_llm_client)
        config = RewriteConfig(include_original=False)
        result = await rewriter.rewrite("test query", config)

        # Should return empty list on error when not including original
        assert result.variants == []

    @pytest.mark.asyncio
    async def test_rewrite_invalid_json_fallback(self, json_failing_llm_client):
        """Test fallback parsing when JSON is invalid."""
        rewriter = QueryRewriter(llm_client=json_failing_llm_client)
        result = await rewriter.rewrite("test query")

        # Should still return something (fallback parsing)
        assert len(result.variants) >= 1


class TestQueryRewriterCaching:
    """Tests for QueryRewriter caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, mock_llm_client):
        """Test that cache returns stored results."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=True)
        config = RewriteConfig(strategy=RewriteStrategy.SYNONYM)

        # First call - should hit LLM
        result1 = await rewriter.rewrite("test query", config)
        assert result1.cached is False

        # Second call - should use cache
        result2 = await rewriter.rewrite("test query", config)
        assert result2.cached is True
        assert result2.variants == result1.variants

    @pytest.mark.asyncio
    async def test_cache_key_includes_strategy(self, mock_llm_client):
        """Test that cache keys are strategy-specific."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=True)

        # Call with synonym strategy
        await rewriter.rewrite(
            "test query",
            RewriteConfig(strategy=RewriteStrategy.SYNONYM),
        )

        # Call with decompose strategy - should not hit cache
        result2 = await rewriter.rewrite(
            "test query",
            RewriteConfig(strategy=RewriteStrategy.DECOMPOSE),
        )

        # Results should be different (different LLM responses for each strategy)
        assert result2.cached is False

    @pytest.mark.asyncio
    async def test_cache_key_case_insensitive(self, mock_llm_client):
        """Test that cache keys are case-insensitive."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=True)

        await rewriter.rewrite("Test Query")
        result2 = await rewriter.rewrite("test query")

        # Second call should hit cache (case-insensitive)
        assert result2.cached is True

    @pytest.mark.asyncio
    async def test_clear_cache(self, mock_llm_client):
        """Test clearing the cache."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=True)

        # Populate cache
        await rewriter.rewrite("test query")
        assert len(rewriter._cache) > 0

        # Clear cache
        rewriter.clear_cache()
        assert len(rewriter._cache) == 0

    @pytest.mark.asyncio
    async def test_cache_stats(self, mock_llm_client):
        """Test getting cache statistics."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=True)

        stats = rewriter.get_cache_stats()
        assert stats["cache_size"] == 0
        assert stats["cache_enabled"] is True

        # Add some entries
        await rewriter.rewrite("test query 1")
        await rewriter.rewrite("test query 2")

        stats = rewriter.get_cache_stats()
        assert stats["cache_size"] == 2

    @pytest.mark.asyncio
    async def test_cache_disabled_skips_cache(self, mock_llm_client):
        """Test that disabling cache skips caching logic."""
        rewriter = QueryRewriter(llm_client=mock_llm_client, cache_enabled=False)

        result1 = await rewriter.rewrite("test query")
        result2 = await rewriter.rewrite("test query")

        # Both should be marked as not cached
        assert result1.cached is False
        assert result2.cached is False

        # Cache should remain empty
        assert len(rewriter._cache) == 0


class TestQueryRewriterSync:
    """Tests for synchronous rewrite method."""

    def test_rewrite_sync_basic(self):
        """Test synchronous rewrite with basic variants."""
        client = MockLLMClient()
        rewriter = QueryRewriter(llm_client=client)

        result = rewriter.rewrite_sync("brave warrior")

        assert result.original_query == "brave warrior"
        assert "brave warrior" in result.variants
        assert result.cached is False

    def test_rewrite_sync_with_synonyms(self):
        """Test synchronous rewrite generates synonyms."""
        client = MockLLMClient()
        rewriter = QueryRewriter(llm_client=client)

        result = rewriter.rewrite_sync("protagonist motivation")

        # Check for known synonyms
        assert any(
            "main character" in v.lower() or "hero" in v.lower()
            for v in result.variants
        )

    def test_rewrite_sync_respects_max_variants(self):
        """Test synchronous rewrite respects max_variants."""
        client = MockLLMClient()
        rewriter = QueryRewriter(llm_client=client)
        config = RewriteConfig(max_variants=2)

        result = rewriter.rewrite_sync("test query", config)

        assert len(result.variants) <= 3  # original + max_variants

    def test_rewrite_sync_excludes_original(self):
        """Test synchronous rewrite can exclude original."""
        client = MockLLMClient()
        rewriter = QueryRewriter(llm_client=client)
        config = RewriteConfig(include_original=False)

        result = rewriter.rewrite_sync("test query", config)

        assert "test query" not in result.variants


class TestQueryRewriterPrompts:
    """Tests for prompt generation and LLM interaction."""

    def test_synonym_strategy_prompt(self, query_rewriter):
        """Test that synonym strategy generates correct prompt."""
        prompt = query_rewriter._build_prompt("test query", query_rewriter._config)
        system = query_rewriter._get_system_prompt(RewriteStrategy.SYNONYM)

        assert "test query" in prompt
        assert "synonym" in system.lower() or "expansion" in system.lower()

    def test_decompose_strategy_prompt(self, query_rewriter):
        """Test that decompose strategy generates correct prompt."""
        system = query_rewriter._get_system_prompt(RewriteStrategy.DECOMPOSE)

        assert "decompose" in system.lower() or "sub-query" in system.lower()

    def test_hybrid_strategy_prompt(self, query_rewriter):
        """Test that hybrid strategy generates correct prompt."""
        system = query_rewriter._get_system_prompt(RewriteStrategy.HYBRID)

        # Hybrid should mention both approaches
        assert "expand" in system.lower() or "synonym" in system.lower()

    def test_parse_json_array_response(self, query_rewriter):
        """Test parsing JSON array response."""
        text = '["variant 1", "variant 2", "variant 3"]'
        variants = query_rewriter._parse_response(text, 5)

        assert len(variants) == 3
        assert "variant 1" in variants

    def test_parse_json_from_markdown(self, query_rewriter):
        """Test parsing JSON from markdown code block."""
        text = '```json\n["variant 1", "variant 2"]\n```'
        variants = query_rewriter._parse_response(text, 5)

        assert len(variants) == 2

    def test_parse_malformed_json_fallback(self, query_rewriter):
        """Test fallback parsing for malformed JSON."""
        text = "variant 1\nvariant 2\nvariant 3"
        variants = query_rewriter._parse_response(text, 5)

        # Should still extract something
        assert len(variants) >= 1

    def test_parse_respects_max_variants(self, query_rewriter):
        """Test parsing respects max_variants limit."""
        text = '["v1", "v2", "v3", "v4", "v5"]'
        variants = query_rewriter._parse_response(text, 3)

        assert len(variants) == 3


class TestRewriteStrategy:
    """Tests for RewriteStrategy enumeration."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert RewriteStrategy.SYNONYM == "synonym"
        assert RewriteStrategy.DECOMPOSE == "decompose"
        assert RewriteStrategy.HYBRID == "hybrid"

    def test_strategy_is_string(self):
        """Test strategy enum is string-compatible."""
        strategy = RewriteStrategy.SYNONYM
        assert strategy.value == "synonym"
        # String representation of enum includes the class name
        assert "synonym" in str(strategy).lower()


class TestQueryRewriterCacheEntry:
    """Tests for QueryRewriterCacheEntry value object."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = QueryRewriterCacheEntry(
            variants=["v1", "v2"],
            strategy=RewriteStrategy.SYNONYM,
        )

        assert entry.variants == ["v1", "v2"]
        assert entry.strategy == RewriteStrategy.SYNONYM


class TestMockLLMClient:
    """Tests for MockLLMClient test helper."""

    @pytest.mark.asyncio
    async def test_mock_returns_default_response(self):
        """Test mock returns default response."""
        client = MockLLMClient()
        request = LLMRequest(system_prompt="", user_prompt="test")

        response = await client.generate(request)

        assert response.text == "mock response"
        assert response.model == "mock-model"

    @pytest.mark.asyncio
    async def test_mock_returns_mapped_response(self):
        """Test mock returns mapped response."""
        client = MockLLMClient(responses={"test": "matched!"})
        request = LLMRequest(system_prompt="", user_prompt="this is a test")

        response = await client.generate(request)

        assert "matched!" in response.text

    @pytest.mark.asyncio
    async def test_mock_rewrite_query_response(self):
        """Test mock returns rewrite query response."""
        client = MockLLMClient()
        request = LLMRequest(
            system_prompt="rewrite the query",
            user_prompt="test"
        )

        response = await client.generate(request)

        # Should return JSON array format
        assert "[" in response.text

    def test_mock_call_count(self):
        """Test mock tracks call count."""
        client = MockLLMClient()

        # Sync wrapper for testing
        import asyncio

        async def make_calls():
            await client.generate(LLMRequest(system_prompt="", user_prompt="test1"))
            await client.generate(LLMRequest(system_prompt="", user_prompt="test2"))

        asyncio.run(make_calls())

        assert client.call_count == 2

    def test_mock_reset(self):
        """Test mock can be reset."""
        client = MockLLMClient()

        import asyncio

        async def make_call():
            await client.generate(LLMRequest(system_prompt="", user_prompt="test"))

        asyncio.run(make_call())
        assert client.call_count == 1

        client.reset()
        assert client.call_count == 0

    def test_mock_last_request(self):
        """Test mock tracks last request."""
        client = MockLLMClient()
        request = LLMRequest(system_prompt="sys", user_prompt="user")

        import asyncio

        async def make_call():
            await client.generate(request)

        asyncio.run(make_call())

        assert client.last_request == request
