"""
Base Models and Common Database Patterns
=======================================

Base model classes, mixins, and common database patterns for Novel Engine platform.
"""

import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, TypeVar

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func

from .database import Base

T = TypeVar("T", bound="BaseModel")


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin to add soft delete functionality."""

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    def soft_delete(self):
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)

    def restore(self):
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """Mixin to add audit fields for tracking changes."""

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    version = Column(String(50), nullable=True)

    @declared_attr
    def audit_data(cls):
        return Column(JSON, nullable=True)


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common functionality.

    Features:
    - UUID primary key
    - Automatic timestamps
    - JSON serialization
    - Common query methods
    - Validation hooks
    """

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    def to_dict(
        self, exclude: Optional[List[str]] = None, include_relationships: bool = False
    ) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        exclude = exclude or []
        result = {}

        # Include column attributes
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle UUID serialization
                if isinstance(value, uuid.UUID):
                    value = str(value)
                # Handle datetime serialization
                elif isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value

        # Include relationships if requested
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                if relationship.key not in exclude:
                    value = getattr(self, relationship.key)
                    if value is not None:
                        if hasattr(value, "to_dict"):
                            result[relationship.key] = value.to_dict()
                        elif hasattr(value, "__iter__"):
                            result[relationship.key] = [
                                (
                                    item.to_dict()
                                    if hasattr(item, "to_dict")
                                    else str(item)
                                )
                                for item in value
                            ]
                        else:
                            result[relationship.key] = str(value)

        return result

    def update(self, **kwargs) -> None:
        """Update model attributes from keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def create(cls, **kwargs) -> "BaseModel":
        """Create a new instance with given attributes."""
        return cls(**kwargs)

    def validate(self) -> List[str]:
        """Validate the model instance. Override in subclasses."""
        return []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """Base model with soft delete functionality."""

    __abstract__ = True


class AuditableModel(BaseModel, AuditMixin):
    """Base model with full audit trail."""

    __abstract__ = True


class FullAuditModel(BaseModel, SoftDeleteMixin, AuditMixin):
    """Base model with soft delete and audit trail."""

    __abstract__ = True


class OutboxEvent(BaseModel):
    """
    Outbox pattern event storage for reliable message delivery.

    Stores events that need to be published to message queues,
    ensuring eventual consistency across service boundaries.
    """

    __tablename__ = "outbox_events"

    # Event identification
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False)
    event_type = Column(String(200), nullable=False)
    event_version = Column(String(20), nullable=False, default="1.0.0")

    # Event data
    event_data = Column(JSON, nullable=False)

    # Event metadata
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(String(10), default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Publishing details
    topic = Column(String(200), nullable=False)
    partition_key = Column(String(200), nullable=True)

    def mark_processed(self):
        """Mark the event as successfully processed."""
        self.processed = True
        self.processed_at = datetime.now(UTC)
        self.error_message = None

    def mark_failed(self, error: str):
        """Mark the event as failed with error message."""
        self.processed = False
        self.error_message = error
        self.retry_count += 1

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if the event can be retried."""
        return self.retry_count < max_retries


class EventStore(BaseModel):
    """
    Event store for event sourcing patterns.

    Stores all domain events in append-only fashion for
    event replay, audit trails, and temporal queries.
    """

    __tablename__ = "event_store"

    # Stream identification
    stream_id = Column(String(200), nullable=False, index=True)
    stream_type = Column(String(100), nullable=False)

    # Event identification
    event_id = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    event_type = Column(String(200), nullable=False)
    event_version = Column(String(20), nullable=False)

    # Event sequencing
    sequence_number = Column(String(20), nullable=False)
    global_sequence = Column(String(50), nullable=False, unique=True)

    # Event data
    event_data = Column(JSON, nullable=False)
    event_metadata = Column(JSON, nullable=True)

    # Event context
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamp (from TimestampMixin)
    # created_at is the event timestamp

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.global_sequence:
            self.global_sequence = f"{int(datetime.now(UTC).timestamp() * 1000000)}"


# Event listeners for automatic audit trail
@event.listens_for(AuditableModel, "before_insert", propagate=True)
def set_audit_create(mapper, connection, target):
    """Set audit fields on creation."""
    # This would typically get user context from request context
    # For now, we'll leave it as None - implement based on your auth system
    pass


@event.listens_for(AuditableModel, "before_update", propagate=True)
def set_audit_update(mapper, connection, target):
    """Set audit fields on update."""
    # This would typically get user context from request context
    # For now, we'll leave it as None - implement based on your auth system
    pass
