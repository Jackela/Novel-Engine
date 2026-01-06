#!/usr/bin/env python3
"""
Event Coordinator
=================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Manages cross-system event coordination and handling.

Responsibilities:
- Manage event bus lifecycle
- Set up event subscriptions
- Emit integration events
- Handle cross-system events
- Coordinate between traditional and AI systems

This class follows the Single Responsibility Principle by focusing solely on
event coordination, separate from integration orchestration.
"""

import logging
from typing import Any, Callable, Dict, Optional

from src.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventCoordinator:
    """
    Coordinates events between traditional and AI subsystems.

    This class encapsulates all event management logic, providing a clean
    interface for setting up event handlers, emitting events, and coordinating
    cross-system communication.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the event coordinator.

        Args:
            event_bus: Optional existing EventBus instance. If not provided,
                      a new EventBus will be created.
        """
        self.event_bus = event_bus or EventBus()
        self._handlers_registered = False

        logger.info("Event Coordinator initialized successfully")

    # ===================================================================
    # Event Bus Access
    # ===================================================================

    def get_event_bus(self) -> EventBus:
        """
        Get the event bus instance.

        Returns:
            EventBus: The event bus for direct access
        """
        return self.event_bus

    # ===================================================================
    # Event Coordination Setup
    # ===================================================================

    async def setup_event_coordination(
        self,
        character_state_handler: Optional[Callable] = None,
        story_generation_handler: Optional[Callable] = None,
        user_interaction_handler: Optional[Callable] = None,
    ):
        """
        Set up event coordination between traditional and AI systems.

        Subscribes to cross-system events and registers handlers.

        Args:
            character_state_handler: Handler for character state change events
            story_generation_handler: Handler for story generation events
            user_interaction_handler: Handler for user interaction events
        """
        if self._handlers_registered:
            logger.warning("Event handlers already registered, skipping setup")
            return

        # Register event handlers for cross-system coordination
        if character_state_handler:
            self.event_bus.subscribe("character_state_changed", character_state_handler)
            logger.debug("Registered character_state_changed handler")

        if story_generation_handler:
            self.event_bus.subscribe("story_generated", story_generation_handler)
            logger.debug("Registered story_generated handler")

        if user_interaction_handler:
            self.event_bus.subscribe("user_interaction", user_interaction_handler)
            logger.debug("Registered user_interaction handler")

        self._handlers_registered = True
        logger.info("Event coordination setup completed")

    # ===================================================================
    # Event Emission
    # ===================================================================

    async def emit_integration_event(self, event_type: str, data: Dict[str, Any]):
        """
        Emit integration event for monitoring and coordination.

        Args:
            event_type: Type of event to emit
            data: Event data payload
        """
        self.event_bus.emit(event_type, data)
        logger.debug(f"Emitted integration event: {event_type}")

    # ===================================================================
    # Default Event Handlers
    # ===================================================================

    async def handle_character_state_change(self, event_data: Dict[str, Any]):
        """
        Handle character state change events.

        Default implementation logs the event. Override or extend in subclass
        for custom behavior.

        Args:
            event_data: Event data containing character state information
        """
        logger.debug(
            f"Character state change event received: {event_data.get('agent_id', 'unknown')}"
        )
        # Default implementation is a no-op
        # Subclasses or configuration can provide custom handlers

    async def handle_story_generation(self, event_data: Dict[str, Any]):
        """
        Handle story generation events.

        Default implementation logs the event. Override or extend in subclass
        for custom behavior.

        Args:
            event_data: Event data containing story generation information
        """
        logger.debug("Story generation event received")
        # Default implementation is a no-op
        # Subclasses or configuration can provide custom handlers

    async def handle_user_interaction(self, event_data: Dict[str, Any]):
        """
        Handle user interaction events.

        Default implementation logs the event. Override or extend in subclass
        for custom behavior.

        Args:
            event_data: Event data containing user interaction information
        """
        logger.debug(
            f"User interaction event received: {event_data.get('interaction_type', 'unknown')}"
        )
        # Default implementation is a no-op
        # Subclasses or configuration can provide custom handlers


__all__ = ["EventCoordinator"]
