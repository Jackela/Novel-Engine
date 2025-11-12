#!/usr/bin/env python3
"""
Bridge Types and Enums
=======================

Type definitions for Enhanced Multi-Agent Bridge components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
    batch_timeout_ms: int = 100
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    priority_boost_factor: float = 1.5
    cost_optimization: bool = True
    max_concurrent_requests: int = 10
    enable_fallback: bool = True
    fallback_timeout_ms: int = 5000


@dataclass
class BatchedRequest:
    """Represents a batched LLM request."""

    request_id: str
    agent_id: str
    request_type: str
    priority: RequestPriority
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    callback: Optional[callable] = None


@dataclass
class CoordinationMetrics:
    """Metrics for coordination system performance."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    batch_efficiency: float = 0.0
    cost_savings: float = 0.0
    active_dialogues: int = 0
