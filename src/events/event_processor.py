#!/usr/bin/env python3
"""
Event Processor Implementation
=============================

Event processing strategies and handlers for asynchronous event processing.
This is a minimal implementation to resolve import dependencies.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, List

from .event_bus import Event, EventHandler

logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """Event processing strategies."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"


class EventProcessor:
    """Processes events using configurable strategies."""

    def __init__(self, strategy: ProcessingStrategy = ProcessingStrategy.SEQUENTIAL):
        """Initialize the event processor."""
        self.strategy = strategy
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.is_running = False

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def process_event(self, event: Event) -> None:
        """Process a single event."""
        if event.event_type not in self.handlers:
            logger.warning(f"No handlers registered for event type: {event.event_type}")
            return

        handlers = self.handlers[event.event_type]

        if self.strategy == ProcessingStrategy.SEQUENTIAL:
            for handler in handlers:
                await self._call_handler(handler, event)
        elif self.strategy == ProcessingStrategy.PARALLEL:
            tasks = [self._call_handler(handler, event) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Default to sequential
            for handler in handlers:
                await self._call_handler(handler, event)

    async def _call_handler(self, handler: EventHandler, event: Event) -> None:
        """Call an event handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")

    def start(self) -> None:
        """Start the event processor."""
        self.is_running = True
        logger.info(f"Event processor started with strategy: {self.strategy}")

    def stop(self) -> None:
        """Stop the event processor."""
        self.is_running = False
        logger.info("Event processor stopped")
