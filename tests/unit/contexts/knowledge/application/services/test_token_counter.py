"""
Unit Tests for Token Counter

Tests token counting accuracy and fallback behavior for multiple LLM providers.

Warzone 4: AI Brain - BRAIN-011A
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.services.token_counter import (
    TokenCounter,
    LLMProvider,
    ModelFamily,
    TokenCountResult,
    create_token_counter,
    TIKTOKEN_AVAILABLE,
    MODEL_FAMILY_MAPPING,
)


class TestTokenCounter:
    """Test suite for TokenCounter class."""

    def test_init_default(self):
        """Test default initialization."""
        counter = TokenCounter()
        assert counter is not None
        assert counter._default_provider == LLMProvider.OPENAI

    def test_init_with_provider(self):
        """Test initialization with custom provider."""
        counter = TokenCounter(default_provider=LLMProvider.ANTHROPIC)
        assert counter._default_provider == LLMProvider.ANTHROPIC

    def test_init_with_model(self):
        """Test initialization with model name."""
        counter = TokenCounter(default_model="gpt-4")
        assert counter._default_provider == LLMProvider.OPENAI
        assert counter._default_family == ModelFamily.GPT4

    def test_init_with_claude_model(self):
        """Test initialization with Claude model."""
        counter = TokenCounter(default_model="claude-3-opus")
        assert counter._default_provider == LLMProvider.ANTHROPIC
        assert counter._default_family == ModelFamily.CLAUDE_3

    def test_init_with_gemini_model(self):
        """Test initialization with Gemini model."""
        counter = TokenCounter(default_model="gemini-1.5-pro")
        assert counter._default_provider == LLMProvider.GEMINI
        assert counter._default_family == ModelFamily.GEMINI_1

    def test_count_empty_string(self):
        """Test counting empty string."""
        counter = TokenCounter()
        result = counter.count("")
        assert result.token_count == 0
        assert result.provider == LLMProvider.OPENAI

    def test_count_simple_text(self):
        """Test counting simple text."""
        counter = TokenCounter()
        result = counter.count("Hello, world!")
        assert result.token_count > 0
        if TIKTOKEN_AVAILABLE:
            assert result.method in ("tiktoken", "estimation")

    def test_count_with_model_override(self):
        """Test counting with model parameter override."""
        counter = TokenCounter(default_model="gpt-4")
        result = counter.count("Test text", model="gpt-4o")
        assert result.provider == LLMProvider.OPENAI
        assert result.model_family == ModelFamily.GPT4O

    def test_count_with_provider_override(self):
        """Test counting with provider parameter override."""
        counter = TokenCounter(default_provider=LLMProvider.OPENAI)
        result = counter.count("Test text", provider=LLMProvider.ANTHROPIC)
        assert result.provider == LLMProvider.ANTHROPIC

    def test_count_with_family_override(self):
        """Test counting with family parameter override."""
        counter = TokenCounter(default_model="gpt-4")
        result = counter.count("Test text", model_family=ModelFamily.GPT35)
        assert result.model_family == ModelFamily.GPT35

    def test_count_invalid_type_raises(self):
        """Test that counting non-string raises ValueError."""
        counter = TokenCounter()
        with pytest.raises(ValueError, match="must be a string"):
            counter.count(123)  # type: ignore

    def test_count_returns_token_count_result(self):
        """Test that count returns TokenCountResult."""
        counter = TokenCounter()
        result = counter.count("Hello")
        assert isinstance(result, TokenCountResult)
        assert hasattr(result, "token_count")
        assert hasattr(result, "method")
        assert hasattr(result, "provider")
        assert hasattr(result, "model_family")

    def test_count_batch_empty_list(self):
        """Test batch counting with empty list."""
        counter = TokenCounter()
        results = counter.count_batch([])
        assert results == []

    def test_count_batch_multiple_texts(self):
        """Test batch counting multiple texts."""
        counter = TokenCounter()
        texts = ["Hello", "world", "test"]
        results = counter.count_batch(texts)
        assert len(results) == 3
        for result in results:
            assert result.token_count >= 0

    def test_count_batch_with_empty_strings(self):
        """Test batch counting with empty strings."""
        counter = TokenCounter()
        texts = ["Hello", "", "world"]
        results = counter.count_batch(texts)
        assert len(results) == 3
        assert results[0].token_count > 0
        assert results[1].token_count == 0
        assert results[2].token_count > 0

    def test_count_from_messages_empty(self):
        """Test counting empty message list."""
        counter = TokenCounter()
        result = counter.count_from_messages([])
        # Should have reply priming tokens
        assert result.token_count >= 0

    def test_count_from_messages_single(self):
        """Test counting single message."""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello, world!"}]
        result = counter.count_from_messages(messages)
        assert result.token_count > 0
        # Content tokens + format overhead
        assert result.token_count >= 4  # At least format overhead

    def test_count_from_messages_multiple(self):
        """Test counting multiple messages."""
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = counter.count_from_messages(messages)
        assert result.token_count > 10  # Multiple messages with overhead

    def test_count_from_messages_with_model(self):
        """Test counting messages with model parameter."""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Test"}]
        result = counter.count_from_messages(messages, model="gpt-4")
        assert result.token_count > 0
        assert result.provider == LLMProvider.OPENAI

    def test_estimate_max_chunks(self):
        """Test estimating max chunks that fit in budget."""
        counter = TokenCounter()
        text = "This is a test sentence for chunk estimation."

        # First, get the token count
        count_result = counter.count(text)
        tokens_per_chunk = count_result.token_count

        # Estimate max chunks
        max_chunks = counter.estimate_max_chunks(text, max_tokens=tokens_per_chunk * 5)
        assert max_chunks == 5

    def test_estimate_max_chunks_empty_text(self):
        """Test estimating max chunks with empty text."""
        counter = TokenCounter()
        max_chunks = counter.estimate_max_chunks("", max_tokens=100)
        assert max_chunks == 0

    def test_estimate_max_chunks_with_model(self):
        """Test estimating max chunks with model parameter."""
        counter = TokenCounter()
        text = "Test text for estimation."

        max_chunks = counter.estimate_max_chunks(text, max_tokens=100, model="gpt-4")
        assert max_chunks > 0

    def test_truncate_to_tokens_under_budget(self):
        """Test truncating text that's under budget."""
        counter = TokenCounter()
        text = "Short text"
        result = counter.truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_truncate_to_tokens_over_budget(self):
        """Test truncating text that's over budget."""
        counter = TokenCounter()
        text = "This is a much longer text that needs to be truncated."
        result = counter.truncate_to_tokens(text, max_tokens=5)
        assert len(result) < len(text)

    def test_truncate_to_tokens_with_ellipsis(self):
        """Test truncating with ellipsis."""
        counter = TokenCounter()
        text = "This is a very long text that definitely needs to be truncated."
        result = counter.truncate_to_tokens(text, max_tokens=5, add_ellipsis=True)
        assert result.endswith("...")

    def test_truncate_to_tokens_empty_text(self):
        """Test truncating empty text."""
        counter = TokenCounter()
        result = counter.truncate_to_tokens("", max_tokens=100)
        assert result == ""

    def test_is_available(self):
        """Test availability checker."""
        counter = TokenCounter()
        availability = counter.is_available()
        assert "tiktoken" in availability
        assert "estimation" in availability
        assert availability["estimation"] is True
        assert availability["tiktoken"] == TIKTOKEN_AVAILABLE

    def test_detect_provider_gpt4o(self):
        """Test provider detection for GPT-4o."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("gpt-4o")
        assert provider == LLMProvider.OPENAI
        assert family == ModelFamily.GPT4O

    def test_detect_provider_gpt4_turbo(self):
        """Test provider detection for GPT-4 Turbo."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("gpt-4-turbo")
        assert provider == LLMProvider.OPENAI
        assert family == ModelFamily.GPT4

    def test_detect_provider_claude_3(self):
        """Test provider detection for Claude 3."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("claude-3-opus")
        assert provider == LLMProvider.ANTHROPIC
        assert family == ModelFamily.CLAUDE_3

    def test_detect_provider_gemini(self):
        """Test provider detection for Gemini."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("gemini-1.5-pro")
        assert provider == LLMProvider.GEMINI
        assert family == ModelFamily.GEMINI_1

    def test_detect_provider_gemini_2(self):
        """Test provider detection for Gemini 2.0."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("gemini-2.0-flash")
        assert provider == LLMProvider.GEMINI
        assert family == ModelFamily.GEMINI_2

    def test_detect_provider_unknown(self):
        """Test provider detection for unknown model."""
        counter = TokenCounter()
        provider, family = counter._detect_provider_and_family("unknown-model")
        assert provider == LLMProvider.GENERIC
        assert family == ModelFamily.GENERIC

    def test_llm_provider_enum(self):
        """Test LLMProvider enum properties."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.GEMINI == "gemini"
        assert LLMProvider.GENERIC == "generic"

    def test_model_family_enum(self):
        """Test ModelFamily enum properties."""
        assert ModelFamily.GPT4O == "gpt-4o"
        assert ModelFamily.GPT4 == "gpt-4"
        assert ModelFamily.CLAUDE_3 == "claude-3"


class TestTokenCounterWithTiktoken:
    """Tests specifically for tiktoken integration (when available)."""

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_tiktoken_accurate_counting(self):
        """Test that tiktoken provides accurate counts for known text."""
        counter = TokenCounter()
        # "Hello, world!" should be 4 tokens in cl100k_base
        result = counter.count("Hello, world!", model="gpt-4")
        # Using tiktoken, this should be exactly 4 tokens
        assert result.token_count == 4
        assert result.method == "tiktoken"

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_tiktoken_gpt4o_encoding(self):
        """Test GPT-4o encoding (o200k_base)."""
        counter = TokenCounter()
        # GPT-4o uses a different encoding
        result = counter.count("Hello, world!", model="gpt-4o")
        assert result.method == "tiktoken"
        assert result.model_family == ModelFamily.GPT4O

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_tiktoken_anthropic_fallback(self):
        """Test that Anthropic uses tiktoken as approximation."""
        counter = TokenCounter()
        result = counter.count("Hello, world!", provider=LLMProvider.ANTHROPIC)
        # Should use tiktoken for Anthropic (as approximation)
        assert result.method == "tiktoken"

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_tiktoken_batch_counting(self):
        """Test batch counting with tiktoken."""
        counter = TokenCounter()
        texts = ["Hello", "world", "test"]
        results = counter.count_batch(texts, model="gpt-4")
        for result in results:
            assert result.method == "tiktoken"

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_tiktoken_caching(self):
        """Test that tiktoken encodings are cached."""
        counter = TokenCounter()
        # First call should create encoding
        counter.count("test", model="gpt-4")
        assert ModelFamily.GPT4 in counter._tiktoken_cache
        # Second call should use cached encoding
        counter.count("test2", model="gpt-4")
        assert ModelFamily.GPT4 in counter._tiktoken_cache


class TestTokenCounterFallback:
    """Tests for fallback behavior when tiktoken is unavailable."""

    @pytest.mark.skipif(TIKTOKEN_AVAILABLE, reason="tiktoken available, testing fallback")
    def test_estimation_fallback(self):
        """Test character-based estimation when tiktoken unavailable."""
        counter = TokenCounter()
        result = counter.count("Hello, world!")
        assert result.token_count > 0
        assert result.method in ("estimation", "fallback")

    @pytest.mark.skipif(TIKTOKEN_AVAILABLE, reason="tiktoken available, testing fallback")
    def test_different_provider_ratios(self):
        """Test different token ratios for different providers."""
        counter = TokenCounter()
        text = "This is a test text for token counting estimation."

        openai_result = counter.count(text, provider=LLMProvider.OPENAI)
        gemini_result = counter.count(text, provider=LLMProvider.GEMINI)

        # Both should have similar estimates with same text length
        assert abs(openai_result.token_count - gemini_result.token_count) <= 1


class TestCreateTokenCounter:
    """Test factory function."""

    def test_create_token_counter_default(self):
        """Test factory with default parameters."""
        counter = create_token_counter()
        assert isinstance(counter, TokenCounter)

    def test_create_token_counter_with_model(self):
        """Test factory with model parameter."""
        counter = create_token_counter(model="gpt-4o")
        assert isinstance(counter, TokenCounter)
        assert counter._default_provider == LLMProvider.OPENAI
        assert counter._default_family == ModelFamily.GPT4O

    def test_create_token_counter_with_provider(self):
        """Test factory with provider parameter."""
        counter = create_token_counter(provider=LLMProvider.ANTHROPIC)
        assert isinstance(counter, TokenCounter)
        assert counter._default_provider == LLMProvider.ANTHROPIC


class TestModelFamilyMapping:
    """Test model family mapping constants."""

    def test_model_family_mapping_has_openai(self):
        """Test that OpenAI models are mapped."""
        assert "gpt-4o" in MODEL_FAMILY_MAPPING
        assert "gpt-4" in MODEL_FAMILY_MAPPING
        assert "gpt-3.5-turbo" in MODEL_FAMILY_MAPPING

    def test_model_family_mapping_has_anthropic(self):
        """Test that Anthropic models are mapped."""
        assert "claude-3-opus" in MODEL_FAMILY_MAPPING
        assert "claude-3-sonnet" in MODEL_FAMILY_MAPPING

    def test_model_family_mapping_has_gemini(self):
        """Test that Gemini models are mapped."""
        assert "gemini-1.5-pro" in MODEL_FAMILY_MAPPING
        assert "gemini-pro" in MODEL_FAMILY_MAPPING

    def test_model_family_mapping_values(self):
        """Test that mapped values are correct types."""
        for model, (provider, family) in MODEL_FAMILY_MAPPING.items():
            assert isinstance(provider, LLMProvider)
            assert isinstance(family, ModelFamily)


class TestTokenCountResult:
    """Test TokenCountResult value object."""

    def test_token_count_result_immutable(self):
        """Test that TokenCountResult is frozen."""
        result = TokenCountResult(
            token_count=10,
            method="tiktoken",
            provider=LLMProvider.OPENAI,
            model_family=ModelFamily.GPT4,
        )
        with pytest.raises(Exception):  # FrozenInstanceError or dataclass error
            result.token_count = 20

    def test_token_count_result_attributes(self):
        """Test TokenCountResult attributes."""
        result = TokenCountResult(
            token_count=100,
            method="estimation",
            provider=LLMProvider.GEMINI,
            model_family=ModelFamily.GEMINI_1,
        )
        assert result.token_count == 100
        assert result.method == "estimation"
        assert result.provider == LLMProvider.GEMINI
        assert result.model_family == ModelFamily.GEMINI_1
