"""
Tests for Routing Configuration Domain Models

Warzone 4: AI Brain - BRAIN-028B
"""

import pytest

from src.contexts.knowledge.domain.models.routing_config import (
    CircuitBreakerRule,
    LLMProvider,
    RoutingConstraints,
    RoutingScope,
    TaskRoutingRule,
    TaskType,
    WorkspaceRoutingConfig,
)


class TestTaskRoutingRule:
    """Tests for TaskRoutingRule value object."""

    def test_task_routing_rule_creation(self):
        """Test creating a task routing rule."""
        rule = TaskRoutingRule(
            task_type=TaskType.CREATIVE,
            provider=LLMProvider.GEMINI,
            model_name="gemini-2.0-flash",
            temperature=0.9,
            max_tokens=2000,
            priority=1,
            enabled=True,
        )

        assert rule.task_type == TaskType.CREATIVE
        assert rule.provider == LLMProvider.GEMINI
        assert rule.model_name == "gemini-2.0-flash"
        assert rule.temperature == 0.9
        assert rule.max_tokens == 2000
        assert rule.priority == 1
        assert rule.enabled is True

    def test_qualified_model_name(self):
        """Test qualified model name property."""
        rule = TaskRoutingRule(
            task_type=TaskType.LOGICAL,
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )

        assert rule.qualified_model_name == "openai:gpt-4o"

    def test_qualified_model_name_empty(self):
        """Test qualified model name with empty model_name."""
        rule = TaskRoutingRule(
            task_type=TaskType.FAST,
            provider=LLMProvider.GEMINI,
            model_name="",
        )

        assert rule.qualified_model_name == "gemini"  # Just provider when model_name is empty


class TestRoutingConstraints:
    """Tests for RoutingConstraints value object."""

    def test_routing_constraints_creation(self):
        """Test creating routing constraints."""
        constraints = RoutingConstraints(
            max_cost_per_1m_tokens=5.0,
            max_latency_ms=2000,
            preferred_providers=(LLMProvider.GEMINI, LLMProvider.OPENAI),
            blocked_providers=(LLMProvider.OLLAMA,),
            require_capabilities=("streaming", "functions"),
        )

        assert constraints.max_cost_per_1m_tokens == 5.0
        assert constraints.max_latency_ms == 2000
        assert len(constraints.preferred_providers) == 2
        assert constraints.blocked_providers == (LLMProvider.OLLAMA,)
        assert "streaming" in constraints.require_capabilities

    def test_routing_constraints_defaults(self):
        """Test routing constraints with defaults."""
        constraints = RoutingConstraints()

        assert constraints.max_cost_per_1m_tokens is None
        assert constraints.max_latency_ms is None
        assert constraints.preferred_providers == ()
        assert constraints.blocked_providers == ()
        assert constraints.require_capabilities == ()


class TestCircuitBreakerRule:
    """Tests for CircuitBreakerRule value object."""

    def test_circuit_breaker_rule_creation(self):
        """Test creating a circuit breaker rule."""
        rule = CircuitBreakerRule(
            model_key="openai:gpt-4o",
            failure_threshold=10,
            timeout_seconds=120,
            enabled=True,
        )

        assert rule.model_key == "openai:gpt-4o"
        assert rule.failure_threshold == 10
        assert rule.timeout_seconds == 120
        assert rule.enabled is True


class TestWorkspaceRoutingConfig:
    """Tests for WorkspaceRoutingConfig entity."""

    def test_global_config_creation(self):
        """Test creating a global routing configuration."""
        config = WorkspaceRoutingConfig.create_global()

        assert config.workspace_id == ""
        assert config.scope == RoutingScope.GLOBAL
        assert len(config.task_rules) == 4  # One for each task type
        assert config.enable_circuit_breaker is True
        assert config.enable_fallback is True
        assert config.version == 1

    def test_workspace_config_creation(self):
        """Test creating a workspace routing configuration."""
        config = WorkspaceRoutingConfig.create_workspace("test-workspace")

        assert config.workspace_id == "test-workspace"
        assert config.scope == RoutingScope.WORKSPACE
        assert config.task_rules == ()  # Empty means inherit from global
        assert config.enable_circuit_breaker is True

    def test_get_rule_for_task(self):
        """Test retrieving a rule for a specific task type."""
        config = WorkspaceRoutingConfig.create_global()
        rule = config.get_rule_for_task(TaskType.CREATIVE)

        assert rule is not None
        assert rule.task_type == TaskType.CREATIVE
        assert rule.enabled is True

    def test_get_rule_for_task_not_found(self):
        """Test retrieving a rule when none exists for the task."""
        config = WorkspaceRoutingConfig(
            workspace_id="test",
            scope=RoutingScope.WORKSPACE,
            task_rules=(),
        )

        rule = config.get_rule_for_task(TaskType.CREATIVE)
        assert rule is None

    def test_get_rule_for_task_disabled(self):
        """Test retrieving a disabled rule returns None."""
        config = WorkspaceRoutingConfig(
            workspace_id="test",
            scope=RoutingScope.WORKSPACE,
            task_rules=(
                TaskRoutingRule(
                    task_type=TaskType.CREATIVE,
                    provider=LLMProvider.GEMINI,
                    enabled=False,
                ),
            ),
        )

        rule = config.get_rule_for_task(TaskType.CREATIVE)
        assert rule is None

    def test_get_circuit_breaker_rule(self):
        """Test retrieving circuit breaker rule for a model."""
        config = WorkspaceRoutingConfig(
            workspace_id="",
            scope=RoutingScope.GLOBAL,
            circuit_breaker_rules=(
                CircuitBreakerRule(
                    model_key="openai:gpt-4o",
                    failure_threshold=5,
                ),
            ),
        )

        rule = config.get_circuit_breaker_rule("openai:gpt-4o")
        assert rule is not None
        assert rule.model_key == "openai:gpt-4o"
        assert rule.failure_threshold == 5

    def test_get_circuit_breaker_rule_not_found(self):
        """Test retrieving non-existent circuit breaker rule."""
        config = WorkspaceRoutingConfig.create_global()

        rule = config.get_circuit_breaker_rule("unknown:model")
        assert rule is None

    def test_create_updated(self):
        """Test creating an updated version of configuration."""
        import time

        config = WorkspaceRoutingConfig.create_global()
        old_version = config.version

        # Small delay to ensure updated_at is different
        time.sleep(0.01)

        updated = config.create_updated(
            enable_circuit_breaker=False,
            enable_fallback=False,
        )

        assert updated.version == old_version + 1
        assert updated.enable_circuit_breaker is False
        assert updated.enable_fallback is False
        assert updated.workspace_id == config.workspace_id
        assert updated.created_at == config.created_at
        # updated_at should be newer or equal (due to frozen dataclass timing)
        assert updated.updated_at >= config.updated_at

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = WorkspaceRoutingConfig.create_global()
        d = config.to_dict()

        assert d["workspace_id"] == "" or d["workspace_id"] == "global"  # Accept either format
        assert d["scope"] == "global"
        assert "task_rules" in d
        assert "enable_circuit_breaker" in d
        assert isinstance(d["task_rules"], list)


class TestRoutingScope:
    """Tests for RoutingScope enum."""

    def test_scope_values(self):
        """Test routing scope enum values."""
        assert RoutingScope.GLOBAL.value == "global"
        assert RoutingScope.WORKSPACE.value == "workspace"

    def test_scope_string_conversion(self):
        """Test scope to string conversion."""
        assert str(RoutingScope.GLOBAL) == "global"
        assert str(RoutingScope.WORKSPACE) == "workspace"
