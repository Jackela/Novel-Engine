"""
Budget Alert Service

Warzone 4: AI Brain - BRAIN-034B
Service for monitoring token usage and triggering budget alerts.

Constitution Compliance:
- Article II (Hexagonal): Application service with no infrastructure dependencies
- Article V (SOLID): SRP - alert evaluation and notification only
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Optional

import structlog

from ...application.ports.i_budget_alert_repository import IBudgetAlertRepository
from ...application.ports.i_token_usage_repository import ITokenUsageRepository
from ...domain.models.budget_alert import (
    AlertComparisonOperator,
    AlertEvaluationResult,
    AlertFrequency,
    AlertThresholdType,
    AlertTriggeredEvent,
    BudgetAlertConfig,
    BudgetAlertState,
)
from ...domain.models.token_usage import TokenUsage

if TYPE_CHECKING:
    from ...domain.models.token_usage import TokenUsageStats


logger = structlog.get_logger()


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class BudgetAlertServiceConfig:
    """
    Configuration for BudgetAlertService.

    Attributes:
        enabled: Whether alert checking is enabled
        check_interval_seconds: How often to check for threshold violations
        batch_size: Number of usages to process per batch
        max_concurrent_checks: Maximum concurrent alert evaluations
        default_workspace_id: Default workspace for alerts
        default_user_id: Default user for alerts
    """

    enabled: bool = True
    check_interval_seconds: int = 60  # Check every minute by default
    batch_size: int = 1000
    max_concurrent_checks: int = 10
    default_workspace_id: Optional[str] = None
    default_user_id: Optional[str] = None


# Type alias for alert notification handler
AlertHandler = Callable[[AlertTriggeredEvent], Awaitable[None] | None]


@dataclass
class BudgetAlertService:
    """
    Service for monitoring token usage and triggering budget alerts.

    Why:
        - Monitors LLM usage in real-time for budget overruns
        - Provides configurable thresholds for cost/token/request limits
        - Supports per-workspace and per-user alerting
        - Enables proactive cost management

    Features:
        - Multiple threshold types (cost, tokens, requests, API calls)
        - Configurable comparison operators (gt, gte, lt, lte)
        - Frequency-based alerting (once, daily, weekly, always)
        - Time-windowed aggregation
        - Cooldown periods to prevent spam
        - Async notification handlers

    Example:
        >>> service = BudgetAlertService(repository, usage_repository)
        >>>
        >>> # Register an alert handler
        >>> async def handle_alert(event: AlertTriggeredEvent):
        >>>     send_email(event.message)
        >>>
        >>> service.register_handler(handle_alert)
        >>>
        >>> # Check usage after an API call
        >>> result = await service.evaluate_usage(usage_record)
        >>> if result.triggered:
        >>>     print(f"Alert triggered: {len(result.events)} alerts")
    """

    _repository: IBudgetAlertRepository
    _usage_repository: ITokenUsageRepository
    _config: BudgetAlertServiceConfig
    _handlers: list[AlertHandler] = field(default_factory=list, init=False, repr=False)
    _check_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock, init=False, repr=False
    )
    _background_task: asyncio.Task[None] | None = field(
        default=None, init=False, repr=False
    )

    def __init__(
        self,
        repository: IBudgetAlertRepository,
        usage_repository: ITokenUsageRepository,
        config: BudgetAlertServiceConfig | None = None,
    ) -> None:
        """
        Initialize the budget alert service.

        Args:
            repository: Budget alert repository for state persistence
            usage_repository: Token usage repository for aggregation
            config: Optional service configuration
        """
        self._repository = repository
        self._usage_repository = usage_repository
        self._config = config or BudgetAlertServiceConfig()

        logger.info(
            "budget_alert_service_initialized",
            enabled=self._config.enabled,
            check_interval=self._config.check_interval_seconds,
        )

    def register_handler(self, handler: AlertHandler) -> None:
        """
        Register an alert notification handler.

        Args:
            handler: Async or sync function to call when alert triggers
        """
        if handler not in self._handlers:
            self._handlers.append(handler)
            logger.debug("alert_handler_registered", handler=str(handler))

    def unregister_handler(self, handler: AlertHandler) -> None:
        """
        Unregister an alert notification handler.

        Args:
            handler: Handler function to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            logger.debug("alert_handler_unregistered", handler=str(handler))

    async def evaluate_usage(
        self,
        usage: TokenUsage,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> AlertEvaluationResult:
        """
        Evaluate a usage event against all applicable alerts.

        Args:
            usage: The token usage event to evaluate
            workspace_id: Optional workspace override
            user_id: Optional user override

        Returns:
            AlertEvaluationResult with any triggered alerts
        """
        if not self._config.enabled:
            return AlertEvaluationResult(triggered=False, alerts_checked=0)

        # Get applicable alerts
        workspace_filter = (
            workspace_id or usage.workspace_id or self._config.default_workspace_id
        )
        user_filter = user_id or usage.user_id or self._config.default_user_id

        alerts = await self._repository.get_all_alerts(
            workspace_id=workspace_filter,
            user_id=user_filter,
            enabled_only=True,
        )

        if not alerts:
            return AlertEvaluationResult(triggered=False, alerts_checked=0)

        triggered_events: list[AlertTriggeredEvent] = []
        now = _utcnow()

        for alert_state in alerts:
            config = alert_state.config

            # Filter by provider/model if configured
            if config.provider and config.provider != usage.provider:
                continue
            if config.model_name and config.model_name != usage.model_name:
                continue

            # Check if alert should be evaluated
            if not self._should_evaluate_alert(alert_state, config, now):
                continue

            # Evaluate the alert
            event = await self._evaluate_single_alert(alert_state, usage, now)
            if event:
                triggered_events.append(event)

                # Update alert state
                alert_state.mark_triggered(notified=True)
                await self._repository.save_alert(alert_state)

                # Log the event
                await self._repository.log_triggered_event(event)

        # Notify handlers
        for event in triggered_events:
            await self._notify_handlers(event)

        return AlertEvaluationResult(
            triggered=len(triggered_events) > 0,
            events=tuple(triggered_events),
            alerts_checked=len(alerts),
        )

    async def check_thresholds(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> AlertEvaluationResult:
        """
        Check all alerts against current aggregated usage.

        This is useful for periodic background checks.

        Args:
            workspace_id: Optional workspace to check
            user_id: Optional user to check

        Returns:
            AlertEvaluationResult with any triggered alerts
        """
        if not self._config.enabled:
            return AlertEvaluationResult(triggered=False, alerts_checked=0)

        async with self._check_lock:
            workspace_filter = workspace_id or self._config.default_workspace_id
            user_filter = user_id or self._config.default_user_id

            alerts = await self._repository.get_all_alerts(
                workspace_id=workspace_filter,
                user_id=user_filter,
                enabled_only=True,
            )

            if not alerts:
                return AlertEvaluationResult(triggered=False, alerts_checked=0)

            triggered_events: list[AlertTriggeredEvent] = []
            now = _utcnow()

            for alert_state in alerts:
                config = alert_state.config

                # Check if alert should be evaluated
                if not self._should_evaluate_alert(alert_state, config, now):
                    continue

                # Get aggregated stats for the time window
                start_time = now - timedelta(seconds=config.time_window_seconds)

                try:
                    stats = await self._usage_repository.get_stats(
                        start_time=start_time,
                        end_time=now,
                        provider=config.provider,
                        model_name=config.model_name,
                        workspace_id=config.workspace_id,
                    )
                except Exception as e:
                    logger.warning(
                        "budget_alert_stats_fetch_failed",
                        alert_id=alert_state.id,
                        error=str(e),
                    )
                    continue

                # Evaluate based on threshold type
                current_value = self._get_value_from_stats(stats, config.threshold_type)

                if self._check_threshold(
                    current_value, config.threshold_value, config.operator
                ):
                    # Threshold exceeded!
                    event = AlertTriggeredEvent(
                        alert_id=alert_state.id,
                        threshold_type=config.threshold_type,
                        current_value=current_value,
                        threshold_value=config.threshold_value,
                        severity=config.severity,
                        message=self._format_alert_message(
                            config, current_value, stats
                        ),
                        workspace_id=config.workspace_id,
                        user_id=config.user_id,
                        timestamp=now,
                        metadata={
                            "time_window_seconds": config.time_window_seconds,
                            "operator": config.operator.value,
                            "stats": stats.to_dict()
                            if hasattr(stats, "to_dict")
                            else None,
                        },
                    )

                    triggered_events.append(event)

                    # Update alert state
                    should_notify = alert_state.should_notify
                    alert_state.mark_triggered(notified=should_notify)
                    await self._repository.save_alert(alert_state)

                    # Log the event
                    await self._repository.log_triggered_event(event)

                    # Notify if appropriate
                    if should_notify:
                        await self._notify_handlers(event)

            return AlertEvaluationResult(
                triggered=len(triggered_events) > 0,
                events=tuple(triggered_events),
                alerts_checked=len(alerts),
            )

    async def add_alert(self, config: BudgetAlertConfig) -> BudgetAlertState:
        """
        Add a new budget alert.

        Args:
            config: Alert configuration

        Returns:
            The created alert state
        """
        alert_state = BudgetAlertState.create(config)
        await self._repository.save_alert(alert_state)
        logger.info(
            "budget_alert_created",
            alert_id=alert_state.id,
            threshold_type=config.threshold_type.value,
            threshold_value=config.threshold_value,
        )
        return alert_state

    async def remove_alert(self, alert_id: str) -> bool:
        """
        Remove a budget alert.

        Args:
            alert_id: ID of the alert to remove

        Returns:
            True if removed, False if not found
        """
        result = await self._repository.delete_alert(alert_id)
        if result:
            logger.info("budget_alert_removed", alert_id=alert_id)
        return result

    async def get_alerts(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> list[BudgetAlertState]:
        """
        Get all alerts for a workspace/user.

        Args:
            workspace_id: Optional workspace filter
            user_id: Optional user filter

        Returns:
            List of alert states
        """
        return await self._repository.get_all_alerts(
            workspace_id=workspace_id,
            user_id=user_id,
            enabled_only=False,
        )

    async def get_triggered_history(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AlertTriggeredEvent]:
        """
        Get history of triggered alerts.

        Args:
            workspace_id: Optional workspace filter
            user_id: Optional user filter
            start_time: Optional start of time range
            end_time: Optional end of time range
            limit: Maximum results to return

        Returns:
            List of triggered alert events
        """
        return await self._repository.get_triggered_events(
            workspace_id=workspace_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def _should_evaluate_alert(
        self,
        alert_state: BudgetAlertState,
        config: BudgetAlertConfig,
        now: datetime,
    ) -> bool:
        """
        Check if an alert should be evaluated based on frequency/cooldown.

        Args:
            alert_state: Current alert state
            config: Alert configuration
            now: Current timestamp

        Returns:
            True if alert should be evaluated
        """
        # Always evaluate if never triggered
        if alert_state.last_triggered is None:
            return True

        # Check frequency-based rules
        match config.frequency:
            case AlertFrequency.ALWAYS:
                # Check cooldown only
                return (now - alert_state.last_triggered) >= config.cooldown
            case AlertFrequency.ONCE:
                # Only check if never triggered (already handled above)
                return False
            case AlertFrequency.DAILY:
                # Check if last trigger was on a different day
                last_date = alert_state.last_triggered.date()
                current_date = now.date()
                return last_date != current_date
            case AlertFrequency.WEEKLY:
                # Check if at least a week has passed
                return (now - alert_state.last_triggered) >= timedelta(weeks=1)

        return True

    async def _evaluate_single_alert(
        self,
        alert_state: BudgetAlertState,
        usage: TokenUsage,
        now: datetime,
    ) -> AlertTriggeredEvent | None:
        """
        Evaluate a single alert against a usage event.

        Args:
            alert_state: Alert state to evaluate
            usage: Usage event to check
            now: Current timestamp

        Returns:
            AlertTriggeredEvent if threshold exceeded, None otherwise
        """
        config = alert_state.config

        # Get the value to check based on threshold type
        current_value = self._get_value_from_usage(usage, config.threshold_type)

        # Check if threshold is exceeded
        if not self._check_threshold(
            current_value, config.threshold_value, config.operator
        ):
            return None

        # Create alert event
        return AlertTriggeredEvent(
            alert_id=alert_state.id,
            threshold_type=config.threshold_type,
            current_value=current_value,
            threshold_value=config.threshold_value,
            severity=config.severity,
            message=self._format_usage_alert_message(config, usage, current_value),
            workspace_id=config.workspace_id or usage.workspace_id,
            user_id=config.user_id or usage.user_id,
            timestamp=now,
            metadata={
                "usage_id": usage.id,
                "provider": usage.provider,
                "model_name": usage.model_name,
                "operator": config.operator.value,
            },
        )

    def _get_value_from_usage(
        self,
        usage: TokenUsage,
        threshold_type: AlertThresholdType,
    ) -> float:
        """
        Extract the relevant value from a usage event.

        Args:
            usage: Token usage event
            threshold_type: Type of threshold to check

        Returns:
            The numeric value to compare against the threshold
        """
        match threshold_type:
            case AlertThresholdType.COST:
                return float(usage.total_cost)
            case AlertThresholdType.TOKENS:
                return float(usage.total_tokens)
            case AlertThresholdType.REQUESTS:
                return 1.0  # Each usage event is one request
            case AlertThresholdType.API_CALLS:
                return 1.0  # Each usage event is one API call
            case _:
                return 0.0

    def _get_value_from_stats(
        self,
        stats: TokenUsageStats,
        threshold_type: AlertThresholdType,
    ) -> float:
        """
        Extract the relevant value from aggregated stats.

        Args:
            stats: Aggregated token usage stats
            threshold_type: Type of threshold to check

        Returns:
            The numeric value to compare against the threshold
        """
        match threshold_type:
            case AlertThresholdType.COST:
                return float(stats.total_cost)
            case AlertThresholdType.TOKENS:
                return float(stats.total_tokens)
            case AlertThresholdType.REQUESTS:
                return float(stats.total_requests)
            case AlertThresholdType.API_CALLS:
                return float(stats.total_requests)
            case _:
                return 0.0

    def _check_threshold(
        self,
        current_value: float,
        threshold_value: float,
        operator: AlertComparisonOperator,
    ) -> bool:
        """
        Check if a threshold is exceeded based on the comparison operator.

        Args:
            current_value: Current value
            threshold_value: Threshold value
            operator: Comparison operator

        Returns:
            True if threshold is exceeded
        """
        match operator:
            case AlertComparisonOperator.GREATER_THAN:
                return current_value > threshold_value
            case AlertComparisonOperator.GREATER_THAN_OR_EQUAL:
                return current_value >= threshold_value
            case AlertComparisonOperator.LESS_THAN:
                return current_value < threshold_value
            case AlertComparisonOperator.LESS_THAN_OR_EQUAL:
                return current_value <= threshold_value

        return False

    def _format_alert_message(
        self,
        config: BudgetAlertConfig,
        current_value: float,
        stats: TokenUsageStats,
    ) -> str:
        """
        Format a human-readable alert message.

        Args:
            config: Alert configuration
            current_value: Current value that triggered the alert
            stats: Aggregated statistics

        Returns:
            Formatted alert message
        """
        threshold_type_name = config.threshold_type.value.replace("_", " ").title()

        # Build scope description
        scope_parts = []
        if config.workspace_id:
            scope_parts.append(f"workspace {config.workspace_id}")
        if config.user_id:
            scope_parts.append(f"user {config.user_id}")
        if config.provider:
            scope_parts.append(f"provider {config.provider}")
        if config.model_name:
            scope_parts.append(f"model {config.model_name}")

        scope = f" for {', '.join(scope_parts)}" if scope_parts else ""

        return (
            f"Budget Alert: {threshold_type_name} threshold exceeded{scope}. "
            f"Current: {current_value:.2f}, Threshold: {config.threshold_value:.2f}. "
            f"Period: {config.time_window_seconds}s window."
        )

    def _format_usage_alert_message(
        self,
        config: BudgetAlertConfig,
        usage: TokenUsage,
        current_value: float,
    ) -> str:
        """
        Format a human-readable alert message for a single usage event.

        Args:
            config: Alert configuration
            usage: The usage event that triggered the alert
            current_value: Current value that triggered the alert

        Returns:
            Formatted alert message
        """
        threshold_type_name = config.threshold_type.value.replace("_", " ").title()

        return (
            f"Budget Alert: {threshold_type_name} threshold exceeded. "
            f"Current value: {current_value:.2f}, Threshold: {config.threshold_value:.2f}. "
            f"Triggered by {usage.provider}:{usage.model_name} "
            f"(request ID: {usage.request_id or 'N/A'})"
        )

    async def _notify_handlers(self, event: AlertTriggeredEvent) -> None:
        """
        Notify all registered handlers of an alert.

        Args:
            event: The alert event to notify about
        """
        for handler in self._handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(
                    "alert_handler_failed",
                    alert_id=event.alert_id,
                    handler=str(handler),
                    error=str(e),
                )

    async def shutdown(self) -> None:
        """
        Shutdown the alert service.

        Stops any background tasks.
        """
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        logger.info("budget_alert_service_shutdown")


def create_budget_alert_service(
    repository: IBudgetAlertRepository,
    usage_repository: ITokenUsageRepository,
    config: BudgetAlertServiceConfig | None = None,
) -> BudgetAlertService:
    """
    Factory function to create a configured BudgetAlertService.

    Args:
        repository: Budget alert repository
        usage_repository: Token usage repository
        config: Optional service configuration

    Returns:
        Configured BudgetAlertService instance
    """
    return BudgetAlertService(
        repository=repository,
        usage_repository=usage_repository,
        config=config or BudgetAlertServiceConfig(),
    )


__all__ = [
    "BudgetAlertService",
    "BudgetAlertServiceConfig",
    "AlertHandler",
    "create_budget_alert_service",
]
