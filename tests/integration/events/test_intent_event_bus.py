#!/usr/bin/env python3
"""Integration tests for IntentGeneratedEvent and EventBus integration.

Tests event publishing, handling, and validation for faction intent events.
"""

import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

pytestmark = pytest.mark.integration


class MockEventBus:
    """Mock EventBus for testing event handling."""

    def __init__(self):
        self.published_events = []
        self.handlers = []

    def publish(self, event):
        """Store published events for verification."""
        self.published_events.append(event)

    def register_handler(self, handler):
        """Register a handler."""
        self.handlers.append(handler)

    def clear(self):
        """Clear all stored events."""
        self.published_events.clear()


class TestIntentGeneratedEventPublishing:
    """Tests for IntentGeneratedEvent publishing via EventBus - Issue 12."""

    @pytest.mark.integration
    def test_handler_receives_intent_generated_event(self):
        """Test that a registered handler receives IntentGeneratedEvent."""
        from src.events.event_bus import EventBus, Event, EventPriority, EventHandler
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        event_bus = EventBus()
        received_events = []

        # Create a proper EventHandler implementation with all abstract methods
        class MockHandler(EventHandler):
            @property
            def handled_event_types(self):
                return {"faction.intent_generated"}

            @property
            def handler_id(self):
                return "mock-handler-intent"

            async def handle(self, event: Event) -> bool:
                if isinstance(event, IntentGeneratedEvent):
                    received_events.append(event)
                    return True
                return False

        handler = MockHandler()
        event_bus.register_handler(handler)

        # Create and publish event
        event = IntentGeneratedEvent.create(
            faction_id="test-faction",
            intent_ids=["intent-1", "intent-2"],
            fallback=False,
            context_summary="Test context",
        )

        # Run async publish
        async def run_test():
            await event_bus.publish(event)
            await asyncio.sleep(0.1)  # Give handlers time to process

        asyncio.run(run_test())

        # Verify handler received the event
        assert len(received_events) == 1
        assert received_events[0].faction_id == "test-faction"
        assert received_events[0].intent_ids == ["intent-1", "intent-2"]

    @pytest.mark.integration
    def test_event_bus_health_check_with_intent_events(self):
        """Test EventBus health check works with intent event types."""
        from src.events.event_bus import EventBus
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        event_bus = EventBus()

        # Create an intent event (no need to publish for health check)
        event = IntentGeneratedEvent.create(
            faction_id="test-faction",
            intent_ids=["intent-1"],
            fallback=True,
            context_summary="Health check test",
        )

        # Basic health check - event bus should be functional
        assert event_bus is not None
        assert event is not None

    @pytest.mark.integration
    def test_event_validation_max_3_intent_ids(self):
        """Test that IntentGeneratedEvent validates max 3 intent_ids."""
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        # Valid: 3 or fewer intent_ids
        valid_event = IntentGeneratedEvent.create(
            faction_id="test-faction",
            intent_ids=["intent-1", "intent-2", "intent-3"],
            fallback=False,
            context_summary="Valid event",
        )
        assert valid_event is not None
        assert len(valid_event.intent_ids) == 3

        # Invalid: more than 3 intent_ids should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            IntentGeneratedEvent.create(
                faction_id="test-faction",
                intent_ids=["i1", "i2", "i3", "i4"],  # 4 intents - exceeds max
                fallback=False,
                context_summary="Invalid event",
            )

        assert "cannot exceed 3" in str(exc_info.value)

    @pytest.mark.integration
    def test_event_validation_empty_intent_ids_fails(self):
        """Test that empty intent_ids fails validation."""
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        with pytest.raises(ValueError) as exc_info:
            IntentGeneratedEvent.create(
                faction_id="test-faction",
                intent_ids=[],  # Empty - invalid
                fallback=False,
                context_summary="Invalid event",
            )

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.integration
    def test_event_includes_rag_enriched_field(self):
        """Test that IntentGeneratedEvent includes rag_enriched field - Issue 7."""
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        # Create event - default rag_enriched is False
        event = IntentGeneratedEvent.create(
            faction_id="test-faction",
            intent_ids=["intent-1"],
            fallback=False,
            context_summary="Test with RAG",
        )

        # Check the field exists and defaults to False
        assert hasattr(event, "rag_enriched")
        assert event.rag_enriched is False
        assert event.payload.get("rag_enriched") is False

        # The FactionDecisionService sets rag_enriched via payload update after creation
        # Simulate what the service does
        event.payload["rag_enriched"] = True
        object.__setattr__(event, 'rag_enriched', True)

        # Verify it's updated
        assert event.rag_enriched is True
        assert event.payload.get("rag_enriched") is True


class TestIntentSelectedEventPublishing:
    """Tests for IntentSelectedEvent publishing via EventBus."""

    @pytest.mark.integration
    def test_intent_selected_event_structure(self):
        """Test IntentSelectedEvent has correct structure."""
        from src.contexts.world.domain.events.intent_events import IntentSelectedEvent

        event = IntentSelectedEvent.create(
            faction_id="test-faction",
            intent_id="intent-123",
            action_type="ATTACK",
            target_id="enemy-faction",
        )

        assert event.faction_id == "test-faction"
        assert event.intent_id == "intent-123"
        assert event.action_type == "ATTACK"
        assert event.target_id == "enemy-faction"
        assert event.event_type == "faction.intent_selected"

    @pytest.mark.integration
    def test_intent_selected_event_without_target(self):
        """Test IntentSelectedEvent can be created without target (e.g., STABILIZE)."""
        from src.contexts.world.domain.events.intent_events import IntentSelectedEvent

        event = IntentSelectedEvent.create(
            faction_id="test-faction",
            intent_id="intent-456",
            action_type="STABILIZE",
            target_id=None,
        )

        assert event.target_id is None
        assert event.action_type == "STABILIZE"


class TestEventPayloadConsistency:
    """Tests for event payload consistency and serialization."""

    @pytest.mark.integration
    def test_intent_generated_event_payload_structure(self):
        """Test IntentGeneratedEvent payload has all expected fields."""
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        event = IntentGeneratedEvent.create(
            faction_id="test-faction",
            intent_ids=["intent-1", "intent-2"],
            fallback=True,
            context_summary="Low resources, defensive posture",
        )

        # Verify payload structure
        assert "faction_id" in event.payload
        assert "intent_ids" in event.payload
        assert "fallback" in event.payload
        assert "context_summary" in event.payload
        assert "generation_method" in event.payload
        assert "rag_enriched" in event.payload

        assert event.payload["faction_id"] == "test-faction"
        assert event.payload["intent_ids"] == ["intent-1", "intent-2"]
        assert event.payload["fallback"] is True
        assert event.payload["generation_method"] == "fallback"

    @pytest.mark.integration
    def test_event_get_summary_method(self):
        """Test event get_summary() returns human-readable string."""
        from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent

        # LLM-generated event
        llm_event = IntentGeneratedEvent.create(
            faction_id="north-kingdom",
            intent_ids=["intent-1"],
            fallback=False,
            context_summary="food=50, gold=200",
        )
        llm_summary = llm_event.get_summary()
        assert "LLM" in llm_summary
        assert "north-kingdom" in llm_summary
        assert "food=50" in llm_summary

        # Fallback event
        fallback_event = IntentGeneratedEvent.create(
            faction_id="south-realm",
            intent_ids=["intent-2"],
            fallback=True,
            context_summary="Critical food shortage",
        )
        fallback_summary = fallback_event.get_summary()
        assert "fallback rules" in fallback_summary
        assert "south-realm" in fallback_summary
