"""
Token Usage Entity

Warzone 4: AI Brain - BRAIN-034A
Domain entity for tracking LLM token usage and costs.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from .model_registry import LLMProvider


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def _calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cost_per_1m_input: float,
    cost_per_1m_output: float,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calculate cost from token usage and per-1M pricing.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_per_1m_input: Cost per 1M input tokens in USD
        cost_per_1m_output: Cost per 1M output tokens in USD

    Returns:
        Tuple of (input_cost, output_cost, total_cost) as Decimal
    """
    input_cost = Decimal(str(input_tokens * cost_per_1m_input / 1_000_000))
    output_cost = Decimal(str(output_tokens * cost_per_1m_output / 1_000_000))
    total_cost = input_cost + output_cost

    # Round to 6 decimal places (microdollars)
    input_cost = input_cost.quantize(Decimal("0.000001"))
    output_cost = output_cost.quantize(Decimal("0.000001"))
    total_cost = total_cost.quantize(Decimal("0.000001"))

    return input_cost, output_cost, total_cost


@dataclass
class TokenUsage:
    """
    Entity representing a single LLM API call with token usage.

    Why not frozen:
        Usage records are created once and never modified, but we need
        to allow dataclass flexibility for creation.

    Tracks every LLM generation event for analytics:
    - Token usage (input/output)
    - Cost calculation
    - Latency
    - Workspace/user tracking for multi-tenancy
    - Model identification

    Attributes:
        id: Unique identifier for this usage event (UUID)
        timestamp: When the generation occurred
        provider: LLM provider used (openai, anthropic, gemini, ollama)
        model_name: Model name used
        input_tokens: Estimated or actual number of input tokens
        output_tokens: Estimated or actual number of output tokens
        total_tokens: Total tokens consumed (input + output)
        input_cost: Cost for input tokens in USD
        output_cost: Cost for output tokens in USD
        total_cost: Total cost in USD
        latency_ms: Time taken for generation in milliseconds
        success: Whether generation was successful
        error_message: Error message if generation failed
        workspace_id: Optional workspace identifier for multi-tenant analytics
        user_id: Optional user identifier for user-specific analytics
        request_id: Optional request identifier for correlation
        metadata: Additional metadata (task_type, route_used, etc.)

    Invariants:
        - id must be non-empty
        - total_tokens == input_tokens + output_tokens
        - total_cost == input_cost + output_cost
        - latency_ms >= 0
        - input_tokens >= 0, output_tokens >= 0
    """

    id: str
    timestamp: datetime
    provider: str
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: Decimal = field(default_factory=Decimal)
    output_cost: Decimal = field(default_factory=Decimal)
    total_cost: Decimal = field(default_factory=Decimal)
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate usage event invariants."""
        # Validate non-negative token counts
        if self.input_tokens < 0:
            raise ValueError(
                f"TokenUsage.input_tokens cannot be negative, got: {self.input_tokens}"
            )

        if self.output_tokens < 0:
            raise ValueError(
                f"TokenUsage.output_tokens cannot be negative, got: {self.output_tokens}"
            )

        # Validate total matches sum
        calculated_total = self.input_tokens + self.output_tokens
        if self.total_tokens != calculated_total:
            raise ValueError(
                f"TokenUsage.total_tokens ({self.total_tokens}) must equal "
                f"input_tokens ({self.input_tokens}) + output_tokens ({self.output_tokens}), "
                f"expected {calculated_total}"
            )

        # Validate costs
        calculated_total_cost = self.input_cost + self.output_cost
        if self.total_cost != calculated_total_cost:
            raise ValueError(
                f"TokenUsage.total_cost ({self.total_cost}) must equal "
                f"input_cost ({self.input_cost}) + output_cost ({self.output_cost})"
            )

        # Validate latency
        if self.latency_ms < 0:
            raise ValueError(
                f"TokenUsage.latency_ms cannot be negative, got: {self.latency_ms}"
            )

        # Normalize timestamp to UTC
        if self.timestamp.tzinfo is None:
            object.__setattr__(
                self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc)
            )
        else:
            object.__setattr__(
                self, "timestamp", self.timestamp.astimezone(timezone.utc)
            )

    @property
    def model_identifier(self) -> str:
        """Get the full model identifier (provider:model_name)."""
        return f"{self.provider}:{self.model_name}"

    @property
    def cost_per_million_tokens(self) -> float:
        """Get effective cost per million tokens."""
        if self.total_tokens == 0:
            return 0.0
        return float(self.total_cost) * 1_000_000 / self.total_tokens

    def to_dict(self) -> dict[str, Any]:
        """
        Convert usage event to dictionary for serialization.

        Returns:
            Dictionary representation of the usage event
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model_name": self.model_name,
            "model_identifier": self.model_identifier,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": str(self.input_cost),
            "output_cost": str(self.output_cost),
            "total_cost": str(self.total_cost),
            "latency_ms": round(self.latency_ms, 2),
            "success": self.success,
            "error_message": self.error_message,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenUsage:
        """
        Create usage event from dictionary.

        Args:
            data: Dictionary containing usage event data

        Returns:
            TokenUsage instance
        """
        return cls(
            id=data["id"],
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else _utcnow()
            ),
            provider=data["provider"],
            model_name=data["model_name"],
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            input_cost=Decimal(data.get("input_cost", "0")),
            output_cost=Decimal(data.get("output_cost", "0")),
            total_cost=Decimal(data.get("total_cost", "0")),
            latency_ms=data.get("latency_ms", 0.0),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            workspace_id=data.get("workspace_id"),
            user_id=data.get("user_id"),
            request_id=data.get("request_id"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        provider: str | LLMProvider,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_per_1m_input: float = 0.0,
        cost_per_1m_output: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> TokenUsage:
        """
        Factory method to create a new usage event.

        Args:
            provider: LLM provider used
            model_name: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_per_1m_input: Cost per 1M input tokens in USD
            cost_per_1m_output: Cost per 1M output tokens in USD
            latency_ms: Generation latency in milliseconds
            success: Whether generation succeeded
            error_message: Error message if failed
            workspace_id: Optional workspace identifier
            user_id: Optional user identifier
            request_id: Optional request identifier
            metadata: Additional metadata
            timestamp: Optional timestamp (defaults to now)
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New TokenUsage instance
        """
        # Normalize provider to string (LLMProvider is a str enum)
        provider_str = str(provider)

        total_tokens = input_tokens + output_tokens
        input_cost, output_cost, total_cost = _calculate_cost(
            input_tokens, output_tokens, cost_per_1m_input, cost_per_1m_output
        )

        return cls(
            id=id or str(uuid4()),
            timestamp=timestamp or _utcnow(),
            provider=provider_str,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            workspace_id=workspace_id,
            user_id=user_id,
            request_id=request_id,
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class TokenUsageStats:
    """
    Aggregated statistics for token usage.

    Why frozen:
        Immutable snapshot of aggregated data.

    Attributes:
        provider: LLM provider (or "all" for aggregated)
        model_name: Model name (or "all" for aggregated)
        workspace_id: Optional workspace filter
        period_start: Start of aggregation period
        period_end: End of aggregation period
        total_requests: Total number of requests
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        total_tokens: Total tokens consumed
        total_input_tokens: Total input tokens
        total_output_tokens: Total output tokens
        total_cost: Total cost in USD
        total_input_cost: Total input token cost
        total_output_cost: Total output token cost
        total_latency_ms: Total latency across all requests
        first_used: Timestamp of first usage
        last_used: Timestamp of most recent usage

    Invariants:
        - total_requests >= 0
        - total_requests == successful_requests + failed_requests
        - total_tokens == total_input_tokens + total_output_tokens
    """

    provider: str
    model_name: str
    workspace_id: Optional[str]
    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    total_input_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    total_output_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    total_latency_ms: float = 0.0
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate stats invariants."""
        if self.total_requests < 0:
            raise ValueError("TokenUsageStats.total_requests cannot be negative")

        if self.successful_requests < 0:
            raise ValueError("TokenUsageStats.successful_requests cannot be negative")

        if self.failed_requests < 0:
            raise ValueError("TokenUsageStats.failed_requests cannot be negative")

        if self.total_requests != self.successful_requests + self.failed_requests:
            raise ValueError(
                f"TokenUsageStats.total_requests ({self.total_requests}) must equal "
                f"successful_requests ({self.successful_requests}) + failed_requests ({self.failed_requests})"
            )

        if self.total_tokens != self.total_input_tokens + self.total_output_tokens:
            raise ValueError(
                f"TokenUsageStats.total_tokens ({self.total_tokens}) must equal "
                f"total_input_tokens ({self.total_input_tokens}) + total_output_tokens ({self.total_output_tokens})"
            )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests * 100.0) / self.total_requests

    @property
    def avg_tokens_per_request(self) -> float:
        """Calculate average tokens per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_tokens / self.total_requests

    @property
    def avg_input_tokens(self) -> float:
        """Calculate average input tokens."""
        if self.total_requests == 0:
            return 0.0
        return self.total_input_tokens / self.total_requests

    @property
    def avg_output_tokens(self) -> float:
        """Calculate average output tokens."""
        if self.total_requests == 0:
            return 0.0
        return self.total_output_tokens / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def avg_cost_per_request(self) -> Decimal:
        """Calculate average cost per request."""
        if self.total_requests == 0:
            return Decimal("0")
        return (self.total_cost / self.total_requests).quantize(Decimal("0.000001"))

    @property
    def cost_per_million_tokens(self) -> float:
        """Get effective cost per million tokens."""
        if self.total_tokens == 0:
            return 0.0
        return float(self.total_cost) * 1_000_000 / self.total_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary for serialization."""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "workspace_id": self.workspace_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 2),
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_tokens_per_request": round(self.avg_tokens_per_request, 2),
            "avg_input_tokens": round(self.avg_input_tokens, 2),
            "avg_output_tokens": round(self.avg_output_tokens, 2),
            "total_cost": str(self.total_cost),
            "total_input_cost": str(self.total_input_cost),
            "total_output_cost": str(self.total_output_cost),
            "avg_cost_per_request": str(self.avg_cost_per_request),
            "cost_per_million_tokens": round(self.cost_per_million_tokens, 6),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_usages(
        cls,
        usages: list[TokenUsage],
        provider: str = "all",
        model_name: str = "all",
        workspace_id: Optional[str] = None,
    ) -> TokenUsageStats:
        """
        Calculate stats from a list of usage events.

        Args:
            usages: List of TokenUsage events
            provider: Provider filter (or "all")
            model_name: Model filter (or "all")
            workspace_id: Optional workspace filter

        Returns:
            Aggregated TokenUsageStats
        """
        if not usages:
            return cls(
                provider=provider,
                model_name=model_name,
                workspace_id=workspace_id,
                period_start=_utcnow(),
                period_end=_utcnow(),
            )

        # Filter by workspace if specified
        filtered = usages
        if workspace_id is not None:
            filtered = [u for u in filtered if u.workspace_id == workspace_id]

        if not filtered:
            return cls(
                provider=provider,
                model_name=model_name,
                workspace_id=workspace_id,
                period_start=_utcnow(),
                period_end=_utcnow(),
            )

        # Resolve provider/model defaults from data when possible
        resolved_provider = provider
        resolved_model_name = model_name
        if provider == "all":
            providers = {u.provider for u in filtered if u.provider}
            if len(providers) == 1:
                resolved_provider = providers.pop()
        if model_name == "all":
            models = {u.model_name for u in filtered if u.model_name}
            if len(models) == 1:
                resolved_model_name = models.pop()

        # Find time range
        timestamps = [u.timestamp for u in filtered]
        first_used = min(timestamps)
        last_used = max(timestamps)

        # Aggregate
        total_requests = len(filtered)
        successful_requests = sum(1 for u in filtered if u.success)
        failed_requests = total_requests - successful_requests
        total_tokens = sum(u.total_tokens for u in filtered)
        total_input_tokens = sum(u.input_tokens for u in filtered)
        total_output_tokens = sum(u.output_tokens for u in filtered)
        total_latency_ms = sum(u.latency_ms for u in filtered)

        # Aggregate costs
        total_cost = sum((u.total_cost for u in filtered), Decimal("0"))
        total_input_cost = sum((u.input_cost for u in filtered), Decimal("0"))
        total_output_cost = sum((u.output_cost for u in filtered), Decimal("0"))

        return cls(
            provider=resolved_provider,
            model_name=resolved_model_name,
            workspace_id=workspace_id,
            period_start=first_used,
            period_end=last_used,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost=total_cost,
            total_input_cost=total_input_cost,
            total_output_cost=total_output_cost,
            total_latency_ms=total_latency_ms,
            first_used=first_used,
            last_used=last_used,
        )


__all__ = [
    "TokenUsage",
    "TokenUsageStats",
    "_calculate_cost",
]
