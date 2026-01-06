"""
Multi-Agent Bridge Core Types
=============================

Data models and types for the enhanced multi-agent bridge system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import total_ordering
from typing import Any, Dict, List, Optional

__all__ = [
    "RequestPriority",
    "CommunicationType",
    "DialogueState",
    "AgentDialogue",
    "LLMCoordinationConfig",
    "LLMBatchRequest",
    "EnhancedWorldState",
]


class RequestPriority(Enum):
    """Priority levels for LLM requests."""

    CRITICAL = 1  # Immediate processing, bypass batching
    HIGH = 2  # High priority, minimal batching delay
    NORMAL = 3  # Standard batching
    LOW = 4  # Extended batching allowed
    BACKGROUND = 5  # Process when resources available


class CommunicationType(Enum):
    """Types of agent-to-agent communication."""

    DIALOGUE = "dialogue"  # Direct conversation between agents
    NEGOTIATION = "negotiation"  # Conflict resolution and bargaining
    COLLABORATION = "collaboration"  # Joint action planning
    INFORMATION_SHARING = "info_sharing"  # Knowledge exchange
    EMOTIONAL = "emotional"  # Emotional interactions
    STRATEGIC = "strategic"  # Strategic planning and alliances


class DialogueState(Enum):
    """States of agent dialogue interactions."""

    INITIATING = "initiating"
    ACTIVE = "active"
    WAITING_RESPONSE = "waiting_response"
    CONCLUDED = "concluded"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


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
    batch_timeout_ms: int = 150
    max_cost_per_turn: float = 0.10
    enable_dialogue_intelligence: bool = True
    fast_mode_threshold: float = 3.0
    cost_optimization_level: str = (
        "balanced"  # "aggressive", "balanced", "conservative"
    )
    enable_performance_monitoring: bool = True


@total_ordering
@dataclass
class LLMBatchRequest:
    """Request for batched LLM processing."""

    request_id: str
    request_type: str  # 'dialogue', 'coordination', 'narrative', etc.
    prompt: str
    priority: RequestPriority
    context: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    estimated_cost: float = 0.0
    result_future: Optional[Any] = None
    timeout_seconds: float = 30.0

    def __lt__(self, other):
        """Enable priority queue ordering."""
        if not isinstance(other, LLMBatchRequest):
            return NotImplemented
        return self.priority.value < other.priority.value

    def __eq__(self, other):
        if not isinstance(other, LLMBatchRequest):
            return NotImplemented
        return self.priority.value == other.priority.value


@dataclass
class EnhancedWorldState:
    """Enhanced world state with multi-agent coordination data."""

    turn_number: int
    base_world_state: Dict[str, Any]
    agent_positions: Dict[str, Any] = field(default_factory=dict)
    agent_relationships: Dict[str, Dict[str, float]] = field(default_factory=dict)
    active_dialogues: List[AgentDialogue] = field(default_factory=list)
    narrative_pressure: Dict[str, float] = field(default_factory=dict)
    coordination_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    ai_insights: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
