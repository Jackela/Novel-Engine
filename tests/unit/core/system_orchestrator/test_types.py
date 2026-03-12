"""
Unit tests for system_orchestrator types module.

Tests cover:
- OrchestratorMode enum values and behavior
- SystemHealth enum values and behavior
- OrchestratorConfig dataclass creation and defaults
- SystemMetrics dataclass creation and defaults
- DatabaseInterface protocol compliance
"""

from datetime import datetime
from enum import Enum

import pytest

from src.core.system_orchestrator.types import (
    DatabaseInterface,
    OrchestratorConfig,
    OrchestratorMode,
    SystemHealth,
    SystemMetrics,
)

pytestmark = pytest.mark.unit


class TestOrchestratorMode:
    """Tests for OrchestratorMode enum."""

    def test_enum_values(self) -> None:
        """Test that all enum values are correctly defined."""
        assert OrchestratorMode.AUTONOMOUS.value == "autonomous"
        assert OrchestratorMode.INTERACTIVE.value == "interactive"
        assert OrchestratorMode.SIMULATION.value == "simulation"
        assert OrchestratorMode.DEVELOPMENT.value == "development"
        assert OrchestratorMode.PRODUCTION.value == "production"
        assert OrchestratorMode.TESTING.value == "testing"

    def test_enum_membership(self) -> None:
        """Test that all expected modes are present."""
        modes = list(OrchestratorMode)
        assert len(modes) == 6
        assert OrchestratorMode.AUTONOMOUS in modes
        assert OrchestratorMode.INTERACTIVE in modes
        assert OrchestratorMode.SIMULATION in modes
        assert OrchestratorMode.DEVELOPMENT in modes
        assert OrchestratorMode.PRODUCTION in modes
        assert OrchestratorMode.TESTING in modes

    def test_is_enum(self) -> None:
        """Test that OrchestratorMode is an Enum."""
        assert issubclass(OrchestratorMode, Enum)


class TestSystemHealth:
    """Tests for SystemHealth enum."""

    def test_enum_values(self) -> None:
        """Test that all enum values are correctly defined."""
        assert SystemHealth.OPTIMAL.value == "optimal"
        assert SystemHealth.DEGRADED.value == "degraded"
        assert SystemHealth.CRITICAL.value == "critical"
        assert SystemHealth.EMERGENCY.value == "emergency"
        assert SystemHealth.MAINTENANCE.value == "maintenance"

    def test_enum_membership(self) -> None:
        """Test that all expected health states are present."""
        states = list(SystemHealth)
        assert len(states) == 5
        assert SystemHealth.OPTIMAL in states
        assert SystemHealth.DEGRADED in states
        assert SystemHealth.CRITICAL in states
        assert SystemHealth.EMERGENCY in states
        assert SystemHealth.MAINTENANCE in states

    def test_is_enum(self) -> None:
        """Test that SystemHealth is an Enum."""
        assert issubclass(SystemHealth, Enum)


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig dataclass."""

    def test_default_creation(self) -> None:
        """Test creating config with default values."""
        config = OrchestratorConfig()
        assert config.mode == OrchestratorMode.AUTONOMOUS
        assert config.max_concurrent_agents == 10
        assert config.memory_cleanup_interval == 3600
        assert config.template_cache_size == 100
        assert config.interaction_queue_size == 50
        assert config.equipment_maintenance_interval == 1800
        assert config.relationship_decay_interval == 86400
        assert config.health_check_interval == 300
        assert config.auto_save_interval == 600
        assert config.debug_logging is False
        assert config.enable_metrics is True
        assert config.enable_auto_backup is True
        assert config.backup_interval == 7200
        assert config.max_memory_items_per_agent == 10000
        assert config.max_interaction_history == 1000
        assert config.enable_cross_system_validation is True
        assert config.performance_monitoring is True

    def test_custom_creation(self) -> None:
        """Test creating config with custom values."""
        config = OrchestratorConfig(
            mode=OrchestratorMode.TESTING,
            max_concurrent_agents=5,
            debug_logging=True,
            enable_metrics=False,
        )
        assert config.mode == OrchestratorMode.TESTING
        assert config.max_concurrent_agents == 5
        assert config.debug_logging is True
        assert config.enable_metrics is False
        # Other values should still be defaults
        assert config.memory_cleanup_interval == 3600

    def test_partial_custom_creation(self) -> None:
        """Test creating config with some custom values."""
        config = OrchestratorConfig(
            mode=OrchestratorMode.PRODUCTION,
            max_concurrent_agents=20,
        )
        assert config.mode == OrchestratorMode.PRODUCTION
        assert config.max_concurrent_agents == 20
        assert config.debug_logging is False  # default


class TestSystemMetrics:
    """Tests for SystemMetrics dataclass."""

    def test_default_creation(self) -> None:
        """Test creating metrics with default values."""
        metrics = SystemMetrics()
        assert metrics.active_agents == 0
        assert metrics.total_memory_items == 0
        assert metrics.active_interactions == 0
        assert metrics.template_cache_hits == 0.0
        assert metrics.average_response_time == 0.0
        assert metrics.system_health == SystemHealth.OPTIMAL
        assert metrics.database_connections == 0
        assert metrics.memory_usage_mb == 0.0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.last_backup is None
        assert metrics.uptime_seconds == 0
        assert metrics.operations_per_minute == 0.0
        assert metrics.relationship_count == 0
        assert metrics.equipment_count == 0
        # Timestamp should be close to now
        assert isinstance(metrics.timestamp, datetime)
        assert (datetime.now() - metrics.timestamp).total_seconds() < 1

    def test_custom_creation(self) -> None:
        """Test creating metrics with custom values."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        metrics = SystemMetrics(
            timestamp=custom_time,
            active_agents=5,
            total_memory_items=100,
            system_health=SystemHealth.DEGRADED,
            error_rate=0.05,
        )
        assert metrics.timestamp == custom_time
        assert metrics.active_agents == 5
        assert metrics.total_memory_items == 100
        assert metrics.system_health == SystemHealth.DEGRADED
        assert metrics.error_rate == 0.05

    def test_metrics_health_states(self) -> None:
        """Test metrics with different health states."""
        for health in SystemHealth:
            metrics = SystemMetrics(system_health=health)
            assert metrics.system_health == health


class TestDatabaseInterfaceProtocol:
    """Tests for DatabaseInterface protocol."""

    def test_protocol_exists(self) -> None:
        """Test that DatabaseInterface protocol is defined."""
        assert hasattr(DatabaseInterface, "initialize_standard_temple")
        assert hasattr(DatabaseInterface, "close_standard_temple")
        assert hasattr(DatabaseInterface, "health_check")
        assert hasattr(DatabaseInterface, "register_enhanced_agent")
        assert hasattr(DatabaseInterface, "get_enhanced_connection")

    def test_protocol_is_class(self) -> None:
        """Test that DatabaseInterface is a class (Protocol)."""
        assert isinstance(DatabaseInterface, type)
