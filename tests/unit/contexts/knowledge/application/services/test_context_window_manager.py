"""
Unit tests for ContextWindowManager service.

OPT-009: Context Window Manager tests
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.contexts.knowledge.application.services.context_window_manager import (
    ContextWindowManager,
    ContextWindowConfig,
    ManagedContext,
    ChatMessage,
    PruningStrategy,
    create_context_window_manager,
    DEFAULT_CONTEXT_WINDOWS,
)
from src.contexts.knowledge.application.services.token_counter import (
    TokenCounter,
    TokenCountResult,
    LLMProvider,
)
from src.contexts.knowledge.application.services.context_optimizer import (
    ContextOptimizer,
    OptimizationResult,
    PackingStrategy,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
    SourceType,
)


@pytest.fixture
def mock_token_counter():
    """Mock token counter for testing."""
    counter = MagicMock(spec=TokenCounter)

    def mock_count(text: str, **kwargs) -> TokenCountResult:
        # Simple estimation: 1 token per 4 characters
        token_count = max(1, len(text) // 4)
        return TokenCountResult(
            token_count=token_count,
            method="estimation",
            provider=LLMProvider.OPENAI,
            model_family=MagicMock(),
        )

    counter.count = MagicMock(side_effect=mock_count)
    return counter


@pytest.fixture
def mock_context_optimizer():
    """Mock context optimizer for testing."""
    optimizer = MagicMock(spec=ContextOptimizer)

    async def mock_optimize(chunks, max_tokens=None, strategy=None, config=None):
        # Simple truncation for testing
        max_budget = max_tokens or 100000
        total = 0
        kept = []
        for chunk in chunks:
            chunk_tokens = len(chunk.content) // 4
            if total + chunk_tokens > max_budget:
                break
            kept.append(chunk)
            total += chunk_tokens

        return OptimizationResult(
            chunks=kept,
            total_tokens=total,
            original_count=len(chunks),
            optimized_count=len(kept),
            tokens_saved=0,
            removed_redundant=len(chunks) - len(kept),
            compressed=0,
            strategy_used=strategy or PackingStrategy.RELEVANCE,
        )

    optimizer.optimize_context = AsyncMock(side_effect=mock_optimize)
    return optimizer


@pytest.fixture
def sample_chunks():
    """Create sample RAG chunks for testing."""
    return [
        RetrievedChunk(
            chunk_id=f"chunk_{i}",
            source_id=f"source_{i}",
            source_type=SourceType.LORE,
            content=f"This is chunk {i} with some content for testing purposes. " * 10,
            score=0.9 - (i * 0.1),
            metadata={"index": i},
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_history():
    """Create sample chat history for testing."""
    return [
        ChatMessage(role="user", content=f"This is message {i} from the user. " * 5)
        if i % 2 == 0
        else ChatMessage(role="assistant", content=f"This is message {i} from the assistant. " * 5)
        for i in range(10)
    ]


class TestContextWindowManager:
    """Test suite for ContextWindowManager."""

    def test_init_default(self, mock_token_counter, mock_context_optimizer):
        """Test default initialization."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
        )

        assert manager._token_counter is mock_token_counter
        assert manager._context_optimizer is mock_context_optimizer
        assert isinstance(manager._config, ContextWindowConfig)

    def test_init_with_config(self, mock_token_counter, mock_context_optimizer):
        """Test initialization with custom config."""
        config = ContextWindowConfig(
            model_context_window=4096,
            reserve_for_response=500,
            pruning_strategy=PruningStrategy.KEEP_SYSTEM,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
            config=config,
        )

        assert manager._config is config
        assert manager._config.model_context_window == 4096
        assert manager._config.reserve_for_response == 500

    @pytest.mark.asyncio
    async def test_manage_context_basic(self, mock_token_counter, mock_context_optimizer, sample_chunks, sample_history):
        """Test basic context management."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
        )

        system_prompt = "You are a helpful assistant."
        query = "What is the story about?"

        result = await manager.manage_context(
            system_prompt=system_prompt,
            rag_chunks=sample_chunks,
            chat_history=sample_history,
            query=query,
        )

        assert isinstance(result, ManagedContext)
        assert result.system_prompt == system_prompt
        assert result.fits_window
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_manage_context_empty_inputs(self, mock_token_counter, mock_context_optimizer):
        """Test context management with empty inputs."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
        )

        result = await manager.manage_context(
            system_prompt="You are a helpful assistant.",
            rag_chunks=[],
            chat_history=[],
            query="Hello",
        )

        assert len(result.rag_chunks) == 0
        assert len(result.chat_history) == 1  # Just the query
        assert result.chat_history[0].content == "Hello"
        assert result.fits_window

    @pytest.mark.asyncio
    async def test_pruning_oldest_first(self, mock_token_counter, mock_context_optimizer):
        """Test that oldest messages are pruned first."""
        config = ContextWindowConfig(
            model_context_window=1000,  # Small window to force pruning
            reserve_for_response=100,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
            config=config,
        )

        # Create large history that will exceed window
        large_history = [
            ChatMessage(role="user", content=f"Message {i}: " + "x" * 50)
            for i in range(50)
        ]

        result = await manager.manage_context(
            system_prompt="You are a helpful assistant.",
            rag_chunks=[],
            chat_history=large_history,
            query="Current question",
        )

        # Should have pruned some messages
        assert result.messages_pruned > 0
        # Query should always be included
        assert any(msg.content == "Current question" for msg in result.chat_history)
        # Most recent messages should be kept
        assert len(result.chat_history) < len(large_history)

    @pytest.mark.asyncio
    async def test_system_prompt_preserved(self, mock_token_counter, mock_context_optimizer):
        """Test that system prompt is always preserved."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
        )

        system_prompt = "You are a specialized assistant for fantasy novels."

        result = await manager.manage_context(
            system_prompt=system_prompt,
            rag_chunks=[],
            chat_history=[],
            query="Hello",
        )

        assert result.system_prompt == system_prompt

    @pytest.mark.asyncio
    async def test_rag_chunks_optimized(self, mock_token_counter, mock_context_optimizer, sample_chunks):
        """Test that RAG chunks are optimized when enabled."""
        config = ContextWindowConfig(
            enable_rag_optimization=True,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
            config=config,
        )

        result = await manager.manage_context(
            system_prompt="You are a helpful assistant.",
            rag_chunks=sample_chunks,
            chat_history=[],
            query="Hello",
        )

        # Context optimizer should have been called
        mock_context_optimizer.optimize_context.assert_called_once()
        assert len(result.rag_chunks) <= len(sample_chunks)

    @pytest.mark.asyncio
    async def test_rag_chunks_not_optimized_when_disabled(self, mock_token_counter, sample_chunks):
        """Test that RAG chunks are not optimized when disabled."""
        config = ContextWindowConfig(
            enable_rag_optimization=False,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            config=config,
        )

        result = await manager.manage_context(
            system_prompt="You are a helpful assistant.",
            rag_chunks=sample_chunks,
            chat_history=[],
            query="Hello",
        )

        # Some chunks may be truncated due to token limits, but not via optimizer
        assert len(result.rag_chunks) <= len(sample_chunks)

    @pytest.mark.asyncio
    async def test_priority_order_preserved(self, mock_token_counter, mock_context_optimizer):
        """Test priority: System > RAG > Recent History."""
        config = ContextWindowConfig(
            model_context_window=500,  # Very small window
            reserve_for_response=50,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
            config=config,
        )

        large_chunks = [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id=f"source_{i}",
                source_type=SourceType.LORE,
                content="x" * 100,  # Large chunks
                score=0.9,
                metadata={},
            )
            for i in range(10)
        ]

        large_history = [
            ChatMessage(role="user", content="y" * 50)
            for i in range(20)
        ]

        result = await manager.manage_context(
            system_prompt="System prompt here.",
            rag_chunks=large_chunks,
            chat_history=large_history,
            query="Query",
        )

        # System prompt should be preserved
        assert result.system_prompt == "System prompt here."
        # Some chunks and history may be pruned
        assert result.fits_window or result.total_tokens <= config.model_context_window

    @pytest.mark.asyncio
    async def test_system_prompt_too_large_raises(self, mock_token_counter, mock_context_optimizer):
        """Test that ValueError is raised if system prompt exceeds window."""
        config = ContextWindowConfig(
            model_context_window=100,
        )

        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
            config=config,
        )

        # System prompt that exceeds window
        large_prompt = "x" * 1000

        with pytest.raises(ValueError, match="System prompt.*exceeds model context window"):
            await manager.manage_context(
                system_prompt=large_prompt,
                rag_chunks=[],
                chat_history=[],
                query="Hello",
            )

    def test_calculate_available_tokens(self, mock_token_counter):
        """Test calculation of available tokens."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
        )

        available = manager.calculate_available_tokens(
            model_name="gpt-4o",
            system_prompt="You are helpful.",
            reserve_for_response=1000,
        )

        assert available > 0
        # gpt-4o has 128k window
        # system_prompt ~5 tokens, reserve 1000
        # available = 128000 - 5 - 1000
        assert available > 120000

    def test_to_api_messages(self, mock_token_counter, mock_context_optimizer):
        """Test conversion to API message format."""
        manager = ContextWindowManager(
            token_counter=mock_token_counter,
            context_optimizer=mock_context_optimizer,
        )

        result = ManagedContext(
            system_prompt="System prompt",
            rag_chunks=[],
            chat_history=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there"),
            ],
            total_tokens=100,
            system_tokens=20,
            rag_tokens=0,
            history_tokens=80,
            reserved_tokens=1000,
            messages_pruned=0,
            chunks_optimized=0,
            fits_window=True,
        )

        messages = result.to_api_messages()

        assert len(messages) == 3  # system + user + assistant
        assert messages[0] == {"role": "system", "content": "System prompt"}
        assert messages[1] == {"role": "user", "content": "Hello"}
        assert messages[2] == {"role": "assistant", "content": "Hi there"}


class TestCreateContextWindowManager:
    """Test factory function."""

    def test_create_default(self):
        """Test factory with default parameters."""
        manager = create_context_window_manager()

        assert isinstance(manager, ContextWindowManager)
        assert manager._config.enable_rag_optimization is True
        assert manager._config.model_context_window == 128000

    def test_create_with_model(self):
        """Test factory with specific model."""
        manager = create_context_window_manager(model_name="gpt-4")

        assert isinstance(manager, ContextWindowManager)
        # gpt-4 has 8192 context window
        assert manager._config.model_context_window == 8192

    def test_create_with_provider(self):
        """Test factory with specific provider."""
        manager = create_context_window_manager(provider=LLMProvider.ANTHROPIC)

        assert isinstance(manager, ContextWindowManager)


class TestContextWindowConfig:
    """Test ContextWindowConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ContextWindowConfig()

        assert config.model_context_window == 128000
        assert config.system_prompt_tokens == 500
        assert config.reserve_for_response == 2000
        assert config.pruning_strategy == PruningStrategy.OLDEST_FIRST
        assert config.enable_rag_optimization is True
        assert config.rag_strategy == PackingStrategy.REMOVE_REDUNDANCY


class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_with_tokens(self):
        """Test updating token count."""
        msg = ChatMessage(role="user", content="Hello", tokens=0)

        updated = msg.with_tokens(5)

        assert updated.role == "user"
        assert updated.content == "Hello"
        assert updated.tokens == 5


class TestDefaultContextWindows:
    """Test DEFAULT_CONTEXT_WINDOWS mapping."""

    def test_contains_expected_models(self):
        """Test that expected models are in the mapping."""
        assert "gpt-4o" in DEFAULT_CONTEXT_WINDOWS
        assert "gpt-4" in DEFAULT_CONTEXT_WINDOWS
        assert "claude-3-5-sonnet" in DEFAULT_CONTEXT_WINDOWS
        assert "gemini-2.0-flash" in DEFAULT_CONTEXT_WINDOWS

    def test_context_window_values(self):
        """Test context window values are positive."""
        for model, window in DEFAULT_CONTEXT_WINDOWS.items():
            assert window > 0, f"{model} has invalid context window: {window}"
