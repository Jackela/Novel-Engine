"""
Routing Configuration Domain Models

Per-workspace and global routing configuration for model selection.
Supports configurable routing rules, preferences, and constraints.

Constitution Compliance:
- Article II (Hexagonal): Domain models independent of infrastructure
- Article I (DDD): Value objects for routing configuration

Warzone 4: AI Brain - BRAIN-028B
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from .model_registry import LLMProvider, TaskType

if TYPE_CHECKING:
    pass


class RoutingScope(str, Enum):
    """
    Scope of routing configuration.

    Why str enum:
        String-compatible enum allows JSON serialization.

    Scopes:
        GLOBAL: Applies to all workspaces
        WORKSPACE: Applies to a specific workspace
    """

    GLOBAL = "global"
    WORKSPACE = "workspace"

    def __str__(self) -> str:
        """Return string value of the scope."""
        return self.value


@dataclass(frozen=True, slots=True)
class TaskRoutingRule:
    """
    Routing rule for a specific task type.

    Why frozen:
        Routing rules should be immutable once defined.

    Attributes:
        task_type: The task type this rule applies to
        provider: Preferred provider for this task
        model_name: Preferred model name (empty = use provider default)
        temperature: Temperature override (None = use model default)
        max_tokens: Max tokens override (None = use model default)
        priority: Rule priority (higher = more important)
        enabled: Whether this rule is active
    """

    task_type: TaskType
    provider: LLMProvider
    model_name: str = ""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    priority: int = 0
    enabled: bool = True

    @property
    def qualified_model_name(self) -> str:
        """Get the fully qualified model name (provider:model_name)."""
        return f"{self.provider.value}:{self.model_name}" if self.model_name else self.provider.value


@dataclass(frozen=True, slots=True)
class RoutingConstraints:
    """
    Constraints for model routing decisions.

    Why frozen:
        Constraints should be immutable once defined.

    Attributes:
        max_cost_per_1m_tokens: Maximum cost for routing (USD)
        max_latency_ms: Maximum acceptable latency
        preferred_providers: Provider preference order
        blocked_providers: Providers to never use
        require_capabilities: Required capabilities (functions, vision, streaming)
    """

    max_cost_per_1m_tokens: Optional[float] = None
    max_latency_ms: Optional[int] = None
    preferred_providers: tuple[LLMProvider, ...] = ()
    blocked_providers: tuple[LLMProvider, ...] = ()
    require_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CircuitBreakerRule:
    """
    Circuit breaker configuration for a specific model.

    Why frozen:
        Circuit breaker rules should be immutable once defined.

    Attributes:
        model_key: Model identifier (provider:model)
        failure_threshold: Failures before opening circuit
        timeout_seconds: Seconds before half-open state
        enabled: Whether circuit breaker is enabled
    """

    model_key: str
    failure_threshold: int = 5
    timeout_seconds: int = 60
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class WorkspaceRoutingConfig:
    """
    Complete routing configuration for a workspace.

    Why frozen dataclass with timestamp:
        Configuration snapshots are immutable for audit trail.
        Use create_updated() for modifications.

    Attributes:
        workspace_id: Workspace identifier (empty for global config)
        scope: Configuration scope (global or workspace)
        task_rules: Routing rules per task type
        constraints: General routing constraints
        circuit_breaker_rules: Circuit breaker settings per model
        enable_circuit_breaker: Whether circuit breaker is enabled
        enable_fallback: Whether fallback chain is enabled
        created_at: When this configuration was created
        updated_at: When this configuration was last updated
        version: Configuration version number
    """

    workspace_id: str
    scope: RoutingScope
    task_rules: tuple[TaskRoutingRule, ...] = ()
    constraints: Optional[RoutingConstraints] = None
    circuit_breaker_rules: tuple[CircuitBreakerRule, ...] = ()
    enable_circuit_breaker: bool = True
    enable_fallback: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1

    def get_rule_for_task(self, task_type: TaskType) -> Optional[TaskRoutingRule]:
        """
        Get the highest priority enabled rule for a task type.

        Args:
            task_type: The task type to find a rule for

        Returns:
            The highest priority rule, or None if no enabled rule exists
        """
        enabled_rules = [r for r in self.task_rules if r.task_type == task_type and r.enabled]
        if not enabled_rules:
            return None
        return max(enabled_rules, key=lambda r: r.priority)

    def get_circuit_breaker_rule(self, model_key: str) -> Optional[CircuitBreakerRule]:
        """
        Get circuit breaker rule for a specific model.

        Args:
            model_key: Model identifier (provider:model)

        Returns:
            Circuit breaker rule, or None if not configured
        """
        for rule in self.circuit_breaker_rules:
            if rule.model_key == model_key and rule.enabled:
                return rule
        return None

    def create_updated(
        self,
        task_rules: Optional[tuple[TaskRoutingRule, ...]] = None,
        constraints: Optional[RoutingConstraints] = None,
        circuit_breaker_rules: Optional[tuple[CircuitBreakerRule, ...]] = None,
        enable_circuit_breaker: Optional[bool] = None,
        enable_fallback: Optional[bool] = None,
    ) -> "WorkspaceRoutingConfig":
        """
        Create an updated version of this configuration.

        Why:
            Immutable updates create audit trail and prevent accidental modification.

        Args:
            task_rules: New task rules (or keep existing)
            constraints: New constraints (or keep existing)
            circuit_breaker_rules: New circuit breaker rules (or keep existing)
            enable_circuit_breaker: New circuit breaker setting
            enable_fallback: New fallback setting

        Returns:
            New WorkspaceRoutingConfig with updated version
        """
        return WorkspaceRoutingConfig(
            workspace_id=self.workspace_id,
            scope=self.scope,
            task_rules=task_rules if task_rules is not None else self.task_rules,
            constraints=constraints if constraints is not None else self.constraints,
            circuit_breaker_rules=circuit_breaker_rules if circuit_breaker_rules is not None else self.circuit_breaker_rules,
            enable_circuit_breaker=enable_circuit_breaker if enable_circuit_breaker is not None else self.enable_circuit_breaker,
            enable_fallback=enable_fallback if enable_fallback is not None else self.enable_fallback,
            created_at=self.created_at,
            updated_at=datetime.now(),
            version=self.version + 1,
        )

    @classmethod
    def create_global(cls) -> "WorkspaceRoutingConfig":
        """Create a new global routing configuration with defaults."""
        return cls(
            workspace_id="",
            scope=RoutingScope.GLOBAL,
            task_rules=(
                TaskRoutingRule(TaskType.CREATIVE, LLMProvider.GEMINI, "gemini-2.0-flash", temperature=0.9, max_tokens=2000, priority=0),
                TaskRoutingRule(TaskType.LOGICAL, LLMProvider.OPENAI, "gpt-4o", temperature=0.2, max_tokens=4000, priority=0),
                TaskRoutingRule(TaskType.FAST, LLMProvider.GEMINI, "gemini-2.0-flash", temperature=0.5, max_tokens=1000, priority=0),
                TaskRoutingRule(TaskType.CHEAP, LLMProvider.GEMINI, "gemini-2.0-flash", temperature=0.7, max_tokens=1000, priority=0),
            ),
            constraints=RoutingConstraints(),
            enable_circuit_breaker=True,
            enable_fallback=True,
        )

    @classmethod
    def create_workspace(cls, workspace_id: str) -> "WorkspaceRoutingConfig":
        """Create a new workspace routing configuration (inherits from global)."""
        return cls(
            workspace_id=workspace_id,
            scope=RoutingScope.WORKSPACE,
            task_rules=(),  # Empty means inherit from global
            constraints=None,  # None means inherit from global
            enable_circuit_breaker=True,
            enable_fallback=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "workspace_id": self.workspace_id,
            "scope": self.scope.value,
            "task_rules": [
                {
                    "task_type": r.task_type.value,
                    "provider": r.provider.value,
                    "model_name": r.model_name,
                    "temperature": r.temperature,
                    "max_tokens": r.max_tokens,
                    "priority": r.priority,
                    "enabled": r.enabled,
                }
                for r in self.task_rules
            ],
            "constraints": (
                {
                    "max_cost_per_1m_tokens": self.constraints.max_cost_per_1m_tokens,
                    "max_latency_ms": self.constraints.max_latency_ms,
                    "preferred_providers": [p.value for p in self.constraints.preferred_providers],
                    "blocked_providers": [p.value for p in self.constraints.blocked_providers],
                    "require_capabilities": list(self.constraints.require_capabilities),
                }
                if self.constraints
                else None
            ),
            "circuit_breaker_rules": [
                {
                    "model_key": r.model_key,
                    "failure_threshold": r.failure_threshold,
                    "timeout_seconds": r.timeout_seconds,
                    "enabled": r.enabled,
                }
                for r in self.circuit_breaker_rules
            ],
            "enable_circuit_breaker": self.enable_circuit_breaker,
            "enable_fallback": self.enable_fallback,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }


__all__ = [
    "RoutingScope",
    "TaskRoutingRule",
    "RoutingConstraints",
    "CircuitBreakerRule",
    "WorkspaceRoutingConfig",
]
