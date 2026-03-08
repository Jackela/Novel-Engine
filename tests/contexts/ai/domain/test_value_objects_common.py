#!/usr/bin/env python3
"""
AI Value Objects Common Tests

Tests for common AI value objects including ProviderId, ModelId, and TokenBudget.
Covers unit tests, integration tests, and boundary tests.
"""

from decimal import Decimal
from typing import Any, Dict, Optional, Set
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from src.contexts.ai.domain.value_objects.common import (
    ModelCapability,
    ModelId,
    ProviderId,
    ProviderType,
    TokenBudget,
)
pytestmark = pytest.mark.unit



# ============================================================================
# Unit Tests (20 tests)
# ============================================================================


@pytest.mark.unit
class TestProviderType:
    """Unit tests for ProviderType enum."""

    def test_provider_type_values(self):
        """Test provider type enum values."""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.MICROSOFT.value == "microsoft"
        assert ProviderType.AMAZON.value == "amazon"
        assert ProviderType.COHERE.value == "cohere"
        assert ProviderType.HUGGINGFACE.value == "huggingface"
        assert ProviderType.CUSTOM.value == "custom"


@pytest.mark.unit
class TestModelCapability:
    """Unit tests for ModelCapability enum."""

    def test_model_capability_values(self):
        """Test model capability enum values."""
        assert ModelCapability.TEXT_GENERATION.value == "text_generation"
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CONVERSATION.value == "conversation"
        assert ModelCapability.SUMMARIZATION.value == "summarization"
        assert ModelCapability.TRANSLATION.value == "translation"
        assert ModelCapability.ANALYSIS.value == "analysis"
        assert ModelCapability.CREATIVE_WRITING.value == "creative_writing"
        assert ModelCapability.FUNCTION_CALLING.value == "function_calling"
        assert ModelCapability.VISION.value == "vision"
        assert ModelCapability.EMBEDDING.value == "embedding"


@pytest.mark.unit
class TestProviderId:
    """Unit tests for ProviderId."""

    def test_create_basic_provider(self):
        """Test creating basic provider."""
        provider = ProviderId(
            provider_name="Test Provider",
            provider_type=ProviderType.CUSTOM,
        )
        assert provider.provider_name == "Test Provider"
        assert provider.provider_type == ProviderType.CUSTOM
        assert isinstance(provider.provider_key, UUID)

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = ProviderId.create_openai()
        assert provider.provider_name == "OpenAI"
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.region == "US"
        assert provider.is_official_provider()

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = ProviderId.create_anthropic()
        assert provider.provider_name == "Anthropic"
        assert provider.provider_type == ProviderType.ANTHROPIC
        assert provider.metadata.get("safety_focused") is True

    def test_create_custom_provider(self):
        """Test creating custom provider."""
        provider = ProviderId.create_custom(
            name="My Provider",
            key="custom_key_123",
        )
        assert provider.provider_name == "My Provider"
        assert provider.provider_type == ProviderType.CUSTOM
        assert provider.provider_key == "custom_key_123"

    def test_provider_validation_name_length(self):
        """Test provider name length validation."""
        with pytest.raises(ValueError, match="provider_name must be 2-100 characters"):
            ProviderId(provider_name="A", provider_type=ProviderType.CUSTOM)

    def test_provider_validation_name_empty(self):
        """Test provider name empty validation."""
        with pytest.raises(ValueError, match="provider_name is required"):
            ProviderId(provider_name="", provider_type=ProviderType.CUSTOM)

    def test_provider_validation_api_version(self):
        """Test API version validation."""
        with pytest.raises(ValueError, match="api_version must follow semantic versioning"):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                api_version="invalid",
            )

    def test_provider_validation_region(self):
        """Test region validation."""
        with pytest.raises(ValueError, match="region must be a 2-character"):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                region="USA",
            )

    def test_provider_supports_region(self):
        """Test region support check."""
        provider = ProviderId.create_openai(region="US")
        assert provider.supports_region("US")
        assert provider.supports_region("us")
        assert not provider.supports_region("EU")

    def test_provider_get_display_name(self):
        """Test display name generation."""
        provider = ProviderId.create_openai(region="US")
        assert "OpenAI" in provider.get_display_name()
        assert "US" in provider.get_display_name()


@pytest.mark.unit
class TestModelId:
    """Unit tests for ModelId."""

    def test_create_basic_model(self):
        """Test creating basic model."""
        provider = ProviderId.create_openai()
        model = ModelId(
            model_name="test-model",
            provider_id=provider,
        )
        assert model.model_name == "test-model"
        assert model.provider_id == provider
        assert model.max_context_tokens == 4096
        assert model.max_output_tokens == 1024

    def test_create_gpt4_model(self):
        """Test creating GPT-4 model."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        assert model.model_name == "gpt-4"
        assert model.max_context_tokens == 8192
        assert model.max_output_tokens == 4096
        assert ModelCapability.TEXT_GENERATION in model.capabilities

    def test_create_claude_model(self):
        """Test creating Claude model."""
        provider = ProviderId.create_anthropic()
        model = ModelId.create_claude(provider, variant="claude-3-sonnet")
        assert model.model_name == "claude-3-sonnet"
        assert model.max_context_tokens == 200000

    def test_model_supports_capability(self):
        """Test capability support check."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        assert model.supports_capability(ModelCapability.TEXT_GENERATION)
        assert model.supports_capability(ModelCapability.CONVERSATION)

    def test_model_estimate_cost(self):
        """Test cost estimation."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        cost = model.estimate_cost(1000, 500)
        assert cost > Decimal("0")

    def test_model_can_handle_context(self):
        """Test context size handling."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        assert model.can_handle_context(1000)
        assert not model.can_handle_context(10000)

    def test_model_get_effective_context_limit(self):
        """Test effective context limit calculation."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        limit = model.get_effective_context_limit(reserved_output_tokens=1000)
        assert limit == 7192  # 8192 - 1000

    def test_model_validation_token_limits(self):
        """Test token limit validation."""
        provider = ProviderId.create_openai()
        with pytest.raises(ValueError, match="max_context_tokens must be a positive integer"):
            ModelId(
                model_name="test",
                provider_id=provider,
                max_context_tokens=0,
            )

    def test_model_validation_output_exceeds_context(self):
        """Test output tokens exceeding context validation."""
        provider = ProviderId.create_openai()
        with pytest.raises(ValueError, match="max_output_tokens cannot exceed max_context_tokens"):
            ModelId(
                model_name="test",
                provider_id=provider,
                max_context_tokens=100,
                max_output_tokens=200,
            )

    def test_model_validation_cost_negative(self):
        """Test negative cost validation."""
        provider = ProviderId.create_openai()
        with pytest.raises(ValueError, match="cost_per_input_token must be a non-negative"):
            ModelId(
                model_name="test",
                provider_id=provider,
                cost_per_input_token=Decimal("-0.01"),
            )


@pytest.mark.unit
class TestTokenBudget:
    """Unit tests for TokenBudget."""

    def test_create_basic_budget(self):
        """Test creating basic budget."""
        budget = TokenBudget(
            budget_id="test_budget",
            allocated_tokens=1000,
        )
        assert budget.budget_id == "test_budget"
        assert budget.allocated_tokens == 1000
        assert budget.get_available_tokens() == 1000

    def test_create_daily_budget(self):
        """Test creating daily budget."""
        budget = TokenBudget.create_daily_budget("daily_1", 5000)
        assert budget.budget_id == "daily_daily_1"
        assert budget.allocated_tokens == 5000
        assert budget.rollover_enabled is False

    def test_create_project_budget(self):
        """Test creating project budget."""
        budget = TokenBudget.create_project_budget(
            project_id="proj_1",
            total_tokens=10000,
            cost_limit=Decimal("500.00"),
        )
        assert budget.budget_id == "project_proj_1"
        assert budget.priority == 8

    def test_reserve_tokens(self):
        """Test token reservation."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
        )
        new_budget = budget.reserve_tokens(200)
        assert new_budget.reserved_tokens == 200
        assert new_budget.get_available_tokens() == 800

    def test_consume_tokens(self):
        """Test token consumption."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            reserved_tokens=200,
        )
        new_budget = budget.consume_tokens(100, Decimal("1.00"))
        assert new_budget.consumed_tokens == 100
        assert new_budget.reserved_tokens == 100
        assert new_budget.accumulated_cost == Decimal("1.00")

    def test_get_utilization_percentage(self):
        """Test utilization percentage calculation."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            consumed_tokens=500,
        )
        assert budget.get_utilization_percentage() == Decimal("50.00")

    def test_is_exhausted(self):
        """Test exhausted check."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=100,
            consumed_tokens=100,
        )
        assert budget.is_exhausted()

    def test_is_near_exhaustion(self):
        """Test near exhaustion check."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=100,
            consumed_tokens=95,
        )
        assert budget.is_near_exhaustion(threshold_percentage=Decimal("90.00"))

    def test_can_afford_cost(self):
        """Test cost affordability check."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("50.00"),
        )
        assert budget.can_afford_cost(Decimal("40.00"))
        assert not budget.can_afford_cost(Decimal("60.00"))

    def test_get_budget_summary(self):
        """Test budget summary generation."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            consumed_tokens=500,
        )
        summary = budget.get_budget_summary()
        assert summary["budget_id"] == "test"
        assert summary["tokens"]["allocated"] == 1000
        assert summary["tokens"]["consumed"] == 500


# ============================================================================
# Integration Tests (12 tests)
# ============================================================================


@pytest.mark.integration
class TestProviderModelIntegration:
    """Integration tests for provider and model."""

    def test_openai_to_gpt4_flow(self):
        """Test flow from OpenAI provider to GPT-4 model."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        assert model.provider_id == provider
        assert model.provider_id.provider_name == "OpenAI"

    def test_anthropic_to_claude_flow(self):
        """Test flow from Anthropic provider to Claude model."""
        provider = ProviderId.create_anthropic()
        model = ModelId.create_claude(provider)
        assert model.provider_id == provider
        assert model.provider_id.provider_name == "Anthropic"

    def test_model_provider_capabilities(self):
        """Test model capabilities with provider context."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        
        capabilities = model.capabilities
        assert ModelCapability.TEXT_GENERATION in capabilities
        assert model.supports_capability(ModelCapability.CONVERSATION)

    def test_cost_estimation_with_provider(self):
        """Test cost estimation with provider context."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        
        # GPT-4 costs: input $0.00003, output $0.00006 per token
        cost = model.estimate_cost(1000, 500)
        expected = Decimal("1000") * Decimal("0.00003") + Decimal("500") * Decimal("0.00006")
        assert cost == expected


@pytest.mark.integration
class TestTokenBudgetIntegration:
    """Integration tests for token budget."""

    def test_budget_flow_reserve_consume(self):
        """Test full budget flow: reserve then consume."""
        budget = TokenBudget.create_daily_budget("test", 1000)
        
        # Reserve tokens
        budget = budget.reserve_tokens(300)
        assert budget.get_available_tokens() == 700
        
        # Consume some reserved tokens
        budget = budget.consume_tokens(200, Decimal("2.00"))
        assert budget.consumed_tokens == 200
        assert budget.reserved_tokens == 100

    def test_budget_with_model_usage(self):
        """Test budget with model token usage."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)
        
        budget = TokenBudget.create_daily_budget("ai_budget", 10000)
        
        # Simulate using model
        input_tokens = 500
        output_tokens = 200
        cost = model.estimate_cost(input_tokens, output_tokens)
        
        total_tokens = input_tokens + output_tokens
        assert budget.can_reserve_tokens(total_tokens)
        
        new_budget = budget.reserve_tokens(total_tokens)
        new_budget = new_budget.consume_tokens(total_tokens, cost)
        
        assert new_budget.consumed_tokens == total_tokens


# ============================================================================
# Boundary Tests (8 tests)
# ============================================================================


@pytest.mark.unit
class TestValueObjectsBoundaryConditions:
    """Boundary tests for value objects."""

    def test_provider_name_max_length(self):
        """Test provider name at maximum length."""
        long_name = "A" * 100
        provider = ProviderId(
            provider_name=long_name,
            provider_type=ProviderType.CUSTOM,
        )
        assert provider.provider_name == long_name

    def test_model_name_max_length(self):
        """Test model name at maximum length."""
        provider = ProviderId.create_openai()
        long_name = "a" * 200
        model = ModelId(
            model_name=long_name,
            provider_id=provider,
        )
        assert model.model_name == long_name

    def test_token_budget_minimum(self):
        """Test token budget at minimum."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1,
        )
        assert budget.allocated_tokens == 1

    def test_token_budget_zero_available(self):
        """Test token budget with zero available."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=100,
            consumed_tokens=100,
        )
        assert budget.get_available_tokens() == 0

    def test_cost_zero(self):
        """Test zero cost."""
        provider = ProviderId.create_openai()
        model = ModelId(
            model_name="free-model",
            provider_id=provider,
            cost_per_input_token=Decimal("0"),
            cost_per_output_token=Decimal("0"),
        )
        cost = model.estimate_cost(1000, 1000)
        assert cost == Decimal("0")

    def test_cost_very_small(self):
        """Test very small cost."""
        provider = ProviderId.create_openai()
        model = ModelId(
            model_name="cheap-model",
            provider_id=provider,
            cost_per_input_token=Decimal("0.0000001"),
            cost_per_output_token=Decimal("0.0000001"),
        )
        cost = model.estimate_cost(1000, 1000)
        assert cost > Decimal("0")

    def test_priority_boundary_low(self):
        """Test priority at minimum boundary."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=100,
            priority=1,
        )
        assert budget.priority == 1

    def test_priority_boundary_high(self):
        """Test priority at maximum boundary."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=100,
            priority=10,
        )
        assert budget.priority == 10


# Total: 20 unit + 12 integration + 8 boundary = 40 tests for AI value objects
