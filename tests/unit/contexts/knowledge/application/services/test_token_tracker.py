"""
Tests for Token Tracker Service

Warzone 4: AI Brain - BRAIN-034A
Tests for TokenTracker middleware/decorator.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.knowledge.application.services.model_registry import (
    ModelRegistry,
)
from src.contexts.knowledge.application.services.token_tracker import (
    TokenAwareConfig,
    TokenTracker,
    TrackingContext,
    create_token_tracker,
)
from src.contexts.knowledge.domain.models.model_registry import (
    LLMProvider,
    ModelDefinition,
)
from src.contexts.knowledge.domain.models.token_usage import TokenUsage

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_registry():
    """Create a mock model registry."""
    registry = MagicMock(spec=ModelRegistry)

    # Setup resolve_model to return model definitions
    def mock_resolve(model_ref: str):
        from src.contexts.knowledge.application.services.model_registry import (
            ModelLookupResult,
        )

        if "gpt" in model_ref.lower():
            return ModelLookupResult(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4o",
                model_definition=ModelDefinition(
                    provider=LLMProvider.OPENAI,
                    model_name="gpt-4o",
                    display_name="GPT-4o",
                    max_context_tokens=128000,
                    max_output_tokens=4096,
                    supports_functions=True,
                    supports_vision=True,
                    supports_streaming=True,
                    cost_per_1m_input_tokens=2.50,
                    cost_per_1m_output_tokens=10.00,
                ),
            )
        elif "claude" in model_ref.lower():
            return ModelLookupResult(
                provider=LLMProvider.ANTHROPIC,
                model_name="claude-3-5-sonnet-20241022",
                model_definition=ModelDefinition(
                    provider=LLMProvider.ANTHROPIC,
                    model_name="claude-3-5-sonnet-20241022",
                    display_name="Claude 3.5 Sonnet",
                    max_context_tokens=200000,
                    max_output_tokens=8192,
                    supports_functions=True,
                    supports_vision=True,
                    supports_streaming=True,
                    cost_per_1m_input_tokens=3.00,
                    cost_per_1m_output_tokens=15.00,
                ),
            )
        else:
            return ModelLookupResult(
                provider=LLMProvider.GEMINI,
                model_name="gemini-2.0-flash",
                model_definition=ModelDefinition(
                    provider=LLMProvider.GEMINI,
                    model_name="gemini-2.0-flash",
                    display_name="Gemini 2.0 Flash",
                    max_context_tokens=1000000,
                    max_output_tokens=8192,
                    supports_functions=True,
                    supports_vision=True,
                    supports_streaming=True,
                    cost_per_1m_input_tokens=0.075,
                    cost_per_1m_output_tokens=0.30,
                ),
            )

    registry.resolve_model = mock_resolve
    return registry


@pytest.fixture
def mock_repository():
    """Create a mock token usage repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.save_batch = AsyncMock()
    return repo


@pytest.fixture
def tracker(mock_repository, mock_registry):
    """Create a token tracker with mock dependencies."""
    config = TokenAwareConfig(
        enabled=True,
        batch_size=1,  # Immediate save for testing
        flush_interval_seconds=0,
        track_individual_calls=True,
    )
    return TokenTracker(
        repository=mock_repository,
        model_registry=mock_registry,
        config=config,
    )


class TestTrackingContext:
    """Tests for TrackingContext."""

    def test_record_success(self):
        """Test recording a successful LLM call."""
        ctx = TrackingContext(
            provider="openai",
            model_name="gpt-4o",
        )

        usage = ctx.record_success(
            input_tokens=100,
            output_tokens=200,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        assert usage.success is True
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300
        assert usage.provider == "openai"
        assert usage.model_name == "gpt-4o"
        assert usage.input_cost == Decimal("0.000250")  # 100 * 2.50 / 1M
        assert usage.output_cost == Decimal("0.002000")  # 200 * 10.00 / 1M

    def test_record_failure(self):
        """Test recording a failed LLM call."""
        ctx = TrackingContext(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
        )

        usage = ctx.record_failure(
            error_message="Rate limit exceeded",
            input_tokens=50,
            cost_per_1m_input=3.00,
            cost_per_1m_output=15.00,
        )

        assert usage.success is False
        assert usage.error_message == "Rate limit exceeded"
        assert usage.input_tokens == 50
        assert usage.output_tokens == 0
        assert usage.total_tokens == 50

    def test_elapsed_ms(self):
        """Test elapsed time calculation."""
        ctx = TrackingContext(
            provider="gemini",
            model_name="gemini-2.0-flash",
        )

        # Elapsed should be non-negative
        assert ctx.elapsed_ms >= 0

    def test_record_with_pre_counted_tokens(self):
        """Test recording with pre-counted input tokens."""
        ctx = TrackingContext(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,  # Pre-counted
        )

        usage = ctx.record_success(
            output_tokens=200,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        assert usage.input_tokens == 100


class TestTokenTracker:
    """Tests for TokenTracker service."""

    @pytest.mark.asyncio
    async def test_record_usage(self, tracker, mock_repository):
        """Test recording a usage event."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=200,
        )

        await tracker.record(usage)

        mock_repository.save.assert_called_once_with(usage)

    @pytest.mark.asyncio
    async def test_record_disabled(self, mock_repository, mock_registry):
        """Test that recording is skipped when disabled."""
        config = TokenAwareConfig(enabled=False)
        tracker = TokenTracker(
            repository=mock_repository,
            model_registry=mock_registry,
            config=config,
        )

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
        )

        await tracker.record(usage)

        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_call_context_manager(self, tracker, mock_repository):
        """Test tracking via context manager."""
        async with tracker.track_call("gpt-4o") as ctx:
            # Record success within context
            ctx.record_success(
                input_tokens=100,
                output_tokens=200,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            )

        # Usage should have been recorded after context exits
        mock_repository.save.assert_called_once()
        usage_arg = mock_repository.save.call_args[0][0]
        assert usage_arg.provider == "openai"
        assert usage_arg.model_name == "gpt-4o"

    @pytest.mark.asyncio
    async def test_track_call_with_metadata(self, tracker, mock_repository):
        """Test tracking with custom metadata."""
        async with tracker.track_call(
            "gpt-4o",
            workspace_id="workspace-123",
            user_id="user-456",
            request_id="request-789",
            metadata={"task_type": "summarization"},
        ) as ctx:
            ctx.record_success(
                input_tokens=100,
                output_tokens=200,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            )

        usage_arg = mock_repository.save.call_args[0][0]
        assert usage_arg.workspace_id == "workspace-123"
        assert usage_arg.user_id == "user-456"
        assert usage_arg.request_id == "request-789"
        assert usage_arg.metadata["task_type"] == "summarization"

    @pytest.mark.asyncio
    async def test_track_call_with_prompt_estimation(self, tracker, mock_repository):
        """Test tracking with input token estimation from prompt."""
        prompt = "Write a story about a brave warrior."
        async with tracker.track_call("gpt-4o", prompt=prompt) as ctx:
            # Input tokens should have been estimated
            assert ctx.input_tokens is not None and ctx.input_tokens > 0

            ctx.record_success(
                output_tokens=200,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            )

        usage_arg = mock_repository.save.call_args[0][0]
        assert usage_arg.input_tokens > 0

    @pytest.mark.asyncio
    async def test_get_summary(self, tracker, mock_repository):
        """Test getting usage summary."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        mock_summary = MagicMock()
        mock_summary.total_requests = 10
        mock_summary.total_tokens = 5000

        mock_repository.get_summary = AsyncMock(return_value=mock_summary)

        summary = await tracker.get_summary(start, now)

        mock_repository.get_summary.assert_called_once_with(
            start_time=start,
            end_time=now,
            provider=None,
            model_name=None,
            workspace_id=None,
        )

    @pytest.mark.asyncio
    async def test_shutdown(self, tracker):
        """Test tracker shutdown."""
        # No-op for now since we don't have background tasks in test config
        await tracker.shutdown()


class TestTokenTrackerIntegration:
    """Integration tests for TokenTracker."""

    @pytest.mark.asyncio
    async def test_decorator_tracking(self, mock_repository, mock_registry):
        """Test the decorator functionality."""
        from src.contexts.knowledge.application.ports.i_llm_client import (
            LLMRequest,
            LLMResponse,
        )

        config = TokenAwareConfig(
            enabled=True,
            batch_size=1,
        )
        tracker = create_token_tracker(
            repository=mock_repository,
            model_registry=mock_registry,
            config=config,
        )

        # Create a mock LLM function
        @tracker.track_llm_call(model_ref="gpt-4o")
        async def mock_generate(request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text="Generated text",
                model="gpt-4o",
                tokens_used=300,
                input_tokens=100,
                output_tokens=200,
            )

        # Call the function
        request = LLMRequest(
            system_prompt="You are helpful.",
            user_prompt="Hello",
        )
        result = await mock_generate(request)

        # Check result
        assert result.text == "Generated text"

        # Check that usage was recorded
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_writes(self, mock_repository):
        """Test batch write behavior."""
        config = TokenAwareConfig(
            enabled=True,
            batch_size=10,
        )
        tracker = TokenTracker(
            repository=mock_repository,
            model_registry=MagicMock(),
            config=config,
        )

        # Record multiple usages
        for _ in range(5):
            usage = TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
            )
            await tracker.record(usage)

        # Should not have saved yet (batch not full)
        mock_repository.save.assert_not_called()

        # Shutdown should flush
        await tracker.shutdown()
        mock_repository.save_batch.assert_called_once()


def test_create_token_tracker(mock_repository, mock_registry):
    """Test factory function."""
    tracker = create_token_tracker(
        repository=mock_repository,
        model_registry=mock_registry,
    )

    assert tracker._repository == mock_repository
    assert tracker._model_registry == mock_registry
    assert tracker._config.enabled is True


class TestTokenAwareConfig:
    """Tests for TokenAwareConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TokenAwareConfig()

        assert config.enabled is True
        assert config.count_input_tokens is True
        assert config.estimate_missing_tokens is True
        assert config.batch_size == 100
        assert config.flush_interval_seconds == 10.0
        assert config.track_individual_calls is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TokenAwareConfig(
            enabled=False,
            batch_size=50,
            track_individual_calls=False,
        )

        assert config.enabled is False
        assert config.batch_size == 50
        assert config.track_individual_calls is False
