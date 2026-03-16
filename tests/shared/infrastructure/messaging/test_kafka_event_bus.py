"""Tests for Kafka event bus implementation."""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

from src.shared.infrastructure.messaging.event_bus import (
    DomainEvent,
    EventBusNotStartedError,
    EventPublishError,
    EventSubscribeError,
)

# Skip all tests if aiokafka is not installed
try:
    from src.shared.infrastructure.messaging.kafka_event_bus import KafkaEventBus

    AIOKAFKA_AVAILABLE = True
except ImportError:
    AIOKAFKA_AVAILABLE = False
    KafkaEventBus = None  # type: ignore

pytestmark = pytest.mark.skipif(not AIOKAFKA_AVAILABLE, reason="aiokafka not installed")


@pytest.fixture
def mock_kafka_producer():
    """Create a mock Kafka producer."""
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock()
    producer.send = AsyncMock()
    return producer


@pytest.fixture
def mock_kafka_consumer():
    """Create a mock Kafka consumer."""
    consumer = AsyncMock()
    return consumer


@pytest.fixture
def sample_event():
    """Create a sample domain event."""
    return DomainEvent(
        event_type="test.event",
        payload={"message": "hello", "number": 42},
        aggregate_id="agg-123",
        correlation_id="corr-456",
        causation_id="cause-789",
    )


class TestKafkaEventBusInitialization:
    """Tests for KafkaEventBus initialization."""

    def test_default_initialization(self) -> None:
        """Test initialization with default parameters."""
        bus = KafkaEventBus()

        assert bus._bootstrap_servers == "localhost:9092"
        assert bus._client_id == "novel-engine-event-bus"
        assert bus._group_id == "novel-engine-consumer-group"
        assert bus._enable_idempotence is True
        assert bus._max_retries == 3

    def test_custom_initialization(self) -> None:
        """Test initialization with custom parameters."""
        bus = KafkaEventBus(
            bootstrap_servers="broker1:9092,broker2:9092",
            client_id="custom-client",
            group_id="custom-group",
            enable_idempotence=False,
            max_retries=5,
            dead_letter_topic="dlq-topic",
        )

        assert bus._bootstrap_servers == "broker1:9092,broker2:9092"
        assert bus._client_id == "custom-client"
        assert bus._group_id == "custom-group"
        assert bus._enable_idempotence is False
        assert bus._max_retries == 5
        assert bus._dead_letter_topic == "dlq-topic"


class TestKafkaEventBusSerialization:
    """Tests for event serialization/deserialization."""

    def test_serialize_event(self, sample_event) -> None:
        """Test serializing a domain event."""
        bus = KafkaEventBus()
        data = bus._serialize_event(sample_event)

        # Should be valid JSON
        event_dict = json.loads(data.decode("utf-8"))

        assert event_dict["event_id"] == str(sample_event.event_id)
        assert event_dict["event_type"] == "test.event"
        assert event_dict["aggregate_id"] == "agg-123"
        assert event_dict["payload"] == {"message": "hello", "number": 42}
        assert event_dict["correlation_id"] == "corr-456"
        assert event_dict["causation_id"] == "cause-789"
        assert "occurred_on" in event_dict
        assert "metadata" in event_dict

    def test_deserialize_event(self, sample_event) -> None:
        """Test deserializing event data."""
        bus = KafkaEventBus()
        data = bus._serialize_event(sample_event)
        restored = bus._deserialize_event(data)

        assert restored.event_id == sample_event.event_id
        assert restored.event_type == sample_event.event_type
        assert restored.aggregate_id == sample_event.aggregate_id
        assert restored.payload == sample_event.payload
        assert restored.correlation_id == sample_event.correlation_id
        assert restored.causation_id == sample_event.causation_id
        assert isinstance(restored.occurred_on, datetime)

    def test_serialize_event_with_uuid_payload(self) -> None:
        """Test serializing event with UUID in payload."""
        test_uuid = uuid4()
        event = DomainEvent(
            event_type="test.event",
            payload={"id": test_uuid, "name": "test"},
        )

        bus = KafkaEventBus()
        data = bus._serialize_event(event)
        event_dict = json.loads(data.decode("utf-8"))

        assert event_dict["payload"]["id"] == str(test_uuid)


class TestKafkaEventBusLifecycle:
    """Tests for KafkaEventBus lifecycle."""

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_start_initializes_producer(self, mock_producer_class) -> None:
        """Test that start initializes the Kafka producer."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()

        mock_producer_class.assert_called_once()
        mock_producer.start.assert_called_once()
        assert bus._started is True

        await bus.stop()

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_stop_cleans_up_producer(self, mock_producer_class) -> None:
        """Test that stop cleans up the producer."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()
        await bus.stop()

        mock_producer.stop.assert_called_once()
        assert bus._producer is None

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self) -> None:
        """Test that starting twice doesn't fail."""
        bus = KafkaEventBus()

        with patch.object(bus, "_producer", AsyncMock()):
            bus._started = True
            await bus.start()  # Should not raise

    @pytest.mark.asyncio
    async def test_double_stop_is_safe(self) -> None:
        """Test that stopping twice doesn't fail."""
        bus = KafkaEventBus()
        await bus.stop()  # Should not raise


class TestKafkaEventBusPublish:
    """Tests for publishing events."""

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_publish_sends_to_correct_topic(
        self, mock_producer_class, sample_event
    ) -> None:
        """Test that publish sends to the correct topic."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()

        await bus.publish(sample_event)

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == "test.event"

        await bus.stop()

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_publish_with_custom_topic(
        self, mock_producer_class, sample_event
    ) -> None:
        """Test publishing to a custom topic."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()

        await bus.publish(sample_event, topic="custom-topic")

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == "custom-topic"

        await bus.stop()

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_publish_uses_aggregate_id_as_key(
        self, mock_producer_class, sample_event
    ) -> None:
        """Test that aggregate ID is used as message key."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()

        await bus.publish(sample_event)

        call_kwargs = mock_producer.send_and_wait.call_args[1]
        assert call_kwargs["key"] == b"agg-123"

        await bus.stop()

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_publish_without_aggregate_id(self, mock_producer_class) -> None:
        """Test publishing event without aggregate ID."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        event = DomainEvent(event_type="test.event", payload={})

        bus = KafkaEventBus()
        await bus.start()

        await bus.publish(event)

        call_kwargs = mock_producer.send_and_wait.call_args[1]
        assert call_kwargs["key"] is None

        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_before_start_raises_error(self, sample_event) -> None:
        """Test that publishing before start raises error."""
        bus = KafkaEventBus()

        with pytest.raises(EventBusNotStartedError):
            await bus.publish(sample_event)

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_publish_error_handling(
        self, mock_producer_class, sample_event
    ) -> None:
        """Test error handling during publish."""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait.side_effect = Exception("Kafka error")
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus()
        await bus.start()

        with pytest.raises(EventPublishError, match="Failed to publish event"):
            await bus.publish(sample_event)

        await bus.stop()


class TestKafkaEventBusSubscribe:
    """Tests for subscribing to events."""

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaConsumer")
    async def test_subscribe_creates_consumer(
        self, mock_consumer_class, mock_producer_class
    ) -> None:
        """Test that subscribe creates a Kafka consumer."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        mock_consumer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer

        bus = KafkaEventBus()
        await bus.start()

        handler = AsyncMock()
        await bus.subscribe("test.event", handler)

        mock_consumer_class.assert_called_once()
        mock_consumer.start.assert_called_once()

        await bus.stop()

    @pytest.mark.asyncio
    async def test_subscribe_before_start_raises_error(self) -> None:
        """Test that subscribing before start raises error."""
        bus = KafkaEventBus()

        with pytest.raises(EventBusNotStartedError):
            await bus.subscribe("test.event", AsyncMock())

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaConsumer")
    async def test_unsubscribe_removes_handler(
        self, mock_consumer_class, mock_producer_class
    ) -> None:
        """Test that unsubscribe removes handler from registry."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        mock_consumer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer

        bus = KafkaEventBus()
        await bus.start()

        handler = AsyncMock()
        await bus.subscribe("test.event", handler)

        # Handler should be registered
        assert handler in bus._handlers.get("test.event", set())

        # Unsubscribe
        await bus.unsubscribe("test.event", handler)

        # Handler should be removed
        assert handler not in bus._handlers.get("test.event", set())

        await bus.stop()


class TestKafkaEventBusSecurity:
    """Tests for security configuration."""

    def test_ssl_security_config(self) -> None:
        """Test SSL security configuration."""
        import ssl

        ssl_context = ssl.create_default_context()
        bus = KafkaEventBus(ssl_context=ssl_context)

        config = bus._get_security_config()
        assert config["security_protocol"] == "SSL"
        assert config["ssl_context"] is ssl_context

    def test_sasl_security_config(self) -> None:
        """Test SASL security configuration."""
        bus = KafkaEventBus(
            sasl_mechanism="PLAIN",
            sasl_plain_username="user",
            sasl_plain_password="pass",
        )

        config = bus._get_security_config()
        assert config["security_protocol"] == "SASL_PLAINTEXT"
        assert config["sasl_mechanism"] == "PLAIN"
        assert config["sasl_plain_username"] == "user"
        assert config["sasl_plain_password"] == "pass"

    def test_ssl_and_sasl_security_config(self) -> None:
        """Test combined SSL and SASL configuration."""
        import ssl

        ssl_context = ssl.create_default_context()
        bus = KafkaEventBus(
            ssl_context=ssl_context,
            sasl_mechanism="SCRAM-SHA-256",
        )

        config = bus._get_security_config()
        assert config["security_protocol"] == "SASL_SSL"

    def test_no_security_config(self) -> None:
        """Test configuration without security."""
        bus = KafkaEventBus()
        config = bus._get_security_config()
        assert config == {}


class TestKafkaEventBusDeadLetterQueue:
    """Tests for dead letter queue functionality."""

    @pytest.mark.asyncio
    @patch("src.shared.infrastructure.messaging.kafka_event_bus.AIOKafkaProducer")
    async def test_failed_message_sent_to_dlq(self, mock_producer_class) -> None:
        """Test that failed messages are sent to dead letter queue."""
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        bus = KafkaEventBus(dead_letter_topic="dlq-topic")
        await bus.start()

        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = "test-topic"
        mock_msg.partition = 0
        mock_msg.offset = 123

        event = DomainEvent(event_type="test.event", payload={})
        error = Exception("Processing failed")

        # Call the dead letter handler
        await bus._handle_failed_message(mock_msg, event, error)

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "dlq-topic"

        # Verify error info is included
        error_data = json.loads(call_args[0][1].decode())
        assert error_data["error"] == "Processing failed"
        assert error_data["error_type"] == "Exception"
        assert error_data["original_topic"] == "test-topic"
        assert error_data["event_id"] == str(event.event_id)

        await bus.stop()

    @pytest.mark.asyncio
    async def test_dlq_error_handling(self) -> None:
        """Test DLQ error handling when DLQ itself fails."""
        bus = KafkaEventBus(dead_letter_topic="dlq-topic")

        mock_msg = MagicMock()
        event = DomainEvent(event_type="test.event", payload={})
        error = Exception("Original error")

        # Should not raise even with no producer
        await bus._handle_failed_message(mock_msg, event, error)
