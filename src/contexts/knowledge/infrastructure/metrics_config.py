"""
Knowledge Management Prometheus Metrics Configuration

Metrics instrumentation for Knowledge Management bounded context.

Constitution Compliance:
- Article VII (Observability): Prometheus metrics for monitoring
- SC-001: Track Admin operation duration (≤30s target)
- SC-002: Track knowledge retrieval performance (≤500ms target)
"""

from prometheus_client import Counter, Gauge, Histogram, Summary

# ==============================================================================
# Knowledge Entry CRUD Metrics
# ==============================================================================

knowledge_entry_created_total = Counter(
    "knowledge_entry_created_total",
    "Total number of knowledge entries created",
    ["knowledge_type", "access_level"],
)

knowledge_entry_updated_total = Counter(
    "knowledge_entry_updated_total",
    "Total number of knowledge entries updated",
    ["knowledge_type"],
)

knowledge_entry_deleted_total = Counter(
    "knowledge_entry_deleted_total",
    "Total number of knowledge entries deleted",
    ["knowledge_type"],
)

# ==============================================================================
# Knowledge Retrieval Metrics (SC-002: <500ms target)
# ==============================================================================

knowledge_retrieval_duration_seconds = Histogram(
    "knowledge_retrieval_duration_seconds",
    "Duration of knowledge retrieval operations in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],  # 10ms to 5s
)

knowledge_retrieval_count_total = Counter(
    "knowledge_retrieval_count_total",
    "Total number of knowledge retrieval operations",
    ["agent_character_id", "turn_number"],
)

knowledge_entries_retrieved_total = Summary(
    "knowledge_entries_retrieved_total",
    "Number of knowledge entries retrieved per operation",
    ["agent_character_id"],
)

# ==============================================================================
# Access Control Metrics
# ==============================================================================

access_denied_total = Counter(
    "knowledge_access_denied_total",
    "Total number of access denied events",
    ["entry_id", "agent_character_id", "access_level"],
)

access_granted_total = Counter(
    "knowledge_access_granted_total",
    "Total number of access granted events",
    ["access_level"],
)

# ==============================================================================
# Admin API Metrics (SC-001: <30s target)
# ==============================================================================

admin_operation_duration_seconds = Histogram(
    "knowledge_admin_operation_duration_seconds",
    "Duration of admin operations in seconds",
    ["operation"],  # create, update, delete, list, get
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],  # 100ms to 60s
)

admin_operation_total = Counter(
    "knowledge_admin_operation_total",
    "Total number of admin operations",
    ["operation", "status"],  # status: success, error
)

# ==============================================================================
# Database Metrics
# ==============================================================================

database_query_duration_seconds = Histogram(
    "knowledge_database_query_duration_seconds",
    "Duration of database queries in seconds",
    ["query_type"],  # insert, update, delete, select
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],  # 1ms to 1s
)

database_connection_pool_size = Gauge(
    "knowledge_database_connection_pool_size",
    "Current size of database connection pool",
)

database_connection_pool_active = Gauge(
    "knowledge_database_connection_pool_active",
    "Number of active database connections",
)

# ==============================================================================
# Event Publishing Metrics
# ==============================================================================

event_published_total = Counter(
    "knowledge_event_published_total",
    "Total number of domain events published",
    ["event_type"],  # created, updated, deleted
)

event_publish_failed_total = Counter(
    "knowledge_event_publish_failed_total",
    "Total number of failed event publishing attempts",
    ["event_type", "error_type"],
)

event_publish_duration_seconds = Histogram(
    "knowledge_event_publish_duration_seconds",
    "Duration of event publishing operations in seconds",
    ["event_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],  # 10ms to 1s
)

# ==============================================================================
# Migration Metrics
# ==============================================================================

migration_entries_processed_total = Counter(
    "knowledge_migration_entries_processed_total",
    "Total number of entries processed during Markdown migration",
    ["status"],  # success, error, skipped
)

migration_duration_seconds = Histogram(
    "knowledge_migration_duration_seconds",
    "Duration of migration operations in seconds",
    ["operation"],  # migrate, verify, rollback
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],  # 1s to 5min
)

# ==============================================================================
# System Health Metrics
# ==============================================================================

knowledge_system_health = Gauge(
    "knowledge_system_health",
    "Overall health status of Knowledge Management system (1=healthy, 0=unhealthy)",
)

knowledge_entries_count = Gauge(
    "knowledge_entries_count",
    "Current total number of knowledge entries",
    ["knowledge_type", "access_level"],
)

# ==============================================================================
# Metric Helper Functions
# ==============================================================================


def record_knowledge_entry_created(knowledge_type: str, access_level: str) -> None:
    """Record knowledge entry creation metric."""
    knowledge_entry_created_total.labels(
        knowledge_type=knowledge_type,
        access_level=access_level,
    ).inc()


def record_knowledge_entry_updated(knowledge_type: str) -> None:
    """Record knowledge entry update metric."""
    knowledge_entry_updated_total.labels(knowledge_type=knowledge_type).inc()


def record_knowledge_entry_deleted(knowledge_type: str) -> None:
    """Record knowledge entry deletion metric."""
    knowledge_entry_deleted_total.labels(knowledge_type=knowledge_type).inc()


def record_knowledge_retrieval(
    agent_character_id: str,
    turn_number: int,
    entry_count: int,
    duration_seconds: float,
) -> None:
    """Record knowledge retrieval metrics."""
    knowledge_retrieval_count_total.labels(
        agent_character_id=agent_character_id,
        turn_number=str(turn_number),
    ).inc()

    knowledge_entries_retrieved_total.labels(
        agent_character_id=agent_character_id,
    ).observe(entry_count)

    knowledge_retrieval_duration_seconds.labels(
        operation="retrieve_agent_context",
    ).observe(duration_seconds)


def record_access_denied(
    entry_id: str,
    agent_character_id: str,
    access_level: str,
) -> None:
    """Record access denied metric."""
    access_denied_total.labels(
        entry_id=entry_id,
        agent_character_id=agent_character_id,
        access_level=access_level,
    ).inc()


def record_access_granted(access_level: str) -> None:
    """Record access granted metric."""
    access_granted_total.labels(access_level=access_level).inc()


def record_admin_operation(
    operation: str,
    duration_seconds: float,
    status: str,
) -> None:
    """Record admin operation metrics."""
    admin_operation_duration_seconds.labels(operation=operation).observe(
        duration_seconds
    )
    admin_operation_total.labels(operation=operation, status=status).inc()


def record_event_published(event_type: str, duration_seconds: float) -> None:
    """Record event publishing metrics."""
    event_published_total.labels(event_type=event_type).inc()
    event_publish_duration_seconds.labels(event_type=event_type).observe(
        duration_seconds
    )


def record_event_publish_failed(event_type: str, error_type: str) -> None:
    """Record failed event publishing metric."""
    event_publish_failed_total.labels(
        event_type=event_type,
        error_type=error_type,
    ).inc()


def update_knowledge_entries_count(
    knowledge_type: str,
    access_level: str,
    count: int,
) -> None:
    """Update total knowledge entries count gauge."""
    knowledge_entries_count.labels(
        knowledge_type=knowledge_type,
        access_level=access_level,
    ).set(count)


def set_system_health(is_healthy: bool) -> None:
    """Set system health status (1=healthy, 0=unhealthy)."""
    knowledge_system_health.set(1 if is_healthy else 0)
