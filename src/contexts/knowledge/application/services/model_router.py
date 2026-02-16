"""
Model Router Service

Intelligent model selection and routing based on task type, complexity,
cost budget, and latency requirements. Implements fallback chains and
circuit breaker pattern for resilience.

Constitution Compliance:
- Article II (Hexagonal): Application service with port dependencies only
- Article V (SOLID): SRP - model routing logic only

Warzone 4: AI Brain - BRAIN-028A
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

import structlog

from ...domain.models.model_registry import (
    LLMProvider,
    TaskType,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class RoutingReason(str, Enum):
    """
    Reasons for model routing decisions.

    Why str enum:
        String-compatible enum allows JSON serialization for analytics.
    """

    TASK_DEFAULT = "task_default"  # Using default model for task type
    COST_BUDGET = "cost_budget"  # Selected for cost constraints
    LOW_LATENCY = "low_latency"  # Selected for speed requirements
    FALLBACK = "fallback"  # Primary model failed, using fallback
    CIRCUIT_OPEN = "circuit_open"  # Model in circuit breaker, using alternative
    CAPABILITY_REQUIRED = "capability_required"  # Need specific capability
    UNAVAILABLE = "unavailable"  # Primary model unavailable
    MANUAL_OVERRIDE = "manual_override"  # User specified model


class CircuitState(str, Enum):
    """
    Circuit breaker states.

    States:
        CLOSED: Circuit is closed, requests flow through normally
        OPEN: Circuit is open, requests fail fast
        HALF_OPEN: Circuit is half-open, testing if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        success_threshold: Number of successes to close circuit from half-open
        timeout_seconds: Seconds to wait before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Max calls allowed in HALF_OPEN state
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerState:
    """
    State of a circuit breaker for a specific model.

    Attributes:
        state: Current circuit state
        failure_count: Consecutive failures
        success_count: Consecutive successes (in half-open)
        last_failure_time: Last time a failure occurred
        last_state_change: Last time circuit state changed
        opened_count: Total times circuit has opened
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)
    opened_count: int = 0
    half_open_calls: int = 0


@dataclass
class RoutingDecision:
    """
    Record of a routing decision for analytics.

    Attributes:
        task_type: The task type being routed
        selected_provider: Provider that was selected
        selected_model: Model that was selected
        reason: Why this model was selected
        fallback_used: Whether a fallback was used
        circuit_bypassed: Whether circuit breaker was bypassed
        execution_time_ms: Time to make the decision
        timestamp: When the decision was made
        metadata: Additional context
    """

    task_type: Optional[TaskType]
    selected_provider: LLMProvider
    selected_model: str
    reason: RoutingReason
    fallback_used: bool = False
    circuit_bypassed: bool = False
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_model_name(self) -> str:
        """Get the fully qualified model name."""
        return f"{self.selected_provider.value}:{self.selected_model}"

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return {
            "task_type": self.task_type.value if self.task_type else None,
            "provider": self.selected_provider.value,
            "model": self.selected_model,
            "qualified_name": self.qualified_model_name,
            "reason": self.reason.value,
            "fallback_used": self.fallback_used,
            "circuit_bypassed": self.circuit_bypassed,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            **self.metadata,
        }


@dataclass
class RoutingConfig:
    """
    Configuration for model routing behavior.

    Attributes:
        enable_circuit_breaker: Whether circuit breaker is enabled
        enable_fallback: Whether fallback chain is enabled
        max_cost_per_1m_tokens: Maximum cost for routing (USD)
        max_latency_ms: Maximum acceptable latency
        preferred_providers: Provider preference order
        blocked_providers: Providers to never use
        require_capability: Required capabilities
    """

    enable_circuit_breaker: bool = True
    enable_fallback: bool = True
    max_cost_per_1m_tokens: Optional[float] = None
    max_latency_ms: Optional[int] = None
    preferred_providers: list[LLMProvider] = field(default_factory=list)
    blocked_providers: list[LLMProvider] = field(default_factory=list)
    require_capability: Optional[set[str]] = None


class CircuitBreaker:
    """
    Circuit breaker for failing models.

    Why:
        - Prevents cascading failures by stopping requests to failing models
        - Allows models time to recover without continuous requests
        - Implements standard circuit breaker pattern with CLOSED/OPEN/HALF_OPEN states

    The circuit breaker:
    1. Starts in CLOSED state (requests allowed)
    2. Opens after failure_threshold consecutive failures
    3. After timeout, transitions to HALF_OPEN (test requests allowed)
    4. Closes after success_threshold consecutive successes
    5. Re-opens on any failure in HALF_OPEN
    """

    def __init__(
        self,
        model_key: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        """
        Initialize the circuit breaker.

        Args:
            model_key: Unique identifier for the model (provider:model)
            config: Circuit breaker configuration
        """
        self._model_key = model_key
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

        log = logger.bind(model=model_key)
        log.info("circuit_breaker_initialized")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def failure_count(self) -> int:
        """Get consecutive failure count."""
        return self._state.failure_count

    def is_open(self) -> bool:
        """
        Check if circuit is open (requests blocked).

        Returns:
            True if circuit is OPEN, False otherwise
        """
        return self._state.state == CircuitState.OPEN

    def can_request(self) -> bool:
        """
        Check if a request is allowed through the circuit.

        Returns:
            True if request should be allowed, False if it should be rejected
        """
        # Auto-transition from OPEN to HALF_OPEN after timeout
        if self._state.state == CircuitState.OPEN and self._state.last_failure_time:
            time_since_failure = datetime.now() - self._state.last_failure_time
            if time_since_failure.total_seconds() >= self._config.timeout_seconds:
                # Transition to HALF_OPEN
                self._state.state = CircuitState.HALF_OPEN
                self._state.last_state_change = datetime.now()
                self._state.half_open_calls = 0

                log = logger.bind(model=self._model_key)
                log.info(
                    "circuit_breaker_half_open",
                    time_open_seconds=time_since_failure.total_seconds(),
                )

        return self._state.state != CircuitState.OPEN or (
            self._state.state == CircuitState.HALF_OPEN
            and self._state.half_open_calls < self._config.half_open_max_calls
        )

    async def record_success(self) -> None:
        """
        Record a successful request.

        Resets failure count and may close circuit if in HALF_OPEN.
        """
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1

                # Close circuit after threshold successes
                if self._state.success_count >= self._config.success_threshold:
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.success_count = 0
                    self._state.last_state_change = datetime.now()

                    log = logger.bind(model=self._model_key)
                    log.info("circuit_breaker_closed", after_half_open=True)
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self._state.failure_count = 0

    async def record_failure(self) -> None:
        """
        Record a failed request.

        May open circuit if failure threshold is reached.
        """
        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = datetime.now()

            if self._state.state == CircuitState.HALF_OPEN:
                # Re-open circuit on failure in half-open
                self._state.state = CircuitState.OPEN
                self._state.success_count = 0
                self._state.last_state_change = datetime.now()
                self._state.opened_count += 1

                log = logger.bind(model=self._model_key)
                log.warning(
                    "circuit_breaker_reopened",
                    failure_count=self._state.failure_count,
                )
            elif (
                self._state.state == CircuitState.CLOSED
                and self._state.failure_count >= self._config.failure_threshold
            ):
                # Open circuit after threshold failures
                self._state.state = CircuitState.OPEN
                self._state.last_state_change = datetime.now()
                self._state.opened_count += 1

                log = logger.bind(model=self._model_key)
                log.warning(
                    "circuit_breaker_opened",
                    failure_count=self._state.failure_count,
                    threshold=self._config.failure_threshold,
                )

    def get_state_info(self) -> dict[str, Any]:
        """
        Get circuit breaker state information.

        Returns:
            Dictionary with current state info
        """
        return {
            "model": self._model_key,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure_time": (
                self._state.last_failure_time.isoformat()
                if self._state.last_failure_time
                else None
            ),
            "last_state_change": self._state.last_state_change.isoformat(),
            "opened_count": self._state.opened_count,
            "config": {
                "failure_threshold": self._config.failure_threshold,
                "success_threshold": self._config.success_threshold,
                "timeout_seconds": self._config.timeout_seconds,
            },
        }


class ModelRouter:
    """
    Intelligent model routing service.

    Why:
        - Automatic model selection based on task requirements
        - Fallback chain for resilience
        - Circuit breaker to prevent cascading failures
        - Cost and latency optimization
        - Analytics for routing decisions

    The router:
    1. Evaluates task type, complexity, cost budget, latency requirements
    2. Selects best model from available options
    3. Applies circuit breaker to skip failing models
    4. Falls back through configured chain if primary fails
    5. Logs all decisions for analytics

    Example:
        >>> router = ModelRouter(model_registry)
        >>> decision = router.select_model(TaskType.CREATIVE)
        >>> print(decision.qualified_model_name)  # "gemini:gemini-2.0-flash"
        >>>
        >>> # With constraints
        >>> decision = router.select_model(
        ...     TaskType.LOGICAL,
        ...     config=RoutingConfig(max_cost_per_1m_tokens=5.0)
        ... )
    """

    def __init__(
        self,
        model_registry,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        """
        Initialize the model router.

        Args:
            model_registry: ModelRegistry instance for model lookups
            circuit_breaker_config: Optional circuit breaker configuration
        """
        # Avoid circular import by using the registry passed in
        from .model_registry import ModelRegistry

        if not isinstance(model_registry, ModelRegistry):
            raise ValueError(
                f"model_registry must be a ModelRegistry, got {type(model_registry)}"
            )

        self._registry = model_registry
        self._circuit_config = circuit_breaker_config or CircuitBreakerConfig()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._routing_history: list[RoutingDecision] = []
        self._max_history_size = 1000

        log = logger.bind(
            circuit_breaker_enabled=self._circuit_config is not None,
            failure_threshold=self._circuit_config.failure_threshold,
        )
        log.info("model_router_initialized")

    def _get_start_time(self) -> float:
        """Get start time for timing, handling both async and sync contexts."""
        try:
            return asyncio.get_running_loop().time()
        except RuntimeError:
            return time.perf_counter()

    def _get_elapsed_ms(self, start_time: float) -> float:
        """Get elapsed milliseconds since start_time."""
        try:
            return (asyncio.get_running_loop().time() - start_time) * 1000
        except RuntimeError:
            return (time.perf_counter() - start_time) * 1000

    def select_model(
        self,
        task_type: TaskType,
        config: Optional[RoutingConfig] = None,
        complexity_score: Optional[float] = None,
    ) -> RoutingDecision:
        """
        Select the best model for a given task and constraints.

        Args:
            task_type: The type of task (CREATIVE, LOGICAL, FAST, CHEAP)
            config: Optional routing configuration with constraints
            complexity_score: Optional complexity (0.0-1.0) for smarter routing

        Returns:
            RoutingDecision with selected model and reasoning

        Example:
            >>> decision = router.select_model(TaskType.CREATIVE)
            >>> if decision.reason == RoutingReason.FALLBACK:
            ...     print(f"Using fallback: {decision.selected_model}")
        """
        start_time = self._get_start_time()

        config = config or RoutingConfig()
        log = logger.bind(task_type=task_type.value)

        # Get task configuration
        task_config = self._registry.get_model_for_task(task_type)

        # Build candidate list with primary and fallbacks
        candidates = [(task_config.provider, task_config.model_name)]

        # Add fallback providers
        for fallback_provider in task_config.fallback_providers:
            # For fallback, use same model name if available, or pick one from provider
            fallback_model = self._find_model_for_provider(
                fallback_provider,
                task_type,
                config,
            )
            if fallback_model:
                candidates.append((fallback_provider, fallback_model))

        # Always add mock as final fallback
        candidates.append((LLMProvider.MOCK, "mock-model"))

        # Filter out blocked providers
        candidates = [
            (p, m) for p, m in candidates if p not in config.blocked_providers
        ]

        # Select best candidate
        selected_provider = None
        selected_model = None
        reason = RoutingReason.TASK_DEFAULT
        fallback_used = False

        for idx, (provider, model_name) in enumerate(candidates):
            model_key = f"{provider.value}:{model_name}"

            # Check circuit breaker
            if config.enable_circuit_breaker:
                breaker = self._get_circuit_breaker(model_key)
                if not breaker.can_request():
                    log.debug(
                        "model_circuit_open",
                        model=model_key,
                        failure_count=breaker.failure_count,
                    )
                    continue

            # Check model availability
            if not self._registry.is_model_available(provider, model_name):
                log.debug("model_unavailable", model=model_key)
                continue

            # Check cost constraint
            if config.max_cost_per_1m_tokens is not None:
                model_def = self._registry.get_model(provider, model_name)
                if (
                    model_def
                    and model_def.cost_per_1m_output_tokens
                    > config.max_cost_per_1m_tokens
                ):
                    log.debug(
                        "model_too_expensive",
                        model=model_key,
                        cost=model_def.cost_per_1m_output_tokens,
                        max_cost=config.max_cost_per_1m_tokens,
                    )
                    continue

            # Apply preferred provider ordering
            if config.preferred_providers:
                if provider not in config.preferred_providers:
                    # Skip if not in preferred list but still have candidates
                    if idx < len(candidates) - 1:
                        continue

            selected_provider = provider
            selected_model = model_name

            if idx == 0:
                reason = RoutingReason.TASK_DEFAULT
                fallback_used = False
            else:
                reason = RoutingReason.FALLBACK
                fallback_used = True

            break

        # Fallback to mock if nothing else selected
        if selected_provider is None:
            selected_provider = LLMProvider.MOCK
            selected_model = "mock-model"
            reason = RoutingReason.UNAVAILABLE
            fallback_used = True

        # Calculate execution time
        execution_time = self._get_elapsed_ms(start_time)

        decision = RoutingDecision(
            task_type=task_type,
            selected_provider=selected_provider,
            selected_model=selected_model,
            reason=reason,
            fallback_used=fallback_used,
            execution_time_ms=execution_time,
            metadata={
                "complexity_score": complexity_score,
                "has_circuit_breaker": config.enable_circuit_breaker,
                "preferred_providers": [p.value for p in config.preferred_providers],
            },
        )

        # Record decision
        self._record_decision(decision)

        # Log the decision
        log.info(
            "model_routing_decision",
            **decision.to_log_dict(),
        )

        return decision

    def select_model_by_name(
        self,
        model_ref: str,
        config: Optional[RoutingConfig] = None,
        task_type: Optional[TaskType] = None,
    ) -> RoutingDecision:
        """
        Select a specific model by reference (alias or qualified name).

        Args:
            model_ref: Model reference (alias, provider:model, or model name)
            config: Optional routing configuration
            task_type: Optional task type for context

        Returns:
            RoutingDecision with selected model

        Example:
            >>> decision = router.select_model_by_name("gpt4")
            >>> print(decision.qualified_model_name)  # "openai:gpt-4o"
        """
        start_time = self._get_start_time()

        config = config or RoutingConfig()
        log = logger.bind(model_ref=model_ref, task_type=task_type)

        try:
            # Resolve the model reference
            lookup_result = self._registry.resolve_model(model_ref)
            provider = lookup_result.provider
            model_name = lookup_result.model_name

            # Check circuit breaker
            model_key = f"{provider.value}:{model_name}"
            if config.enable_circuit_breaker:
                breaker = self._get_circuit_breaker(model_key)
                if not breaker.can_request():
                    log.warning(
                        "requested_model_circuit_open",
                        model=model_key,
                        failure_count=breaker.failure_count,
                    )
                    # Fall back to task-based routing
                    if task_type:
                        return self.select_model(task_type, config)
                    else:
                        return self.select_model(TaskType.CHEAP, config)

            # Check blocked providers
            if provider in config.blocked_providers:
                log.warning("requested_model_blocked", provider=provider.value)
                if task_type:
                    return self.select_model(task_type, config)
                else:
                    return self.select_model(TaskType.CHEAP, config)

            execution_time = self._get_elapsed_ms(start_time)

            decision = RoutingDecision(
                task_type=task_type,
                selected_provider=provider,
                selected_model=model_name,
                reason=RoutingReason.MANUAL_OVERRIDE,
                fallback_used=False,
                execution_time_ms=execution_time,
                metadata={"alias_used": lookup_result.alias_used},
            )

            self._record_decision(decision)

            log.info(
                "model_selected_by_name",
                **decision.to_log_dict(),
            )

            return decision

        except ValueError as e:
            log.error("model_resolution_failed", error=str(e))
            # Fall back to task-based routing
            if task_type:
                return self.select_model(task_type, config)
            else:
                return self.select_model(TaskType.CHEAP, config)

    def _find_model_for_provider(
        self,
        provider: LLMProvider,
        task_type: TaskType,
        config: RoutingConfig,
    ) -> Optional[str]:
        """
        Find a suitable model for a provider.

        Args:
            provider: The provider to find a model for
            task_type: The task type
            config: Routing configuration

        Returns:
            Model name if found, None otherwise
        """
        # Get models for this provider
        models = self._registry.list_models(
            provider=provider,
            include_deprecated=False,
        )

        # Filter by cost constraint
        if config.max_cost_per_1m_tokens is not None:
            models = [
                m
                for m in models
                if m.cost_per_1m_output_tokens <= config.max_cost_per_1m_tokens
            ]

        if not models:
            return None

        # Select best model (prefer lower cost, then higher context)
        best_model = min(
            models,
            key=lambda m: (m.cost_factor, -m.max_context_tokens),
        )

        return best_model.model_name

    def _get_circuit_breaker(self, model_key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a model."""
        if model_key not in self._circuit_breakers:
            self._circuit_breakers[model_key] = CircuitBreaker(
                model_key, self._circuit_config
            )
        return self._circuit_breakers[model_key]

    def _record_decision(self, decision: RoutingDecision) -> None:
        """Record routing decision for analytics."""
        self._routing_history.append(decision)

        # Trim history if needed
        if len(self._routing_history) > self._max_history_size:
            self._routing_history = self._routing_history[-self._max_history_size :]

    async def record_model_success(
        self, provider: LLMProvider, model_name: str
    ) -> None:
        """
        Record a successful model execution.

        Args:
            provider: The provider that succeeded
            model_name: The model that succeeded
        """
        model_key = f"{provider.value}:{model_name}"
        breaker = self._get_circuit_breaker(model_key)
        await breaker.record_success()

        logger.debug(
            "model_success_recorded",
            model=model_key,
            circuit_state=breaker.state.value,
        )

    async def record_model_failure(
        self,
        provider: LLMProvider,
        model_name: str,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a failed model execution.

        Args:
            provider: The provider that failed
            model_name: The model that failed
            error: Optional error message
        """
        model_key = f"{provider.value}:{model_name}"
        breaker = self._get_circuit_breaker(model_key)
        await breaker.record_failure()

        logger.warning(
            "model_failure_recorded",
            model=model_key,
            circuit_state=breaker.state.value,
            error=error,
        )

    def get_routing_stats(self) -> dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dictionary with routing analytics
        """
        if not self._routing_history:
            return {"total_decisions": 0}

        # Count by reason
        reason_counts: dict[str, int] = {}
        fallback_count = 0

        for decision in self._routing_history:
            reason = decision.reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if decision.fallback_used:
                fallback_count += 1

        # Count by provider
        provider_counts: dict[str, int] = {}
        for decision in self._routing_history:
            provider = decision.selected_provider.value
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

        # Calculate avg execution time
        avg_time = sum(d.execution_time_ms for d in self._routing_history) / len(
            self._routing_history
        )

        # Circuit breaker stats
        open_circuits = [
            (k, v.get_state_info())
            for k, v in self._circuit_breakers.items()
            if v.is_open()
        ]

        return {
            "total_decisions": len(self._routing_history),
            "fallback_count": fallback_count,
            "fallback_rate": fallback_count / len(self._routing_history),
            "reason_counts": reason_counts,
            "provider_counts": provider_counts,
            "avg_routing_time_ms": avg_time,
            "open_circuits": open_circuits,
            "total_circuits": len(self._circuit_breakers),
        }

    def get_circuit_breaker_state(self, model_key: str) -> Optional[dict[str, Any]]:
        """
        Get circuit breaker state for a specific model.

        Args:
            model_key: Model key in format "provider:model"

        Returns:
            Circuit breaker state info, or None if no breaker exists
        """
        breaker = self._circuit_breakers.get(model_key)
        if breaker:
            return breaker.get_state_info()
        return None

    def reset_circuit_breaker(self, model_key: str) -> bool:
        """
        Reset a circuit breaker to closed state.

        Args:
            model_key: Model key in format "provider:model"

        Returns:
            True if reset was successful, False if breaker not found
        """
        if model_key in self._circuit_breakers:
            # Replace with new circuit breaker in closed state
            self._circuit_breakers[model_key] = CircuitBreaker(
                model_key, self._circuit_config
            )
            logger.info("circuit_breaker_reset", model=model_key)
            return True
        return False

    def list_recent_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent routing decisions.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of routing decision dictionaries
        """
        recent = self._routing_history[-limit:]
        return [d.to_log_dict() for d in reversed(recent)]


def create_model_router(
    model_registry,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
) -> ModelRouter:
    """
    Factory function to create a ModelRouter.

    Why factory:
        - Provides convenient instantiation
        - Allows for future dependency injection
        - Consistent with other service factories

    Args:
        model_registry: ModelRegistry instance
        circuit_breaker_config: Optional circuit breaker configuration

    Returns:
        Configured ModelRouter instance
    """
    return ModelRouter(model_registry, circuit_breaker_config)


__all__ = [
    "ModelRouter",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "RoutingDecision",
    "RoutingConfig",
    "RoutingReason",
    "CircuitState",
    "create_model_router",
]
