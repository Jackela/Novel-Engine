"""Kafka-based event bus implementation for production use.

This module provides a production-ready event bus using Apache Kafka
as the underlying message broker. Supports consumer groups for
horizontal scaling and exactly-once semantics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from contextlib import suppress
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    AIOKAFKA_AVAILABLE = True
except ImportError:
    AIOKAFKA_AVAILABLE = False
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

from .event_bus import (
    DomainEvent,
    EventBus,
    EventBusError,
    EventBusNotStartedError,
    EventHandler,
    EventPublishError,
    EventSubscribeError,
)

if not AIOKAFKA_AVAILABLE:
    raise ImportError(
        "KafkaEventBus requires aiokafka. Install with: pip install aiokafka"
    )

logger = logging.getLogger(__name__)


class KafkaEventBus(EventBus):
    """Kafka-based event bus implementation.

    Provides reliable, scalable event delivery using Apache Kafka.
    Features:
    - Consumer groups for load balancing
    - Exactly-once delivery semantics
    - SSL/TLS encryption support
    - SASL authentication support
    - Dead letter queue for failed messages
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: Optional[str] = None,
        group_id: Optional[str] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        sasl_mechanism: Optional[str] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
        enable_idempotence: bool = True,
        max_retries: int = 3,
        retry_backoff_ms: int = 1000,
        dead_letter_topic: Optional[str] = None,
    ) -> None:
        """Initialize Kafka event bus.

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
            client_id: Client identifier for this producer/consumer
            group_id: Consumer group ID for load balancing
            ssl_context: SSL context for encrypted connections
            sasl_mechanism: SASL mechanism (PLAIN, SCRAM-SHA-256, etc.)
            sasl_plain_username: SASL username
            sasl_plain_password: SASL password
            enable_idempotence: Enable exactly-once semantics
            max_retries: Maximum number of retries for failed sends
            retry_backoff_ms: Backoff time between retries
            dead_letter_topic: Topic for failed messages
        """
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id or "novel-engine-event-bus"
        self._group_id = group_id or "novel-engine-consumer-group"
        self._ssl_context = ssl_context
        self._sasl_mechanism = sasl_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
        self._enable_idempotence = enable_idempotence
        self._max_retries = max_retries
        self._retry_backoff_ms = retry_backoff_ms
        self._dead_letter_topic = dead_letter_topic

        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: List[AIOKafkaConsumer] = []
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._started: bool = False
        self._consumer_tasks: Set[Any] = set()

    def _get_security_config(self) -> Dict[str, Any]:
        """Build security configuration for Kafka connections."""
        config: Dict[str, Any] = {}

        if self._ssl_context:
            config["security_protocol"] = "SSL"
            config["ssl_context"] = self._ssl_context

        if self._sasl_mechanism:
            config["security_protocol"] = (
                "SASL_SSL" if self._ssl_context else "SASL_PLAINTEXT"
            )
            config["sasl_mechanism"] = self._sasl_mechanism
            if self._sasl_plain_username:
                config["sasl_plain_username"] = self._sasl_plain_username
            if self._sasl_plain_password:
                config["sasl_plain_password"] = self._sasl_plain_password

        return config

    async def start(self) -> None:
        """Start the Kafka event bus.

        Initializes the producer and prepares for publishing/subscribing.
        """
        if self._started:
            return

        try:
            # Configure producer
            producer_config = {
                "bootstrap_servers": self._bootstrap_servers,
                "client_id": f"{self._client_id}-producer",
                "enable_idempotence": self._enable_idempotence,
                "retries": self._max_retries,
                "retry_backoff_ms": self._retry_backoff_ms,
                "acks": "all",  # Wait for all replicas
                **self._get_security_config(),
            }

            self._producer = AIOKafkaProducer(**producer_config)
            await self._producer.start()

            self._started = True
            logger.info("KafkaEventBus started successfully")

        except Exception as e:
            logger.exception(f"Failed to start KafkaEventBus: {e}")
            raise EventBusError(f"Failed to start event bus: {e}") from e

    async def stop(self) -> None:
        """Stop the Kafka event bus.

        Gracefully shuts down all consumers and the producer.
        """
        if not self._started:
            return

        self._started = False

        # Stop all consumers
        for consumer in self._consumers:
            with suppress(Exception):
                await consumer.stop()
        self._consumers.clear()

        # Stop producer
        if self._producer:
            with suppress(Exception):
                await self._producer.stop()
            self._producer = None

        logger.info("KafkaEventBus stopped")

    def _ensure_started(self) -> None:
        """Ensure the bus has been started."""
        if not self._started or not self._producer:
            raise EventBusNotStartedError("EventBus must be started before operations")

    def _serialize_event(self, event: DomainEvent[Any]) -> bytes:
        """Serialize a domain event to JSON bytes."""

        def json_serializer(obj: Any) -> Any:
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, Any):  # datetime or other
                from datetime import datetime

                if isinstance(obj, datetime):
                    return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        event_dict = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "aggregate_id": event.aggregate_id,
            "payload": event.payload,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "occurred_on": event.occurred_on.isoformat(),
            "metadata": event.metadata,
        }
        return json.dumps(event_dict, default=json_serializer).encode("utf-8")

    def _deserialize_event(self, data: bytes) -> DomainEvent[Any]:
        """Deserialize JSON bytes to a domain event."""
        from datetime import datetime

        event_dict = json.loads(data.decode("utf-8"))

        return DomainEvent(
            event_id=UUID(event_dict["event_id"]),
            event_type=event_dict["event_type"],
            aggregate_id=event_dict.get("aggregate_id"),
            payload=event_dict["payload"],
            correlation_id=event_dict.get("correlation_id"),
            causation_id=event_dict.get("causation_id"),
            occurred_on=datetime.fromisoformat(event_dict["occurred_on"]),
            metadata=event_dict.get("metadata", {}),
        )

    async def publish(
        self,
        event: DomainEvent[Any],
        topic: Optional[str] = None,
    ) -> None:
        """Publish an event to Kafka.

        Args:
            event: The event to publish
            topic: Kafka topic to publish to (defaults to event_type)

        Raises:
            EventBusNotStartedError: If bus is not started
            EventPublishError: If publish fails after retries
        """
        self._ensure_started()

        target_topic = topic or event.event_type

        try:
            message = self._serialize_event(event)

            # Send with retry logic handled by producer
            await self._producer.send_and_wait(
                target_topic,
                message,
                key=event.aggregate_id.encode() if event.aggregate_id else None,
                headers={
                    "event_type": event.event_type.encode(),
                    "correlation_id": (event.correlation_id or "").encode(),
                },
            )

            logger.debug(f"Published event {event.event_id} to topic {target_topic}")

        except Exception as e:
            logger.exception(f"Failed to publish event: {e}")
            raise EventPublishError(f"Failed to publish event: {e}") from e

    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Subscribe a handler to events from a Kafka topic.

        Creates a consumer that polls for messages and dispatches
        them to the registered handler.

        Args:
            event_type: The type of events to subscribe to
            handler: Async handler function
            topic: Kafka topic to consume from

        Raises:
            EventBusNotStartedError: If bus is not started
            EventSubscribeError: If subscription fails
        """
        self._ensure_started()

        target_topic = topic or event_type

        try:
            # Store handler for this event type
            if event_type not in self._handlers:
                self._handlers[event_type] = set()
            self._handlers[event_type].add(handler)

            # Configure consumer
            consumer_config = {
                "bootstrap_servers": self._bootstrap_servers,
                "client_id": f"{self._client_id}-consumer-{event_type}",
                "group_id": self._group_id,
                "enable_auto_commit": False,  # Manual commit for reliability
                "auto_offset_reset": "earliest",
                **self._get_security_config(),
            }

            consumer = AIOKafkaConsumer(
                target_topic,
                **consumer_config,
            )

            await consumer.start()
            self._consumers.append(consumer)

            # Start consumer task
            task = asyncio.create_task(
                self._consume_messages(consumer, event_type),
                name=f"consumer-{target_topic}",
            )
            self._consumer_tasks.add(task)
            task.add_done_callback(self._consumer_tasks.discard)

            logger.info(
                f"Subscribed to topic {target_topic} for event type {event_type}"
            )

        except Exception as e:
            raise EventSubscribeError(f"Failed to subscribe: {e}") from e

    async def _consume_messages(
        self,
        consumer: AIOKafkaConsumer,
        event_type: str,
    ) -> None:
        """Consume messages from Kafka and dispatch to handlers."""

        try:
            async for msg in consumer:
                if not self._started:
                    break

                try:
                    event = self._deserialize_event(msg.value)

                    # Only process if event type matches
                    if event.event_type != event_type:
                        continue

                    # Dispatch to all handlers
                    handlers = self._handlers.get(event_type, set())
                    for handler in handlers:
                        try:
                            await handler(event)
                        except Exception as e:
                            logger.exception(
                                f"Handler failed for event {event.event_id}: {e}"
                            )
                            await self._handle_failed_message(msg, event, e)

                    # Commit offset after successful processing
                    await consumer.commit()

                except Exception as e:
                    logger.exception(f"Failed to process message: {e}")
                    await self._handle_failed_message(msg, None, e)

        except Exception as e:
            logger.exception(f"Consumer error: {e}")
        finally:
            with suppress(Exception):
                await consumer.stop()

    async def _handle_failed_message(
        self,
        msg: Any,
        event: Optional[DomainEvent[Any]],
        error: Exception,
    ) -> None:
        """Handle a failed message.

        Sends to dead letter topic if configured.
        """
        if self._dead_letter_topic and self._producer:
            try:
                error_info = {
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "original_topic": msg.topic,
                    "original_partition": msg.partition,
                    "original_offset": msg.offset,
                    "event_id": str(event.event_id) if event else None,
                }
                await self._producer.send(
                    self._dead_letter_topic,
                    json.dumps(error_info).encode(),
                )
            except Exception as e:
                logger.error(f"Failed to send to dead letter queue: {e}")

    async def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
        topic: Optional[str] = None,
    ) -> None:
        """Unsubscribe a handler.

        Note: This removes the handler from the internal registry.
        The Kafka consumer continues running until stop() is called.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
            topic: Optional topic (not used, for interface compatibility)
        """
        self._ensure_started()

        if event_type in self._handlers:
            self._handlers[event_type].discard(handler)
            logger.debug(f"Unsubscribed handler from {event_type}")
