"""
Tests for ModelRouter Service

Unit tests for intelligent model routing, circuit breaker, fallback chain,
and routing analytics.

Warzone 4: AI Brain - BRAIN-028A
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.contexts.knowledge.application.services.model_registry import (
    ModelRegistry,
)
from src.contexts.knowledge.application.services.model_router import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ModelRouter,
    RoutingConfig,
    RoutingDecision,
    RoutingReason,
    create_model_router,
)
from src.contexts.knowledge.domain.models.model_registry import (
    LLMProvider,
    ModelDefinition,
    TaskModelConfig,
    TaskType,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def model_registry() -> ModelRegistry:
    """Create a model registry for testing."""
    return ModelRegistry()


@pytest.fixture
def model_router(model_registry: ModelRegistry) -> ModelRouter:
    """Create a model router for testing."""
    return ModelRouter(model_registry)


class TestRoutingReason:
    """Tests for RoutingReason enum."""

    def test_reason_values(self) -> None:
        """Test routing reason enum values are correct strings."""
        assert RoutingReason.TASK_DEFAULT.value == "task_default"
        assert RoutingReason.COST_BUDGET.value == "cost_budget"
        assert RoutingReason.FALLBACK.value == "fallback"
        assert RoutingReason.CIRCUIT_OPEN.value == "circuit_open"
        assert RoutingReason.UNAVAILABLE.value == "unavailable"
        assert RoutingReason.MANUAL_OVERRIDE.value == "manual_override"


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_state_values(self) -> None:
        """Test circuit state enum values are correct strings."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state(self) -> None:
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test:model")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert not breaker.is_open()

    def test_can_request_when_closed(self) -> None:
        """Test can_request returns True when circuit is closed."""
        breaker = CircuitBreaker("test:model")
        assert breaker.can_request()

    def test_circuit_opens_after_threshold(self) -> None:
        """Test circuit opens after failure threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test:model", config)

        # Record failures up to threshold
        async def record_failures():
            for _ in range(config.failure_threshold):
                await breaker.record_failure()

        asyncio.run(record_failures())

        assert breaker.is_open()

    def test_circuit_allows_request_in_half_open(self) -> None:
        """Test circuit allows requests in HALF_OPEN state."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0,  # Immediate transition
        )
        breaker = CircuitBreaker("test:model", config)

        # Open the circuit
        async def record_failures():
            await breaker.record_failure()
            await breaker.record_failure()

        asyncio.run(record_failures())

        assert breaker.is_open()

        # Force transition to HALF_OPEN by simulating timeout
        breaker._state.state = CircuitState.HALF_OPEN
        breaker._state.last_state_change = datetime.now()

        # Should allow requests in half-open
        assert breaker.can_request()

    def test_success_in_half_open_closes_circuit(self) -> None:
        """Test consecutive successes in HALF_OPEN closes the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test:model", config)

        # Set to HALF_OPEN
        breaker._state.state = CircuitState.HALF_OPEN

        # Record successes
        async def record_successes():
            await breaker.record_success()
            await breaker.record_success()

        asyncio.run(record_successes())

        # Should be closed now
        assert breaker.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self) -> None:
        """Test failure in HALF_OPEN reopens the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test:model", config)

        # Set to HALF_OPEN with some success count
        breaker._state.state = CircuitState.HALF_OPEN
        breaker._state.success_count = 1

        # Record failure
        asyncio.run(breaker.record_failure())

        # Should be open again
        assert breaker.state == CircuitState.OPEN

    def test_get_state_info(self) -> None:
        """Test getting circuit breaker state info."""
        breaker = CircuitBreaker("test:model")
        info = breaker.get_state_info()

        assert info["model"] == "test:model"
        assert info["state"] == "closed"
        assert "failure_count" in info
        assert "config" in info


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_decision_properties(self) -> None:
        """Test routing decision properties."""
        decision = RoutingDecision(
            task_type=TaskType.CREATIVE,
            selected_provider=LLMProvider.GEMINI,
            selected_model="gemini-2.0-flash",
            reason=RoutingReason.TASK_DEFAULT,
        )

        assert decision.task_type == TaskType.CREATIVE
        assert decision.selected_provider == LLMProvider.GEMINI
        assert decision.selected_model == "gemini-2.0-flash"
        assert decision.reason == RoutingReason.TASK_DEFAULT
        assert not decision.fallback_used
        assert decision.qualified_model_name == "gemini:gemini-2.0-flash"

    def test_to_log_dict(self) -> None:
        """Test converting decision to log dictionary."""
        decision = RoutingDecision(
            task_type=TaskType.LOGICAL,
            selected_provider=LLMProvider.OPENAI,
            selected_model="gpt-4o",
            reason=RoutingReason.FALLBACK,
            fallback_used=True,
            execution_time_ms=5.5,
        )

        log_dict = decision.to_log_dict()

        assert log_dict["task_type"] == "logical"
        assert log_dict["provider"] == "openai"
        assert log_dict["model"] == "gpt-4o"
        assert log_dict["qualified_name"] == "openai:gpt-4o"
        assert log_dict["reason"] == "fallback"
        assert log_dict["fallback_used"] is True
        assert log_dict["execution_time_ms"] == 5.5


class TestModelRouter:
    """Tests for ModelRouter service."""

    def test_initialization(self, model_registry: ModelRegistry) -> None:
        """Test router initializes correctly."""
        router = ModelRouter(model_registry)

        assert router._registry is model_registry
        assert router.get_routing_stats()["total_decisions"] == 0

    def test_select_model_by_task_default(self, model_router: ModelRouter) -> None:
        """Test selecting model by task type uses default config."""
        decision = model_router.select_model(TaskType.CREATIVE)

        assert decision.task_type == TaskType.CREATIVE
        assert decision.selected_provider in [
            LLMProvider.GEMINI,
            LLMProvider.ANTHROPIC,
            LLMProvider.OPENAI,
        ]
        assert decision.reason == RoutingReason.TASK_DEFAULT
        assert not decision.fallback_used

    def test_select_model_by_task_logical(self, model_router: ModelRouter) -> None:
        """Test selecting model for LOGICAL task."""
        decision = model_router.select_model(TaskType.LOGICAL)

        assert decision.task_type == TaskType.LOGICAL
        # LOGICAL task should prefer OpenAI
        assert decision.selected_provider == LLMProvider.OPENAI
        assert decision.reason == RoutingReason.TASK_DEFAULT

    def test_select_model_by_task_fast(self, model_router: ModelRouter) -> None:
        """Test selecting model for FAST task."""
        decision = model_router.select_model(TaskType.FAST)

        assert decision.task_type == TaskType.FAST
        assert decision.selected_provider == LLMProvider.GEMINI  # Fast models

    def test_select_model_by_task_cheap(self, model_router: ModelRouter) -> None:
        """Test selecting model for CHEAP task."""
        decision = model_router.select_model(TaskType.CHEAP)

        assert decision.task_type == TaskType.CHEAP
        # CHEAP task should use lowest cost option
        model = model_router._registry.get_model(
            decision.selected_provider, decision.selected_model
        )
        if model:
            # Gemini Flash is cheap, or Ollama which is free
            assert decision.selected_provider in [
                LLMProvider.GEMINI,
                LLMProvider.OLLAMA,
            ]

    def test_select_model_with_cost_constraint(self, model_router: ModelRouter) -> None:
        """Test selecting model with cost budget constraint."""
        config = RoutingConfig(max_cost_per_1m_tokens=1.0)
        decision = model_router.select_model(TaskType.LOGICAL, config)

        # Should select a model within cost limit
        model = model_router._registry.get_model(
            decision.selected_provider, decision.selected_model
        )
        if model:
            assert model.cost_per_1m_output_tokens <= 1.0

    def test_select_model_with_blocked_provider(
        self, model_router: ModelRouter
    ) -> None:
        """Test selecting model with blocked providers."""
        config = RoutingConfig(blocked_providers=[LLMProvider.OPENAI])
        decision = model_router.select_model(TaskType.LOGICAL, config)

        # Should not use blocked provider
        assert decision.selected_provider != LLMProvider.OPENAI

    def test_select_model_by_name(self, model_router: ModelRouter) -> None:
        """Test selecting specific model by name."""
        decision = model_router.select_model_by_name("gpt4")

        assert decision.reason == RoutingReason.MANUAL_OVERRIDE
        assert decision.selected_provider == LLMProvider.OPENAI
        assert "gpt-4" in decision.selected_model

    def test_select_model_by_qualified_name(self, model_router: ModelRouter) -> None:
        """Test selecting model with qualified name."""
        decision = model_router.select_model_by_name(
            "anthropic:claude-3-5-sonnet-20241022"
        )

        assert decision.reason == RoutingReason.MANUAL_OVERRIDE
        assert decision.selected_provider == LLMProvider.ANTHROPIC
        assert "sonnet" in decision.selected_model

    def test_select_model_by_invalid_name_falls_back_to_task(
        self, model_router: ModelRouter
    ) -> None:
        """Test selecting invalid model name falls back to task-based routing."""
        decision = model_router.select_model_by_name(
            "invalid:model", task_type=TaskType.CHEAP
        )

        # Should fall back to task-based selection
        assert decision.task_type == TaskType.CHEAP

    def test_record_routing_decision(self, model_router: ModelRouter) -> None:
        """Test that routing decisions are recorded."""
        initial_stats = model_router.get_routing_stats()

        model_router.select_model(TaskType.CREATIVE)
        model_router.select_model(TaskType.LOGICAL)

        final_stats = model_router.get_routing_stats()
        assert final_stats["total_decisions"] == initial_stats["total_decisions"] + 2

    def test_get_routing_stats(self, model_router: ModelRouter) -> None:
        """Test getting routing statistics."""
        # Make some decisions
        model_router.select_model(TaskType.CREATIVE)
        model_router.select_model(TaskType.LOGICAL)

        stats = model_router.get_routing_stats()

        assert stats["total_decisions"] >= 2
        assert "provider_counts" in stats
        assert "reason_counts" in stats
        assert "avg_routing_time_ms" in stats

    def test_list_recent_decisions(self, model_router: ModelRouter) -> None:
        """Test listing recent routing decisions."""
        model_router.select_model(TaskType.CREATIVE)
        model_router.select_model(TaskType.LOGICAL)

        recent = model_router.list_recent_decisions(limit=10)

        assert len(recent) >= 2
        assert all("provider" in d for d in recent)
        assert all("model" in d for d in recent)

    def test_list_recent_decisions_with_limit(self, model_router: ModelRouter) -> None:
        """Test listing decisions respects limit parameter."""
        for _ in range(5):
            model_router.select_model(TaskType.FAST)

        recent = model_router.list_recent_decisions(limit=3)

        assert len(recent) == 3


class TestModelRouterCircuitBreaker:
    """Tests for ModelRouter circuit breaker integration."""

    def test_circuit_breaker_created_for_model(self, model_router: ModelRouter) -> None:
        """Test that circuit breaker is created when model is used."""
        # Select a model - this should create a circuit breaker
        decision = model_router.select_model(TaskType.CREATIVE)
        model_key = f"{decision.selected_provider.value}:{decision.selected_model}"

        # Circuit breaker should exist
        state = model_router.get_circuit_breaker_state(model_key)
        assert state is not None
        assert state["state"] == "closed"

    def test_circuit_breaker_blocks_failed_model(
        self, model_router: ModelRouter
    ) -> None:
        """Test that circuit breaker blocks models after failures."""
        model_key = "openai:gpt-4o"

        # Simulate failures to open circuit
        breaker = model_router._get_circuit_breaker(model_key)

        # Open the circuit directly for testing
        async def record_failures():
            for _ in range(10):
                await breaker.record_failure()

        asyncio.run(record_failures())

        assert breaker.is_open()

        # Now routing should skip this model
        config = RoutingConfig(preferred_providers=[LLMProvider.OPENAI])
        decision = model_router.select_model(TaskType.LOGICAL, config)

        # Should have fallen back to a different provider
        assert decision.fallback_used is True

    def test_record_model_success(self, model_router: ModelRouter) -> None:
        """Test recording successful model execution."""
        decision = model_router.select_model(TaskType.CREATIVE)

        # Record success
        asyncio.run(
            model_router.record_model_success(
                decision.selected_provider, decision.selected_model
            )
        )

        # Circuit breaker should still be closed
        model_key = decision.qualified_model_name
        state = model_router.get_circuit_breaker_state(model_key)
        assert state["state"] == "closed"
        assert state["failure_count"] == 0

    def test_record_model_failure(self, model_router: ModelRouter) -> None:
        """Test recording failed model execution."""
        decision = model_router.select_model(TaskType.CREATIVE)

        # Record failure
        asyncio.run(
            model_router.record_model_failure(
                decision.selected_provider, decision.selected_model, "Test error"
            )
        )

        # Failure count should increase
        model_key = decision.qualified_model_name
        state = model_router.get_circuit_breaker_state(model_key)
        assert state["failure_count"] == 1

    def test_reset_circuit_breaker(self, model_router: ModelRouter) -> None:
        """Test resetting a circuit breaker."""
        model_key = "openai:gpt-4o"

        # Open the circuit
        breaker = model_router._get_circuit_breaker(model_key)

        async def record_failures():
            for _ in range(10):
                await breaker.record_failure()

        asyncio.run(record_failures())

        assert breaker.is_open()

        # Reset it
        result = model_router.reset_circuit_breaker(model_key)
        assert result is True

        # Should be closed now
        new_breaker = model_router._circuit_breakers[model_key]
        assert not new_breaker.is_open()

    def test_reset_nonexistent_circuit_breaker(self, model_router: ModelRouter) -> None:
        """Test resetting a circuit breaker that doesn't exist."""
        result = model_router.reset_circuit_breaker("nonexistent:model")
        assert result is False


class TestModelRouterFallbackChain:
    """Tests for ModelRouter fallback chain behavior."""

    def test_fallback_chain_activates_on_circuit_open(
        self, model_router: ModelRouter
    ) -> None:
        """Test that fallback chain activates when primary circuit is open."""
        # Open circuit on primary model for CREATIVE task
        task_config = model_router._registry.get_model_for_task(TaskType.CREATIVE)
        primary_key = f"{task_config.provider.value}:{task_config.model_name}"
        breaker = model_router._get_circuit_breaker(primary_key)

        # Force circuit open
        breaker._state.state = CircuitState.OPEN
        breaker._state.failure_count = 100

        # Select model - should use fallback
        decision = model_router.select_model(TaskType.CREATIVE)

        # Should have used fallback
        assert decision.fallback_used is True

    def test_fallback_to_mock_when_all_others_fail(
        self, model_router: ModelRouter
    ) -> None:
        """Test ultimate fallback to mock model."""
        # Create config that blocks all real providers
        config = RoutingConfig(
            blocked_providers=[
                LLMProvider.OPENAI,
                LLMProvider.ANTHROPIC,
                LLMProvider.GEMINI,
                LLMProvider.OLLAMA,
            ]
        )

        decision = model_router.select_model(TaskType.CREATIVE, config)

        # Should fall back to mock (mock is in fallback chain, so becomes the default)
        assert decision.selected_provider == LLMProvider.MOCK
        assert "mock" in decision.selected_model
        # Mock is in the fallback chain, so it appears as the selected model
        # The reason depends on where in the chain it was selected
        assert decision.reason in [
            RoutingReason.TASK_DEFAULT,
            RoutingReason.UNAVAILABLE,
            RoutingReason.FALLBACK,
        ]


class TestModelRouterFactory:
    """Tests for the create_model_router factory function."""

    def test_factory_creates_router(self, model_registry: ModelRegistry) -> None:
        """Test factory creates a properly configured router."""
        router = create_model_router(model_registry)

        assert isinstance(router, ModelRouter)
        assert router._registry is model_registry

    def test_factory_with_custom_circuit_config(
        self, model_registry: ModelRegistry
    ) -> None:
        """Test factory with custom circuit breaker configuration."""
        config = CircuitBreakerConfig(failure_threshold=10, timeout_seconds=120)
        router = create_model_router(model_registry, config)

        assert router._circuit_config.failure_threshold == 10
        assert router._circuit_config.timeout_seconds == 120


class TestRoutingConfig:
    """Tests for RoutingConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default routing configuration."""
        config = RoutingConfig()

        assert config.enable_circuit_breaker is True
        assert config.enable_fallback is True
        assert config.max_cost_per_1m_tokens is None
        assert config.preferred_providers == []
        assert config.blocked_providers == []

    def test_custom_config(self) -> None:
        """Test custom routing configuration."""
        config = RoutingConfig(
            enable_circuit_breaker=False,
            max_cost_per_1m_tokens=5.0,
            preferred_providers=[LLMProvider.OPENAI],
            blocked_providers=[LLMProvider.OLLAMA],
        )

        assert config.enable_circuit_breaker is False
        assert config.max_cost_per_1m_tokens == 5.0
        assert config.preferred_providers == [LLMProvider.OPENAI]
        assert config.blocked_providers == [LLMProvider.OLLAMA]


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default circuit breaker configuration."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 60
        assert config.half_open_max_calls == 3

    def test_custom_config(self) -> None:
        """Test custom circuit breaker configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=3,
            timeout_seconds=120,
            half_open_max_calls=5,
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 3
        assert config.timeout_seconds == 120
        assert config.half_open_max_calls == 5
