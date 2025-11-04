"""
Kafka Event Publisher Adapter

Concrete implementation of IEventPublisher for Kafka messaging infrastructure.
Part of Hexagonal Architecture - Infrastructure Layer adapter.

Constitution Compliance:
- Article II (Hexagonal Architecture): Adapter implementing port interface
- Article VI (Event-Driven Architecture): Kafka integration for domain events
- Article VII (Observability): Structured logging and error handling
"""

import logging
from typing import Any, Dict

from core_platform.messaging.kafka_client import get_kafka_client, KafkaClient

from ...application.ports.i_event_publisher import (
    EventPublishException,
    IEventPublisher,
)

logger = logging.getLogger(__name__)


class KafkaEventPublisher(IEventPublisher):
    """
    Kafka-based implementation of the IEventPublisher port.
    
    Features:
    - Asynchronous event publishing with at-least-once delivery
    - Automatic retry with exponential backoff
    - Batch publishing support for improved throughput
    - Health monitoring and connection management
    - Idempotency through event_id in message payload
    
    Usage:
        publisher = KafkaEventPublisher()
        await publisher.publish(
            topic="knowledge.entry.created",
            event={
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "entry_id": "123e4567-e89b-12d3-a456-426614174000",
                "knowledge_type": "profile",
                "created_by": "user-001",
                "timestamp": "2025-11-04T00:00:00Z"
            },
            key="123e4567-e89b-12d3-a456-426614174000"
        )
    """

    def __init__(self, kafka_client: KafkaClient | None = None):
        """
        Initialize Kafka event publisher.
        
        Args:
            kafka_client: Optional Kafka client instance (uses global if None)
        """
        self._kafka_client = kafka_client or get_kafka_client()
        logger.info("Initialized KafkaEventPublisher")

    async def publish(
        self,
        topic: str,
        event: Dict[str, Any],
        key: str | None = None,
        headers: Dict[str, str] | None = None,
    ) -> None:
        """
        Publish a single domain event to Kafka topic.
        
        Args:
            topic: Target topic name (e.g., "knowledge.entry.created")
            event: Domain event data as dictionary
            key: Optional partition key for ordering (typically entry_id)
            headers: Optional message headers
            
        Raises:
            EventPublishException: If publishing fails after retries
        """
        try:
            logger.debug(
                f"Publishing event to topic {topic} with key {key}",
                extra={
                    "topic": topic,
                    "event_id": event.get("event_id"),
                    "partition_key": key,
                },
            )

            # Add default headers
            event_headers = headers or {}
            event_headers.setdefault("event_type", topic)
            event_headers.setdefault("source", "knowledge-management")

            # Publish to Kafka
            await self._kafka_client.publish(
                topic=topic,
                message=event,
                key=key,
                headers=event_headers,
            )

            logger.info(
                f"Successfully published event to {topic}",
                extra={
                    "topic": topic,
                    "event_id": event.get("event_id"),
                    "partition_key": key,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to publish event to {topic}: {e}",
                extra={
                    "topic": topic,
                    "event_id": event.get("event_id"),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise EventPublishException(
                f"Failed to publish event to {topic}: {e}"
            ) from e

    async def publish_batch(
        self,
        topic: str,
        events: list[Dict[str, Any]],
        keys: list[str | None] | None = None,
        headers: list[Dict[str, str] | None] | None = None,
    ) -> None:
        """
        Publish multiple domain events to Kafka topic in a batch.
        
        Batch publishing improves throughput for bulk operations.
        
        Args:
            topic: Target topic name
            events: List of domain event data dictionaries
            keys: Optional list of partition keys (same length as events)
            headers: Optional list of headers (same length as events)
            
        Raises:
            EventPublishException: If batch publishing fails after retries
        """
        try:
            batch_size = len(events)
            logger.debug(
                f"Publishing batch of {batch_size} events to topic {topic}",
                extra={"topic": topic, "batch_size": batch_size},
            )

            # Prepare default headers for each event
            if headers is None:
                headers = [None] * batch_size

            processed_headers = []
            for i, event_headers in enumerate(headers):
                event_headers = event_headers or {}
                event_headers.setdefault("event_type", topic)
                event_headers.setdefault("source", "knowledge-management")
                processed_headers.append(event_headers)

            # Publish batch to Kafka
            await self._kafka_client.publish_batch(
                topic=topic,
                messages=events,
                keys=keys,
                headers=processed_headers,
            )

            logger.info(
                f"Successfully published batch of {batch_size} events to {topic}",
                extra={"topic": topic, "batch_size": batch_size},
            )

        except Exception as e:
            logger.error(
                f"Failed to publish batch to {topic}: {e}",
                extra={
                    "topic": topic,
                    "batch_size": len(events),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise EventPublishException(
                f"Failed to publish batch to {topic}: {e}"
            ) from e

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of Kafka event publishing infrastructure.
        
        Returns:
            Dictionary with health status:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "connected": bool,
                "producer_ready": bool,
                "errors": list[str]
            }
        """
        try:
            kafka_health = await self._kafka_client.health_check()

            # Map Kafka health to event publisher health
            return {
                "status": kafka_health.get("status", "unknown"),
                "connected": kafka_health.get("connected", False),
                "producer_ready": kafka_health.get("producer_ready", False),
                "errors": kafka_health.get("errors", []),
                "cluster_metadata": kafka_health.get("cluster_metadata"),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "connected": False,
                "producer_ready": False,
                "errors": [f"Health check failed: {str(e)}"],
            }
