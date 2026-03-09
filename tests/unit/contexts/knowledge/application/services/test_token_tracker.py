"""
Tests for TokenTracker Service.

Unit tests for token tracking, cost calculation, and usage recording.

Warzone 4: AI Brain - BRAIN-034A
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.knowledge.application.services.model_registry import (
    ModelRegistry,
)
from src.contexts.knowledge.application.services.token_tracker import (
    TokenTracker,
    TokenTrackerConfig,
)
from src.contexts.knowledge.domain.models.model_registry import (
    LLMProvider,
    ModelDefinition,
)
from src.contexts.knowledge.domain.models.token_usage import TokenUsage

# Alias for backward compatibility
TokenAwareConfig = TokenTrackerConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_registry():
    """Create a mock model registry."""
    from src.contexts.knowledge.application.services.model_registry import (
        ModelLookupResult,
    )
    from src.core.result import Ok

    registry = MagicMock(spec=ModelRegistry)

    # Setup resolve_model to return Result with model definitions
    def mock_resolve(model_ref: str):
        if "gpt" in model_ref.lower():
            return Ok(
                ModelLookupResult(
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
            )
        elif "claude" in model_ref.lower():
            return Ok(
                ModelLookupResult(
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
            )
        else:
            return Ok(
                ModelLookupResult(
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
    """Tests for TrackingContext class."""

    def test_elapsed_ms(self):
        """Test elapsed time calculation."""
        import time

        from src.contexts.knowledge.application.services.token_tracker import (
            TrackingContext,
        )

        ctx = TrackingContext(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )
        time.sleep(0.01)  # 10ms
        elapsed = ctx.elapsed_ms
        assert elapsed >= 10  # At least 10ms

    def test_record_success(self):
        """Test recording successful LLM call."""
        from src.contexts.knowledge.application.services.token_tracker import (
            TrackingContext,
        )

        ctx = TrackingContext(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            input_tokens=100,
        )
        usage = ctx.record_success(
            input_tokens=100,
            output_tokens=50,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        assert usage.provider == "openai"
        assert usage.model_name == "gpt-4o"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.success is True

    def test_record_failure(self):
        """Test recording failed LLM call."""
        from src.contexts.knowledge.application.services.token_tracker import (
            TrackingContext,
        )

        ctx = TrackingContext(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )
        usage = ctx.record_failure(
            error_message="Rate limit exceeded",
            input_tokens=100,
        )

        assert usage.provider == "openai"
        assert usage.success is False
        assert usage.error_message == "Rate limit exceeded"

    def test_record_success_with_estimation(self):
        """Test recording with token estimation."""
        from src.contexts.knowledge.application.services.token_tracker import (
            TrackingContext,
        )

        ctx = TrackingContext(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )
        usage = ctx.record_success(
            response_text="This is a test response with some tokens.",
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        assert usage.success is True
        # Tokens should be estimated from response
        assert usage.output_tokens > 0


class TestTokenTracker:
    """Tests for TokenTracker class."""

    def test_init(self, mock_repository, mock_registry):
        """Test tracker initialization."""
        tracker = TokenTracker(
            repository=mock_repository,
            model_registry=mock_registry,
        )

        assert tracker._repository is mock_repository
        assert tracker._model_registry is mock_registry

    @pytest.mark.asyncio
    async def test_record_usage(self, tracker, mock_repository):
        """Test recording a usage event."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
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
            input_tokens=100,
            output_tokens=50,
        )

        await tracker.record(usage)

        # Repository should not be called when disabled
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_call_context_manager(self, tracker):
        """Test tracking via context manager."""
        async with tracker.track_call("gpt-4o") as ctx:
            ctx.record_success(
                input_tokens=100,
                output_tokens=50,
            )

        # Usage should be recorded
        assert ctx.usage is not None
        assert ctx.usage.input_tokens == 100

    @pytest.mark.asyncio
    async def test_track_call_with_metadata(self, tracker):
        """Test tracking with metadata."""
        metadata = {"scene_id": "scene-123", "request_type": "generation"}

        async with tracker.track_call(
            "gpt-4o",
            workspace_id="ws-123",
            user_id="user-456",
            metadata=metadata,
        ) as ctx:
            ctx.record_success(input_tokens=100, output_tokens=50)

        assert ctx.usage.workspace_id == "ws-123"
        assert ctx.usage.user_id == "user-456"
        assert ctx.usage.metadata["scene_id"] == "scene-123"

    @pytest.mark.asyncio
    async def test_track_call_with_prompt_estimation(self, tracker):
        """Test tracking with prompt-based input token estimation."""
        async with tracker.track_call(
            "gpt-4o",
            prompt="This is a test prompt for token estimation.",
        ) as ctx:
            ctx.record_success(output_tokens=50)

        # Input tokens should be estimated from prompt
        assert ctx.usage.input_tokens > 0

    @pytest.mark.asyncio
    async def test_shutdown(self, tracker, mock_repository):
        """Test tracker shutdown."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        tracker._pending_records.append(usage)

        await tracker.shutdown()

        # Pending records should be flushed
        mock_repository.save_batch.assert_called_once()


class TestTokenTrackerConfig:
    """Tests for TokenTrackerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TokenTrackerConfig()

        assert config.enabled is True
        assert config.count_input_tokens is True
        assert config.estimate_missing_tokens is True
        assert config.batch_size == 100
        assert config.track_individual_calls is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TokenTrackerConfig(
            enabled=False,
            batch_size=50,
            track_individual_calls=False,
        )

        assert config.enabled is False
        assert config.batch_size == 50
        assert config.track_individual_calls is False


class TestTokenTrackerIntegration:
    """Integration tests for TokenTracker."""

    @pytest.mark.asyncio
    async def test_decorator_tracking(self, mock_repository, mock_registry):
        """Test tracking via decorator."""
        tracker = TokenTracker(
            repository=mock_repository,
            model_registry=mock_registry,
            config=TokenTrackerConfig(enabled=True, batch_size=1),
        )

        class MockLLMResponse:
            def __init__(self):
                self.tokens_used = 150
                self.input_tokens = 100
                self.output_tokens = 50

        @tracker.track_llm_call(model_ref="gpt-4o")
        async def mock_generate(request):
            return MockLLMResponse()

        class MockRequest:
            model = "gpt-4o"

        request = MockRequest()
        result = await mock_generate(request)

        assert result.tokens_used == 150
        # Usage should be recorded
        mock_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_decorator_with_exception(self, mock_repository, mock_registry):
        """Test decorator records failure on exception."""
        tracker = TokenTracker(
            repository=mock_repository,
            model_registry=mock_registry,
            config=TokenTrackerConfig(enabled=True, batch_size=1),
        )

        @tracker.track_llm_call(model_ref="gpt-4o")
        async def mock_failing_generate(request):
            raise ValueError("API Error")

        class MockRequest:
            model = "gpt-4o"

        with pytest.raises(ValueError):
            await mock_failing_generate(MockRequest())

        # Failure should be recorded
        mock_repository.save.assert_called_once()
        call_args = mock_repository.save.call_args[0][0]
        assert call_args.success is False
        assert "API Error" in call_args.error_message


class TestTokenUsageModel:
    """Tests for TokenUsage domain model."""

    def test_usage_creation(self):
        """Test creating a TokenUsage instance."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        assert usage.provider == "openai"
        assert usage.model_name == "gpt-4o"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150
        # Cost calculation: (100/1M * 2.50) + (50/1M * 10.00) = 0.00025 + 0.0005 = 0.00075
        assert abs(float(usage.total_cost) - float(Decimal("0.00075"))) < 0.00001

    def test_usage_id_generation(self):
        """Test that each usage gets a unique ID."""
        usage1 = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        usage2 = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )

        assert usage1.id != usage2.id

    def test_usage_timestamp(self):
        """Test that usage has timestamp."""
        before = datetime.now(timezone.utc)
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        after = datetime.now(timezone.utc)

        assert before <= usage.timestamp <= after


class TestCostCalculation:
    """Tests for cost calculation."""

    def test_cost_calculation_openai(self):
        """Test cost calculation for OpenAI model."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        # (1000/1M * 2.50) + (500/1M * 10.00) = 0.0025 + 0.005 = 0.0075
        expected_cost = Decimal("0.0075")
        assert abs(float(usage.total_cost) - float(expected_cost)) < 0.00001

    def test_cost_calculation_gemini(self):
        """Test cost calculation for Gemini model."""
        usage = TokenUsage.create(
            provider="gemini",
            model_name="gemini-2.0-flash",
            input_tokens=10000,
            output_tokens=5000,
            cost_per_1m_input=0.075,
            cost_per_1m_output=0.30,
        )

        # Cost should be calculated correctly
        assert float(usage.total_cost) > 0

    def test_cost_calculation_ollama(self):
        """Test cost calculation for Ollama (free)."""
        usage = TokenUsage.create(
            provider="ollama",
            model_name="llama3.2",
            input_tokens=10000,
            output_tokens=5000,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
        )

        # Cost should be zero
        assert float(usage.total_cost) == 0.0


class TestTokenUsageStats:
    """Tests for TokenUsageStats."""

    def test_stats_creation(self):
        """Test creating usage stats."""
        from datetime import datetime, timezone

        from src.contexts.knowledge.domain.models.token_usage import TokenUsageStats

        now = datetime.now(timezone.utc)
        stats = TokenUsageStats(
            provider="openai",
            model_name="gpt-4o",
            workspace_id=None,
            period_start=now,
            period_end=now,
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            total_tokens=15000,
            total_input_tokens=10000,
            total_output_tokens=5000,
            total_cost=Decimal("0.5"),
        )

        assert stats.total_requests == 100
        assert stats.total_tokens == 15000
        assert float(stats.total_cost) == 0.5
