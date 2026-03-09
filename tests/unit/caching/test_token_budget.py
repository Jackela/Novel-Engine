"""
Unit tests for TokenBudgetManager implementation.

Tests cover:
- Budget limit configuration
- Cost estimation
- Budget approval checking
- Operation recording
- Usage reporting
- Cost optimization
- Persistence
"""

import tempfile
from pathlib import Path

import pytest

from src.caching.token_budget import (
    BudgetLimit,
    BudgetPeriod,
    OperationType,
    TokenBudgetConfig,
    TokenBudgetManager,
    _compute_cost,
)

pytestmark = pytest.mark.unit


class TestBudgetPeriod:
    """Tests for BudgetPeriod enum."""

    def test_period_seconds(self) -> None:
        """Test period duration in seconds."""
        assert BudgetPeriod.HOURLY.seconds == 3600
        assert BudgetPeriod.DAILY.seconds == 86400
        assert BudgetPeriod.MONTHLY.seconds == 30 * 86400


class TestBudgetLimit:
    """Tests for BudgetLimit dataclass."""

    def test_budget_limit_creation(self) -> None:
        """Test creating budget limit."""
        limit = BudgetLimit(
            period=BudgetPeriod.DAILY,
            max_tokens=10000,
            max_cost=1.0,
            max_operations=100,
        )
        assert limit.period == BudgetPeriod.DAILY
        assert limit.max_tokens == 10000
        assert limit.max_cost == 1.0
        assert limit.max_operations == 100

    def test_budget_limit_optional_fields(self) -> None:
        """Test creating budget limit with optional fields."""
        limit = BudgetLimit(period=BudgetPeriod.HOURLY)
        assert limit.max_tokens is None
        assert limit.max_cost is None
        assert limit.max_operations is None


class TestTokenBudgetConfig:
    """Tests for TokenBudgetConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = TokenBudgetConfig()
        assert config.enable_persistence is True
        assert config.persistence_file is None
        assert config.enable_cache_integration is True
        assert config.enable_debug_logging is False

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = TokenBudgetConfig(
            enable_persistence=False,
            persistence_file=Path("/tmp/budget.json"),
            enable_cache_integration=False,
            enable_debug_logging=True,
        )
        assert config.enable_persistence is False
        assert config.persistence_file == Path("/tmp/budget.json")
        assert config.enable_cache_integration is False
        assert config.enable_debug_logging is True


class TestTokenBudgetManagerInit:
    """Tests for TokenBudgetManager initialization."""

    def test_init_default(self) -> None:
        """Test initialization with default config."""
        manager = TokenBudgetManager()
        assert manager.config.enable_persistence is True

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = TokenBudgetConfig(enable_persistence=False)
        manager = TokenBudgetManager(config)
        assert manager.config.enable_persistence is False


class TestAddBudgetLimit:
    """Tests for add_budget_limit method."""

    def test_add_single_limit(self) -> None:
        """Test adding a single budget limit."""
        manager = TokenBudgetManager()
        limit = BudgetLimit(period=BudgetPeriod.DAILY, max_tokens=1000)
        manager.add_budget_limit(limit)
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert len(report["limits"]) == 1

    def test_add_multiple_limits(self) -> None:
        """Test adding multiple budget limits."""
        manager = TokenBudgetManager()
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.HOURLY, max_tokens=100))
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.DAILY, max_cost=10.0))
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert len(report["limits"]) == 2


class TestEstimateOperationCost:
    """Tests for estimate_operation_cost method."""

    def test_estimate_basic(self) -> None:
        """Test basic cost estimation."""
        manager = TokenBudgetManager()
        result = manager.estimate_operation_cost(
            operation_type=OperationType.CHAT_COMPLETION,
            prompt_text="Hello world",
            model_name="gpt-3.5-turbo",
            completion_tokens_estimate=50,
        )
        assert result["operation_type"] == "chat_completion"
        assert result["model_name"] == "gpt-3.5-turbo"
        assert result["estimated_prompt_tokens"] > 0
        assert result["estimated_completion_tokens"] == 50
        assert "estimated_total_cost" in result
        assert "budget_check" in result

    def test_estimate_empty_prompt(self) -> None:
        """Test cost estimation with empty prompt."""
        manager = TokenBudgetManager()
        result = manager.estimate_operation_cost(
            operation_type=OperationType.EMBEDDING,
            prompt_text="",
            model_name="gpt-4o-mini",
            completion_tokens_estimate=0,
        )
        assert result["estimated_prompt_tokens"] == 1  # Minimum 1 token
        assert result["estimated_completion_tokens"] == 0

    def test_estimate_different_models(self) -> None:
        """Test cost estimation for different models."""
        manager = TokenBudgetManager()
        result_gpt35 = manager.estimate_operation_cost(
            operation_type=OperationType.CHAT_COMPLETION,
            prompt_text="Test prompt",
            model_name="gpt-3.5-turbo",
            completion_tokens_estimate=10,
        )
        result_fallback = manager.estimate_operation_cost(
            operation_type=OperationType.CHAT_COMPLETION,
            prompt_text="Test prompt",
            model_name="unknown-model",
            completion_tokens_estimate=10,
        )
        # Different models should have different costs
        assert result_gpt35["estimated_total_cost"] != result_fallback["estimated_total_cost"]


class TestCheckBudgetApproval:
    """Tests for check_budget_approval method."""

    def test_approval_within_budget(self) -> None:
        """Test approval when within budget."""
        manager = TokenBudgetManager()
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.DAILY, max_tokens=10000))
        result = manager.check_budget_approval(
            operation_type=OperationType.CHAT_COMPLETION,
            estimated_tokens=100,
            estimated_cost=0.01,
        )
        assert result["approved"] is True
        assert "Within configured limits" in result["reason"]

    def test_denial_over_budget(self) -> None:
        """Test denial when over budget."""
        manager = TokenBudgetManager()
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.DAILY, max_tokens=10))
        result = manager.check_budget_approval(
            operation_type=OperationType.CHAT_COMPLETION,
            estimated_tokens=100,
            estimated_cost=0.01,
        )
        assert result["approved"] is False
        assert "exceeds configured budget" in result["reason"]

    def test_denial_low_priority(self) -> None:
        """Test denial for low priority operation."""
        manager = TokenBudgetManager()
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.DAILY, max_tokens=10))
        result = manager.check_budget_approval(
            operation_type=OperationType.CHAT_COMPLETION,
            estimated_tokens=100,
            estimated_cost=0.01,
            priority="low",
        )
        assert result["approved"] is False
        assert "auto-denied for low priority" in result["reason"]

    def test_approval_no_limits(self) -> None:
        """Test approval when no limits configured."""
        manager = TokenBudgetManager()  # No limits added
        result = manager.check_budget_approval(
            operation_type=OperationType.CHAT_COMPLETION,
            estimated_tokens=1000000,
            estimated_cost=1000.0,
        )
        assert result["approved"] is True


class TestRecordOperation:
    """Tests for record_operation method."""

    def test_record_success(self) -> None:
        """Test successful operation recording."""
        manager = TokenBudgetManager()
        result = manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
        assert result is True
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert report["summary_metrics"]["total_operations"] == 1

    def test_record_denied_over_budget(self) -> None:
        """Test operation denied due to budget."""
        manager = TokenBudgetManager()
        manager.add_budget_limit(BudgetLimit(period=BudgetPeriod.DAILY, max_tokens=10))
        result = manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
        assert result is False

    def test_record_with_optional_fields(self) -> None:
        """Test recording with optional fields."""
        manager = TokenBudgetManager()
        manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.EMBEDDING,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=0,
            duration_ms=500,
            success=True,
            character_id="char1",
            operation_context="test context",
        )
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert report["summary_metrics"]["total_operations"] == 1


class TestGetUsageReport:
    """Tests for get_usage_report method."""

    def test_empty_report(self) -> None:
        """Test report with no operations."""
        manager = TokenBudgetManager()
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert report["period"] == "daily"
        assert report["summary_metrics"]["total_operations"] == 0
        assert report["summary_metrics"]["total_tokens"] == 0
        assert report["summary_metrics"]["total_cost"] == 0.0

    def test_report_with_operations(self) -> None:
        """Test report with recorded operations."""
        manager = TokenBudgetManager()
        manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
        manager.record_operation(
            operation_id="op2",
            operation_type=OperationType.EMBEDDING,
            model_name="gpt-3.5-turbo",
            prompt_tokens=200,
            completion_tokens=0,
            duration_ms=500,
            success=True,
        )
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert report["summary_metrics"]["total_operations"] == 2
        assert report["summary_metrics"]["total_tokens"] == 350
        assert report["operations"]["chat_completion"] == 1
        assert report["operations"]["embedding"] == 1

    def test_report_by_period(self) -> None:
        """Test report filtered by period."""
        manager = TokenBudgetManager()
        # Record old operation (would require mocking time for precise test)
        manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
        # Recent operation should be included
        report = manager.get_usage_report(BudgetPeriod.DAILY)
        assert report["summary_metrics"]["total_operations"] == 1


class TestOptimizeCosts:
    """Tests for optimize_costs method."""

    def test_optimize_empty_usage(self) -> None:
        """Test optimization with no usage data."""
        manager = TokenBudgetManager()
        result = manager.optimize_costs()
        assert len(result["recommendations"]) == 1
        assert "Enable caching" in result["recommendations"][0]

    def test_optimize_with_usage(self) -> None:
        """Test optimization with usage data."""
        manager = TokenBudgetManager()
        manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            duration_ms=1000,
            success=True,
        )
        result = manager.optimize_costs()
        assert len(result["recommendations"]) > 0
        assert any("Review usage" in rec for rec in result["recommendations"])


class TestPersistence:
    """Tests for persistence functionality."""

    def test_save_and_load(self) -> None:
        """Test saving and loading usage data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "budget.json"
            
            # Create and populate manager
            config = TokenBudgetConfig(persistence_file=file_path)
            manager1 = TokenBudgetManager(config)
            manager1.record_operation(
                operation_id="op1",
                operation_type=OperationType.CHAT_COMPLETION,
                model_name="gpt-3.5-turbo",
                prompt_tokens=100,
                completion_tokens=50,
                duration_ms=1000,
                success=True,
            )
            manager1.save_usage_data()
            
            # Load in new manager
            manager2 = TokenBudgetManager(config)
            report = manager2.get_usage_report(BudgetPeriod.DAILY)
            assert report["summary_metrics"]["total_operations"] == 1

    def test_save_without_file(self) -> None:
        """Test save without persistence file."""
        config = TokenBudgetConfig(persistence_file=None)
        manager = TokenBudgetManager(config)
        manager.record_operation(
            operation_id="op1",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
        manager.save_usage_data()  # Should not raise

    def test_save_disabled(self) -> None:
        """Test save when persistence is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "budget.json"
            config = TokenBudgetConfig(
                enable_persistence=False,
                persistence_file=file_path,
            )
            manager = TokenBudgetManager(config)
            manager.save_usage_data()  # Should not raise
            assert not file_path.exists()

    def test_load_missing_file(self) -> None:
        """Test loading with missing file."""
        config = TokenBudgetConfig(persistence_file=Path("/nonexistent/file.json"))
        manager = TokenBudgetManager(config)  # Should not raise
        assert manager.get_usage_report(BudgetPeriod.DAILY)["summary_metrics"]["total_operations"] == 0

    def test_load_invalid_json(self) -> None:
        """Test loading with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "budget.json"
            file_path.write_text("invalid json")
            config = TokenBudgetConfig(persistence_file=file_path)
            manager = TokenBudgetManager(config)  # Should not raise
            assert manager.get_usage_report(BudgetPeriod.DAILY)["summary_metrics"]["total_operations"] == 0


class TestComputeCost:
    """Tests for _compute_cost function."""

    def test_compute_cost_gpt35(self) -> None:
        """Test cost computation for gpt-3.5-turbo."""
        cost = _compute_cost("gpt-3.5-turbo", 1000, 500)
        assert cost > 0
        # Check approximate cost (should be around 0.0025 for 1000 prompt + 500 completion)

    def test_compute_cost_fallback(self) -> None:
        """Test cost computation for unknown model."""
        cost = _compute_cost("unknown-model", 1000, 0)
        assert cost > 0
        # Should use fallback pricing

    def test_compute_cost_case_insensitive(self) -> None:
        """Test that model name matching is case-insensitive."""
        cost_lower = _compute_cost("gpt-3.5-turbo", 1000, 0)
        cost_upper = _compute_cost("GPT-3.5-TURBO", 1000, 0)
        assert cost_lower == cost_upper
