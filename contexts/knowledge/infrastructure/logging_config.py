"""
Knowledge Management Logging Configuration

Structured logging setup for Knowledge Management bounded context with
correlation IDs, context tracking, and performance monitoring.

Constitution Compliance:
- Article VII (Observability): Structured logging for all operations
- FR-011: Audit trail for all knowledge entry changes
"""

from typing import Any, Dict, Optional

from src.core.logging_system import (
    LogContext,
    PerformanceTracker,
    StructuredLogger,
)

def get_knowledge_logger(
    component: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> StructuredLogger:
    """
    Get a structured logger for Knowledge Management operations.

    Args:
        component: Component name (e.g., "repository", "use_case", "api")
        correlation_id: Optional correlation ID for request tracing
        user_id: Optional user ID for audit trail

    Returns:
        StructuredLogger instance configured for Knowledge Management

    Usage:
        logger = get_knowledge_logger(
            component="CreateKnowledgeEntryUseCase",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="user-001"
        )
        logger.info("Creating knowledge entry", entry_id="123")
    """
    context = LogContext(
        correlation_id=correlation_id,
        user_id=user_id,
        component=f"knowledge.{component}",
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    return structured_logger


def log_knowledge_entry_created(
    entry_id: str,
    knowledge_type: str,
    created_by: str,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log knowledge entry creation event.

    Args:
        entry_id: Knowledge entry ID
        knowledge_type: Type of knowledge (profile, objective, etc.)
        created_by: User ID who created the entry
        correlation_id: Optional correlation ID
        metadata: Optional additional metadata
    """
    context = LogContext(
        correlation_id=correlation_id,
        user_id=created_by,
        component="knowledge.repository",
        operation="create_entry",
        metadata=metadata or {},
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    structured_logger.audit(
        "Knowledge entry created",
        entry_id=entry_id,
        knowledge_type=knowledge_type,
        created_by=created_by,
    )


def log_knowledge_entry_updated(
    entry_id: str,
    updated_by: str,
    correlation_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log knowledge entry update event.

    Args:
        entry_id: Knowledge entry ID
        updated_by: User ID who updated the entry
        correlation_id: Optional correlation ID
        changes: Optional dictionary of changed fields
    """
    context = LogContext(
        correlation_id=correlation_id,
        user_id=updated_by,
        component="knowledge.repository",
        operation="update_entry",
        metadata={"changes": changes} if changes else {},
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    structured_logger.audit(
        "Knowledge entry updated",
        entry_id=entry_id,
        updated_by=updated_by,
        changes=changes,
    )


def log_knowledge_entry_deleted(
    entry_id: str,
    deleted_by: str,
    correlation_id: Optional[str] = None,
    snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log knowledge entry deletion event.

    Args:
        entry_id: Knowledge entry ID
        deleted_by: User ID who deleted the entry
        correlation_id: Optional correlation ID
        snapshot: Optional snapshot of deleted entry for audit trail
    """
    context = LogContext(
        correlation_id=correlation_id,
        user_id=deleted_by,
        component="knowledge.repository",
        operation="delete_entry",
        metadata={"snapshot": snapshot} if snapshot else {},
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    structured_logger.audit(
        "Knowledge entry deleted",
        entry_id=entry_id,
        deleted_by=deleted_by,
    )


def log_knowledge_retrieval(
    agent_character_id: str,
    turn_number: int,
    entry_count: int,
    duration_ms: float,
    correlation_id: Optional[str] = None,
) -> None:
    """
    Log knowledge retrieval operation for agent context assembly.

    Args:
        agent_character_id: Character ID of agent
        turn_number: Simulation turn number
        entry_count: Number of entries retrieved
        duration_ms: Retrieval duration in milliseconds
        correlation_id: Optional correlation ID
    """
    context = LogContext(
        correlation_id=correlation_id,
        component="knowledge.retrieval",
        operation="retrieve_agent_context",
        metadata={
            "agent_character_id": agent_character_id,
            "turn_number": turn_number,
            "entry_count": entry_count,
        },
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    structured_logger.performance(
        "Knowledge retrieval completed",
        agent_character_id=agent_character_id,
        turn_number=turn_number,
        entry_count=entry_count,
        duration_ms=duration_ms,
    )


def log_access_denied(
    entry_id: str,
    agent_character_id: str,
    access_level: str,
    correlation_id: Optional[str] = None,
) -> None:
    """
    Log access control violation for security monitoring.

    Args:
        entry_id: Knowledge entry ID that was denied
        agent_character_id: Character ID that was denied access
        access_level: Access level of the entry
        correlation_id: Optional correlation ID
    """
    context = LogContext(
        correlation_id=correlation_id,
        component="knowledge.access_control",
        operation="check_access",
        metadata={
            "entry_id": entry_id,
            "agent_character_id": agent_character_id,
            "access_level": access_level,
        },
    )

    structured_logger = StructuredLogger("novel_engine.knowledge")
    structured_logger.push_context(context)
    structured_logger.security(
        "Access denied to knowledge entry",
        entry_id=entry_id,
        agent_character_id=agent_character_id,
        access_level=access_level,
    )


class KnowledgePerformanceTracker(PerformanceTracker):
    """
    Performance tracker for Knowledge Management operations.

    Extends PerformanceTracker with Knowledge-specific context.
    """

    def __init__(
        self,
        operation: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize performance tracker for Knowledge Management.

        Args:
            operation: Operation name (e.g., "retrieve_agent_context")
            correlation_id: Optional correlation ID
            metadata: Optional operation metadata
        """
        context = LogContext(
            correlation_id=correlation_id,
            component="knowledge.performance",
            operation=operation,
            metadata=metadata or {},
        )
        super().__init__(operation=operation, context=context)
