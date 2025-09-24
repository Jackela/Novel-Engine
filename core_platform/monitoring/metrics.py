"""
Platform Metrics Collection
============================

Metrics collection and monitoring for platform services including
outbox pattern, event bus, and other core components.
"""

import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class BaseMetrics:
    """Base class for metrics collection."""

    def __init__(self):
        """Initialize base metrics."""
        self._metrics: Dict[str, Any] = defaultdict(int)
        self._timing_metrics: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._start_time = time.time()

    def increment(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._metrics[metric_name] += value

    def set_gauge(self, metric_name: str, value: Any) -> None:
        """Set a gauge metric value."""
        with self._lock:
            self._metrics[metric_name] = value

    def record_timing(self, metric_name: str, duration_ms: float) -> None:
        """Record timing metric."""
        with self._lock:
            self._timing_metrics[metric_name].append(duration_ms)
            # Keep only last 1000 measurements
            if len(self._timing_metrics[metric_name]) > 1000:
                self._timing_metrics[metric_name] = self._timing_metrics[
                    metric_name
                ][-1000:]

    def get_metric(self, metric_name: str) -> Any:
        """Get specific metric value."""
        with self._lock:
            return self._metrics.get(metric_name, 0)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            metrics = dict(self._metrics)

            # Add timing statistics
            timing_stats = {}
            for metric_name, timings in self._timing_metrics.items():
                if timings:
                    timing_stats[f"{metric_name}_avg"] = sum(timings) / len(
                        timings
                    )
                    timing_stats[f"{metric_name}_min"] = min(timings)
                    timing_stats[f"{metric_name}_max"] = max(timings)
                    timing_stats[f"{metric_name}_count"] = len(timings)

            metrics.update(timing_stats)
            metrics["uptime_seconds"] = time.time() - self._start_time

            return metrics

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._timing_metrics.clear()


class OutboxMetrics(BaseMetrics):
    """Metrics for outbox pattern operations."""

    def __init__(self):
        """Initialize outbox metrics."""
        super().__init__()

    def record_outbox_event_stored(self) -> None:
        """Record that an event was stored in outbox."""
        self.increment("outbox_events_stored_total")

    def record_outbox_event_store_failed(self) -> None:
        """Record that event storage failed."""
        self.increment("outbox_events_store_failed_total")

    def record_outbox_batch_stored(self) -> None:
        """Record that a batch was stored in outbox."""
        self.increment("outbox_batches_stored_total")

    def record_outbox_batch_store_failed(self) -> None:
        """Record that batch storage failed."""
        self.increment("outbox_batches_store_failed_total")

    def record_outbox_batch_processing_start(self, batch_size: int) -> None:
        """Record start of batch processing."""
        self.increment("outbox_batch_processing_started_total")
        self.set_gauge("outbox_current_batch_size", batch_size)

    def record_outbox_events_published(self, count: int) -> None:
        """Record successful event publishing."""
        self.increment("outbox_events_published_total", count)

    def record_outbox_events_failed(self, count: int) -> None:
        """Record failed event publishing."""
        self.increment("outbox_events_failed_total", count)

    def record_outbox_events_cleaned(self, count: int) -> None:
        """Record cleaned up events."""
        self.increment("outbox_events_cleaned_total", count)

    def record_outbox_processing_error(self) -> None:
        """Record processing error."""
        self.increment("outbox_processing_errors_total")


class EventBusMetrics(BaseMetrics):
    """Metrics for event bus operations."""

    def __init__(self):
        """Initialize event bus metrics."""
        super().__init__()
        self._event_type_counters = Counter()
        self._topic_counters = Counter()

    def record_event_publish_start(self) -> None:
        """Record start of event publishing."""
        self.increment("event_bus_publish_started_total")

    def record_event_published(self, event_type: str, topic: str) -> None:
        """Record successful event publishing."""
        self.increment("event_bus_events_published_total")
        self._event_type_counters[event_type] += 1
        self._topic_counters[topic] += 1

    def record_event_publish_failed(self, event_type: str) -> None:
        """Record failed event publishing."""
        self.increment("event_bus_events_publish_failed_total")
        self.increment(f"event_bus_events_failed_{event_type}")

    def record_batch_publish_start(self) -> None:
        """Record start of batch publishing."""
        self.increment("event_bus_batch_publish_started_total")

    def record_batch_published(self, count: int) -> None:
        """Record successful batch publishing."""
        self.increment("event_bus_batches_published_total")
        self.increment("event_bus_batch_events_published_total", count)

    def record_batch_publish_failed(self) -> None:
        """Record failed batch publishing."""
        self.increment("event_bus_batches_publish_failed_total")

    def record_event_received(self, event_type: str) -> None:
        """Record event received for handling."""
        self.increment("event_bus_events_received_total")
        self.increment(f"event_bus_events_received_{event_type}")

    def record_event_handled(self, event_type: str) -> None:
        """Record successful event handling."""
        self.increment("event_bus_events_handled_total")
        self.increment(f"event_bus_events_handled_{event_type}")

    def record_event_handling_failed(self, event_type: str) -> None:
        """Record failed event handling."""
        self.increment("event_bus_events_handling_failed_total")
        self.increment(f"event_bus_events_failed_{event_type}")

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics including event type and topic breakdowns."""
        metrics = super().get_all_metrics()

        # Add event type breakdown
        metrics["event_types"] = dict(
            self._event_type_counters.most_common(10)
        )
        metrics["topics"] = dict(self._topic_counters.most_common(10))

        return metrics


class KafkaMetrics(BaseMetrics):
    """Metrics for Kafka client operations."""

    def __init__(self):
        """Initialize Kafka metrics."""
        super().__init__()

    def record_connection_attempt(self) -> None:
        """Record Kafka connection attempt."""
        self.increment("kafka_connection_attempts_total")

    def record_connection_success(self) -> None:
        """Record successful Kafka connection."""
        self.increment("kafka_connections_successful_total")
        self.set_gauge("kafka_connected", 1)

    def record_connection_failed(self) -> None:
        """Record failed Kafka connection."""
        self.increment("kafka_connections_failed_total")
        self.set_gauge("kafka_connected", 0)

    def record_message_published(self, topic: str) -> None:
        """Record successful message publishing."""
        self.increment("kafka_messages_published_total")
        self.increment(f"kafka_messages_published_{topic}")

    def record_message_publish_failed(self, topic: str) -> None:
        """Record failed message publishing."""
        self.increment("kafka_messages_publish_failed_total")
        self.increment(f"kafka_messages_failed_{topic}")

    def record_batch_published(self, topic: str, count: int) -> None:
        """Record successful batch publishing."""
        self.increment("kafka_batches_published_total")
        self.increment("kafka_batch_messages_published_total", count)
        self.increment(f"kafka_batch_published_{topic}")


class MessagingMetrics(BaseMetrics):
    """Metrics for messaging operations including Kafka and event bus."""

    def __init__(self):
        """Initialize messaging metrics."""
        super().__init__()

    def record_message_sent(self, topic: str) -> None:
        """Record message sent."""
        self.increment("messaging_messages_sent_total")
        self.increment(f"messaging_messages_sent_{topic}")

    def record_message_send_failed(self, topic: str) -> None:
        """Record failed message send."""
        self.increment("messaging_messages_send_failed_total")
        self.increment(f"messaging_messages_failed_{topic}")

    def record_message_received(self, topic: str) -> None:
        """Record message received."""
        self.increment("messaging_messages_received_total")
        self.increment(f"messaging_messages_received_{topic}")


class ProjectorMetrics(BaseMetrics):
    """Metrics for projection operations."""

    def __init__(self):
        """Initialize projector metrics."""
        super().__init__()

    def record_projection_started(self, projection_type: str) -> None:
        """Record projection started."""
        self.increment("projector_projections_started_total")
        self.increment(f"projector_projections_started_{projection_type}")

    def record_projection_completed(self, projection_type: str) -> None:
        """Record projection completed."""
        self.increment("projector_projections_completed_total")
        self.increment(f"projector_projections_completed_{projection_type}")

    def record_projection_failed(self, projection_type: str) -> None:
        """Record projection failed."""
        self.increment("projector_projections_failed_total")
        self.increment(f"projector_projections_failed_{projection_type}")


class DatabaseMetrics(BaseMetrics):
    """Metrics for database operations."""

    def __init__(self):
        """Initialize database metrics."""
        super().__init__()

    def record_connection_created(self) -> None:
        """Record database connection creation."""
        self.increment("db_connections_created_total")

    def record_connection_closed(self) -> None:
        """Record database connection closure."""
        self.increment("db_connections_closed_total")

    def record_query_executed(self, query_type: str = "unknown") -> None:
        """Record database query execution."""
        self.increment("db_queries_executed_total")
        self.increment(f"db_queries_{query_type}_total")

    def record_query_failed(self, query_type: str = "unknown") -> None:
        """Record failed database query."""
        self.increment("db_queries_failed_total")
        self.increment(f"db_queries_failed_{query_type}_total")

    def record_transaction_committed(self) -> None:
        """Record successful transaction commit."""
        self.increment("db_transactions_committed_total")

    def record_transaction_rolled_back(self) -> None:
        """Record transaction rollback."""
        self.increment("db_transactions_rolled_back_total")


# Global metrics instances
_outbox_metrics: Optional[OutboxMetrics] = None
_event_bus_metrics: Optional[EventBusMetrics] = None
_kafka_metrics: Optional[KafkaMetrics] = None
_database_metrics: Optional[DatabaseMetrics] = None


def get_outbox_metrics() -> OutboxMetrics:
    """Get global outbox metrics instance."""
    global _outbox_metrics
    if _outbox_metrics is None:
        _outbox_metrics = OutboxMetrics()
    return _outbox_metrics


def get_event_bus_metrics() -> EventBusMetrics:
    """Get global event bus metrics instance."""
    global _event_bus_metrics
    if _event_bus_metrics is None:
        _event_bus_metrics = EventBusMetrics()
    return _event_bus_metrics


def get_kafka_metrics() -> KafkaMetrics:
    """Get global Kafka metrics instance."""
    global _kafka_metrics
    if _kafka_metrics is None:
        _kafka_metrics = KafkaMetrics()
    return _kafka_metrics


def get_database_metrics() -> DatabaseMetrics:
    """Get global database metrics instance."""
    global _database_metrics
    if _database_metrics is None:
        _database_metrics = DatabaseMetrics()
    return _database_metrics


def get_all_platform_metrics() -> Dict[str, Any]:
    """Get all platform metrics."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outbox": get_outbox_metrics().get_all_metrics(),
        "event_bus": get_event_bus_metrics().get_all_metrics(),
        "kafka": get_kafka_metrics().get_all_metrics(),
        "database": get_database_metrics().get_all_metrics(),
    }


def reset_all_metrics() -> None:
    """Reset all platform metrics."""
    global _outbox_metrics, _event_bus_metrics, _kafka_metrics, _database_metrics

    if _outbox_metrics:
        _outbox_metrics.reset()
    if _event_bus_metrics:
        _event_bus_metrics.reset()
    if _kafka_metrics:
        _kafka_metrics.reset()
    if _database_metrics:
        _database_metrics.reset()
