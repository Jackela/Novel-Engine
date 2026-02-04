"""
Prompt Experiment Entity

Warzone 4: AI Brain - BRAIN-018A
Domain entity for A/B testing prompt templates.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class ExperimentStatus(str, Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"  # Being configured, not yet active
    RUNNING = "running"  # Active and collecting data
    PAUSED = "paused"  # Temporarily stopped
    COMPLETED = "completed"  # Finished with a winner declared
    ARCHIVED = "archived"  # No longer relevant


class ExperimentMetric(str, Enum):
    """Metrics to track for experiment comparison."""

    SUCCESS_RATE = "success_rate"  # Percentage of successful generations
    USER_RATING = "user_rating"  # Average user feedback rating
    TOKEN_EFFICIENCY = "token_efficiency"  # Tokens per successful generation
    LATENCY = "latency"  # Average response time in milliseconds


@dataclass(frozen=True, slots=True)
class ExperimentMetrics:
    """
    Aggregated metrics for an experiment variant.

    Why frozen:
        Immutable snapshot prevents accidental modification.

    Attributes:
        total_runs: Total number of times this variant was used
        success_count: Number of successful generations
        failure_count: Number of failed generations
        total_tokens: Total tokens consumed across all runs
        total_latency_ms: Total latency across all runs
        rating_sum: Sum of all user ratings (for average calculation)
        rating_count: Number of ratings received

    Invariants:
        - total_runs >= 0
        - success_count >= 0
        - failure_count >= 0
        - total_runs == success_count + failure_count
    """

    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    rating_sum: float = 0.0
    rating_count: int = 0

    def __post_init__(self) -> None:
        """Validate metrics invariants."""
        if self.total_runs < 0:
            raise ValueError("ExperimentMetrics.total_runs cannot be negative")

        if self.success_count < 0:
            raise ValueError("ExperimentMetrics.success_count cannot be negative")

        if self.failure_count < 0:
            raise ValueError("ExperimentMetrics.failure_count cannot be negative")

        if self.total_runs != self.success_count + self.failure_count:
            raise ValueError(
                f"ExperimentMetrics.total_runs ({self.total_runs}) must equal "
                f"success_count ({self.success_count}) + failure_count ({self.failure_count})"
            )

        if self.total_tokens < 0:
            raise ValueError("ExperimentMetrics.total_tokens cannot be negative")

        if self.total_latency_ms < 0:
            raise ValueError("ExperimentMetrics.total_latency_ms cannot be negative")

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        if self.total_runs == 0:
            return 0.0
        return (self.success_count / self.total_runs) * 100

    @property
    def avg_rating(self) -> float:
        """Calculate average user rating."""
        if self.rating_count == 0:
            return 0.0
        return self.rating_sum / self.rating_count

    @property
    def avg_tokens_per_run(self) -> float:
        """Calculate average tokens per run."""
        if self.total_runs == 0:
            return 0.0
        return self.total_tokens / self.total_runs

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_runs == 0:
            return 0.0
        return self.total_latency_ms / self.total_runs

    @property
    def token_efficiency(self) -> float:
        """
        Calculate token efficiency (tokens per successful generation).

        Lower is better - fewer tokens to achieve success.
        """
        if self.success_count == 0:
            return float("inf")  # No successes, infinite cost per success
        return self.total_tokens / self.success_count

    def record_run(
        self,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
        rating: Optional[float] = None,
    ) -> ExperimentMetrics:
        """
        Record a single generation run.

        Args:
            success: Whether the generation was successful
            tokens: Number of tokens consumed
            latency_ms: Response time in milliseconds
            rating: Optional user rating (1-5 scale)

        Returns:
            New ExperimentMetrics with updated values
        """
        return ExperimentMetrics(
            total_runs=self.total_runs + 1,
            success_count=self.success_count + (1 if success else 0),
            failure_count=self.failure_count + (0 if success else 1),
            total_tokens=self.total_tokens + max(0, tokens),
            total_latency_ms=self.total_latency_ms + max(0, latency_ms),
            rating_sum=self.rating_sum + (rating or 0.0),
            rating_count=self.rating_count + (1 if rating is not None else 0),
        )

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for serialization."""
        return {
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 2),
            "total_tokens": self.total_tokens,
            "avg_tokens_per_run": round(self.avg_tokens_per_run, 2),
            "token_efficiency": round(self.token_efficiency, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "rating_sum": round(self.rating_sum, 2),
            "rating_count": self.rating_count,
            "avg_rating": round(self.avg_rating, 2),
        }


@dataclass
class PromptExperiment:
    """
    Entity representing an A/B testing experiment for prompt templates.

    Why not frozen:
        Entity may need to update status and metrics.

    Experiments compare two prompt variants (A and B) to determine which
    performs better based on specified metrics.

    Attributes:
        id: Unique identifier for this experiment (UUID)
        name: Human-readable name for the experiment
        description: Description of what is being tested
        prompt_a_id: ID of the first prompt template variant
        prompt_b_id: ID of the second prompt template variant
        metric: Primary metric for determining the winner
        traffic_split: Percentage of traffic for variant A (0-100). B gets (100 - traffic_split)
        status: Current status of the experiment
        metrics_a: Aggregated metrics for variant A
        metrics_b: Aggregated metrics for variant B
        winner: Winning variant ID if experiment is completed (None if running)
        created_at: Timestamp when experiment was created
        started_at: Timestamp when experiment was started
        ended_at: Timestamp when experiment was completed
        created_by: Optional identifier of who created this experiment
        min_sample_size: Minimum runs per variant before declaring winner
        confidence_threshold: Statistical confidence threshold (0-1) for declaring winner

    Invariants:
        - id must be non-empty
        - name must be non-empty
        - prompt_a_id and prompt_b_id must be different
        - traffic_split must be between 0 and 100
        - metrics_a and metrics_b must be valid ExperimentMetrics
    """

    id: str
    name: str
    prompt_a_id: str
    prompt_b_id: str
    metric: ExperimentMetric
    traffic_split: int = 50  # Default 50/50 split
    status: ExperimentStatus = ExperimentStatus.DRAFT
    description: str = ""
    metrics_a: ExperimentMetrics = field(default_factory=ExperimentMetrics)
    metrics_b: ExperimentMetrics = field(default_factory=ExperimentMetrics)
    winner: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_by: Optional[str] = None
    min_sample_size: int = 100
    confidence_threshold: float = 0.95

    def __post_init__(self) -> None:
        """Validate experiment invariants."""
        if not self.id or not self.id.strip():
            raise ValueError("PromptExperiment.id cannot be empty")

        if not self.name or not self.name.strip():
            raise ValueError("PromptExperiment.name cannot be empty")

        if self.prompt_a_id == self.prompt_b_id:
            raise ValueError(
                "PromptExperiment.prompt_a_id and prompt_b_id must be different"
            )

        if not 0 <= self.traffic_split <= 100:
            raise ValueError(
                f"PromptExperiment.traffic_split must be between 0 and 100, got: {self.traffic_split}"
            )

        if self.min_sample_size < 1:
            raise ValueError(
                f"PromptExperiment.min_sample_size must be positive, got: {self.min_sample_size}"
            )

        if not 0 < self.confidence_threshold <= 1:
            raise ValueError(
                f"PromptExperiment.confidence_threshold must be between 0 and 1, got: {self.confidence_threshold}"
            )

        # Normalize timestamps to UTC
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "created_at", self.created_at.astimezone(timezone.utc))

        if self.started_at is not None and self.started_at.tzinfo is None:
            object.__setattr__(self, "started_at", self.started_at.replace(tzinfo=timezone.utc))

        if self.ended_at is not None and self.ended_at.tzinfo is None:
            object.__setattr__(self, "ended_at", self.ended_at.replace(tzinfo=timezone.utc))

    def assign_variant(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Assign a user to a variant using consistent hashing.

        Consistent hashing ensures the same user always gets the same variant,
        which is important for valid A/B testing.

        Args:
            user_id: Unique identifier for the user
            session_id: Optional session ID for additional consistency

        Returns:
            ID of the assigned prompt variant (prompt_a_id or prompt_b_id)
        """
        # Create a stable key from user_id and optional session_id
        key = f"{user_id}:{session_id or ''}"

        # Hash the key using SHA-256 for stable distribution
        hash_bytes = hashlib.sha256(key.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:8], byteorder="big")

        # Map hash to 0-100 range
        hash_value = hash_int % 101

        # Assign to A if hash is below traffic_split, otherwise B
        if hash_value < self.traffic_split:
            return self.prompt_a_id
        return self.prompt_b_id

    def record_success(
        self,
        variant_id: str,
        tokens: int = 0,
        latency_ms: float = 0.0,
        rating: Optional[float] = None,
    ) -> None:
        """
        Record a successful generation for a variant.

        Args:
            variant_id: ID of the variant (prompt_a_id or prompt_b_id)
            tokens: Number of tokens consumed
            latency_ms: Response time in milliseconds
            rating: Optional user rating (1-5 scale)

        Raises:
            ValueError: If variant_id is not prompt_a_id or prompt_b_id
        """
        if variant_id not in (self.prompt_a_id, self.prompt_b_id):
            raise ValueError(
                f"variant_id must be prompt_a_id or prompt_b_id, got: {variant_id}"
            )

        if variant_id == self.prompt_a_id:
            object.__setattr__(
                self, "metrics_a", self.metrics_a.record_run(True, tokens, latency_ms, rating)
            )
        else:
            object.__setattr__(
                self, "metrics_b", self.metrics_b.record_run(True, tokens, latency_ms, rating)
            )

    def record_failure(
        self,
        variant_id: str,
        tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Record a failed generation for a variant.

        Args:
            variant_id: ID of the variant (prompt_a_id or prompt_b_id)
            tokens: Number of tokens consumed
            latency_ms: Response time in milliseconds

        Raises:
            ValueError: If variant_id is not prompt_a_id or prompt_b_id
        """
        if variant_id not in (self.prompt_a_id, self.prompt_b_id):
            raise ValueError(
                f"variant_id must be prompt_a_id or prompt_b_id, got: {variant_id}"
            )

        if variant_id == self.prompt_a_id:
            object.__setattr__(
                self, "metrics_a", self.metrics_a.record_run(False, tokens, latency_ms)
            )
        else:
            object.__setattr__(
                self, "metrics_b", self.metrics_b.record_run(False, tokens, latency_ms)
            )

    def start(self) -> None:
        """
        Start the experiment.

        Raises:
            ValueError: If experiment is not in DRAFT status
        """
        if self.status != ExperimentStatus.DRAFT:
            raise ValueError(
                f"Cannot start experiment with status {self.status.value}, "
                "only DRAFT experiments can be started"
            )

        object.__setattr__(self, "status", ExperimentStatus.RUNNING)
        object.__setattr__(self, "started_at", _utcnow())

    def pause(self) -> None:
        """
        Pause the experiment.

        Raises:
            ValueError: If experiment is not RUNNING
        """
        if self.status != ExperimentStatus.RUNNING:
            raise ValueError(
                f"Cannot pause experiment with status {self.status.value}, "
                "only RUNNING experiments can be paused"
            )

        object.__setattr__(self, "status", ExperimentStatus.PAUSED)

    def resume(self) -> None:
        """
        Resume a paused experiment.

        Raises:
            ValueError: If experiment is not PAUSED
        """
        if self.status != ExperimentStatus.PAUSED:
            raise ValueError(
                f"Cannot resume experiment with status {self.status.value}, "
                "only PAUSED experiments can be resumed"
            )

        object.__setattr__(self, "status", ExperimentStatus.RUNNING)

    def complete(self, winner_id: Optional[str] = None) -> None:
        """
        Mark the experiment as completed with an optional winner.

        Args:
            winner_id: ID of the winning variant (auto-detected if None)

        Raises:
            ValueError: If experiment is not RUNNING or PAUSED
        """
        if self.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            raise ValueError(
                f"Cannot complete experiment with status {self.status.value}, "
                "only RUNNING or PAUSED experiments can be completed"
            )

        object.__setattr__(self, "status", ExperimentStatus.COMPLETED)
        object.__setattr__(self, "ended_at", _utcnow())

        # Auto-detect winner if not specified
        if winner_id is None:
            winner_id = self._detect_winner()
        elif winner_id not in (self.prompt_a_id, self.prompt_b_id):
            raise ValueError(
                f"winner_id must be prompt_a_id or prompt_b_id, got: {winner_id}"
            )

        object.__setattr__(self, "winner", winner_id)

    def _detect_winner(self) -> Optional[str]:
        """
        Detect the winning variant based on the experiment metric.

        Returns:
            ID of the winning variant, or None if insufficient data

        Note:
            This is a simplified winner detection. For production use,
            consider implementing proper statistical tests (e.g., chi-square,
            t-test) for significance.
        """
        # Check if we have enough samples
        if (
            self.metrics_a.total_runs < self.min_sample_size
            or self.metrics_b.total_runs < self.min_sample_size
        ):
            return None

        # Compare based on the experiment's primary metric
        match self.metric:
            case ExperimentMetric.SUCCESS_RATE:
                # Higher success rate wins
                if self.metrics_a.success_rate > self.metrics_b.success_rate:
                    return self.prompt_a_id
                elif self.metrics_b.success_rate > self.metrics_a.success_rate:
                    return self.prompt_b_id

            case ExperimentMetric.USER_RATING:
                # Higher rating wins
                if self.metrics_a.avg_rating > self.metrics_b.avg_rating:
                    return self.prompt_a_id
                elif self.metrics_b.avg_rating > self.metrics_a.avg_rating:
                    return self.prompt_b_id

            case ExperimentMetric.TOKEN_EFFICIENCY:
                # Lower token efficiency (fewer tokens per success) wins
                if (
                    self.metrics_a.token_efficiency != float("inf")
                    and self.metrics_b.token_efficiency != float("inf")
                ):
                    if self.metrics_a.token_efficiency < self.metrics_b.token_efficiency:
                        return self.prompt_a_id
                    elif self.metrics_b.token_efficiency < self.metrics_a.token_efficiency:
                        return self.prompt_b_id
                # Handle infinite values (no successes)
                elif self.metrics_a.token_efficiency != float("inf"):
                    return self.prompt_a_id
                elif self.metrics_b.token_efficiency != float("inf"):
                    return self.prompt_b_id

            case ExperimentMetric.LATENCY:
                # Lower latency wins
                if self.metrics_a.avg_latency_ms < self.metrics_b.avg_latency_ms:
                    return self.prompt_a_id
                elif self.metrics_b.avg_latency_ms < self.metrics_a.avg_latency_ms:
                    return self.prompt_b_id

        # No clear winner or tie
        return None

    def get_results(self) -> dict:
        """
        Get experiment results summary.

        Returns:
            Dictionary containing experiment results and comparison
        """
        winner_name = "A" if self.winner == self.prompt_a_id else "B" if self.winner == self.prompt_b_id else None

        return {
            "experiment_id": self.id,
            "name": self.name,
            "status": self.status.value,
            "metric": self.metric.value,
            "winner": winner_name,
            "min_sample_size": self.min_sample_size,
            "traffic_split": {
                "A": self.traffic_split,
                "B": 100 - self.traffic_split,
            },
            "variant_a": {
                "prompt_id": self.prompt_a_id,
                **self.metrics_a.to_dict(),
            },
            "variant_b": {
                "prompt_id": self.prompt_b_id,
                **self.metrics_b.to_dict(),
            },
            "comparison": self._compare_variants(),
            "timeline": {
                "created_at": self.created_at.isoformat(),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            },
        }

    def _compare_variants(self) -> dict:
        """
        Compare the two variants across all metrics.

        Returns:
            Dictionary containing comparison data
        """
        # Calculate relative differences
        def safe_divide(a: float, b: float) -> float:
            if b == 0:
                return 0.0
            return ((a - b) / b) * 100

        return {
            "success_rate_diff": round(
                self.metrics_a.success_rate - self.metrics_b.success_rate, 2
            ),
            "success_rate_rel_diff": round(
                safe_divide(self.metrics_a.success_rate, self.metrics_b.success_rate), 2
            ),
            "avg_rating_diff": round(
                self.metrics_a.avg_rating - self.metrics_b.avg_rating, 2
            ),
            "avg_rating_rel_diff": round(
                safe_divide(self.metrics_a.avg_rating, self.metrics_b.avg_rating), 2
            ),
            "token_efficiency_diff": round(
                self.metrics_a.token_efficiency - self.metrics_b.token_efficiency, 2
            ),
            "avg_latency_diff": round(
                self.metrics_a.avg_latency_ms - self.metrics_b.avg_latency_ms, 2
            ),
            "avg_latency_rel_diff": round(
                safe_divide(self.metrics_a.avg_latency_ms, self.metrics_b.avg_latency_ms), 2
            ),
        }

    def to_dict(self) -> dict:
        """
        Convert experiment to dictionary for serialization.

        Returns:
            Dictionary representation of the experiment
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_a_id": self.prompt_a_id,
            "prompt_b_id": self.prompt_b_id,
            "metric": self.metric.value,
            "traffic_split": self.traffic_split,
            "status": self.status.value,
            "metrics_a": self.metrics_a.to_dict(),
            "metrics_b": self.metrics_b.to_dict(),
            "winner": self.winner,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_by": self.created_by,
            "min_sample_size": self.min_sample_size,
            "confidence_threshold": self.confidence_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PromptExperiment:
        """
        Create experiment from dictionary.

        Args:
            data: Dictionary containing experiment data

        Returns:
            PromptExperiment instance
        """
        # Recreate metrics from dicts
        metrics_a_data = data.get("metrics_a", {})
        metrics_a = ExperimentMetrics(
            total_runs=metrics_a_data.get("total_runs", 0),
            success_count=metrics_a_data.get("success_count", 0),
            failure_count=metrics_a_data.get("failure_count", 0),
            total_tokens=metrics_a_data.get("total_tokens", 0),
            total_latency_ms=metrics_a_data.get("total_latency_ms", 0.0),
            rating_sum=metrics_a_data.get("rating_sum", 0.0),
            rating_count=metrics_a_data.get("rating_count", 0),
        )

        metrics_b_data = data.get("metrics_b", {})
        metrics_b = ExperimentMetrics(
            total_runs=metrics_b_data.get("total_runs", 0),
            success_count=metrics_b_data.get("success_count", 0),
            failure_count=metrics_b_data.get("failure_count", 0),
            total_tokens=metrics_b_data.get("total_tokens", 0),
            total_latency_ms=metrics_b_data.get("total_latency_ms", 0.0),
            rating_sum=metrics_b_data.get("rating_sum", 0.0),
            rating_count=metrics_b_data.get("rating_count", 0),
        )

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            prompt_a_id=data["prompt_a_id"],
            prompt_b_id=data["prompt_b_id"],
            metric=ExperimentMetric(data["metric"]),
            traffic_split=data.get("traffic_split", 50),
            status=ExperimentStatus(data.get("status", "draft")),
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            winner=data.get("winner"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else _utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            created_by=data.get("created_by"),
            min_sample_size=data.get("min_sample_size", 100),
            confidence_threshold=data.get("confidence_threshold", 0.95),
        )

    @classmethod
    def create(
        cls,
        name: str,
        prompt_a_id: str,
        prompt_b_id: str,
        metric: ExperimentMetric,
        traffic_split: int = 50,
        description: str = "",
        min_sample_size: int = 100,
        confidence_threshold: float = 0.95,
        created_by: Optional[str] = None,
        id: Optional[str] = None,
    ) -> PromptExperiment:
        """
        Factory method to create a new experiment.

        Args:
            name: Human-readable name
            prompt_a_id: ID of the first prompt variant
            prompt_b_id: ID of the second prompt variant
            metric: Primary metric for comparison
            traffic_split: Traffic percentage for variant A (0-100)
            description: Description of what is being tested
            min_sample_size: Minimum runs per variant for statistical significance
            confidence_threshold: Statistical confidence threshold
            created_by: Optional creator identifier
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New PromptExperiment instance
        """
        return cls(
            id=id or str(uuid4()),
            name=name,
            description=description,
            prompt_a_id=prompt_a_id,
            prompt_b_id=prompt_b_id,
            metric=metric,
            traffic_split=traffic_split,
            min_sample_size=min_sample_size,
            confidence_threshold=confidence_threshold,
            created_by=created_by,
        )


__all__ = [
    "PromptExperiment",
    "ExperimentStatus",
    "ExperimentMetric",
    "ExperimentMetrics",
]
