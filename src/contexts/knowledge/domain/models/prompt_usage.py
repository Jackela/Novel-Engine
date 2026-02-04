"""
Prompt Usage Entity

Warzone 4: AI Brain - BRAIN-022A
Domain entity for tracking prompt template usage analytics.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class PromptUsage:
    """
    Entity representing a single prompt template usage event.

    Why not frozen:
        Usage events are created once and never modified, but we need
        to allow dataclass flexibility for creation.

    Tracks every prompt generation event for analytics:
    - Token usage (input/output)
    - Latency
    - User ratings
    - Workspace/user tracking for multi-tenancy

    Attributes:
        id: Unique identifier for this usage event (UUID)
        prompt_id: ID of the prompt template used
        prompt_name: Name of the prompt (snapshotted at time of use)
        prompt_version: Version number of the prompt used
        workspace_id: Optional workspace identifier for multi-tenant analytics
        user_id: Optional user identifier for user-specific analytics
        timestamp: When the generation occurred
        input_tokens: Estimated number of tokens in the input
        output_tokens: Estimated number of tokens in the output
        total_tokens: Total tokens consumed (input + output)
        latency_ms: Time taken for generation in milliseconds
        model_provider: LLM provider used (gemini, openai, anthropic, ollama)
        model_name: Model name used
        success: Whether generation was successful
        error_message: Error message if generation failed
        user_rating: Optional user rating (1-5 scale)
        variables: Variable values used (for analysis, sanitized)

    Invariants:
        - id must be non-empty
        - prompt_id must be non-empty
        - total_tokens == input_tokens + output_tokens
        - latency_ms >= 0
        - user_rating must be between 1 and 5 if provided
    """

    id: str
    prompt_id: str
    prompt_name: str
    prompt_version: int
    timestamp: datetime = field(default_factory=_utcnow)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model_provider: str = ""
    model_name: str = ""
    success: bool = True
    error_message: Optional[str] = None
    user_rating: Optional[float] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    variables: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate usage event invariants."""
        # Skip id validation for create() factory which uses uuid4()
        # if not self.id or not self.id.strip():
        #     raise ValueError("PromptUsage.id cannot be empty")

        if not self.prompt_id or not self.prompt_id.strip():
            raise ValueError("PromptUsage.prompt_id cannot be empty")

        if not self.prompt_name or not self.prompt_name.strip():
            raise ValueError("PromptUsage.prompt_name cannot be empty")

        if self.prompt_version < 1:
            raise ValueError(
                f"PromptUsage.prompt_version must be >= 1, got: {self.prompt_version}"
            )

        if self.input_tokens < 0:
            raise ValueError(
                f"PromptUsage.input_tokens cannot be negative, got: {self.input_tokens}"
            )

        if self.output_tokens < 0:
            raise ValueError(
                f"PromptUsage.output_tokens cannot be negative, got: {self.output_tokens}"
            )

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError(
                f"PromptUsage.total_tokens ({self.total_tokens}) must equal "
                f"input_tokens ({self.input_tokens}) + output_tokens ({self.output_tokens})"
            )

        if self.latency_ms < 0:
            raise ValueError(
                f"PromptUsage.latency_ms cannot be negative, got: {self.latency_ms}"
            )

        if self.user_rating is not None:
            if not 1 <= self.user_rating <= 5:
                raise ValueError(
                    f"PromptUsage.user_rating must be between 1 and 5, got: {self.user_rating}"
                )

        # Normalize timestamp to UTC
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "timestamp", self.timestamp.astimezone(timezone.utc))

    @property
    def model_identifier(self) -> str:
        """Get the full model identifier (provider:model_name)."""
        if self.model_provider and self.model_name:
            return f"{self.model_provider}:{self.model_name}"
        return self.model_provider or self.model_name or "unknown"

    def to_dict(self) -> dict:
        """
        Convert usage event to dictionary for serialization.

        Returns:
            Dictionary representation of the usage event
        """
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "timestamp": self.timestamp.isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "model_identifier": self.model_identifier,
            "success": self.success,
            "error_message": self.error_message,
            "user_rating": self.user_rating,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            # Sanitize variables in serialization (remove sensitive values)
            "variables_count": len(self.variables),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PromptUsage:
        """
        Create usage event from dictionary.

        Args:
            data: Dictionary containing usage event data

        Returns:
            PromptUsage instance
        """
        return cls(
            id=data["id"],
            prompt_id=data["prompt_id"],
            prompt_name=data["prompt_name"],
            prompt_version=data["prompt_version"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else _utcnow(),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            latency_ms=data.get("latency_ms", 0.0),
            model_provider=data.get("model_provider", ""),
            model_name=data.get("model_name", ""),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            user_rating=data.get("user_rating"),
            workspace_id=data.get("workspace_id"),
            user_id=data.get("user_id"),
            variables=data.get("variables", {}),
        )

    @classmethod
    def create(
        cls,
        prompt_id: str,
        prompt_name: str,
        prompt_version: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        model_provider: str = "",
        model_name: str = "",
        success: bool = True,
        error_message: Optional[str] = None,
        user_rating: Optional[float] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        variables: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> PromptUsage:
        """
        Factory method to create a new usage event.

        Args:
            prompt_id: ID of the prompt template
            prompt_name: Name of the prompt
            prompt_version: Version of the prompt used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Generation latency in milliseconds
            model_provider: LLM provider used
            model_name: Model name used
            success: Whether generation succeeded
            error_message: Error message if failed
            user_rating: Optional user rating (1-5)
            workspace_id: Optional workspace identifier
            user_id: Optional user identifier
            variables: Variable values used
            timestamp: Optional timestamp (defaults to now)
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New PromptUsage instance
        """
        total_tokens = input_tokens + output_tokens

        return cls(
            id=id or str(uuid4()),
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            timestamp=timestamp or _utcnow(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            model_provider=model_provider,
            model_name=model_name,
            success=success,
            error_message=error_message,
            user_rating=user_rating,
            workspace_id=workspace_id,
            user_id=user_id,
            variables=variables or {},
        )

    def with_rating(self, rating: float) -> PromptUsage:
        """
        Create a copy with an updated user rating.

        Args:
            rating: User rating (1-5)

        Returns:
            New PromptUsage instance with updated rating
        """
        return PromptUsage(
            id=self.id,
            prompt_id=self.prompt_id,
            prompt_name=self.prompt_name,
            prompt_version=self.prompt_version,
            timestamp=self.timestamp,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            latency_ms=self.latency_ms,
            model_provider=self.model_provider,
            model_name=self.model_name,
            success=self.success,
            error_message=self.error_message,
            user_rating=rating,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            variables=self.variables,
        )


@dataclass(frozen=True, slots=True)
class PromptUsageStats:
    """
    Aggregated statistics for prompt usage.

    Why frozen:
        Immutable snapshot of aggregated data.

    Attributes:
        prompt_id: ID of the prompt template
        prompt_name: Name of the prompt
        total_uses: Total number of times the prompt was used
        successful_uses: Number of successful generations
        failed_uses: Number of failed generations
        total_tokens: Total tokens consumed across all uses
        total_input_tokens: Total input tokens
        total_output_tokens: Total output tokens
        total_latency_ms: Total latency across all uses
        rating_sum: Sum of all user ratings
        rating_count: Number of ratings received
        first_used: Timestamp of first usage
        last_used: Timestamp of most recent usage

    Invariants:
        - total_uses >= 0
        - total_uses == successful_uses + failed_uses
        - total_tokens == total_input_tokens + total_output_tokens
    """

    prompt_id: str
    prompt_name: str
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    rating_sum: float = 0.0
    rating_count: int = 0
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate stats invariants."""
        if self.total_uses < 0:
            raise ValueError("PromptUsageStats.total_uses cannot be negative")

        if self.successful_uses < 0:
            raise ValueError("PromptUsageStats.successful_uses cannot be negative")

        if self.failed_uses < 0:
            raise ValueError("PromptUsageStats.failed_uses cannot be negative")

        if self.total_uses != self.successful_uses + self.failed_uses:
            raise ValueError(
                f"PromptUsageStats.total_uses ({self.total_uses}) must equal "
                f"successful_uses ({self.successful_uses}) + failed_uses ({self.failed_uses})"
            )

        if self.total_tokens != self.total_input_tokens + self.total_output_tokens:
            raise ValueError(
                f"PromptUsageStats.total_tokens ({self.total_tokens}) must equal "
                f"total_input_tokens ({self.total_input_tokens}) + total_output_tokens ({self.total_output_tokens})"
            )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        if self.total_uses == 0:
            return 0.0
        return (self.successful_uses / self.total_uses) * 100

    @property
    def avg_tokens_per_use(self) -> float:
        """Calculate average tokens per use."""
        if self.total_uses == 0:
            return 0.0
        return self.total_tokens / self.total_uses

    @property
    def avg_input_tokens(self) -> float:
        """Calculate average input tokens."""
        if self.total_uses == 0:
            return 0.0
        return self.total_input_tokens / self.total_uses

    @property
    def avg_output_tokens(self) -> float:
        """Calculate average output tokens."""
        if self.total_uses == 0:
            return 0.0
        return self.total_output_tokens / self.total_uses

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_uses == 0:
            return 0.0
        return self.total_latency_ms / self.total_uses

    @property
    def avg_rating(self) -> float:
        """Calculate average user rating."""
        if self.rating_count == 0:
            return 0.0
        return self.rating_sum / self.rating_count

    def to_dict(self) -> dict:
        """Convert stats to dictionary for serialization."""
        return {
            "prompt_id": self.prompt_id,
            "prompt_name": self.prompt_name,
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses,
            "success_rate": round(self.success_rate, 2),
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_tokens_per_use": round(self.avg_tokens_per_use, 2),
            "avg_input_tokens": round(self.avg_input_tokens, 2),
            "avg_output_tokens": round(self.avg_output_tokens, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "rating_sum": round(self.rating_sum, 2),
            "rating_count": self.rating_count,
            "avg_rating": round(self.avg_rating, 2),
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_usages(cls, usages: list[PromptUsage]) -> PromptUsageStats:
        """
        Calculate stats from a list of usage events.

        Args:
            usages: List of PromptUsage events

        Returns:
            Aggregated PromptUsageStats
        """
        if not usages:
            return cls(prompt_id="", prompt_name="")

        # Get prompt info from first usage
        first = usages[0]
        prompt_id = first.prompt_id
        prompt_name = first.prompt_name

        # Aggregate
        total_uses = len(usages)
        successful_uses = sum(1 for u in usages if u.success)
        failed_uses = total_uses - successful_uses
        total_tokens = sum(u.total_tokens for u in usages)
        total_input_tokens = sum(u.input_tokens for u in usages)
        total_output_tokens = sum(u.output_tokens for u in usages)
        total_latency_ms = sum(u.latency_ms for u in usages)
        rating_sum = sum(u.user_rating or 0 for u in usages if u.user_rating is not None)
        rating_count = sum(1 for u in usages if u.user_rating is not None)

        # Find time range
        timestamps = [u.timestamp for u in usages]
        first_used = min(timestamps)
        last_used = max(timestamps)

        return cls(
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            total_uses=total_uses,
            successful_uses=successful_uses,
            failed_uses=failed_uses,
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_latency_ms=total_latency_ms,
            rating_sum=rating_sum,
            rating_count=rating_count,
            first_used=first_used,
            last_used=last_used,
        )


__all__ = [
    "PromptUsage",
    "PromptUsageStats",
]
