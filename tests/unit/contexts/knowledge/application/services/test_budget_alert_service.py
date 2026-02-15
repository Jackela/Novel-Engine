"""
Tests for Budget Alert Service

Warzone 4: AI Brain - BRAIN-034B
Tests for BudgetAlertService budget monitoring and alerting.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.contexts.knowledge.application.services.budget_alert_service import (
    BudgetAlertServiceConfig,
    create_budget_alert_service,
)
from src.contexts.knowledge.domain.models.budget_alert import (
    AlertComparisonOperator,
    AlertEvaluationResult,
    AlertFrequency,
    AlertSeverity,
    AlertThresholdType,
    AlertTriggeredEvent,
    BudgetAlertConfig,
    BudgetAlertState,
)
from src.contexts.knowledge.domain.models.token_usage import (
    TokenUsage,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_budget_alert_repository import (
    InMemoryBudgetAlertRepository,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_token_usage_repository import (
    InMemoryTokenUsageRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def alert_repository():
    """Create an in-memory budget alert repository."""
    return InMemoryBudgetAlertRepository()


@pytest.fixture
def usage_repository():
    """Create an in-memory token usage repository."""
    return InMemoryTokenUsageRepository()


@pytest.fixture
def alert_service(alert_repository, usage_repository):
    """Create a budget alert service with default config."""
    return create_budget_alert_service(
        repository=alert_repository,
        usage_repository=usage_repository,
    )


class TestBudgetAlertConfig:
    """Tests for BudgetAlertConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )

        assert config.threshold_type == AlertThresholdType.COST
        assert config.threshold_value == 10.0
        assert config.operator == AlertComparisonOperator.GREATER_THAN_OR_EQUAL
        assert config.severity == AlertSeverity.WARNING
        assert config.frequency == AlertFrequency.DAILY
        assert config.time_window_seconds == 86400  # 24 hours
        assert config.workspace_id is None
        assert config.user_id is None
        assert config.provider is None
        assert config.model_name is None
        assert config.enabled is True
        assert config.cooldown_seconds == 3600  # 1 hour

    def test_custom_config(self):
        """Test custom configuration."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.TOKENS,
            threshold_value=100000,
            operator=AlertComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.CRITICAL,
            frequency=AlertFrequency.ONCE,
            time_window_seconds=3600,
            workspace_id="ws-123",
            user_id="user-456",
            provider="openai",
            model_name="gpt-4o",
            cooldown_seconds=300,
        )

        assert config.threshold_type == AlertThresholdType.TOKENS
        assert config.threshold_value == 100000
        assert config.operator == AlertComparisonOperator.GREATER_THAN
        assert config.severity == AlertSeverity.CRITICAL
        assert config.frequency == AlertFrequency.ONCE
        assert config.time_window_seconds == 3600
        assert config.workspace_id == "ws-123"
        assert config.user_id == "user-456"
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"
        assert config.cooldown_seconds == 300

    def test_invalid_negative_threshold(self):
        """Test that negative threshold values are rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            BudgetAlertConfig(
                threshold_type=AlertThresholdType.COST,
                threshold_value=-10.0,
            )

    def test_invalid_negative_time_window(self):
        """Test that negative time windows are rejected."""
        with pytest.raises(ValueError, match="time_window_seconds cannot be negative"):
            BudgetAlertConfig(
                threshold_type=AlertThresholdType.COST,
                threshold_value=10.0,
                time_window_seconds=-1,
            )

    def test_time_window_property(self):
        """Test time_window property returns timedelta."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            time_window_seconds=3600,
        )

        assert config.time_window == timedelta(seconds=3600)


class TestBudgetAlertState:
    """Tests for BudgetAlertState."""

    def test_create_alert_state(self):
        """Test creating a new alert state."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        state = BudgetAlertState.create(config)

        assert state.id is not None
        assert state.config == config
        assert state.last_triggered is None
        assert state.last_notified is None
        assert state.trigger_count == 0
        assert state.notification_count == 0

    def test_should_notify_first_time(self):
        """Test that first trigger should notify."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        state = BudgetAlertState.create(config)

        assert state.should_notify is True

    def test_should_notify_with_cooldown(self):
        """Test that cooldown prevents notification."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            cooldown_seconds=300,  # 5 minutes
        )
        state = BudgetAlertState.create(config)

        # Mark as notified just now
        state.mark_triggered(notified=True)
        assert state.should_notify is False

    def test_should_notify_after_cooldown(self):
        """Test that notification is allowed after cooldown."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            cooldown_seconds=1,  # 1 second
            frequency=AlertFrequency.ALWAYS,
        )
        state = BudgetAlertState.create(config)

        # Mark as notified
        state.mark_triggered(notified=True)
        assert state.should_notify is False

        # Wait for cooldown
        import time

        time.sleep(1.1)

        # Now should notify again
        assert state.should_notify is True

    def test_should_notify_once_only(self):
        """Test that ONCE frequency only notifies once."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            frequency=AlertFrequency.ONCE,
        )
        state = BudgetAlertState.create(config)

        assert state.should_notify is True

        state.mark_triggered(notified=True)
        assert state.should_notify is False

    def test_mark_triggered_without_notify(self):
        """Test marking triggered without notification."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        state = BudgetAlertState.create(config)

        state.mark_triggered(notified=False)

        assert state.trigger_count == 1
        assert state.notification_count == 0
        assert state.last_triggered is not None
        assert state.last_notified is None

    def test_mark_triggered_with_notify(self):
        """Test marking triggered with notification."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        state = BudgetAlertState.create(config)

        state.mark_triggered(notified=True)

        assert state.trigger_count == 1
        assert state.notification_count == 1
        assert state.last_triggered is not None
        assert state.last_notified is not None

    def test_reset(self):
        """Test resetting alert state."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        state = BudgetAlertState.create(config)

        state.mark_triggered(notified=True)
        assert state.trigger_count == 1
        assert state.notification_count == 1

        state.reset()
        assert state.last_triggered is None
        assert state.last_notified is None
        assert state.trigger_count == 0
        assert state.notification_count == 0


class TestBudgetAlertService:
    """Tests for BudgetAlertService."""

    @pytest.mark.asyncio
    async def test_add_alert(self, alert_service):
        """Test adding a new alert."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )

        state = await alert_service.add_alert(config)

        assert state.id is not None
        assert state.config == config

        # Verify it was saved
        retrieved = await alert_service._repository.get_alert(state.id)
        assert retrieved is not None
        assert retrieved.id == state.id

    @pytest.mark.asyncio
    async def test_remove_alert(self, alert_service):
        """Test removing an alert."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )

        state = await alert_service.add_alert(config)
        removed = await alert_service.remove_alert(state.id)

        assert removed is True

        # Verify it was deleted
        retrieved = await alert_service._repository.get_alert(state.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_evaluate_usage_no_alerts(self, alert_service):
        """Test evaluation when no alerts are configured."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=2000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        result = await alert_service.evaluate_usage(usage)

        assert result.triggered is False
        assert result.alerts_checked == 0

    @pytest.mark.asyncio
    async def test_evaluate_usage_cost_threshold_exceeded(self, alert_service):
        """Test evaluation when cost threshold is exceeded."""
        # Add an alert for $10 cost
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            operator=AlertComparisonOperator.GREATER_THAN_OR_EQUAL,
        )
        await alert_service.add_alert(config)

        # Create a usage that exceeds the threshold
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,  # $5
            output_tokens=1_000_000,  # $10
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )
        # Total cost: $5 + $10 = $15, which exceeds $10

        result = await alert_service.evaluate_usage(usage)

        assert result.triggered is True
        assert len(result.events) == 1
        assert result.events[0].threshold_type == AlertThresholdType.COST
        assert result.events[0].current_value == 15.0
        assert result.events[0].threshold_value == 10.0

    @pytest.mark.asyncio
    async def test_evaluate_usage_tokens_threshold_exceeded(self, alert_service):
        """Test evaluation when token threshold is exceeded."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.TOKENS,
            threshold_value=100000,
            operator=AlertComparisonOperator.GREATER_THAN,
        )
        await alert_service.add_alert(config)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=50000,
            output_tokens=60000,  # Total: 110000 > 100000
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        result = await alert_service.evaluate_usage(usage)

        assert result.triggered is True
        assert result.events[0].threshold_type == AlertThresholdType.TOKENS
        assert result.events[0].current_value == 110000.0

    @pytest.mark.asyncio
    async def test_evaluate_usage_not_exceeded(self, alert_service):
        """Test evaluation when threshold is not exceeded."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=100.0,
            operator=AlertComparisonOperator.GREATER_THAN,
        )
        await alert_service.add_alert(config)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=1000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )
        # Total cost is way less than $100

        result = await alert_service.evaluate_usage(usage)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_evaluate_usage_provider_filter(self, alert_service):
        """Test provider filtering."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            provider="openai",  # Only OpenAI
        )
        await alert_service.add_alert(config)

        # Usage from different provider should not trigger
        usage = TokenUsage.create(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=3.00,
            cost_per_1m_output=15.00,
        )

        result = await alert_service.evaluate_usage(usage)
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_evaluate_usage_workspace_filter(self, alert_service):
        """Test workspace filtering."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            workspace_id="ws-123",
        )
        await alert_service.add_alert(config)

        # Usage from different workspace should not trigger
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            workspace_id="ws-456",  # Different workspace
        )

        result = await alert_service.evaluate_usage(usage)
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_evaluate_usage_workspace_match(self, alert_service):
        """Test workspace matching triggers alert."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            workspace_id="ws-123",
        )
        await alert_service.add_alert(config)

        # Usage from same workspace should trigger
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            workspace_id="ws-123",  # Same workspace
        )

        result = await alert_service.evaluate_usage(usage)
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_frequency_once_only_notifies_once(self, alert_service):
        """Test that ONCE frequency only notifies once."""
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            frequency=AlertFrequency.ONCE,
        )
        state = await alert_service.add_alert(config)

        # First usage triggers
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        result1 = await alert_service.evaluate_usage(usage)
        assert result1.triggered is True
        assert state.notification_count == 1

        # Refresh state from repository
        _state = await alert_service._repository.get_alert(state.id)  # noqa: F841

        # Second usage does not notify (already notified once)
        result2 = await alert_service.evaluate_usage(usage)
        # Alert still triggered but not notified again
        assert result2.triggered is False  # No new events

    @pytest.mark.asyncio
    async def test_disabled_service(self, alert_repository, usage_repository):
        """Test that disabled service doesn't evaluate."""
        config = BudgetAlertServiceConfig(enabled=False)
        service = create_budget_alert_service(
            repository=alert_repository,
            usage_repository=usage_repository,
            config=config,
        )

        # Add an alert
        alert_config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        await service.add_alert(alert_config)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        result = await service.evaluate_usage(usage)

        assert result.triggered is False
        assert result.alerts_checked == 0

    @pytest.mark.asyncio
    async def test_register_handler(self, alert_service):
        """Test registering alert handlers."""
        called_events = []

        async def handler(event: AlertTriggeredEvent):
            called_events.append(event)

        alert_service.register_handler(handler)

        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        await alert_service.add_alert(config)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        result = await alert_service.evaluate_usage(usage)

        assert result.triggered is True
        assert len(called_events) == 1
        assert called_events[0].threshold_type == AlertThresholdType.COST

    @pytest.mark.asyncio
    async def test_unregister_handler(self, alert_service):
        """Test unregistering alert handlers."""
        called_events = []

        async def handler(event: AlertTriggeredEvent):
            called_events.append(event)

        alert_service.register_handler(handler)
        alert_service.unregister_handler(handler)

        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        await alert_service.add_alert(config)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )

        await alert_service.evaluate_usage(usage)

        # Handler should not have been called
        assert len(called_events) == 0

    @pytest.mark.asyncio
    async def test_get_alerts(self, alert_service):
        """Test getting all alerts."""
        config1 = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            workspace_id="ws-1",
        )
        config2 = BudgetAlertConfig(
            threshold_type=AlertThresholdType.TOKENS,
            threshold_value=100000,
            workspace_id="ws-2",
        )

        await alert_service.add_alert(config1)
        await alert_service.add_alert(config2)

        all_alerts = await alert_service.get_alerts()
        assert len(all_alerts) == 2

        ws1_alerts = await alert_service.get_alerts(workspace_id="ws-1")
        assert len(ws1_alerts) == 1
        assert ws1_alerts[0].config.workspace_id == "ws-1"

    @pytest.mark.asyncio
    async def test_check_thresholds_with_stats(self, alert_service, usage_repository):
        """Test checking thresholds against aggregated stats."""
        # Add some usage data
        _now = datetime.now(timezone.utc)  # noqa: F841
        for i in range(10):
            usage = TokenUsage.create(
                provider="openai",
                model_name="gpt-4o",
                input_tokens=100000,
                output_tokens=50000,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
            )
            await usage_repository.save(usage)

        # Add alert for $5 cost
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=5.0,
            time_window_seconds=3600,  # 1 hour window
        )
        await alert_service.add_alert(config)

        result = await alert_service.check_thresholds()

        # Should trigger because 10 requests * $0.625 each = $6.25 > $5
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_get_triggered_history(self, alert_service):
        """Test getting triggered event history."""
        # Add an alert
        config = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
        )
        await alert_service.add_alert(config)

        # Trigger it
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            workspace_id="ws-123",
        )

        await alert_service.evaluate_usage(usage)

        # Get history
        history = await alert_service.get_triggered_history(workspace_id="ws-123")

        assert len(history) == 1
        assert history[0].workspace_id == "ws-123"
        assert history[0].threshold_type == AlertThresholdType.COST

    @pytest.mark.asyncio
    async def test_comparison_operators(self, alert_service):
        """Test different comparison operators."""
        # GREATER_THAN
        config_gt = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=10.0,
            operator=AlertComparisonOperator.GREATER_THAN,
        )
        await alert_service.add_alert(config_gt)

        # LESS_THAN
        config_lt = BudgetAlertConfig(
            threshold_type=AlertThresholdType.COST,
            threshold_value=100.0,
            operator=AlertComparisonOperator.LESS_THAN,
        )
        await alert_service.add_alert(config_lt)

        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4o",
            input_tokens=1_000_000,
            output_tokens=500_000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
        )
        # Total cost: $2.50 + $5.00 = $7.50

        result = await alert_service.evaluate_usage(usage)

        # $7.50 is NOT > $10, so GT doesn't trigger
        # $7.50 IS < $100, so LT triggers
        assert result.triggered is True
        assert len(result.events) == 1
        assert result.events[0].threshold_value == 100.0


class TestAlertTriggeredEvent:
    """Tests for AlertTriggeredEvent."""

    def test_to_dict(self):
        """Test converting event to dictionary."""
        event = AlertTriggeredEvent(
            alert_id="alert-123",
            threshold_type=AlertThresholdType.COST,
            current_value=15.50,
            threshold_value=10.0,
            severity=AlertSeverity.WARNING,
            message="Budget alert: Cost exceeded",
            workspace_id="ws-123",
            user_id="user-456",
        )

        data = event.to_dict()

        assert data["alert_id"] == "alert-123"
        assert data["threshold_type"] == "cost"
        assert data["current_value"] == 15.50
        assert data["threshold_value"] == 10.0
        assert data["severity"] == "warning"
        assert data["message"] == "Budget alert: Cost exceeded"
        assert data["workspace_id"] == "ws-123"
        assert data["user_id"] == "user-456"


class TestAlertEvaluationResult:
    """Tests for AlertEvaluationResult."""

    def test_has_critical(self):
        """Test checking for critical alerts."""
        result = AlertEvaluationResult(
            triggered=True,
            events=(
                AlertTriggeredEvent(
                    alert_id="1",
                    threshold_type=AlertThresholdType.COST,
                    current_value=10.0,
                    threshold_value=5.0,
                    severity=AlertSeverity.WARNING,
                    message="Warning",
                ),
                AlertTriggeredEvent(
                    alert_id="2",
                    threshold_type=AlertThresholdType.TOKENS,
                    current_value=100000,
                    threshold_value=50000,
                    severity=AlertSeverity.CRITICAL,
                    message="Critical",
                ),
            ),
        )

        assert result.has_critical is True

    def test_no_critical(self):
        """Test when no critical alerts present."""
        result = AlertEvaluationResult(
            triggered=True,
            events=(
                AlertTriggeredEvent(
                    alert_id="1",
                    threshold_type=AlertThresholdType.COST,
                    current_value=10.0,
                    threshold_value=5.0,
                    severity=AlertSeverity.WARNING,
                    message="Warning",
                ),
            ),
        )

        assert result.has_critical is False

    def test_has_error_or_higher(self):
        """Test checking for error or higher severity."""
        result = AlertEvaluationResult(
            triggered=True,
            events=(
                AlertTriggeredEvent(
                    alert_id="1",
                    threshold_type=AlertThresholdType.COST,
                    current_value=10.0,
                    threshold_value=5.0,
                    severity=AlertSeverity.ERROR,
                    message="Error",
                ),
            ),
        )

        assert result.has_error_or_higher is True

    def test_no_error_or_higher(self):
        """Test when no error or higher severity alerts."""
        result = AlertEvaluationResult(
            triggered=True,
            events=(
                AlertTriggeredEvent(
                    alert_id="1",
                    threshold_type=AlertThresholdType.COST,
                    current_value=10.0,
                    threshold_value=5.0,
                    severity=AlertSeverity.WARNING,
                    message="Warning",
                ),
            ),
        )

        assert result.has_error_or_higher is False


def test_create_budget_alert_service(alert_repository, usage_repository):
    """Test factory function."""
    service = create_budget_alert_service(
        repository=alert_repository,
        usage_repository=usage_repository,
    )

    assert service._repository == alert_repository
    assert service._usage_repository == usage_repository
    assert service._config.enabled is True


class TestBudgetAlertServiceConfig:
    """Tests for BudgetAlertServiceConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = BudgetAlertServiceConfig()

        assert config.enabled is True
        assert config.check_interval_seconds == 60
        assert config.batch_size == 1000
        assert config.max_concurrent_checks == 10
