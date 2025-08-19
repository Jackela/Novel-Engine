#!/usr/bin/env python3
"""
Advanced Event Bus for Enterprise-Grade Event-Driven Architecture

This module provides a production-ready event bus implementation with:
- High-performance async pub/sub patterns
- Event persistence and replay capabilities
- Dead letter queue handling
- Circuit breaker integration
- Distributed event processing
- Event sourcing support
"""

import asyncio
import logging
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union, Set
from enum import Enum
from uuid import uuid4
from abc import ABC, abstractmethod
import weakref
import aioredis
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels for processing optimization."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class EventStatus(Enum):
    """Event processing status tracking."""
    CREATED = "created"
    PUBLISHED = "published"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    REPLAYING = "replaying"

@dataclass
class Event:
    """
    Enterprise-grade event structure with comprehensive metadata.
    
    Supports event sourcing, distributed processing, and audit trails.
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.CREATED
    version: int = 1
    schema_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Validate event structure."""
        if not self.event_type:
            raise ValueError("Event type is required")
        if not self.source:
            raise ValueError("Event source is required")
        
        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary for persistence."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'payload': self.payload,
            'source': self.source,
            'correlation_id': self.correlation_id,
            'causation_id': self.causation_id,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'status': self.status.value,
            'version': self.version,
            'schema_version': self.schema_version,
            'metadata': self.metadata,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'timeout_seconds': self.timeout_seconds,
            'tags': list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Deserialize event from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['priority'] = EventPriority(data['priority'])
        data['status'] = EventStatus(data['status'])
        data['tags'] = set(data['tags'])
        return cls(**data)

class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: Event) -> bool:
        """
        Handle an event.
        
        Args:
            event: Event to handle
            
        Returns:
            True if event was handled successfully, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def handled_event_types(self) -> Set[str]:
        """Set of event types this handler can process."""
        pass
    
    @property
    def handler_id(self) -> str:
        """Unique identifier for this handler."""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

@dataclass
class HandlerRegistry:
    """Registry for managing event handlers."""
    handlers: Dict[str, List[EventHandler]] = field(default_factory=dict)
    handler_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def register(self, handler: EventHandler, metadata: Optional[Dict[str, Any]] = None):
        """Register an event handler."""
        handler_id = handler.handler_id
        
        for event_type in handler.handled_event_types:
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            
            # Avoid duplicate registrations
            if handler not in self.handlers[event_type]:
                self.handlers[event_type].append(handler)
        
        self.handler_metadata[handler_id] = metadata or {}
        logger.info(f"Registered handler {handler_id} for events: {handler.handled_event_types}")
    
    def unregister(self, handler: EventHandler):
        """Unregister an event handler."""
        handler_id = handler.handler_id
        
        for event_type in handler.handled_event_types:
            if event_type in self.handlers:
                self.handlers[event_type] = [h for h in self.handlers[event_type] if h != handler]
                if not self.handlers[event_type]:
                    del self.handlers[event_type]
        
        self.handler_metadata.pop(handler_id, None)
        logger.info(f"Unregistered handler {handler_id}")
    
    def get_handlers(self, event_type: str) -> List[EventHandler]:
        """Get all handlers for a specific event type."""
        return self.handlers.get(event_type, [])

class EventBusConfig:
    """Configuration for the event bus."""
    
    def __init__(self):
        self.max_concurrent_events = 100
        self.default_timeout = 30
        self.max_retries = 3
        self.dead_letter_queue_enabled = True
        self.event_persistence_enabled = True
        self.redis_url = "redis://localhost:6379"
        self.redis_key_prefix = "novel_engine:events"
        self.circuit_breaker_enabled = True
        self.circuit_breaker_failure_threshold = 5
        self.circuit_breaker_timeout = 60
        self.event_replay_enabled = True
        self.batch_processing_enabled = True
        self.batch_size = 10
        self.metrics_enabled = True

class CircuitBreaker:
    """Circuit breaker for event processing resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker moving to half-open state")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful call")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

class EventMetrics:
    """Event processing metrics collection."""
    
    def __init__(self):
        self.events_published = 0
        self.events_processed = 0
        self.events_failed = 0
        self.events_dead_letter = 0
        self.processing_times = []
        self.handler_metrics = {}
        self.start_time = time.time()
    
    def record_event_published(self):
        """Record an event publication."""
        self.events_published += 1
    
    def record_event_processed(self, processing_time: float):
        """Record successful event processing."""
        self.events_processed += 1
        self.processing_times.append(processing_time)
        
        # Keep only last 1000 processing times
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]
    
    def record_event_failed(self):
        """Record failed event processing."""
        self.events_failed += 1
    
    def record_dead_letter(self):
        """Record event moved to dead letter queue."""
        self.events_dead_letter += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        uptime = time.time() - self.start_time
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            'events_published': self.events_published,
            'events_processed': self.events_processed,
            'events_failed': self.events_failed,
            'events_dead_letter': self.events_dead_letter,
            'success_rate': self.events_processed / max(self.events_published, 1),
            'failure_rate': self.events_failed / max(self.events_published, 1),
            'average_processing_time_ms': avg_processing_time * 1000,
            'events_per_second': self.events_processed / max(uptime, 1),
            'uptime_seconds': uptime
        }

class EventBus:
    """
    Enterprise-grade event bus with advanced features.
    
    Features:
    - Async pub/sub with high performance
    - Event persistence and replay
    - Dead letter queue handling
    - Circuit breaker protection
    - Distributed processing with Redis
    - Comprehensive metrics
    - Event sourcing support
    """
    
    def __init__(self, config: Optional[EventBusConfig] = None):
        self.config = config or EventBusConfig()
        self.handler_registry = HandlerRegistry()
        self.circuit_breaker = CircuitBreaker(
            self.config.circuit_breaker_failure_threshold,
            self.config.circuit_breaker_timeout
        ) if self.config.circuit_breaker_enabled else None
        
        self.metrics = EventMetrics() if self.config.metrics_enabled else None
        self.redis: Optional[aioredis.Redis] = None
        self.event_store: List[Event] = []  # In-memory fallback
        self.dead_letter_queue: List[Event] = []
        self.processing_semaphore = asyncio.Semaphore(self.config.max_concurrent_events)
        self._shutdown_event = asyncio.Event()
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info("EventBus initialized with enterprise configuration")
    
    async def initialize(self):
        """Initialize the event bus and its dependencies."""
        try:
            # Initialize Redis connection if enabled
            if self.config.redis_url:
                self.redis = aioredis.from_url(self.config.redis_url)
                await self.redis.ping()
                logger.info("Redis connection established for event bus")
            
            # Start background tasks
            if self.config.batch_processing_enabled:
                task = asyncio.create_task(self._batch_processing_loop())
                self._background_tasks.append(task)
            
            logger.info("EventBus initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize EventBus: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the event bus."""
        logger.info("Shutting down EventBus...")
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connection
        if self.redis:
            await self.redis.close()
        
        logger.info("EventBus shutdown completed")
    
    def register_handler(self, handler: EventHandler, metadata: Optional[Dict[str, Any]] = None):
        """Register an event handler."""
        self.handler_registry.register(handler, metadata)
    
    def unregister_handler(self, handler: EventHandler):
        """Unregister an event handler."""
        self.handler_registry.unregister(handler)
    
    async def publish(self, event: Event) -> str:
        """
        Publish an event to the bus.
        
        Args:
            event: Event to publish
            
        Returns:
            Event ID
        """
        try:
            event.status = EventStatus.PUBLISHED
            event.timestamp = datetime.now()
            
            # Store event for persistence/replay
            if self.config.event_persistence_enabled:
                await self._store_event(event)
            
            # Publish to Redis if available
            if self.redis:
                await self._publish_to_redis(event)
            
            # Process locally
            asyncio.create_task(self._process_event(event))
            
            if self.metrics:
                self.metrics.record_event_published()
            
            logger.debug(f"Published event {event.event_id} of type {event.event_type}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            raise
    
    async def publish_batch(self, events: List[Event]) -> List[str]:
        """Publish multiple events as a batch."""
        event_ids = []
        for event in events:
            event_id = await self.publish(event)
            event_ids.append(event_id)
        return event_ids
    
    async def _process_event(self, event: Event):
        """Process a single event through all registered handlers."""
        async with self.processing_semaphore:
            start_time = time.time()
            handlers = self.handler_registry.get_handlers(event.event_type)
            
            if not handlers:
                logger.warning(f"No handlers registered for event type: {event.event_type}")
                return
            
            event.status = EventStatus.PROCESSING
            success_count = 0
            
            for handler in handlers:
                try:
                    if self.circuit_breaker and self.config.circuit_breaker_enabled:
                        success = await self.circuit_breaker.call(handler.handle, event)
                    else:
                        success = await asyncio.wait_for(
                            handler.handle(event),
                            timeout=event.timeout_seconds
                        )
                    
                    if success:
                        success_count += 1
                        logger.debug(f"Handler {handler.handler_id} processed event {event.event_id}")
                    else:
                        logger.warning(f"Handler {handler.handler_id} failed to process event {event.event_id}")
                
                except asyncio.TimeoutError:
                    logger.error(f"Handler {handler.handler_id} timed out processing event {event.event_id}")
                    await self._handle_retry_or_dead_letter(event)
                
                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} error processing event {event.event_id}: {e}")
                    await self._handle_retry_or_dead_letter(event)
            
            if success_count > 0:
                event.status = EventStatus.COMPLETED
                processing_time = time.time() - start_time
                
                if self.metrics:
                    self.metrics.record_event_processed(processing_time)
                
                logger.debug(f"Event {event.event_id} processed successfully by {success_count} handlers")
            else:
                event.status = EventStatus.FAILED
                if self.metrics:
                    self.metrics.record_event_failed()
    
    async def _handle_retry_or_dead_letter(self, event: Event):
        """Handle event retry logic or move to dead letter queue."""
        event.retry_count += 1
        
        if event.retry_count <= event.max_retries:
            # Exponential backoff
            delay = min(2 ** event.retry_count, 60)
            logger.info(f"Retrying event {event.event_id} in {delay} seconds (attempt {event.retry_count})")
            
            asyncio.create_task(self._retry_event_after_delay(event, delay))
        else:
            # Move to dead letter queue
            event.status = EventStatus.DEAD_LETTER
            if self.config.dead_letter_queue_enabled:
                self.dead_letter_queue.append(event)
                if self.metrics:
                    self.metrics.record_dead_letter()
                
                logger.warning(f"Event {event.event_id} moved to dead letter queue after {event.retry_count} attempts")
    
    async def _retry_event_after_delay(self, event: Event, delay: int):
        """Retry an event after a delay."""
        await asyncio.sleep(delay)
        await self._process_event(event)
    
    async def _store_event(self, event: Event):
        """Store event for persistence."""
        if self.redis:
            key = f"{self.config.redis_key_prefix}:events:{event.event_id}"
            await self.redis.setex(key, 86400, json.dumps(event.to_dict()))  # 24h TTL
        else:
            self.event_store.append(event)
    
    async def _publish_to_redis(self, event: Event):
        """Publish event to Redis pub/sub for distributed processing."""
        if self.redis:
            channel = f"{self.config.redis_key_prefix}:channel:{event.event_type}"
            await self.redis.publish(channel, json.dumps(event.to_dict()))
    
    async def _batch_processing_loop(self):
        """Background task for batch processing optimization."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(1)  # Process batches every second
                # Batch processing logic would go here
                # This is a placeholder for future optimization
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
    
    async def replay_events(self, from_time: datetime, to_time: Optional[datetime] = None, 
                          event_types: Optional[List[str]] = None) -> int:
        """
        Replay events from the event store.
        
        Args:
            from_time: Start time for replay
            to_time: End time for replay (defaults to now)
            event_types: Optional filter for specific event types
            
        Returns:
            Number of events replayed
        """
        if to_time is None:
            to_time = datetime.now()
        
        replayed_count = 0
        
        # Replay from in-memory store
        for event in self.event_store:
            if (from_time <= event.timestamp <= to_time and
                (not event_types or event.event_type in event_types)):
                
                event.status = EventStatus.REPLAYING
                await self._process_event(event)
                replayed_count += 1
        
        # Replay from Redis if available
        if self.redis:
            # This would require a more sophisticated event store implementation
            # For now, we'll log that Redis replay is not implemented
            logger.info("Redis event replay not implemented in this version")
        
        logger.info(f"Replayed {replayed_count} events from {from_time} to {to_time}")
        return replayed_count
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get event bus metrics."""
        if self.metrics:
            return self.metrics.get_metrics()
        return None
    
    def get_dead_letter_queue(self) -> List[Event]:
        """Get events in the dead letter queue."""
        return self.dead_letter_queue.copy()
    
    async def clear_dead_letter_queue(self):
        """Clear the dead letter queue."""
        cleared_count = len(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        logger.info(f"Cleared {cleared_count} events from dead letter queue")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event bus."""
        health = {
            'status': 'healthy',
            'redis_connected': False,
            'active_handlers': sum(len(handlers) for handlers in self.handler_registry.handlers.values()),
            'dead_letter_queue_size': len(self.dead_letter_queue),
            'background_tasks_running': len([t for t in self._background_tasks if not t.done()])
        }
        
        if self.redis:
            try:
                await self.redis.ping()
                health['redis_connected'] = True
            except Exception:
                health['status'] = 'degraded'
                health['redis_connected'] = False
        
        if self.metrics:
            health['metrics'] = self.metrics.get_metrics()
        
        return health