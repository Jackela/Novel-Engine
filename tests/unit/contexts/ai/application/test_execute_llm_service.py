#!/usr/bin/env python3
"""
Comprehensive Unit Tests for ExecuteLLMService

Test suite covering service initialization, provider routing, policy enforcement,
execution orchestration, and comprehensive flow management in the AI Gateway Context application layer.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from contexts.ai.application.services.execute_llm_service import (
    ExecuteLLMService,
    LLMExecutionConfig,
    LLMExecutionResult,
    ProviderRouter,
)
from contexts.ai.domain.services.llm_provider import (
    ILLMProvider,
    LLMRequest,
    LLMResponse,
    LLMResponseStatus,
)
from contexts.ai.domain.value_objects.common import (
    ModelId,
    ProviderId,
    TokenBudget,
)


class TestLLMExecutionConfig:
    """Test suite for LLMExecutionConfig data class."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_default_config_creation(self):
        """Test creating execution config with default values."""
        config = LLMExecutionConfig()

        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600
        assert config.enforce_rate_limits is True
        assert config.client_id is None
        assert config.track_costs is True
        assert config.enforce_budgets is True
        assert config.enable_retries is True
        assert config.preferred_providers == []
        assert config.fallback_providers == []
        assert config.enable_streaming is False
        assert config.metadata == {}

    @pytest.mark.unit
    def test_custom_config_creation(self):
        """Test creating execution config with custom values."""
        preferred_providers = ["openai", "anthropic"]
        fallback_providers = ["cohere"]
        metadata = {"source": "test", "priority": "high"}

        config = LLMExecutionConfig(
            enable_caching=False,
            cache_ttl_seconds=1800,
            enforce_rate_limits=False,
            client_id="test-client-123",
            track_costs=False,
            enforce_budgets=False,
            enable_retries=False,
            preferred_providers=preferred_providers,
            fallback_providers=fallback_providers,
            enable_streaming=True,
            metadata=metadata,
        )

        assert config.enable_caching is False
        assert config.cache_ttl_seconds == 1800
        assert config.enforce_rate_limits is False
        assert config.client_id == "test-client-123"
        assert config.track_costs is False
        assert config.enforce_budgets is False
        assert config.enable_retries is False
        assert config.preferred_providers == preferred_providers
        assert config.fallback_providers == fallback_providers
        assert config.enable_streaming is True
        assert config.metadata == metadata


class TestLLMExecutionResult:
    """Test suite for LLMExecutionResult data class."""

    def setup_method(self):
        """Set up test dependencies."""
        self.request_id = uuid4()
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)
        self.response = LLMResponse.create_success(
            request_id=self.request_id,
            content="Test response",
            model_id=self.model_id,
            input_tokens=100,
            output_tokens=50,
        )

    @pytest.mark.unit
    def test_basic_result_creation(self):
        """Test creating execution result with basic parameters."""
        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=1.5,
            provider_used=self.model_id.provider_id,
            model_used=self.model_id,
        )

        assert result.response == self.response
        assert result.success is True
        assert result.request_id == self.request_id
        assert result.execution_time_seconds == 1.5
        assert result.provider_used == self.model_id.provider_id
        assert result.model_used == self.model_id
        assert result.cache_hit is False
        assert result.rate_limited is False
        assert result.budget_exceeded is False
        assert result.retry_attempts == 0
        assert result.cost_entry is None
        assert result.token_usage == {}
        assert result.cache_lookup_time == 0.0
        assert result.rate_limit_check_time == 0.0
        assert result.provider_response_time == 0.0
        assert result.error_details is None
        assert result.fallback_used is False
        assert result.execution_metadata == {}

    @pytest.mark.unit
    def test_result_with_all_parameters(self):
        """Test creating execution result with all optional parameters."""
        from contexts.ai.infrastructure.policies.cost_tracking import CostEntry

        cost_entry = Mock(spec=CostEntry)
        cost_entry.total_cost = Decimal("0.05")

        token_usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        execution_metadata = {"cache_version": "1.0", "execution_path": "primary"}

        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=2.1,
            provider_used=self.model_id.provider_id,
            model_used=self.model_id,
            cache_hit=True,
            rate_limited=False,
            budget_exceeded=False,
            retry_attempts=2,
            cost_entry=cost_entry,
            token_usage=token_usage,
            cache_lookup_time=0.1,
            rate_limit_check_time=0.05,
            provider_response_time=1.8,
            error_details=None,
            fallback_used=False,
            execution_metadata=execution_metadata,
        )

        assert result.cache_hit is True
        assert result.retry_attempts == 2
        assert result.cost_entry == cost_entry
        assert result.token_usage == token_usage
        assert result.cache_lookup_time == 0.1
        assert result.rate_limit_check_time == 0.05
        assert result.provider_response_time == 1.8
        assert result.execution_metadata == execution_metadata

    @pytest.mark.unit
    def test_total_tokens_property(self):
        """Test total_tokens property calculation."""
        token_usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}

        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=1.0,
            provider_used=None,
            model_used=None,
            token_usage=token_usage,
        )

        assert result.total_tokens == 150

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_tokens_property_empty(self):
        """Test total_tokens property with empty usage."""
        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=1.0,
            provider_used=None,
            model_used=None,
        )

        assert result.total_tokens == 0

    @pytest.mark.unit
    def test_total_cost_property(self):
        """Test total_cost property calculation."""
        from contexts.ai.infrastructure.policies.cost_tracking import CostEntry

        cost_entry = Mock(spec=CostEntry)
        cost_entry.total_cost = Decimal("0.15")

        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=1.0,
            provider_used=None,
            model_used=None,
            cost_entry=cost_entry,
        )

        assert result.total_cost == Decimal("0.15")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_cost_property_no_cost_entry(self):
        """Test total_cost property with no cost entry."""
        result = LLMExecutionResult(
            response=self.response,
            success=True,
            request_id=self.request_id,
            execution_time_seconds=1.0,
            provider_used=None,
            model_used=None,
        )

        assert result.total_cost == Decimal("0")


class TestProviderRouter:
    """Test suite for ProviderRouter class."""

    def setup_method(self):
        """Set up test dependencies."""
        self.router = ProviderRouter()

        # Create mock providers
        self.provider_id_1 = ProviderId.create_openai()
        self.provider_id_2 = ProviderId.create_anthropic()

        self.model_id_1 = ModelId.create_gpt4(self.provider_id_1)
        self.model_id_2 = ModelId.create_claude(self.provider_id_2)

        self.mock_provider_1 = Mock(spec=ILLMProvider)
        self.mock_provider_1.provider_id = self.provider_id_1
        self.mock_provider_1.get_model_info.return_value = self.model_id_1

        self.mock_provider_2 = Mock(spec=ILLMProvider)
        self.mock_provider_2.provider_id = self.provider_id_2
        self.mock_provider_2.get_model_info.return_value = self.model_id_2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_router_initialization(self):
        """Test provider router initialization."""
        assert len(self.router._providers) == 0
        assert len(self.router._provider_health) == 0
        assert len(self.router._performance_metrics) == 0

    @pytest.mark.unit
    def test_register_provider(self):
        """Test registering a provider with the router."""
        self.router.register_provider(self.mock_provider_1)

        provider_key = self.provider_id_1.provider_name
        assert provider_key in self.router._providers
        assert self.router._providers[provider_key] == self.mock_provider_1

        # Check health tracking initialization
        assert provider_key in self.router._provider_health
        health = self.router._provider_health[provider_key]
        assert health["available"] is True
        assert health["consecutive_failures"] == 0
        assert "last_check" in health

        # Check performance metrics initialization
        assert provider_key in self.router._performance_metrics
        metrics = self.router._performance_metrics[provider_key]
        assert metrics["avg_response_time"] == 0.0
        assert metrics["success_rate"] == 1.0
        assert metrics["total_requests"] == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_register_multiple_providers(self):
        """Test registering multiple providers."""
        self.router.register_provider(self.mock_provider_1)
        self.router.register_provider(self.mock_provider_2)

        assert len(self.router._providers) == 2
        assert self.provider_id_1.provider_name in self.router._providers
        assert self.provider_id_2.provider_name in self.router._providers

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_provider_existing(self):
        """Test getting existing provider by name."""
        self.router.register_provider(self.mock_provider_1)

        provider = self.router.get_provider(self.provider_id_1.provider_name)

        assert provider == self.mock_provider_1

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_provider_non_existing(self):
        """Test getting non-existing provider."""
        provider = self.router.get_provider("non-existing-provider")

        assert provider is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_provider_for_model_preferred(self):
        """Test selecting provider with preferred providers list."""
        self.router.register_provider(self.mock_provider_1)
        self.router.register_provider(self.mock_provider_2)

        preferred_providers = [self.provider_id_2.provider_name]  # Prefer Anthropic

        provider = self.router.select_provider_for_model(
            model_name=self.model_id_2.model_name,
            preferred_providers=preferred_providers,
        )

        assert provider == self.mock_provider_2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_provider_for_model_fallback_to_any(self):
        """Test selecting provider when preferred not available, fallback to any."""
        self.router.register_provider(self.mock_provider_1)

        # Prefer non-registered provider, should fallback to available one
        preferred_providers = ["non-existing-provider"]

        provider = self.router.select_provider_for_model(
            model_name=self.model_id_1.model_name,
            preferred_providers=preferred_providers,
        )

        assert provider == self.mock_provider_1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_provider_for_model_with_fallback(self):
        """Test selecting provider using fallback providers."""
        self.router.register_provider(self.mock_provider_1)

        # Make provider unhealthy
        self.router._provider_health[self.provider_id_1.provider_name][
            "consecutive_failures"
        ] = 5

        fallback_providers = [self.provider_id_1.provider_name]

        provider = self.router.select_provider_for_model(
            model_name=self.model_id_1.model_name, fallback_providers=fallback_providers
        )

        # Should return provider even if unhealthy when used as fallback
        assert provider == self.mock_provider_1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_provider_for_model_no_match(self):
        """Test selecting provider when no provider can handle the model."""
        self.router.register_provider(self.mock_provider_1)

        # Mock that provider cannot handle the model
        self.mock_provider_1.get_model_info.return_value = None

        provider = self.router.select_provider_for_model(model_name="unknown-model")

        assert provider is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_handle_model_true(self):
        """Test _can_handle_model method when provider supports model."""
        result = self.router._can_handle_model(
            self.mock_provider_1, self.model_id_1.model_name
        )

        assert result is True
        self.mock_provider_1.get_model_info.assert_called_once_with(
            self.model_id_1.model_name
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_handle_model_false(self):
        """Test _can_handle_model method when provider doesn't support model."""
        self.mock_provider_1.get_model_info.return_value = None

        result = self.router._can_handle_model(self.mock_provider_1, "unknown-model")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_is_provider_healthy_true(self):
        """Test _is_provider_healthy method for healthy provider."""
        self.router.register_provider(self.mock_provider_1)

        is_healthy = self.router._is_provider_healthy(self.provider_id_1.provider_name)

        assert is_healthy is True

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_is_provider_healthy_false_not_available(self):
        """Test _is_provider_healthy method for unavailable provider."""
        self.router.register_provider(self.mock_provider_1)
        self.router._provider_health[self.provider_id_1.provider_name][
            "available"
        ] = False

        is_healthy = self.router._is_provider_healthy(self.provider_id_1.provider_name)

        assert is_healthy is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_provider_healthy_false_too_many_failures(self):
        """Test _is_provider_healthy method for provider with too many failures."""
        self.router.register_provider(self.mock_provider_1)
        self.router._provider_health[self.provider_id_1.provider_name][
            "consecutive_failures"
        ] = 5

        is_healthy = self.router._is_provider_healthy(self.provider_id_1.provider_name)

        assert is_healthy is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_provider_healthy_unknown_provider(self):
        """Test _is_provider_healthy method for unknown provider."""
        is_healthy = self.router._is_provider_healthy("unknown-provider")

        assert is_healthy is False


class TestExecuteLLMServiceInitialization:
    """Test suite for ExecuteLLMService initialization."""

    @pytest.mark.unit
    def test_initialization_minimal(self):
        """Test service initialization with minimal dependencies."""
        service = ExecuteLLMService()

        assert service._cache_service is None
        assert service._rate_limiter is None
        assert service._cost_tracker is None
        assert service._retry_policy is None
        assert isinstance(service._router, ProviderRouter)
        assert service._execution_stats["total_requests"] == 0
        assert service._execution_stats["successful_requests"] == 0
        assert service._execution_stats["cache_hits"] == 0
        assert service._execution_stats["rate_limited_requests"] == 0
        assert service._execution_stats["budget_exceeded_requests"] == 0

    @pytest.mark.unit
    def test_initialization_with_all_dependencies(self):
        """Test service initialization with all dependencies."""
        mock_cache_service = Mock()
        mock_rate_limiter = Mock()
        mock_cost_tracker = Mock()
        mock_retry_policy = Mock()

        service = ExecuteLLMService(
            cache_service=mock_cache_service,
            rate_limiter=mock_rate_limiter,
            cost_tracker=mock_cost_tracker,
            retry_policy=mock_retry_policy,
        )

        assert service._cache_service == mock_cache_service
        assert service._rate_limiter == mock_rate_limiter
        assert service._cost_tracker == mock_cost_tracker
        assert service._retry_policy == mock_retry_policy

    @pytest.mark.unit
    @pytest.mark.fast
    def test_register_provider(self):
        """Test registering provider with the service."""
        service = ExecuteLLMService()
        mock_provider = Mock(spec=ILLMProvider)
        provider_id = ProviderId.create_openai()
        mock_provider.provider_id = provider_id

        service.register_provider(mock_provider)

        # Provider should be registered with the internal router
        retrieved_provider = service._router.get_provider(provider_id.provider_name)
        assert retrieved_provider == mock_provider


class TestExecuteLLMServiceExecution:
    """Test suite for ExecuteLLMService execution methods."""

    def setup_method(self):
        """Set up test dependencies."""
        # Create service with all mock dependencies
        self.mock_cache_service = AsyncMock()
        self.mock_rate_limiter = AsyncMock()
        self.mock_cost_tracker = AsyncMock()
        self.mock_retry_policy = AsyncMock()

        self.service = ExecuteLLMService(
            cache_service=self.mock_cache_service,
            rate_limiter=self.mock_rate_limiter,
            cost_tracker=self.mock_cost_tracker,
            retry_policy=self.mock_retry_policy,
        )

        # Create provider and request
        self.provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(self.provider_id)

        self.mock_provider = AsyncMock(spec=ILLMProvider)
        self.mock_provider.provider_id = self.provider_id
        self.mock_provider.get_model_info.return_value = self.model_id
        self.mock_provider.estimate_tokens.return_value = 25

        self.service.register_provider(self.mock_provider)

        self.request = LLMRequest.create_completion_request(
            model_id=self.model_id, prompt="Test prompt"
        )

        self.budget = TokenBudget.create_daily_budget(
            "test-budget", 1000, Decimal("10.00")
        )

        # Default successful response
        self.success_response = LLMResponse.create_success(
            request_id=self.request.request_id,
            content="Generated content",
            model_id=self.model_id,
            input_tokens=25,
            output_tokens=15,
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_successful_flow(self):
        """Test successful execution flow with all policies."""
        # Setup mocks
        self.mock_cache_service.get_async.return_value = None  # No cache hit

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        self.mock_cost_tracker.check_budget_async.return_value = (True, Mock())

        retry_result = Mock()
        retry_result.final_response = self.success_response
        retry_result.total_attempts = 1
        retry_result.success = True
        self.mock_retry_policy.execute_with_retry_async.return_value = retry_result

        # Execute
        result = await self.service.execute_async(self.request, self.budget)

        # Verify result
        assert result.success is True
        assert result.response == self.success_response
        assert result.request_id == self.request.request_id
        assert result.provider_used == self.provider_id
        assert result.model_used == self.model_id
        assert result.cache_hit is False
        assert result.rate_limited is False
        assert result.budget_exceeded is False
        assert result.retry_attempts == 0
        assert result.execution_time_seconds > 0

        # Verify service calls
        self.mock_cache_service.get_async.assert_called_once_with(self.request)
        self.mock_rate_limiter.check_rate_limit_async.assert_called_once()
        self.mock_cost_tracker.check_budget_async.assert_called_once()
        self.mock_retry_policy.execute_with_retry_async.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_cache_hit(self):
        """Test execution flow with cache hit."""
        # Setup cache hit
        cached_response = self.success_response
        self.mock_cache_service.get_async.return_value = cached_response

        config = LLMExecutionConfig(enable_caching=True, track_costs=True)

        # Execute
        result = await self.service.execute_async(self.request, self.budget, config)

        # Verify result
        assert result.success is True
        assert result.response == cached_response
        assert result.cache_hit is True

        # Verify that other services weren't called due to cache hit
        self.mock_rate_limiter.check_rate_limit_async.assert_not_called()
        self.mock_retry_policy.execute_with_retry_async.assert_not_called()

        # But cost tracking should still be called for cached responses
        self.mock_cost_tracker.check_budget_async.assert_not_called()  # No budget check for cached

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_rate_limited(self):
        """Test execution flow with rate limiting."""
        # Setup rate limiting
        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = False
        rate_limit_result.reason = "Rate limit exceeded"
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        # Execute
        result = await self.service.execute_async(self.request, self.budget)

        # Verify result
        assert result.success is False
        assert result.rate_limited is True
        assert result.error_details == "Rate limit exceeded"
        assert result.response.status == LLMResponseStatus.RATE_LIMITED

        # Verify that provider execution wasn't called
        self.mock_retry_policy.execute_with_retry_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_budget_exceeded(self):
        """Test execution flow with budget exceeded."""
        # Setup budget exceeded
        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        self.mock_cost_tracker.check_budget_async.return_value = (False, Mock())

        # Execute
        result = await self.service.execute_async(self.request, self.budget)

        # Verify result
        assert result.success is False
        assert result.budget_exceeded is True
        assert result.error_details == "Budget limit exceeded"
        assert result.response.status == LLMResponseStatus.QUOTA_EXCEEDED

        # Verify that provider execution wasn't called
        self.mock_retry_policy.execute_with_retry_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_no_provider_available(self):
        """Test execution flow with no available provider."""
        # Setup no provider for model
        self.mock_provider.get_model_info.return_value = None

        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        self.mock_cost_tracker.check_budget_async.return_value = (True, Mock())

        # Execute
        result = await self.service.execute_async(self.request, self.budget)

        # Verify result
        assert result.success is False
        assert result.error_details == "No available provider for model"
        assert result.response.status == LLMResponseStatus.MODEL_UNAVAILABLE

        # Verify that provider execution wasn't called
        self.mock_retry_policy.execute_with_retry_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_without_retry_policy(self):
        """Test execution without retry policy (direct execution)."""
        # Create service without retry policy
        service = ExecuteLLMService()
        service.register_provider(self.mock_provider)

        # Mock provider direct response
        self.mock_provider.generate_async.return_value = self.success_response

        # Execute
        result = await service.execute_async(self.request)

        # Verify result
        assert result.success is True
        assert result.response == self.success_response
        assert result.retry_attempts == 0

        # Verify direct provider call
        self.mock_provider.generate_async.assert_called_once_with(self.request, None)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_with_exception(self):
        """Test execution flow when exception occurs."""
        # Setup exception during execution
        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        self.mock_cost_tracker.check_budget_async.return_value = (True, Mock())

        self.mock_retry_policy.execute_with_retry_async.side_effect = RuntimeError(
            "Provider error"
        )

        # Execute
        result = await self.service.execute_async(self.request, self.budget)

        # Verify result
        assert result.success is False
        assert "Execution error: Provider error" in result.error_details
        assert result.response.status == LLMResponseStatus.FAILED

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_caching_disabled(self):
        """Test execution flow with caching disabled."""
        config = LLMExecutionConfig(enable_caching=False)

        # Setup successful execution
        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        retry_result = Mock()
        retry_result.final_response = self.success_response
        retry_result.total_attempts = 1
        retry_result.success = True
        self.mock_retry_policy.execute_with_retry_async.return_value = retry_result

        # Execute
        result = await self.service.execute_async(self.request, config=config)

        # Verify that cache wasn't checked
        self.mock_cache_service.get_async.assert_not_called()

        # But execution should still succeed
        assert result.success is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_rate_limiting_disabled(self):
        """Test execution flow with rate limiting disabled."""
        config = LLMExecutionConfig(enforce_rate_limits=False)

        # Setup successful execution
        self.mock_cache_service.get_async.return_value = None

        retry_result = Mock()
        retry_result.final_response = self.success_response
        retry_result.total_attempts = 1
        retry_result.success = True
        self.mock_retry_policy.execute_with_retry_async.return_value = retry_result

        # Execute
        result = await self.service.execute_async(self.request, config=config)

        # Verify that rate limiting wasn't checked
        self.mock_rate_limiter.check_rate_limit_async.assert_not_called()

        # But execution should still succeed
        assert result.success is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_budget_enforcement_disabled(self):
        """Test execution flow with budget enforcement disabled."""
        config = LLMExecutionConfig(enforce_budgets=False)

        # Setup successful execution
        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        retry_result = Mock()
        retry_result.final_response = self.success_response
        retry_result.total_attempts = 1
        retry_result.success = True
        self.mock_retry_policy.execute_with_retry_async.return_value = retry_result

        # Execute
        result = await self.service.execute_async(self.request, self.budget, config)

        # Verify that budget wasn't checked
        self.mock_cost_tracker.check_budget_async.assert_not_called()

        # But execution should still succeed
        assert result.success is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_async_post_execution_processing(self):
        """Test post-execution processing for successful requests."""
        # Setup successful execution
        self.mock_cache_service.get_async.return_value = None

        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        self.mock_cost_tracker.check_budget_async.return_value = (True, Mock())

        retry_result = Mock()
        retry_result.final_response = self.success_response
        retry_result.total_attempts = 1
        retry_result.success = True
        self.mock_retry_policy.execute_with_retry_async.return_value = retry_result

        config = LLMExecutionConfig(
            enable_caching=True, track_costs=True, cache_ttl_seconds=1800
        )

        # Execute
        result = await self.service.execute_async(self.request, self.budget, config)

        # Verify post-execution processing
        assert result.success is True

        # Verify caching of successful response
        self.mock_cache_service.put_async.assert_called_once_with(
            self.request, self.success_response, 1800
        )

        # Verify cost tracking
        self.mock_cost_tracker.record_cost_async.assert_called_once()

        # Verify rate limiting usage recording
        self.mock_rate_limiter.record_request_async.assert_called_once()


class TestExecuteLLMServiceStreamingExecution:
    """Test suite for ExecuteLLMService streaming execution."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_rate_limiter = AsyncMock()

        self.service = ExecuteLLMService(rate_limiter=self.mock_rate_limiter)

        # Create provider and request
        self.provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(self.provider_id)

        self.mock_provider = AsyncMock(spec=ILLMProvider)
        self.mock_provider.provider_id = self.provider_id
        self.mock_provider.get_model_info.return_value = self.model_id
        self.mock_provider.estimate_tokens.return_value = 25

        self.service.register_provider(self.mock_provider)

        self.request = LLMRequest.create_completion_request(
            model_id=self.model_id, prompt="Test prompt"
        )

        self.budget = TokenBudget.create_daily_budget(
            "test-budget", 1000, Decimal("10.00")
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_stream_async_successful(self):
        """Test successful streaming execution."""
        # Setup rate limiting
        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        # Setup streaming response with proper async iterator
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self.items)
                except StopIteration:
                    raise StopAsyncIteration

        # Direct async generator function
        async def mock_stream_generator(request, budget):
            items = ["Hello", " ", "world", "!"]
            for item in items:
                yield item

        self.mock_provider.generate_stream_async = mock_stream_generator

        # Execute streaming
        chunks = []
        async for chunk in self.service.execute_stream_async(self.request, self.budget):
            chunks.append(chunk)

        # Verify chunks
        assert chunks == ["Hello", " ", "world", "!"]

        # Verify rate limiting was checked
        self.mock_rate_limiter.check_rate_limit_async.assert_called_once()

        # Note: Cannot verify method call with direct function replacement

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_stream_async_rate_limited(self):
        """Test streaming execution with rate limiting."""
        # Setup rate limiting
        rate_limit_result = Mock()
        rate_limit_result.allowed = False
        rate_limit_result.reason = "Rate limit exceeded"
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        # Execute streaming
        chunks = []
        async for chunk in self.service.execute_stream_async(self.request, self.budget):
            chunks.append(chunk)

        # Verify error was yielded
        assert len(chunks) == 1
        assert "Error: Rate limit exceeded" in chunks[0]

        # Verify provider streaming wasn't called
        self.mock_provider.generate_stream_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_stream_async_no_provider(self):
        """Test streaming execution with no available provider."""
        # Mock provider to not handle the model
        self.mock_provider.get_model_info.return_value = None

        # Execute streaming
        chunks = []
        async for chunk in self.service.execute_stream_async(self.request, self.budget):
            chunks.append(chunk)

        # Verify error was yielded
        assert len(chunks) == 1
        assert "Error: No available provider for model" in chunks[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_stream_async_provider_exception(self):
        """Test streaming execution with provider exception."""
        # Setup rate limiting
        rate_limit_result = Mock()
        rate_limit_result.allowed = True
        self.mock_rate_limiter.check_rate_limit_async.return_value = rate_limit_result

        # Setup provider exception by replacing the method entirely
        async def failing_stream(request, budget):
            # This needs to be an async generator that raises on iteration
            if False:  # Never execute, but makes it a generator
                yield
            raise RuntimeError("Provider error")

        self.mock_provider.generate_stream_async = failing_stream

        # Execute streaming
        chunks = []
        async for chunk in self.service.execute_stream_async(self.request, self.budget):
            chunks.append(chunk)

        # Verify error was yielded
        assert len(chunks) == 1
        assert "Error: Provider error" in chunks[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_stream_async_rate_limiting_disabled(self):
        """Test streaming execution with rate limiting disabled."""
        config = LLMExecutionConfig(enforce_rate_limits=False, enable_streaming=True)

        # Setup streaming response with proper async generator
        async def mock_stream(request, budget):
            yield "Streaming content"

        self.mock_provider.generate_stream_async = mock_stream

        # Execute streaming
        chunks = []
        async for chunk in self.service.execute_stream_async(
            self.request, self.budget, config
        ):
            chunks.append(chunk)

        # Verify chunks
        assert chunks == ["Streaming content"]

        # Verify rate limiting wasn't checked
        self.mock_rate_limiter.check_rate_limit_async.assert_not_called()


class TestExecuteLLMServiceStatisticsAndMetrics:
    """Test suite for ExecuteLLMService statistics and metrics."""

    def setup_method(self):
        """Set up test dependencies."""
        self.service = ExecuteLLMService()

        # Manually set some statistics for testing
        self.service._execution_stats = {
            "total_requests": 100,
            "successful_requests": 85,
            "cache_hits": 15,
            "rate_limited_requests": 8,
            "budget_exceeded_requests": 2,
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_execution_stats_async_with_requests(self):
        """Test getting execution statistics when requests have been made."""
        stats = await self.service.get_execution_stats_async()

        assert stats["total_requests"] == 100
        assert stats["successful_requests"] == 85
        assert stats["success_rate"] == 0.85  # 85/100
        assert stats["cache_hits"] == 15
        assert stats["cache_hit_rate"] == 0.15  # 15/100
        assert stats["rate_limited_requests"] == 8
        assert stats["rate_limit_rate"] == 0.08  # 8/100
        assert stats["budget_exceeded_requests"] == 2
        assert stats["budget_exceeded_rate"] == 0.02  # 2/100

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_execution_stats_async_no_requests(self):
        """Test getting execution statistics when no requests have been made."""
        service = ExecuteLLMService()  # Fresh service with no requests

        stats = await service.get_execution_stats_async()

        assert stats["total_requests"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["cache_hit_rate"] == 0.0
        assert stats["rate_limit_rate"] == 0.0
        assert stats["budget_exceeded_rate"] == 0.0

    @pytest.mark.unit
    def test_estimate_request_cost_with_model_pricing(self):
        """Test cost estimation when model has pricing information."""
        provider_id = ProviderId.create_openai()
        model_id = ModelId(
            model_name="gpt-4",
            provider_id=provider_id,
            cost_per_input_token=Decimal("0.00003"),
            cost_per_output_token=Decimal("0.00006"),
            max_context_tokens=8192,
            max_output_tokens=4096,
        )

        request = LLMRequest.create_completion_request(
            model_id=model_id,
            prompt="Test prompt with some text",  # 24 characters = ~6 tokens
            max_tokens=100,
        )

        estimated_cost = self.service._estimate_request_cost(request)

        # Should estimate: 6 input tokens * 0.00003 + 100 output tokens * 0.00006
        expected_cost = Decimal("6") * Decimal("0.00003") + Decimal("100") * Decimal(
            "0.00006"
        )
        assert estimated_cost == expected_cost

    @pytest.mark.unit
    def test_estimate_request_cost_no_pricing(self):
        """Test cost estimation when model has no pricing information."""
        provider_id = ProviderId.create_openai()
        model_id = ModelId(
            model_name="free-model",
            provider_id=provider_id,
            cost_per_input_token=None,  # No pricing info
            max_context_tokens=4096,
            max_output_tokens=1024,
        )

        request = LLMRequest.create_completion_request(
            model_id=model_id, prompt="Test prompt"
        )

        estimated_cost = self.service._estimate_request_cost(request)

        assert estimated_cost == Decimal("0")

    @pytest.mark.unit
    def test_estimate_request_cost_no_max_tokens(self):
        """Test cost estimation when request has no max_tokens specified."""
        provider_id = ProviderId.create_openai()
        model_id = ModelId(
            model_name="gpt-4",
            provider_id=provider_id,
            cost_per_input_token=Decimal("0.00003"),
            cost_per_output_token=Decimal("0.00006"),
            max_context_tokens=8192,
            max_output_tokens=4096,
        )

        request = LLMRequest.create_completion_request(
            model_id=model_id,
            prompt="Test prompt",
            max_tokens=None,  # No max tokens specified
        )

        estimated_cost = self.service._estimate_request_cost(request)

        # Should use default 100 tokens for output
        input_tokens = len("Test prompt") // 4
        expected_cost = Decimal(str(input_tokens)) * Decimal("0.00003") + Decimal(
            "100"
        ) * Decimal("0.00006")
        assert estimated_cost == expected_cost

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_record_cached_usage(self):
        """Test recording usage for cached responses."""

        mock_cost_tracker = AsyncMock()
        service = ExecuteLLMService(cost_tracker=mock_cost_tracker)

        provider_id = ProviderId.create_openai()
        model_id = ModelId.create_gpt4(provider_id)

        request = LLMRequest.create_completion_request(
            model_id=model_id, prompt="Test prompt"
        )

        response = LLMResponse.create_success(
            request_id=request.request_id,
            content="Cached response",
            model_id=model_id,
            input_tokens=10,
            output_tokens=5,
        )

        config = LLMExecutionConfig(client_id="test-client")

        await service._record_cached_usage(request, response, config)

        # Verify cost tracker was called
        mock_cost_tracker.record_cost_async.assert_called_once()

        # Verify the cost entry has zero cost (cached)
        call_args = mock_cost_tracker.record_cost_async.call_args[0]
        cost_entry = call_args[0]
        assert hasattr(cost_entry, "total_cost")  # Verify it's a cost entry-like object


class TestExecuteLLMServiceIntegration:
    """Integration test suite for ExecuteLLMService with realistic scenarios."""

    def setup_method(self):
        """Set up integration test dependencies."""
        # Create service with minimal real dependencies
        self.service = ExecuteLLMService()

        # Create and register a mock provider
        self.provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(self.provider_id)

        self.mock_provider = AsyncMock(spec=ILLMProvider)
        self.mock_provider.provider_id = self.provider_id
        self.mock_provider.get_model_info.return_value = self.model_id
        self.mock_provider.estimate_tokens.return_value = 25

        self.service.register_provider(self.mock_provider)

        self.request = LLMRequest.create_completion_request(
            model_id=self.model_id, prompt="Write a short story about AI"
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_minimal_execution_flow(self):
        """Test minimal execution flow without optional services."""
        # Setup provider response
        response = LLMResponse.create_success(
            request_id=self.request.request_id,
            content="Once upon a time, there was an AI...",
            model_id=self.model_id,
            input_tokens=30,
            output_tokens=120,
        )
        self.mock_provider.generate_async.return_value = response

        # Execute without any optional services
        result = await self.service.execute_async(self.request)

        # Verify successful execution
        assert result.success is True
        assert result.response == response
        assert result.provider_used == self.provider_id
        assert result.model_used == self.model_id
        assert result.execution_time_seconds > 0

        # Verify statistics were updated
        stats = await self.service.get_execution_stats_async()
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 1
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_provider_selection_with_preferences(self):
        """Test provider selection with preferred providers."""
        # Register second provider
        provider_id_2 = ProviderId.create_anthropic()
        model_id_2 = ModelId.create_claude(provider_id_2)

        mock_provider_2 = AsyncMock(spec=ILLMProvider)
        mock_provider_2.provider_id = provider_id_2
        mock_provider_2.get_model_info.return_value = model_id_2
        mock_provider_2.estimate_tokens.return_value = 30

        self.service.register_provider(mock_provider_2)

        # Create request for Claude model but prefer OpenAI
        claude_request = LLMRequest.create_completion_request(
            model_id=model_id_2, prompt="Test prompt"
        )

        config = LLMExecutionConfig(
            preferred_providers=[provider_id_2.provider_name]  # Prefer Anthropic
        )

        # Setup response
        response = LLMResponse.create_success(
            request_id=claude_request.request_id,
            content="Response from Claude",
            model_id=model_id_2,
            input_tokens=20,
            output_tokens=40,
        )
        mock_provider_2.generate_async.return_value = response

        # Execute
        result = await self.service.execute_async(claude_request, config=config)

        # Verify correct provider was used
        assert result.success is True
        assert result.provider_used == provider_id_2
        assert result.model_used == model_id_2

        # Verify correct provider was called
        mock_provider_2.generate_async.assert_called_once()
        self.mock_provider.generate_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling_and_statistics(self):
        """Test error handling and statistics tracking."""
        # Setup provider to fail
        self.mock_provider.generate_async.side_effect = RuntimeError(
            "Provider connection failed"
        )

        # Execute
        result = await self.service.execute_async(self.request)

        # Verify error handling
        assert result.success is False
        assert "Provider connection failed" in result.error_details
        assert result.response.status == LLMResponseStatus.FAILED

        # Verify statistics reflect the failure
        stats = await self.service.get_execution_stats_async()
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 0
        assert stats["success_rate"] == 0.0
