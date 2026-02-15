"""
Tests for Token Usage Domain Models

Warzone 4: AI Brain - BRAIN-034A
Tests for TokenUsage entity and TokenUsageStats value object.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.contexts.knowledge.domain.models.token_usage import (
    TokenUsage,
    TokenUsageStats,
    _calculate_cost,
)

pytestmark = pytest.mark.unit

def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class TestCalculateCost:
    """Tests for cost calculation function."""

    def test_calculate_cost_basic(self):
        """Test basic cost calculation."""
        input_cost, output_cost, total_cost = _calculate_cost(
            input_tokens=1000,
            output_tokens=2000,
            cost_per_1m_input=0.50,
            cost_per_1m_output=1.50,
        )

        # 1000 * 0.50 / 1M = 0.0005
        assert input_cost == Decimal("0.000500")
        # 2000 * 1.50 / 1M = 0.003
        assert output_cost == Decimal("0.003000")
        assert total_cost == Decimal("0.003500")

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        input_cost, output_cost, total_cost = _calculate_cost(
            input_tokens=0,
            output_tokens=0,
            cost_per_1m_input=0.50,
            cost_per_1m_output=1.50,
        )

        assert input_cost == Decimal("0")
        assert output_cost == Decimal("0")
        assert total_cost == Decimal("0")

    def test_calculate_cost_free_model(self):
        """Test cost calculation for free model (Ollama)."""
        input_cost, output_cost, total_cost = _calculate_cost(
            input_tokens=5000,
            output_tokens=10000,
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
        )

        assert input_cost == Decimal("0")
        assert output_cost == Decimal("0")
        assert total_cost == Decimal("0")


class TestTokenUsage:
    """Tests for TokenUsage entity."""

    def test_create_usage_with_factory(self):
        """Test creating a usage event via factory method."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            latency_ms=1500.0,
            success=True,
            workspace_id="workspace-abc",
            user_id="user-xyz",
        )

        assert usage.provider == "openai"
        assert usage.model_name == "gpt-4o"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300
        assert usage.latency_ms == 1500.0
        assert usage.success is True
        assert usage.workspace_id == "workspace-abc"
        assert usage.user_id == "user-xyz"

    def test_usage_calculates_cost(self):
        """Test that usage calculates cost correctly."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=2000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        # 1000 * 2.50 / 1M = 0.0025
        assert usage.input_cost == Decimal("0.002500")
        # 2000 * 10.00 / 1M = 0.02
        assert usage.output_cost == Decimal("0.020000")
        assert usage.total_cost == Decimal("0.022500")

    def test_model_identifier_property(self):
        """Test model_identifier property."""
        usage = TokenUsage.create(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
        )

        assert usage.model_identifier == "anthropic:claude-3-5-sonnet-20241022"

    def test_cost_per_million_tokens_property(self):
        """Test cost_per_million_tokens property."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=1000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        # Total cost = 0.0025 + 0.01 = 0.0125 for 2000 tokens
        # Per 1M = 0.0125 * 1M / 2000 = 6.25
        assert usage.cost_per_million_tokens == 6.25

    def test_cost_per_million_tokens_zero_tokens(self):
        """Test cost_per_million_tokens with zero tokens."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
        )

        assert usage.cost_per_million_tokens == 0.0

    def test_usage_validation_no_negative_tokens(self):
        """Test that input_tokens cannot be negative."""
        with pytest.raises(ValueError, match="input_tokens cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=-1,
            )

    def test_usage_validation_negative_output_tokens(self):
        """Test that output_tokens cannot be negative."""
        with pytest.raises(ValueError, match="output_tokens cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                output_tokens=-1,
            )

    def test_usage_validation_total_matches_sum(self):
        """Test that total_tokens must equal input + output."""
        with pytest.raises(ValueError, match="total_tokens.*must equal"):
            TokenUsage(
                id="test-id",
                timestamp=_utcnow(),
                provider="openai",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=200,
                total_tokens=400,  # Wrong! Should be 300
            )

    def test_usage_validation_negative_latency(self):
        """Test that latency_ms cannot be negative."""
        with pytest.raises(ValueError, match="latency_ms cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                latency_ms=-1.0,
            )

    def test_usage_with_llm_provider_enum(self):
        """Test creating usage with LLMProvider enum."""
        from src.contexts.knowledge.domain.models.model_registry import LLMProvider

        usage = TokenUsage.create(
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.0-flash",
        )

        assert usage.provider == "gemini"

    def test_failed_usage(self):
        """Test creating a failed usage record."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=100,
            success=False,
            error_message="API rate limit exceeded",
        )

        assert usage.success is False
        assert usage.error_message == "API rate limit exceeded"
        assert usage.output_tokens == 0
        assert usage.total_tokens == 100

    def test_to_dict(self):
        """Test serialization to dictionary."""
        usage = TokenUsage.create(
            id="usage-123",
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            input_tokens=100,
            output_tokens=200,
        )

        data = usage.to_dict()

        assert data["id"] == "usage-123"
        assert data["provider"] == "anthropic"
        assert data["model_name"] == "claude-3-5-sonnet-20241022"
        assert data["model_identifier"] == "anthropic:claude-3-5-sonnet-20241022"
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 200
        assert data["total_tokens"] == 300
        assert "total_cost" in data

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "usage-123",
            "timestamp": "2025-02-05T12:00:00+00:00",
            "provider": "anthropic",
            "model_name": "claude-3-5-sonnet-20241022",
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
            "input_cost": "0.000500",
            "output_cost": "0.001500",
            "total_cost": "0.002000",
            "latency_ms": 500.0,
            "success": True,
        }

        usage = TokenUsage.from_dict(data)

        assert usage.id == "usage-123"
        assert usage.provider == "anthropic"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200


class TestTokenUsageStats:
    """Tests for TokenUsageStats value object."""

    def test_create_stats_from_usages(self):
        """Test calculating stats from usage events."""
        usages = [
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=200,
                latency_ms=1000.0,
                success=True,
            ),
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=150,
                output_tokens=250,
                latency_ms=1500.0,
                success=True,
            ),
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=50,
                output_tokens=0,
                latency_ms=500.0,
                success=False,
                error_message="Rate limit",
            ),
        ]

        stats = TokenUsageStats.from_usages(usages, provider="openai", model_name="gpt-4o")

        assert stats.provider == "openai"
        assert stats.model_name == "gpt-4o"
        assert stats.total_requests == 3
        assert stats.successful_requests == 2
        assert stats.failed_requests == 1
        assert stats.total_tokens == 750  # 300 + 400 + 50
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 450
        assert stats.total_latency_ms == 3000.0

    def test_stats_from_empty_list(self):
        """Test stats from empty usage list."""
        stats = TokenUsageStats.from_usages(
            [],
            provider="openai",
            model_name="gpt-4o",
        )

        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_tokens == 0

    def test_success_rate_property(self):
        """Test success_rate calculation."""
        usages = [
            TokenUsage.create(provider="openai", model_name="gpt-4o", success=True),
            TokenUsage.create(provider="openai", model_name="gpt-4o", success=True),
            TokenUsage.create(provider="openai", model_name="gpt-4o", success=False),
        ]

        stats = TokenUsageStats.from_usages(usages)

        assert stats.success_rate == 200.0 / 3  # ~66.67%

    def test_success_rate_zero_requests(self):
        """Test success_rate with zero requests."""
        stats = TokenUsageStats.from_usages([])

        assert stats.success_rate == 0.0

    def test_avg_tokens_per_request(self):
        """Test average tokens calculation."""
        usages = [
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=200,
            ),
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=200,
                output_tokens=400,
            ),
        ]

        stats = TokenUsageStats.from_usages(usages)

        # (300 + 600) / 2 = 450
        assert stats.avg_tokens_per_request == 450.0

    def test_avg_latency_ms(self):
        """Test average latency calculation."""
        usages = [
            TokenUsage.create(provider="openai", model_name="gpt-4o", latency_ms=1000.0),
            TokenUsage.create(provider="openai", model_name="gpt-4o", latency_ms=2000.0),
        ]

        stats = TokenUsageStats.from_usages(usages)

        assert stats.avg_latency_ms == 1500.0

    def test_avg_cost_per_request(self):
        """Test average cost per request."""
        usages = [
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=1000,
                output_tokens=1000,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            ),
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=2000,
                output_tokens=2000,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            ),
        ]

        stats = TokenUsageStats.from_usages(usages)

        # First: 0.0025 + 0.01 = 0.0125, Second: 0.005 + 0.02 = 0.025
        # Average: (0.0125 + 0.025) / 2 = 0.01875
        assert stats.avg_cost_per_request == Decimal("0.018750")

    def test_cost_per_million_tokens(self):
        """Test effective cost per million tokens."""
        usages = [
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=1000,
                output_tokens=1000,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            ),
        ]

        stats = TokenUsageStats.from_usages(usages)

        # 0.0125 for 2000 tokens -> 6.25 per 1M
        assert stats.cost_per_million_tokens == 6.25

    def test_to_dict(self):
        """Test stats serialization."""
        usages = [
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=200,
                latency_ms=1000.0,
                success=True,
            ),
        ]

        stats = TokenUsageStats.from_usages(usages)
        data = stats.to_dict()

        assert data["provider"] == "openai"
        assert data["model_name"] == "gpt-4o"
        assert data["total_requests"] == 1
        assert data["success_rate"] == 100.0
        assert data["total_tokens"] == 300
        assert "total_cost" in data
