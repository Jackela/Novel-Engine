#!/usr/bin/env python3
"""
ExecuteLLM Application Service

Main orchestration service for AI Gateway operations. Coordinates
provider selection, policy enforcement, and comprehensive execution
of LLM requests with intelligent routing and error handling.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

from ...domain.services.llm_provider import (
    ILLMProvider,
    LLMRequest,
    LLMResponse,
    LLMResponseStatus,
)
from ...domain.value_objects.common import ModelId, ProviderId, TokenBudget
from ...infrastructure.policies.caching import ICacheService
from ...infrastructure.policies.cost_tracking import CostEntry, ICostTracker
from ...infrastructure.policies.rate_limiting import IRateLimiter
from ...infrastructure.policies.retry_fallback import IRetryPolicy


@dataclass
class LLMExecutionConfig:
    """
    Configuration for LLM execution behavior.

    Controls various aspects of request processing including
    caching, rate limiting, cost tracking, and retry behavior.
    """

    # Caching configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Rate limiting configuration
    enforce_rate_limits: bool = True
    client_id: Optional[str] = None

    # Cost tracking configuration
    track_costs: bool = True
    enforce_budgets: bool = True

    # Retry configuration
    enable_retries: bool = True

    # Provider selection
    preferred_providers: List[str] = field(default_factory=list)
    fallback_providers: List[str] = field(default_factory=list)

    # Streaming configuration
    enable_streaming: bool = False

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMExecutionResult:
    """
    Comprehensive result of LLM execution.

    Contains the response, execution metadata, policy enforcement
    results, and performance metrics for analysis and monitoring.
    """

    # Core response
    response: Optional[LLMResponse]
    success: bool

    # Execution metadata
    request_id: UUID
    execution_time_seconds: float
    provider_used: Optional[ProviderId]
    model_used: Optional[ModelId]

    # Policy enforcement results
    cache_hit: bool = False
    rate_limited: bool = False
    budget_exceeded: bool = False
    retry_attempts: int = 0

    # Cost and usage tracking
    cost_entry: Optional[CostEntry] = None
    token_usage: Dict[str, int] = field(default_factory=dict)

    # Performance metrics
    cache_lookup_time: float = 0.0
    rate_limit_check_time: float = 0.0
    provider_response_time: float = 0.0

    # Error handling
    error_details: Optional[str] = None
    fallback_used: bool = False

    # Additional context
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.token_usage.get("total_tokens", 0)

    @property
    def total_cost(self) -> Decimal:
        """Get total cost of execution."""
        return self.cost_entry.total_cost if self.cost_entry else Decimal("0")


class ProviderRouter:
    """
    Intelligent provider routing and selection.

    Handles provider selection based on model availability,
    performance metrics, and fallback strategies.
    """

    def __init__(self):
        self._providers: Dict[str, ILLMProvider] = {}
        self._provider_health: Dict[str, Dict[str, Any]] = {}
        self._performance_metrics: Dict[str, Dict[str, float]] = {}

    def register_provider(self, provider: ILLMProvider) -> None:
        """Register a provider with the router."""
        provider_key = provider.provider_id.provider_name
        self._providers[provider_key] = provider

        # Initialize health and metrics tracking
        self._provider_health[provider_key] = {
            "available": True,
            "last_check": datetime.now(),
            "consecutive_failures": 0,
        }

        self._performance_metrics[provider_key] = {
            "avg_response_time": 0.0,
            "success_rate": 1.0,
            "total_requests": 0,
        }

    def get_provider(self, provider_name: str) -> Optional[ILLMProvider]:
        """Get specific provider by name."""
        return self._providers.get(provider_name)

    def select_provider_for_model(
        self,
        model_name: str,
        preferred_providers: List[str] = None,
        fallback_providers: List[str] = None,
    ) -> Optional[ILLMProvider]:
        """
        Select best provider for given model.

        Args:
            model_name: Name of model to use
            preferred_providers: List of preferred provider names
            fallback_providers: List of fallback provider names

        Returns:
            Selected provider if available, None otherwise
        """
        # Check preferred providers first
        for provider_name in preferred_providers or []:
            provider = self._providers.get(provider_name)
            if provider and self._can_handle_model(provider, model_name):
                if self._is_provider_healthy(provider_name):
                    return provider

        # Check all available providers
        for provider_name, provider in self._providers.items():
            if self._can_handle_model(provider, model_name):
                if self._is_provider_healthy(provider_name):
                    return provider

        # Check fallback providers
        for provider_name in fallback_providers or []:
            provider = self._providers.get(provider_name)
            if provider and self._can_handle_model(provider, model_name):
                # Allow unhealthy providers as fallback
                return provider

        return None

    def _can_handle_model(self, provider: ILLMProvider, model_name: str) -> bool:
        """Check if provider can handle specified model."""
        model_info = provider.get_model_info(model_name)
        return model_info is not None

    def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if provider is healthy."""
        health = self._provider_health.get(provider_name, {})
        return (
            health.get("available", False) and health.get("consecutive_failures", 0) < 3
        )


class ExecuteLLMService:
    """
    Main orchestration service for LLM execution.

    Provides comprehensive LLM execution with policy enforcement,
    intelligent routing, error handling, and performance monitoring.
    """

    def __init__(
        self,
        cache_service: Optional[ICacheService] = None,
        rate_limiter: Optional[IRateLimiter] = None,
        cost_tracker: Optional[ICostTracker] = None,
        retry_policy: Optional[IRetryPolicy] = None,
    ):
        """
        Initialize ExecuteLLM service.

        Args:
            cache_service: Optional caching service
            rate_limiter: Optional rate limiting service
            cost_tracker: Optional cost tracking service
            retry_policy: Optional retry policy service
        """
        self._cache_service = cache_service
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._retry_policy = retry_policy

        # Provider routing
        self._router = ProviderRouter()

        # Performance monitoring
        self._execution_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "cache_hits": 0,
            "rate_limited_requests": 0,
            "budget_exceeded_requests": 0,
        }

    def register_provider(self, provider: ILLMProvider) -> None:
        """
        Register LLM provider with the service.

        Args:
            provider: Provider to register
        """
        self._router.register_provider(provider)

    async def execute_async(
        self,
        request: LLMRequest,
        budget: Optional[TokenBudget] = None,
        config: Optional[LLMExecutionConfig] = None,
    ) -> LLMExecutionResult:
        """
        Execute LLM request with comprehensive orchestration.

        Args:
            request: LLM request to execute
            budget: Optional token budget for enforcement
            config: Optional execution configuration

        Returns:
            Comprehensive execution result
        """
        start_time = asyncio.get_event_loop().time()
        config = config or LLMExecutionConfig()

        # Initialize result
        result = LLMExecutionResult(
            response=None,
            success=False,
            request_id=request.request_id,
            execution_time_seconds=0.0,
            provider_used=None,
            model_used=request.model_id,
        )

        try:
            # Update statistics
            self._execution_stats["total_requests"] += 1

            # Step 1: Check cache if enabled
            if config.enable_caching and self._cache_service:
                cache_start = asyncio.get_event_loop().time()
                cached_response = await self._cache_service.get_async(request)
                result.cache_lookup_time = asyncio.get_event_loop().time() - cache_start

                if cached_response:
                    result.response = cached_response
                    result.success = True
                    result.cache_hit = True
                    self._execution_stats["cache_hits"] += 1
                    self._execution_stats["successful_requests"] += 1

                    # Still record usage for cached responses
                    if config.track_costs and self._cost_tracker:
                        await self._record_cached_usage(
                            request, cached_response, config
                        )

                    result.execution_time_seconds = (
                        asyncio.get_event_loop().time() - start_time
                    )
                    return result

            # Step 2: Rate limiting check
            if config.enforce_rate_limits and self._rate_limiter:
                rate_limit_start = asyncio.get_event_loop().time()

                # Select provider for rate limiting check
                provider = self._router.select_provider_for_model(
                    request.model_id.model_name,
                    config.preferred_providers,
                    config.fallback_providers,
                )

                if provider:
                    estimated_tokens = provider.estimate_tokens(request.prompt)
                    rate_limit_result = await self._rate_limiter.check_rate_limit_async(
                        provider.provider_id, estimated_tokens, config.client_id
                    )

                    result.rate_limit_check_time = (
                        asyncio.get_event_loop().time() - rate_limit_start
                    )

                    if not rate_limit_result.allowed:
                        result.rate_limited = True
                        result.error_details = rate_limit_result.reason
                        self._execution_stats["rate_limited_requests"] += 1

                        # Create rate limited response
                        result.response = LLMResponse.create_error(
                            request_id=request.request_id,
                            status=LLMResponseStatus.RATE_LIMITED,
                            error_details=rate_limit_result.reason,
                        )

                        result.execution_time_seconds = (
                            asyncio.get_event_loop().time() - start_time
                        )
                        return result

            # Step 3: Budget enforcement
            if config.enforce_budgets and budget and self._cost_tracker:
                estimated_cost = self._estimate_request_cost(request)

                is_allowed, budget_status = await self._cost_tracker.check_budget_async(
                    budget, estimated_cost
                )

                if not is_allowed:
                    result.budget_exceeded = True
                    result.error_details = "Budget limit exceeded"
                    self._execution_stats["budget_exceeded_requests"] += 1

                    result.response = LLMResponse.create_error(
                        request_id=request.request_id,
                        status=LLMResponseStatus.QUOTA_EXCEEDED,
                        error_details="Budget limit exceeded",
                    )

                    result.execution_time_seconds = (
                        asyncio.get_event_loop().time() - start_time
                    )
                    return result

            # Step 4: Provider selection and execution
            provider = self._router.select_provider_for_model(
                request.model_id.model_name,
                config.preferred_providers,
                config.fallback_providers,
            )

            if not provider:
                result.error_details = "No available provider for model"
                result.response = LLMResponse.create_error(
                    request_id=request.request_id,
                    status=LLMResponseStatus.MODEL_UNAVAILABLE,
                    error_details="No available provider for model",
                )
                result.execution_time_seconds = (
                    asyncio.get_event_loop().time() - start_time
                )
                return result

            result.provider_used = provider.provider_id

            # Step 5: Execute with retry policy
            provider_start = asyncio.get_event_loop().time()

            if config.enable_retries and self._retry_policy:
                retry_result = await self._retry_policy.execute_with_retry_async(
                    lambda: provider.generate_async(request, budget),
                    request,
                    provider.provider_id,
                )

                result.response = retry_result.final_response
                result.retry_attempts = retry_result.total_attempts - 1
                result.success = retry_result.success

            else:
                # Direct execution without retries
                result.response = await provider.generate_async(request, budget)
                result.success = result.response.status == LLMResponseStatus.SUCCESS

            result.provider_response_time = (
                asyncio.get_event_loop().time() - provider_start
            )

            # Step 6: Post-execution processing
            if result.success:
                self._execution_stats["successful_requests"] += 1

                # Cache successful response
                if config.enable_caching and self._cache_service and result.response:
                    await self._cache_service.put_async(
                        request, result.response, config.cache_ttl_seconds
                    )

                # Record cost tracking
                if config.track_costs and self._cost_tracker and result.response:
                    cost_entry = CostEntry.from_request_response(
                        request,
                        result.response,
                        budget.budget_id if budget else None,
                        config.client_id,
                    )
                    result.cost_entry = cost_entry
                    await self._cost_tracker.record_cost_async(cost_entry)

                # Record rate limiting usage
                if self._rate_limiter and result.response:
                    usage_stats = result.response.usage_stats or {}
                    actual_tokens = usage_stats.get("total_tokens", 0)
                    await self._rate_limiter.record_request_async(
                        provider.provider_id, actual_tokens, config.client_id
                    )

            # Extract token usage
            if result.response and result.response.usage_stats:
                result.token_usage = result.response.usage_stats.copy()

        except Exception as e:
            result.error_details = f"Execution error: {str(e)}"
            result.response = LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.FAILED,
                error_details=result.error_details,
            )

        result.execution_time_seconds = asyncio.get_event_loop().time() - start_time
        return result

    async def execute_stream_async(
        self,
        request: LLMRequest,
        budget: Optional[TokenBudget] = None,
        config: Optional[LLMExecutionConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Execute LLM request with streaming response.

        Args:
            request: LLM request to execute
            budget: Optional token budget for enforcement
            config: Optional execution configuration

        Yields:
            Streaming response chunks
        """
        config = config or LLMExecutionConfig(enable_streaming=True)

        # Perform pre-execution checks (similar to execute_async)
        if config.enforce_rate_limits and self._rate_limiter:
            provider = self._router.select_provider_for_model(
                request.model_id.model_name,
                config.preferred_providers,
                config.fallback_providers,
            )

            if provider:
                estimated_tokens = provider.estimate_tokens(request.prompt)
                rate_limit_result = await self._rate_limiter.check_rate_limit_async(
                    provider.provider_id, estimated_tokens, config.client_id
                )

                if not rate_limit_result.allowed:
                    yield f"Error: {rate_limit_result.reason}"
                    return

        # Provider selection
        provider = self._router.select_provider_for_model(
            request.model_id.model_name,
            config.preferred_providers,
            config.fallback_providers,
        )

        if not provider:
            yield "Error: No available provider for model"
            return

        # Stream execution
        try:
            async for chunk in provider.generate_stream_async(request, budget):
                yield chunk
        except Exception as e:
            yield f"Error: {str(e)}"

    async def get_execution_stats_async(self) -> Dict[str, Any]:
        """
        Get execution statistics and performance metrics.

        Returns:
            Dictionary with comprehensive execution statistics
        """
        total_requests = self._execution_stats["total_requests"]

        if total_requests == 0:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "cache_hit_rate": 0.0,
                "rate_limit_rate": 0.0,
                "budget_exceeded_rate": 0.0,
            }

        return {
            "total_requests": total_requests,
            "successful_requests": self._execution_stats["successful_requests"],
            "success_rate": self._execution_stats["successful_requests"]
            / total_requests,
            "cache_hits": self._execution_stats["cache_hits"],
            "cache_hit_rate": self._execution_stats["cache_hits"] / total_requests,
            "rate_limited_requests": self._execution_stats["rate_limited_requests"],
            "rate_limit_rate": self._execution_stats["rate_limited_requests"]
            / total_requests,
            "budget_exceeded_requests": self._execution_stats[
                "budget_exceeded_requests"
            ],
            "budget_exceeded_rate": self._execution_stats["budget_exceeded_requests"]
            / total_requests,
        }

    def _estimate_request_cost(self, request: LLMRequest) -> Decimal:
        """Estimate cost of request based on model pricing."""
        model_id = request.model_id

        if not model_id.cost_per_input_token:
            return Decimal("0")  # No cost information available

        # Estimate input tokens
        estimated_input_tokens = len(request.prompt) // 4  # Rough estimation
        estimated_output_tokens = request.max_tokens or 100

        input_cost = (
            Decimal(str(estimated_input_tokens)) * model_id.cost_per_input_token
        )
        output_cost = Decimal(str(estimated_output_tokens)) * (
            model_id.cost_per_output_token or model_id.cost_per_input_token
        )

        return input_cost + output_cost

    async def _record_cached_usage(
        self, request: LLMRequest, response: LLMResponse, config: LLMExecutionConfig
    ) -> None:
        """Record usage for cached responses."""
        if self._cost_tracker:
            cost_entry = CostEntry.from_request_response(
                request,
                response,
                None,  # No budget for cached responses
                config.client_id,
            )
            # Mark as cached with zero cost (all cost fields must be zero)
            cost_entry = cost_entry.__class__(
                **{
                    **cost_entry.__dict__,
                    "total_cost": Decimal("0"),
                    "input_cost": Decimal("0"),
                    "output_cost": Decimal("0"),
                }
            )
            await self._cost_tracker.record_cost_async(cost_entry)
