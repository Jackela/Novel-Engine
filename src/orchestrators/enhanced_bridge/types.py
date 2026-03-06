#!/usr/bin/env python3
"""
Enhanced Bridge Types
=====================

Core enums and type definitions for the Enhanced Multi-Agent Bridge.
"""

from enum import Enum

__all__ = [
    "RequestPriority",
    "CommunicationType",
    "DialogueState",
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
