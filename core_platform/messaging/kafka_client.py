"""
Kafka Client and Connection Management
====================================

High-level Kafka client with producer and consumer management,
connection pooling, and health monitoring for Novel Engine platform.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    import aiokafka
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.errors import KafkaConnectionError, KafkaError, KafkaTimeoutError
    from aiokafka.helpers import create_ssl_context

    KAFKA_AVAILABLE = True
except ImportError:
    # Stub implementations when aiokafka is not available
    class KafkaError(Exception):
        pass

    class KafkaConnectionError(Exception):
        pass

    class KafkaTimeoutError(Exception):
        pass

    class AIOKafkaProducer:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            pass

        async def stop(self):
            pass

        async def send(self, topic, value=None, key=None):
            pass

    class AIOKafkaConsumer:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            pass

        async def stop(self):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    def create_ssl_context():
        return None

    KAFKA_AVAILABLE = False

from ..config.settings import get_messaging_settings
from ..monitoring.metrics import MessagingMetrics

logger = logging.getLogger(__name__)


class KafkaClientException(Exception):
    """Base exception for Kafka client operations."""

    pass


class KafkaConnectionException(KafkaClientException):
    """Raised when Kafka connection fails."""

    pass


class KafkaPublishException(KafkaClientException):
    """Raised when message publishing fails."""

    pass


class KafkaConsumeException(KafkaClientException):
    """Raised when message consumption fails."""

    pass


class KafkaClient:
    """
    High-level Kafka client for Novel Engine platform.

    Features:
    - Async producer and consumer management
    - Automatic connection handling and reconnection
    - Message serialization/deserialization
    - Topic management and configuration
    - Health monitoring and metrics collection
    - Error handling and retry mechanisms
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Kafka client with configuration."""
        self.config = config or get_messaging_settings()
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._metrics = MessagingMetrics()
        self._is_connected = False
        self._connection_lock = asyncio.Lock()

        # Connection settings
        self.bootstrap_servers = self.config.get("bootstrap_servers", "localhost:9092")
        self.security_config = self._build_security_config()

        logger.info(f"Initialized Kafka client with servers: {self.bootstrap_servers}")

    async def connect(self) -> None:
        """Establish connection to Kafka cluster."""
        async with self._connection_lock:
            if self._is_connected:
                logger.debug("Kafka client already connected")
                return

            try:
                logger.info("Connecting to Kafka cluster...")

                # Initialize producer
                await self._initialize_producer()

                self._is_connected = True
                self._metrics.record_connection_established()
                logger.info("Kafka client connected successfully")

            except Exception as e:
                self._metrics.record_connection_failed()
                logger.error(f"Failed to connect to Kafka: {e}")
                raise KafkaConnectionException(f"Failed to connect to Kafka: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster and cleanup resources."""
        async with self._connection_lock:
            if not self._is_connected:
                return

            logger.info("Disconnecting from Kafka cluster...")

            try:
                # Stop all consumers
                for consumer_group, consumer in self._consumers.items():
                    await consumer.stop()
                    logger.debug(f"Stopped consumer for group: {consumer_group}")

                self._consumers.clear()

                # Stop producer
                if self._producer:
                    await self._producer.stop()
                    self._producer = None
                    logger.debug("Stopped Kafka producer")

                self._is_connected = False
                self._metrics.record_connection_closed()
                logger.info("Kafka client disconnected successfully")

            except Exception as e:
                logger.error(f"Error during Kafka disconnect: {e}")
                raise

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None,
    ) -> None:
        """
        Publish a message to a Kafka topic.

        Args:
            topic: Topic to publish to
            message: Message payload (will be JSON serialized)
            key: Optional message key for partitioning
            headers: Optional message headers
            partition: Optional specific partition
        """
        if not self._is_connected:
            await self.connect()

        try:
            self._metrics.record_message_publish_start()

            # Serialize message
            serialized_message = self._serialize_message(message)
            serialized_key = key.encode("utf-8") if key else None

            # Prepare headers
            kafka_headers = self._prepare_headers(headers)

            # Send message
            await self._producer.send_and_wait(
                topic,
                value=serialized_message,
                key=serialized_key,
                headers=kafka_headers,
                partition=partition,
            )

            self._metrics.record_message_published(topic)
            logger.debug(f"Published message to topic {topic} with key {key}")

        except Exception as e:
            self._metrics.record_message_publish_failed(topic)
            logger.error(f"Failed to publish message to {topic}: {e}")
            raise KafkaPublishException(f"Failed to publish message: {e}")

    async def publish_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]],
        keys: Optional[List[str]] = None,
        headers: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        Publish multiple messages to a topic in a batch.

        Args:
            topic: Topic to publish to
            messages: List of message payloads
            keys: Optional list of message keys
            headers: Optional list of message headers
        """
        if not self._is_connected:
            await self.connect()

        try:
            self._metrics.record_batch_publish_start()

            # Prepare batch
            batch_size = len(messages)
            keys = keys or [None] * batch_size
            headers = headers or [None] * batch_size

            # Send all messages
            futures = []
            for i, message in enumerate(messages):
                serialized_message = self._serialize_message(message)
                serialized_key = keys[i].encode("utf-8") if keys[i] else None
                kafka_headers = self._prepare_headers(headers[i])

                future = self._producer.send(
                    topic,
                    value=serialized_message,
                    key=serialized_key,
                    headers=kafka_headers,
                )
                futures.append(future)

            # Wait for all messages to be sent
            await asyncio.gather(*futures)

            self._metrics.record_batch_published(topic, batch_size)
            logger.debug(f"Published batch of {batch_size} messages to topic {topic}")

        except Exception as e:
            self._metrics.record_batch_publish_failed(topic)
            logger.error(f"Failed to publish batch to {topic}: {e}")
            raise KafkaPublishException(f"Failed to publish batch: {e}")

    async def subscribe(
        self,
        topics: List[str],
        consumer_group: str,
        message_handler: Callable[[Dict[str, Any], Dict[str, Any]], None],
        auto_commit: bool = True,
        max_poll_records: int = 500,
    ) -> None:
        """
        Subscribe to topics and start consuming messages.

        Args:
            topics: List of topics to subscribe to
            consumer_group: Consumer group ID
            message_handler: Function to handle received messages
            auto_commit: Whether to auto-commit offsets
            max_poll_records: Maximum records per poll
        """
        if consumer_group in self._consumers:
            logger.warning(f"Consumer group {consumer_group} already exists")
            return

        try:
            logger.info(f"Creating consumer for group {consumer_group}, topics: {topics}")

            # Create consumer
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=consumer_group,
                enable_auto_commit=auto_commit,
                max_poll_records=max_poll_records,
                value_deserializer=self._deserialize_message,
                key_deserializer=self._deserialize_key,
                **self.security_config,
            )

            # Start consumer
            await consumer.start()
            self._consumers[consumer_group] = consumer

            # Start consuming in background task
            asyncio.create_task(self._consume_messages(consumer, message_handler, consumer_group))

            logger.info(f"Started consumer for group {consumer_group}")

        except Exception as e:
            logger.error(f"Failed to create consumer for group {consumer_group}: {e}")
            raise KafkaConsumeException(f"Failed to create consumer: {e}")

    async def unsubscribe(self, consumer_group: str) -> None:
        """Stop and remove a consumer group."""
        if consumer_group not in self._consumers:
            logger.warning(f"Consumer group {consumer_group} not found")
            return

        try:
            consumer = self._consumers[consumer_group]
            await consumer.stop()
            del self._consumers[consumer_group]

            logger.info(f"Stopped consumer for group {consumer_group}")

        except Exception as e:
            logger.error(f"Failed to stop consumer for group {consumer_group}: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of Kafka connection."""
        health_status = {
            "status": "healthy",
            "connected": self._is_connected,
            "producer_ready": self._producer is not None,
            "active_consumers": len(self._consumers),
            "errors": [],
        }

        if not self._is_connected:
            health_status["status"] = "unhealthy"
            health_status["errors"].append("Not connected to Kafka")
            return health_status

        # Test producer
        try:
            if self._producer:
                # Get cluster metadata as a health check
                metadata = await self._producer.client.fetch_metadata()
                health_status["cluster_metadata"] = {
                    "brokers": len(metadata.brokers),
                    "topics": len(metadata.topics),
                }
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["errors"].append(f"Producer health check failed: {str(e)}")

        # Test consumers
        unhealthy_consumers = []
        for group_id, consumer in self._consumers.items():
            try:
                # Check if consumer is still running
                if consumer._closed:
                    unhealthy_consumers.append(group_id)
            except Exception as e:
                unhealthy_consumers.append(group_id)
                health_status["errors"].append(f"Consumer {group_id} health check failed: {str(e)}")

        if unhealthy_consumers:
            health_status["status"] = "degraded"
            health_status["unhealthy_consumers"] = unhealthy_consumers

        return health_status

    def get_metrics(self) -> Dict[str, Any]:
        """Get messaging performance metrics."""
        return self._metrics.get_all_metrics()

    async def _initialize_producer(self) -> None:
        """Initialize Kafka producer."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=self._serialize_message,
                key_serializer=lambda x: x.encode("utf-8") if x else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                enable_idempotence=True,
                acks="all",
                **self.security_config,
            )

            await self._producer.start()
            logger.debug("Kafka producer initialized and started")

        except Exception as e:
            logger.error(f"Failed to initialize producer: {e}")
            raise

    async def _consume_messages(
        self, consumer: AIOKafkaConsumer, message_handler: Callable, consumer_group: str
    ) -> None:
        """Background task to consume messages."""
        logger.info(f"Starting message consumption for group {consumer_group}")

        try:
            async for message in consumer:
                try:
                    self._metrics.record_message_received(message.topic)

                    # Deserialize message
                    message_data = self._deserialize_message(message.value)

                    # Prepare message context
                    context = {
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "timestamp": message.timestamp,
                        "key": message.key.decode("utf-8") if message.key else None,
                        "headers": dict(message.headers) if message.headers else {},
                    }

                    # Call message handler
                    if asyncio.iscoroutinefunction(message_handler):
                        await message_handler(message_data, context)
                    else:
                        message_handler(message_data, context)

                    self._metrics.record_message_processed(message.topic)

                except Exception as e:
                    self._metrics.record_message_processing_failed(message.topic)
                    logger.error(f"Failed to process message from {message.topic}: {e}")
                    # Continue processing other messages

        except Exception as e:
            self._metrics.record_consumer_error(consumer_group)
            logger.error(f"Consumer error for group {consumer_group}: {e}")
            # Consumer will be automatically restarted by Kafka client

    def _build_security_config(self) -> Dict[str, Any]:
        """Build security configuration for Kafka connection."""
        security_config = {}

        # SSL configuration
        if self.config.get("use_ssl", False):
            security_config["security_protocol"] = "SSL"
            ssl_context = create_ssl_context(
                cafile=self.config.get("ssl_cafile"),
                certfile=self.config.get("ssl_certfile"),
                keyfile=self.config.get("ssl_keyfile"),
                password=self.config.get("ssl_password"),
            )
            security_config["ssl_context"] = ssl_context

        # SASL configuration
        if self.config.get("use_sasl", False):
            security_config["security_protocol"] = "SASL_PLAINTEXT"
            security_config["sasl_mechanism"] = self.config.get("sasl_mechanism", "PLAIN")
            security_config["sasl_plain_username"] = self.config.get("sasl_username")
            security_config["sasl_plain_password"] = self.config.get("sasl_password")

        return security_config

    def _serialize_message(self, message: Dict[str, Any]) -> bytes:
        """Serialize message to JSON bytes."""
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now(timezone.utc).isoformat()

            return json.dumps(message, default=str).encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise

    def _deserialize_message(self, message_bytes: bytes) -> Dict[str, Any]:
        """Deserialize message from JSON bytes."""
        try:
            if message_bytes is None:
                return {}

            return json.loads(message_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise

    def _deserialize_key(self, key_bytes: Optional[bytes]) -> Optional[str]:
        """Deserialize message key."""
        if key_bytes is None:
            return None
        return key_bytes.decode("utf-8")

    def _prepare_headers(self, headers: Optional[Dict[str, str]]) -> List[tuple]:
        """Prepare headers for Kafka message."""
        if headers is None:
            headers = {}

        # Add default headers
        headers.setdefault("producer", "novel-engine-platform")
        headers.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        # Convert to Kafka format
        return [(k.encode("utf-8"), v.encode("utf-8")) for k, v in headers.items()]


# Global Kafka client instance
_kafka_client: Optional[KafkaClient] = None


def get_kafka_client() -> KafkaClient:
    """Get the global Kafka client instance."""
    global _kafka_client
    if _kafka_client is None:
        _kafka_client = KafkaClient()
    return _kafka_client


async def initialize_messaging() -> None:
    """Initialize the global Kafka client."""
    client = get_kafka_client()
    await client.connect()


async def shutdown_messaging() -> None:
    """Shutdown the global Kafka client."""
    global _kafka_client
    if _kafka_client:
        await _kafka_client.disconnect()
        _kafka_client = None


async def publish_message(
    topic: str,
    message: Dict[str, Any],
    key: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """Convenience function to publish a message."""
    client = get_kafka_client()
    await client.publish(topic, message, key, headers)


async def get_messaging_health() -> Dict[str, Any]:
    """Get messaging system health status."""
    client = get_kafka_client()
    return await client.health_check()
