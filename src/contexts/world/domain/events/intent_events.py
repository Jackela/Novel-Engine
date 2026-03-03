#!/usr/bin/env python3
"""
Faction Intent Domain Events

This module contains domain events specifically for faction intent operations.
These events provide detailed information about intent generation and selection
for AI-driven faction decision-making.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from src.events.event_bus import Event, EventPriority

logger = structlog.get_logger()


@dataclass
class IntentGeneratedEvent(Event):
    """
    Domain event emitted when faction intents are generated.

    This event signals that the AI decision service has generated a set of
    intent options for a faction. It includes metadata about whether the
    generation was via LLM or fallback rules.

    Attributes:
        faction_id: ID of the faction for which intents were generated
        intent_ids: List of generated intent IDs (max 3)
        fallback: True if fallback rule-based generation was used
        context_summary: Brief summary of decision context (resources, diplomacy)
        generation_method: Method used ('llm' or 'fallback')
        rag_enriched: True if RAG context enrichment was successful (Issue 7)

    Example:
        >>> event = IntentGeneratedEvent(
        ...     faction_id="north-kingdom",
        ...     intent_ids=["intent-1", "intent-2", "intent-3"],
        ...     fallback=False,
        ...     context_summary="food=30, gold=500, enemies=1"
        ... )
    """

    # Override base event fields
    event_type: str = field(default="faction.intent_generated", init=False)
    source: str = field(default="faction_decision_service")
    priority: EventPriority = field(default=EventPriority.NORMAL, init=False)

    # Intent-specific event data
    faction_id: str = ""
    intent_ids: List[str] = field(default_factory=list)
    fallback: bool = False
    context_summary: str = ""
    generation_method: str = "llm"
    rag_enriched: bool = False  # Issue 7: Track RAG enrichment status

    def __post_init__(self) -> None:
        """Initialize event with intent-specific metadata and validation."""
        # Set timestamp if not provided
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

        # Generate event ID if not provided
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        # Add intent-specific tags
        self.tags.update({
            "context:world",
            "event:intent_generated",
            f"faction:{self.faction_id}",
            f"method:{self.generation_method}",
        })
        if self.fallback:
            self.tags.add("fallback:True")

        # Set event payload with intent data
        self.payload.update({
            "faction_id": self.faction_id,
            "intent_ids": self.intent_ids,
            "fallback": self.fallback,
            "context_summary": self.context_summary,
            "generation_method": self.generation_method,
            "rag_enriched": self.rag_enriched,
        })

        # Call parent post_init
        super().__post_init__()

        # Validate event data
        self._validate_intent_event()

    def _validate_intent_event(self) -> None:
        """
        Validate intent event data.

        Raises:
            ValueError: If event data is invalid
        """
        errors = []

        # Validate faction_id
        if not self.faction_id:
            errors.append("faction_id is required")

        # Validate intent_ids
        if not self.intent_ids:
            errors.append("intent_ids cannot be empty")
        elif len(self.intent_ids) > 3:
            errors.append(f"intent_ids cannot exceed 3, got {len(self.intent_ids)}")

        # Validate generation_method
        valid_methods = {"llm", "fallback"}
        if self.generation_method not in valid_methods:
            errors.append(
                f"generation_method must be one of {valid_methods}, "
                f"got {self.generation_method}"
            )

        if errors:
            logger.warning(
                "intent_event_validation_failed",
                event_id=self.event_id,
                errors=errors,
                faction_id=self.faction_id,
                intent_count=len(self.intent_ids),
            )
            raise ValueError(
                f"IntentGeneratedEvent validation failed: {'; '.join(errors)}"
            )

    @classmethod
    def create(
        cls,
        faction_id: str,
        intent_ids: List[str],
        fallback: bool = False,
        context_summary: str = "",
        source: str = "faction_decision_service",
    ) -> "IntentGeneratedEvent":
        """
        Factory method to create an IntentGeneratedEvent with validation.

        Args:
            faction_id: ID of the faction
            intent_ids: List of generated intent IDs
            fallback: Whether fallback rules were used
            context_summary: Summary of decision context
            source: Event source identifier

        Returns:
            IntentGeneratedEvent instance

        Example:
            >>> event = IntentGeneratedEvent.create(
            ...     faction_id="north-kingdom",
            ...     intent_ids=["intent-1", "intent-2"],
            ...     fallback=False,
            ...     context_summary="Low food, high gold"
            ... )
        """
        generation_method = "fallback" if fallback else "llm"

        event = cls(
            faction_id=faction_id,
            intent_ids=intent_ids,
            fallback=fallback,
            context_summary=context_summary,
            generation_method=generation_method,
            source=source,
        )

        return event

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the intent generation.

        Returns:
            String summary of the event
        """
        method = "fallback rules" if self.fallback else "LLM"
        return (
            f"Generated {len(self.intent_ids)} intents for {self.faction_id} "
            f"via {method}. Context: {self.context_summary or 'N/A'}"
        )


@dataclass
class IntentSelectedEvent(Event):
    """
    Domain event emitted when a faction intent is selected for execution.

    This event signals that a specific intent has been chosen from the
    generated options and will be executed during the simulation tick.

    Attributes:
        faction_id: ID of the faction
        intent_id: ID of the selected intent
        action_type: Type of action (EXPAND, ATTACK, etc.)
        target_id: ID of the target (if applicable)

    Example:
        >>> event = IntentSelectedEvent(
        ...     faction_id="north-kingdom",
        ...     intent_id="intent-2",
        ...     action_type="TRADE",
        ...     target_id="merchant-guild"
        ... )
    """

    # Override base event fields
    event_type: str = field(default="faction.intent_selected", init=False)
    source: str = field(default="faction_decision_service")
    priority: EventPriority = field(default=EventPriority.HIGH, init=False)

    # Selection-specific event data
    faction_id: str = ""
    intent_id: str = ""
    action_type: str = ""
    target_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize event with selection-specific metadata and validation."""
        # Set timestamp if not provided
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

        # Generate event ID if not provided
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        # Add selection-specific tags
        self.tags.update({
            "context:world",
            "event:intent_selected",
            f"faction:{self.faction_id}",
            f"action:{self.action_type}",
        })

        # Set event payload
        self.payload.update({
            "faction_id": self.faction_id,
            "intent_id": self.intent_id,
            "action_type": self.action_type,
            "target_id": self.target_id,
        })

        # Call parent post_init
        super().__post_init__()

        # Validate event data
        self._validate_selection_event()

    def _validate_selection_event(self) -> None:
        """Validate selection event data."""
        errors = []

        if not self.faction_id:
            errors.append("faction_id is required")
        if not self.intent_id:
            errors.append("intent_id is required")
        if not self.action_type:
            errors.append("action_type is required")

        if errors:
            logger.warning(
                "intent_selection_event_validation_failed",
                event_id=self.event_id,
                errors=errors,
            )
            raise ValueError(
                f"IntentSelectedEvent validation failed: {'; '.join(errors)}"
            )

    @classmethod
    def create(
        cls,
        faction_id: str,
        intent_id: str,
        action_type: str,
        target_id: Optional[str] = None,
        source: str = "faction_decision_service",
    ) -> "IntentSelectedEvent":
        """Factory method to create an IntentSelectedEvent."""
        return cls(
            faction_id=faction_id,
            intent_id=intent_id,
            action_type=action_type,
            target_id=target_id,
            source=source,
        )

    def get_summary(self) -> str:
        """Get a human-readable summary."""
        target = f" -> {self.target_id}" if self.target_id else ""
        return f"{self.faction_id} selected {self.action_type}{target}"
