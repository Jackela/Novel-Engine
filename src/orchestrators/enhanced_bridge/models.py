#!/usr/bin/env python3
"""
Enhanced Bridge Models
======================

Dataclasses and models for the Enhanced Multi-Agent Bridge.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import Any, Callable, Dict, List, Optional

from .types import CommunicationType, DialogueState, RequestPriority

__all__ = [
    "AgentDialogue",
    "LLMCoordinationConfig",
    "LLMBatchRequest",
    "CostTracker",
    "PerformanceBudget",
    "EnhancedWorldState",
    "BridgeConfiguration",
]


@dataclass
class AgentDialogue:
    """Represents an active dialogue between agents."""

    dialogue_id: str
    communication_type: CommunicationType
    participants: List[str]
    initiator: str
    state: DialogueState
    created_at: datetime = field(default_factory=datetime.now)
    max_exchanges: int = 3
    current_exchange: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    resolution: Optional[Dict[str, Any]] = None


@dataclass
class LLMCoordinationConfig:
    """Configuration for LLM-powered smart coordination."""

    enable_smart_batching: bool = True
    max_batch_size: int = 5
    batch_timeout_ms: int = 2000
    priority_queue_enabled: bool = True
    cost_tracking_enabled: bool = True
    max_parallel_llm_calls: int = 3
    dialogue_generation_budget: float = 2.0  # USD per hour
    coordination_temperature: float = 0.8
    max_turn_time_seconds: float = 5.0  # Performance budget
    batch_priority_threshold: float = 0.7  # High priority requests bypass batching
    cost_alert_threshold: float = 0.8  # Alert when 80% of budget used


@total_ordering
@dataclass
class LLMBatchRequest:
    """Represents a batched LLM request."""

    request_id: str
    priority: RequestPriority
    request_type: str  # 'dialogue', 'coordination', 'analysis'
    prompt: str
    context: Dict[str, Any]
    created_at: float
    callback: Optional[Callable[..., Any]] = None
    timeout_seconds: float = 5.0
    estimated_cost: float = 0.0
    tokens_estimate: int = 0

    def __lt__(self, other: Any) -> bool:
        """For priority queue ordering."""
        if not isinstance(other, LLMBatchRequest):
            return NotImplemented
        return (self.priority.value, self.created_at) < (
            other.priority.value,
            other.created_at,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, LLMBatchRequest):
            return False
        return (self.priority.value, self.created_at) == (
            other.priority.value,
            other.created_at,
        )


@dataclass
class CostTracker:
    """Tracks LLM usage costs and budgets."""

    hourly_budget: float
    daily_budget: float
    current_hour_spend: float = 0.0
    current_day_spend: float = 0.0
    last_reset_hour: int = field(default_factory=lambda: datetime.now().hour)
    last_reset_day: int = field(default_factory=lambda: datetime.now().day)
    total_requests: int = 0
    total_tokens: int = 0
    average_cost_per_request: float = 0.0
    cost_by_request_type: Dict[str, float] = field(default_factory=dict)

    def update_cost(self, request_type: str, cost: float, tokens: int) -> bool:
        """Update cost tracking. Returns True if within budget."""
        current_time = datetime.now()

        # Reset hourly tracking if needed
        if current_time.hour != self.last_reset_hour:
            self.current_hour_spend = 0.0
            self.last_reset_hour = current_time.hour

        # Reset daily tracking if needed
        if current_time.day != self.last_reset_day:
            self.current_day_spend = 0.0
            self.last_reset_day = current_time.day

        # Update totals
        self.current_hour_spend += cost
        self.current_day_spend += cost
        self.total_requests += 1
        self.total_tokens += tokens

        # Update averages
        self.average_cost_per_request = self.current_day_spend / max(
            1, self.total_requests
        )

        # Update by request type
        if request_type not in self.cost_by_request_type:
            self.cost_by_request_type[request_type] = 0.0
        self.cost_by_request_type[request_type] += cost

        # Check budget compliance
        return (
            self.current_hour_spend <= self.hourly_budget
            and self.current_day_spend <= self.daily_budget
        )


@dataclass
class PerformanceBudget:
    """Tracks performance budgets and timing."""

    max_turn_time: float
    max_batch_time: float = 2.0
    max_llm_call_time: float = 1.5
    turn_start_time: Optional[float] = None
    batch_timings: List[float] = field(default_factory=list)
    llm_call_timings: List[float] = field(default_factory=list)
    budget_violations: int = 0

    def start_turn(self) -> None:
        """Start turn timing."""
        self.turn_start_time = time.time()

    def get_remaining_time(self) -> float:
        """Get remaining time in current turn."""
        if self.turn_start_time is None:
            return self.max_turn_time
        elapsed = time.time() - self.turn_start_time
        return max(0, self.max_turn_time - elapsed)

    def is_budget_exceeded(self) -> bool:
        """Check if time budget is exceeded."""
        return self.get_remaining_time() <= 0

    def record_batch_time(self, duration: float) -> None:
        """Record batch processing time."""
        self.batch_timings.append(duration)
        if duration > self.max_batch_time:
            self.budget_violations += 1

    def record_llm_time(self, duration: float) -> None:
        """Record LLM call time."""
        self.llm_call_timings.append(duration)
        if duration > self.max_llm_call_time:
            self.budget_violations += 1


@dataclass
class EnhancedWorldState:
    """Enhanced world state with AI intelligence integration."""

    turn_number: int
    simulation_time: str
    base_world_state: Dict[str, Any]
    agent_relationships: Dict[str, Dict[str, float]]
    active_dialogues: List[AgentDialogue]
    narrative_pressure: Dict[str, float]
    story_goals: Dict[str, Any]
    ai_insights: List[Dict[str, Any]]
    coordination_status: Dict[str, Any]
    llm_coordination_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeConfiguration:
    """Test-facing bridge configuration wrapper."""

    enable_advanced_coordination: bool = True
    enable_smart_batching: bool = True
    enable_dialogue_system: bool = True
    enable_performance_monitoring: bool = True
    max_concurrent_agents: int = 20
    turn_timeout_seconds: int = 30
    llm_coordination: LLMCoordinationConfig = field(
        default_factory=LLMCoordinationConfig
    )
