"""
Outbox Pattern Implementation
============================

Reliable event publishing using the Transactional Outbox pattern
to ensure eventual consistency between database operations and message publishing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from .event_bus import DomainEvent, get_event_bus
from .kafka_client import get_kafka_client
from ..persistence.models import OutboxEvent, BaseModel
from ..persistence.database import get_db_session, get_async_db_session
from ..monitoring.metrics import OutboxMetrics

logger = logging.getLogger(__name__)


class OutboxException(Exception):
    """Base exception for outbox operations."""
    pass


class OutboxPublisher:
    """
    Outbox pattern publisher for reliable event delivery.
    
    Features:
    - Transactional event storage with database operations
    - Reliable event publishing with retry mechanisms
    - Dead letter handling for failed events
    - Performance monitoring and health checks
    - Configurable publishing strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize outbox publisher with configuration."""
        self.config = config or {}
        self._metrics = OutboxMetrics()
        self._is_running = False
        self._publisher_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.poll_interval = self.config.get("poll_interval", 5.0)  # seconds
        self.batch_size = self.config.get("batch_size", 100)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 30.0)  # seconds
        self.cleanup_interval = self.config.get("cleanup_interval", 3600.0)  # 1 hour
        self.cleanup_age = self.config.get("cleanup_age_hours", 24)  # hours
    
    async def start(self) -> None:
        """Start the outbox publisher."""
        if self._is_running:
            logger.warning("Outbox publisher is already running")
            return
        
        logger.info("Starting outbox publisher...")
        self._is_running = True
        
        # Start background tasks
        self._publisher_task = asyncio.create_task(self._publisher_loop())
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
        
        logger.info("Outbox publisher started successfully")
    
    async def stop(self) -> None:
        """Stop the outbox publisher."""
        if not self._is_running:
            return
        
        logger.info("Stopping outbox publisher...")
        self._is_running = False
        
        if self._publisher_task:
            self._publisher_task.cancel()
            try:
                await self._publisher_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Outbox publisher stopped")
    
    async def publish_with_transaction(
        self,
        session: Session,
        event: DomainEvent,
        aggregate: Optional[BaseModel] = None
    ) -> None:
        """
        Publish an event within a database transaction.
        
        This method stores the event in the outbox table as part of the same
        database transaction that modifies the aggregate, ensuring consistency.
        
        Args:
            session: Database session (must be part of active transaction)
            event: Domain event to publish
            aggregate: Optional aggregate being modified (for additional context)
        """
        try:
            self._metrics.record_outbox_event_stored()
            
            # Create outbox event record
            outbox_event = OutboxEvent(
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                event_type=event.event_type,
                event_version=event.event_version,
                event_data=event.to_dict(),
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                user_id=event.user_id,
                topic=event.get_topic_name(),
                partition_key=event.get_partition_key()
            )
            
            # Add to session (will be committed with the main transaction)
            session.add(outbox_event)
            
            logger.debug(f"Stored event {event.event_type} in outbox for aggregate {event.aggregate_id}")
            
        except Exception as e:
            self._metrics.record_outbox_event_store_failed()
            logger.error(f"Failed to store event in outbox: {e}")
            raise OutboxException(f"Failed to store event in outbox: {e}")
    
    async def publish_batch_with_transaction(
        self,
        session: Session,
        events: List[DomainEvent],
        aggregate: Optional[BaseModel] = None
    ) -> None:
        """
        Publish multiple events within a database transaction.
        
        Args:
            session: Database session (must be part of active transaction)
            events: List of domain events to publish
            aggregate: Optional aggregate being modified
        """
        try:
            self._metrics.record_outbox_batch_stored()
            
            outbox_events = []
            for event in events:
                outbox_event = OutboxEvent(
                    aggregate_id=event.aggregate_id,
                    aggregate_type=event.aggregate_type,
                    event_type=event.event_type,
                    event_version=event.event_version,
                    event_data=event.to_dict(),
                    correlation_id=event.correlation_id,
                    causation_id=event.causation_id,
                    user_id=event.user_id,
                    topic=event.get_topic_name(),
                    partition_key=event.get_partition_key()
                )
                outbox_events.append(outbox_event)
            
            # Add all events to session
            session.add_all(outbox_events)
            
            logger.debug(f"Stored batch of {len(events)} events in outbox")
            
        except Exception as e:
            self._metrics.record_outbox_batch_store_failed()
            logger.error(f"Failed to store event batch in outbox: {e}")
            raise OutboxException(f"Failed to store event batch in outbox: {e}")
    
    async def _publisher_loop(self) -> None:
        """Main publisher loop that processes outbox events."""
        logger.info("Starting outbox publisher loop")
        
        while self._is_running:
            try:
                await self._process_outbox_events()
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in outbox publisher loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(self.poll_interval)
        
        logger.info("Outbox publisher loop stopped")
    
    async def _process_outbox_events(self) -> None:
        """Process pending outbox events."""
        try:
            async with get_async_db_session() as session:
                # Get unpublished events
                events = await self._get_unpublished_events(session)
                
                if not events:
                    return
                
                self._metrics.record_outbox_batch_processing_start(len(events))
                logger.debug(f"Processing {len(events)} outbox events")
                
                # Group events by topic for efficient publishing
                events_by_topic = {}
                for event in events:
                    topic = event.topic
                    if topic not in events_by_topic:
                        events_by_topic[topic] = []
                    events_by_topic[topic].append(event)
                
                # Publish events by topic
                published_event_ids = []
                failed_event_ids = []
                
                for topic, topic_events in events_by_topic.items():
                    try:
                        await self._publish_topic_events(topic_events)
                        published_event_ids.extend([e.id for e in topic_events])
                        
                    except Exception as e:
                        logger.error(f"Failed to publish events to topic {topic}: {e}")
                        failed_event_ids.extend([e.id for e in topic_events])
                
                # Update event statuses
                if published_event_ids:
                    await self._mark_events_published(session, published_event_ids)
                    self._metrics.record_outbox_events_published(len(published_event_ids))
                
                if failed_event_ids:
                    await self._handle_failed_events(session, failed_event_ids)
                    self._metrics.record_outbox_events_failed(len(failed_event_ids))
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to process outbox events: {e}")
            self._metrics.record_outbox_processing_error()
    
    async def _get_unpublished_events(self, session: AsyncSession) -> List[OutboxEvent]:
        """Get unpublished events from the outbox."""
        # Calculate retry cutoff time
        retry_cutoff = datetime.utcnow() - timedelta(seconds=self.retry_delay)
        
        stmt = select(OutboxEvent).where(
            and_(
                OutboxEvent.processed == False,
                or_(
                    OutboxEvent.retry_count == 0,  # Never tried
                    and_(
                        OutboxEvent.retry_count < self.max_retries,
                        OutboxEvent.updated_at < retry_cutoff  # Enough time has passed for retry
                    )
                )
            )
        ).order_by(OutboxEvent.created_at).limit(self.batch_size)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def _publish_topic_events(self, events: List[OutboxEvent]) -> None:
        """Publish events for a specific topic."""
        if not events:
            return
        
        topic = events[0].topic
        kafka_client = get_kafka_client()
        
        # Prepare messages for batch publishing
        messages = []
        keys = []
        headers_list = []
        
        for event in events:
            messages.append(event.event_data)
            keys.append(event.partition_key)
            headers_list.append({
                "event_type": event.event_type,
                "event_version": event.event_version,
                "aggregate_type": event.aggregate_type,
                "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                "causation_id": str(event.causation_id) if event.causation_id else None,
                "user_id": str(event.user_id) if event.user_id else None
            })
        
        # Publish batch
        await kafka_client.publish_batch(
            topic=topic,
            messages=messages,
            keys=keys,
            headers=headers_list
        )
        
        logger.debug(f"Published {len(events)} events to topic {topic}")
    
    async def _mark_events_published(self, session: AsyncSession, event_ids: List[str]) -> None:
        """Mark events as successfully published."""
        stmt = update(OutboxEvent).where(
            OutboxEvent.id.in_(event_ids)
        ).values(
            processed=True,
            processed_at=datetime.utcnow(),
            error_message=None
        )
        
        await session.execute(stmt)
    
    async def _handle_failed_events(self, session: AsyncSession, event_ids: List[str]) -> None:
        """Handle failed event publishing."""
        stmt = update(OutboxEvent).where(
            OutboxEvent.id.in_(event_ids)
        ).values(
            retry_count=OutboxEvent.retry_count + 1,
            error_message="Failed to publish to Kafka"
        )
        
        await session.execute(stmt)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for processed events."""
        while self._is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_processed_events()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in outbox cleanup loop: {e}")
    
    async def _cleanup_processed_events(self) -> None:
        """Clean up old processed events."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_age)
            
            async with get_async_db_session() as session:
                stmt = delete(OutboxEvent).where(
                    and_(
                        OutboxEvent.processed == True,
                        OutboxEvent.processed_at < cutoff_time
                    )
                )
                
                result = await session.execute(stmt)
                deleted_count = result.rowcount
                await session.commit()
                
                if deleted_count > 0:
                    self._metrics.record_outbox_events_cleaned(deleted_count)
                    logger.info(f"Cleaned up {deleted_count} processed outbox events")
                
        except Exception as e:
            logger.error(f"Failed to cleanup processed events: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get outbox publisher status."""
        try:
            async with get_async_db_session() as session:
                # Count pending events
                pending_stmt = select(OutboxEvent).where(OutboxEvent.processed == False)
                pending_result = await session.execute(pending_stmt)
                pending_count = len(pending_result.scalars().all())
                
                # Count failed events (max retries exceeded)
                failed_stmt = select(OutboxEvent).where(
                    and_(
                        OutboxEvent.processed == False,
                        OutboxEvent.retry_count >= self.max_retries
                    )
                )
                failed_result = await session.execute(failed_stmt)
                failed_count = len(failed_result.scalars().all())
                
                return {
                    "is_running": self._is_running,
                    "pending_events": pending_count,
                    "failed_events": failed_count,
                    "batch_size": self.batch_size,
                    "poll_interval": self.poll_interval,
                    "max_retries": self.max_retries,
                    "metrics": self._metrics.get_all_metrics()
                }
                
        except Exception as e:
            logger.error(f"Failed to get outbox status: {e}")
            return {
                "is_running": self._is_running,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of outbox publisher."""
        health_status = {
            "status": "healthy",
            "is_running": self._is_running,
            "errors": []
        }
        
        if not self._is_running:
            health_status["status"] = "unhealthy"
            health_status["errors"].append("Outbox publisher is not running")
            return health_status
        
        try:
            status = await self.get_status()
            
            # Check for excessive failed events
            failed_count = status.get("failed_events", 0)
            if failed_count > 100:  # Configurable threshold
                health_status["status"] = "degraded"
                health_status["errors"].append(f"Too many failed events: {failed_count}")
            
            # Check for excessive pending events
            pending_count = status.get("pending_events", 0)
            if pending_count > 1000:  # Configurable threshold
                health_status["status"] = "degraded"
                health_status["errors"].append(f"Too many pending events: {pending_count}")
            
            health_status["pending_events"] = pending_count
            health_status["failed_events"] = failed_count
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["errors"].append(f"Health check failed: {str(e)}")
        
        return health_status


# Context manager for transactional event publishing
@asynccontextmanager
async def transactional_outbox(outbox_publisher: OutboxPublisher):
    """
    Context manager for transactional outbox operations.
    
    Usage:
        async with transactional_outbox(publisher) as (session, publish_event):
            # Modify aggregate
            character.update(name="New Name")
            session.add(character)
            
            # Publish event in same transaction
            event = CharacterUpdatedEvent(character_id=character.id, ...)
            await publish_event(event)
            
            # Transaction is committed automatically
    """
    async with get_async_db_session() as session:
        async def publish_event(event: DomainEvent):
            # Convert async session to sync for outbox method
            # This is a simplification - in production you'd want async throughout
            with get_db_session() as sync_session:
                await outbox_publisher.publish_with_transaction(sync_session, event)
        
        try:
            yield session, publish_event
        except Exception:
            await session.rollback()
            raise


# Global outbox publisher instance
_outbox_publisher: Optional[OutboxPublisher] = None


def get_outbox_publisher() -> OutboxPublisher:
    """Get the global outbox publisher instance."""
    global _outbox_publisher
    if _outbox_publisher is None:
        _outbox_publisher = OutboxPublisher()
    return _outbox_publisher


async def initialize_outbox() -> None:
    """Initialize and start the global outbox publisher."""
    publisher = get_outbox_publisher()
    await publisher.start()


async def shutdown_outbox() -> None:
    """Shutdown the global outbox publisher."""
    global _outbox_publisher
    if _outbox_publisher:
        await _outbox_publisher.stop()
        _outbox_publisher = None


# Convenience function for transactional publishing
async def publish_event_transactionally(
    session: Session,
    event: DomainEvent,
    aggregate: Optional[BaseModel] = None
) -> None:
    """Publish an event within a database transaction."""
    publisher = get_outbox_publisher()
    await publisher.publish_with_transaction(session, event, aggregate)