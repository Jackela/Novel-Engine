"""
Budget Alert Domain Models

Warzone 4: AI Brain - BRAIN-034B
Domain entities for budget alert thresholds and notifications.

Constitution Compliance:
- Article I (DDD): Entities with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain models independent of infrastructure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

if TYPE_CHECKING:
    pass


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class AlertThresholdType(str, Enum):
    """Types of alert thresholds."""

    COST = "cost"  # Total cost threshold
    TOKENS = "tokens"  # Total tokens threshold
    REQUESTS = "requests"  # Number of requests threshold
    API_CALLS = "api_calls"  # API-specific call count


class AlertComparisonOperator(str, Enum):
    """Comparison operators for threshold evaluation."""

    GREATER_THAN = "gt"  # Trigger when value > threshold
    GREATER_THAN_OR_EQUAL = "gte"  # Trigger when value >= threshold
    LESS_THAN = "lt"  # Trigger when value < threshold
    LESS_THAN_OR_EQUAL = "lte"  # Trigger when value <= threshold


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    INFO = "info"  # Informational alert
    WARNING = "warning"  # Warning level
    ERROR = "error"  # Error level
    CRITICAL = "critical"  # Critical alert


class AlertFrequency(str, Enum):
    """How often to repeat alerts."""

    ONCE = "once"  # Alert once per threshold period
    DAILY = "daily"  # Alert at most once per day
    WEEKLY = "weekly"  # Alert at most once per week
    ALWAYS = "always"  # Alert every time threshold is exceeded


@dataclass
class AlertTriggeredEvent:
    """
    Event emitted when an alert threshold is triggered.

    Attributes:
        alert_id: ID of the alert that was triggered
        threshold_type: Type of threshold that was triggered
        current_value: Current value that triggered the alert
        threshold_value: The threshold value
        severity: Severity of the alert
        message: Human-readable alert message
        workspace_id: Optional workspace the alert is for
        user_id: Optional user the alert is for
        timestamp: When the alert was triggered
        metadata: Additional context about the alert
    """

    alert_id: str
    threshold_type: AlertThresholdType
    current_value: float
    threshold_value: float
    severity: AlertSeverity
    message: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "threshold_type": self.threshold_type.value,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "severity": self.severity.value,
            "message": self.message,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class BudgetAlertConfig:
    """
    Configuration for a single budget alert.

    Attributes:
        threshold_type: Type of metric to monitor
        threshold_value: The threshold value
        operator: Comparison operator
        severity: Alert severity level
        frequency: How often to repeat alerts
        time_window_seconds: Time window for aggregation (0 = all-time)
        workspace_id: Optional workspace to monitor (None = global)
        user_id: Optional user to monitor (None = all users)
        provider: Optional LLM provider filter (None = all providers)
        model_name: Optional model filter (None = all models)
        enabled: Whether the alert is active
        cooldown_seconds: Minimum time between alerts of this type
    """

    threshold_type: AlertThresholdType
    threshold_value: float
    operator: AlertComparisonOperator = AlertComparisonOperator.GREATER_THAN_OR_EQUAL
    severity: AlertSeverity = AlertSeverity.WARNING
    frequency: AlertFrequency = AlertFrequency.DAILY
    time_window_seconds: int = 86400  # Default: 24 hours
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    enabled: bool = True
    cooldown_seconds: int = 3600  # Default: 1 hour cooldown

    def __post_init__(self) -> None:
        """Validate alert configuration."""
        if self.threshold_value < 0:
            raise ValueError(
                f"BudgetAlertConfig.threshold_value cannot be negative, got: {self.threshold_value}"
            )

        if self.time_window_seconds < 0:
            raise ValueError(
                f"BudgetAlertConfig.time_window_seconds cannot be negative, got: {self.time_window_seconds}"
            )

        if self.cooldown_seconds < 0:
            raise ValueError(
                f"BudgetAlertConfig.cooldown_seconds cannot be negative, got: {self.cooldown_seconds}"
            )

    @property
    def time_window(self) -> timedelta:
        """Get time window as timedelta."""
        return timedelta(seconds=self.time_window_seconds)

    @property
    def cooldown(self) -> timedelta:
        """Get cooldown period as timedelta."""
        return timedelta(seconds=self.cooldown_seconds)


@dataclass
class BudgetAlertState:
    """
    State tracking for a budget alert.

    Tracks when alerts were last triggered to enforce frequency rules.

    Attributes:
        id: Unique state identifier
        config: The alert configuration this state is for
        last_triggered: When the alert was last triggered
        last_notified: When notification was last sent
        trigger_count: How many times the alert has been triggered
        notification_count: How many times notifications were sent
        created_at: When this state was created
        updated_at: When this state was last updated
    """

    id: str
    config: BudgetAlertConfig
    last_triggered: Optional[datetime] = None
    last_notified: Optional[datetime] = None
    trigger_count: int = 0
    notification_count: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate alert state."""
        if self.trigger_count < 0:
            raise ValueError(
                f"BudgetAlertState.trigger_count cannot be negative, got: {self.trigger_count}"
            )

        if self.notification_count < 0:
            raise ValueError(
                f"BudgetAlertState.notification_count cannot be negative, got: {self.notification_count}"
            )

        if self.notification_count > self.trigger_count:
            raise ValueError(
                f"BudgetAlertState.notification_count ({self.notification_count}) "
                f"cannot exceed trigger_count ({self.trigger_count})"
            )

    @property
    def should_notify(self) -> bool:
        """
        Check if notification should be sent based on frequency and cooldown.

        Returns:
            True if notification should be sent
        """
        now = _utcnow()

        # Never triggered before
        if self.last_notified is None:
            return True

        time_since_notify = now - self.last_notified

        # Check cooldown
        if time_since_notify < self.config.cooldown:
            return False

        # Check frequency
        match self.config.frequency:
            case AlertFrequency.ONCE:
                # Only notify once ever
                return False
            case AlertFrequency.DAILY:
                # Notify at most once per day
                return time_since_notify >= timedelta(days=1)
            case AlertFrequency.WEEKLY:
                # Notify at most once per week
                return time_since_notify >= timedelta(weeks=1)
            case AlertFrequency.ALWAYS:
                # Always notify if cooldown passed
                return True

        return False

    def mark_triggered(self, notified: bool = False) -> None:
        """
        Mark the alert as triggered.

        Args:
            notified: Whether notification was sent
        """
        self.last_triggered = _utcnow()
        self.trigger_count += 1
        self.updated_at = _utcnow()

        if notified:
            self.last_notified = _utcnow()
            self.notification_count += 1

    def reset(self) -> None:
        """Reset the alert state (e.g., after configuration change)."""
        self.last_triggered = None
        self.last_notified = None
        self.trigger_count = 0
        self.notification_count = 0
        self.updated_at = _utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "id": self.id,
            "config": {
                "threshold_type": self.config.threshold_type.value,
                "threshold_value": self.config.threshold_value,
                "operator": self.config.operator.value,
                "severity": self.config.severity.value,
                "frequency": self.config.frequency.value,
                "time_window_seconds": self.config.time_window_seconds,
                "workspace_id": self.config.workspace_id,
                "user_id": self.config.user_id,
                "provider": self.config.provider,
                "model_name": self.config.model_name,
                "enabled": self.config.enabled,
                "cooldown_seconds": self.config.cooldown_seconds,
            },
            "last_triggered": self.last_triggered.isoformat()
            if self.last_triggered
            else None,
            "last_notified": self.last_notified.isoformat()
            if self.last_notified
            else None,
            "trigger_count": self.trigger_count,
            "notification_count": self.notification_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def create(
        cls, config: BudgetAlertConfig, id: Optional[str] = None
    ) -> BudgetAlertState:
        """
        Factory method to create a new alert state.

        Args:
            config: Alert configuration
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New BudgetAlertState instance
        """
        return cls(
            id=id or str(uuid4()),
            config=config,
        )


@dataclass(frozen=True, slots=True)
class AlertEvaluationResult:
    """
    Result of evaluating a usage event against alert thresholds.

    Attributes:
        triggered: Whether any threshold was triggered
        events: List of triggered alert events
        alerts_checked: Number of alerts that were evaluated
    """

    triggered: bool
    events: tuple[AlertTriggeredEvent, ...] = ()
    alerts_checked: int = 0

    @property
    def has_critical(self) -> bool:
        """Check if any critical alerts were triggered."""
        return any(e.severity == AlertSeverity.CRITICAL for e in self.events)

    @property
    def has_error_or_higher(self) -> bool:
        """Check if any error or higher severity alerts were triggered."""
        return any(
            e.severity in (AlertSeverity.ERROR, AlertSeverity.CRITICAL)
            for e in self.events
        )


__all__ = [
    "AlertThresholdType",
    "AlertComparisonOperator",
    "AlertSeverity",
    "AlertFrequency",
    "AlertTriggeredEvent",
    "BudgetAlertConfig",
    "BudgetAlertState",
    "AlertEvaluationResult",
]
