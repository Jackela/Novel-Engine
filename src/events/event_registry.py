#!/usr/bin/env python3
"""
Event Registry for Type-Safe Event Management

This module provides a centralized registry for all event types in the Novel Engine,
ensuring type safety, documentation, and proper event versioning.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class EventType(Enum):
    """
    Centralized registry of all event types in the Novel Engine.

    Each event type represents a specific domain event that can occur
    in the system, enabling proper event-driven architecture.
    """

    # Character Events
    CHARACTER_CREATED = "character.created"
    CHARACTER_UPDATED = "character.updated"
    CHARACTER_DELETED = "character.deleted"
    CHARACTER_STATE_CHANGED = "character.state_changed"
    CHARACTER_MEMORY_ADDED = "character.memory_added"
    CHARACTER_EMOTION_CHANGED = "character.emotion_changed"
    CHARACTER_RELATIONSHIP_CHANGED = "character.relationship_changed"

    # Story Events
    STORY_STARTED = "story.started"
    STORY_UPDATED = "story.updated"
    STORY_COMPLETED = "story.completed"
    STORY_BRANCH_CREATED = "story.branch_created"
    STORY_CHOICE_MADE = "story.choice_made"
    STORY_CONTEXT_CHANGED = "story.context_changed"

    # Interaction Events
    INTERACTION_STARTED = "interaction.started"
    INTERACTION_COMPLETED = "interaction.completed"
    INTERACTION_FAILED = "interaction.failed"
    DIALOGUE_EXCHANGE = "interaction.dialogue_exchange"
    COMBAT_ACTION = "interaction.combat_action"
    SOCIAL_INTERACTION = "interaction.social"

    # Memory Events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DECAY = "memory.decay"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # Equipment Events
    EQUIPMENT_ACQUIRED = "equipment.acquired"
    EQUIPMENT_USED = "equipment.used"
    EQUIPMENT_DAMAGED = "equipment.damaged"
    EQUIPMENT_REPAIRED = "equipment.repaired"
    EQUIPMENT_LOST = "equipment.lost"

    # System Events
    SYSTEM_STARTED = "system.started"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    AGENT_REGISTERED = "system.agent_registered"
    AGENT_DEREGISTERED = "system.agent_deregistered"

    # Template Events
    TEMPLATE_RENDERED = "template.rendered"
    TEMPLATE_CACHED = "template.cached"
    TEMPLATE_UPDATED = "template.updated"

    # Performance Events
    PERFORMANCE_METRIC = "performance.metric"
    PERFORMANCE_THRESHOLD_EXCEEDED = "performance.threshold_exceeded"
    CACHE_HIT = "performance.cache_hit"
    CACHE_MISS = "performance.cache_miss"

    # Security Events
    AUTHENTICATION_SUCCESS = "security.auth_success"
    AUTHENTICATION_FAILURE = "security.auth_failure"
    AUTHORIZATION_DENIED = "security.auth_denied"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SECURITY_VIOLATION = "security.violation"


@dataclass
class EventSchema:
    """Schema definition for an event type."""

    event_type: EventType
    version: str
    description: str
    required_fields: Set[str]
    optional_fields: Set[str]
    payload_schema: Dict[str, Any]
    examples: List[Dict[str, Any]]
    deprecated: bool = False
    successor: Optional[EventType] = None


class EventRegistry:
    """
    Registry for managing event schemas and validation.

    Provides type-safe event creation, validation, and documentation.
    """

    def __init__(self):
        self._schemas: Dict[EventType, EventSchema] = {}
        self._initialize_schemas()

    def _initialize_schemas(self):
        """Initialize all event schemas."""

        # Character Events
        self.register_schema(
            EventSchema(
                event_type=EventType.CHARACTER_CREATED,
                version="1.0",
                description="Fired when a new character is created",
                required_fields={"character_id", "character_name"},
                optional_fields={"character_archetype", "traits", "metadata"},
                payload_schema={
                    "character_id": {
                        "type": "string",
                        "description": "Unique character identifier",
                    },
                    "character_name": {
                        "type": "string",
                        "description": "Character display name",
                    },
                    "character_archetype": {
                        "type": "string",
                        "description": "Character archetype",
                    },
                    "traits": {"type": "object", "description": "Character traits"},
                    "metadata": {
                        "type": "object",
                        "description": "Additional character metadata",
                    },
                },
                examples=[
                    {
                        "character_id": "char_123",
                        "character_name": "John Survivor",
                        "character_archetype": "SURVIVOR",
                        "traits": {"strength": 8, "intelligence": 6},
                    }
                ],
            )
        )

        self.register_schema(
            EventSchema(
                event_type=EventType.CHARACTER_STATE_CHANGED,
                version="1.0",
                description="Fired when character state changes",
                required_fields={"character_id", "old_state", "new_state"},
                optional_fields={"change_reason", "metadata"},
                payload_schema={
                    "character_id": {"type": "string"},
                    "old_state": {"type": "object"},
                    "new_state": {"type": "object"},
                    "change_reason": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                examples=[
                    {
                        "character_id": "char_123",
                        "old_state": {"health": 100, "status": "active"},
                        "new_state": {"health": 85, "status": "injured"},
                        "change_reason": "combat_damage",
                    }
                ],
            )
        )

        # Memory Events
        self.register_schema(
            EventSchema(
                event_type=EventType.MEMORY_STORED,
                version="1.0",
                description="Fired when a memory is stored",
                required_fields={"memory_id", "agent_id", "memory_type", "content"},
                optional_fields={"emotional_weight", "relevance_score", "tags"},
                payload_schema={
                    "memory_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "memory_type": {
                        "type": "string",
                        "enum": [
                            "working",
                            "episodic",
                            "semantic",
                            "emotional",
                            "relationship",
                        ],
                    },
                    "content": {"type": "string"},
                    "emotional_weight": {
                        "type": "number",
                        "minimum": -10,
                        "maximum": 10,
                    },
                    "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                examples=[
                    {
                        "memory_id": "mem_456",
                        "agent_id": "char_123",
                        "memory_type": "episodic",
                        "content": "Encountered a hostile faction at the trade post",
                        "emotional_weight": -3.5,
                        "relevance_score": 0.8,
                        "tags": ["combat", "faction_encounter"],
                    }
                ],
            )
        )

        # Interaction Events
        self.register_schema(
            EventSchema(
                event_type=EventType.INTERACTION_STARTED,
                version="1.0",
                description="Fired when an interaction begins",
                required_fields={"interaction_id", "interaction_type", "participants"},
                optional_fields={"context", "metadata"},
                payload_schema={
                    "interaction_id": {"type": "string"},
                    "interaction_type": {
                        "type": "string",
                        "enum": ["dialogue", "combat", "trade", "exploration"],
                    },
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "context": {"type": "object"},
                    "metadata": {"type": "object"},
                },
                examples=[
                    {
                        "interaction_id": "int_789",
                        "interaction_type": "dialogue",
                        "participants": ["char_123", "char_456"],
                        "context": {"location": "trade_post", "mood": "tense"},
                    }
                ],
            )
        )

        # System Events
        self.register_schema(
            EventSchema(
                event_type=EventType.SYSTEM_STARTED,
                version="1.0",
                description="Fired when the system starts up",
                required_fields={"startup_time", "version"},
                optional_fields={"configuration", "components"},
                payload_schema={
                    "startup_time": {"type": "string", "format": "date-time"},
                    "version": {"type": "string"},
                    "configuration": {"type": "object"},
                    "components": {"type": "array", "items": {"type": "string"}},
                },
                examples=[
                    {
                        "startup_time": "2024-01-01T12:00:00Z",
                        "version": "2.0.0",
                        "configuration": {"mode": "production"},
                        "components": [
                            "orchestrator",
                            "memory_system",
                            "interaction_engine",
                        ],
                    }
                ],
            )
        )

        # Performance Events
        self.register_schema(
            EventSchema(
                event_type=EventType.PERFORMANCE_METRIC,
                version="1.0",
                description="Fired when performance metrics are collected",
                required_fields={"metric_name", "value", "unit"},
                optional_fields={"component", "labels", "threshold"},
                payload_schema={
                    "metric_name": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "component": {"type": "string"},
                    "labels": {"type": "object"},
                    "threshold": {"type": "number"},
                },
                examples=[
                    {
                        "metric_name": "response_time",
                        "value": 150.5,
                        "unit": "milliseconds",
                        "component": "api_server",
                        "labels": {"endpoint": "/characters", "method": "GET"},
                    }
                ],
            )
        )

    def register_schema(self, schema: EventSchema):
        """Register an event schema."""
        self._schemas[schema.event_type] = schema

    def get_schema(self, event_type: EventType) -> Optional[EventSchema]:
        """Get schema for an event type."""
        return self._schemas.get(event_type)

    def validate_event_payload(
        self, event_type: EventType, payload: Dict[str, Any]
    ) -> bool:
        """
        Validate an event payload against its schema.

        Args:
            event_type: The event type to validate against
            payload: The event payload to validate

        Returns:
            True if valid, False otherwise
        """
        schema = self.get_schema(event_type)
        if not schema:
            return False

        # Check required fields
        missing_fields = schema.required_fields - set(payload.keys())
        if missing_fields:
            return False

        # Additional validation logic would go here
        # For now, we'll do basic presence checking
        return True

    def get_event_types_by_category(self, category: str) -> List[EventType]:
        """Get all event types for a specific category."""
        return [
            event_type
            for event_type in EventType
            if event_type.value.startswith(f"{category}.")
        ]

    def get_all_schemas(self) -> Dict[EventType, EventSchema]:
        """Get all registered schemas."""
        return self._schemas.copy()

    def get_schema_documentation(
        self, event_type: EventType
    ) -> Optional[Dict[str, Any]]:
        """Get human-readable documentation for an event schema."""
        schema = self.get_schema(event_type)
        if not schema:
            return None

        return {
            "event_type": event_type.value,
            "version": schema.version,
            "description": schema.description,
            "required_fields": list(schema.required_fields),
            "optional_fields": list(schema.optional_fields),
            "payload_schema": schema.payload_schema,
            "examples": schema.examples,
            "deprecated": schema.deprecated,
            "successor": schema.successor.value if schema.successor else None,
        }

    def generate_api_documentation(self) -> Dict[str, Any]:
        """Generate API documentation for all event types."""
        docs = {
            "version": "1.0",
            "description": "Novel Engine Event Types Documentation",
            "generated_at": datetime.now().isoformat(),
            "events": {},
        }

        for event_type in EventType:
            docs["events"][event_type.value] = self.get_schema_documentation(event_type)

        return docs
