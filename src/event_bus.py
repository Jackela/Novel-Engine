#!/usr/bin/env python3
"""
Event Bus System
================

This module provides a simple event bus system for decoupling components
within the simulation. It allows different parts of the system to communicate
asynchronously by emitting and listening for events.
"""

import logging
from collections import defaultdict
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple event bus for handling event-driven communication.
    """

    def __init__(self):
        """Initializes the EventBus."""
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        logger.info("EventBus initialized.")

    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribes a callback function to a specific event type.

        Args:
            event_type: The name of the event to subscribe to.
            callback: The function to call when the event is emitted.
        """
        self._subscribers[event_type].append(callback)
        callback_name = getattr(callback, '__name__', 'mock_callback')
        logger.debug(f"Subscribed {callback_name} to event '{event_type}'")

    def emit(self, event_type: str, *args: Any, **kwargs: Any):
        """
        Emits an event, calling all subscribed callbacks.

        Args:
            event_type: The name of the event to emit.
            *args: Positional arguments to pass to the callbacks.
            **kwargs: Keyword arguments to pass to the callbacks.
        """
        if event_type in self._subscribers:
            logger.info(f"Emitting event '{event_type}' to {len(self._subscribers[event_type])} subscribers.")
            for callback in self._subscribers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event '{event_type}': {e}", exc_info=True)
        else:
            logger.debug(f"Event '{event_type}' emitted, but has no subscribers.")

    async def publish(self, event_type: str, data: Any):
        """
        Publishes an event asynchronously (alias for emit for test compatibility).
        
        Args:
            event_type: The name of the event to publish.
            data: Data to pass to the callbacks.
        """
        if event_type in self._subscribers:
            logger.info(f"Publishing event '{event_type}' to {len(self._subscribers[event_type])} subscribers.")
            for callback in self._subscribers[event_type]:
                try:
                    if hasattr(callback, '__call__'):
                        # Check if callback is async
                        import asyncio
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for event '{event_type}': {e}", exc_info=True)
        else:
            logger.debug(f"Event '{event_type}' published, but has no subscribers.")

    def unsubscribe(self, event_type: str, callback: Callable):
        """
        Unsubscribes a callback function from a specific event type.
        
        Args:
            event_type: The name of the event to unsubscribe from.
            callback: The function to remove from subscribers.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                callback_name = getattr(callback, '__name__', 'unknown_callback')
                logger.debug(f"Unsubscribed {callback_name} from event '{event_type}'")
                
                # Clean up empty subscriber lists
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
            except ValueError:
                logger.warning(f"Callback not found in subscribers for event '{event_type}'")

    async def start(self):
        """Start the event bus (for compatibility)."""
        logger.info("EventBus started.")

    async def stop(self):
        """Stop the event bus (for compatibility)."""
        logger.info("EventBus stopped.")
