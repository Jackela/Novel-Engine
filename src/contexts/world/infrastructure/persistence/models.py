"""SQLAlchemy models for world state persistence."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class WorldStateModel(Base):
    """SQLAlchemy model for WorldState aggregate."""

    __tablename__ = "world_states"

    id = Column(String, primary_key=True)
    story_id = Column(String, nullable=True)
    version = Column(Integer, default=1)
    calendar = Column(JSON, nullable=True)
    factions = Column(JSON, default=dict)
    locations = Column(JSON, default=dict)
    events = Column(JSON, default=list)
    meta_data = Column("metadata", JSON, default=dict)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "story_id": self.story_id,
            "version": self.version,
            "calendar": self.calendar,
            "factions": self.factions,
            "locations": self.locations,
            "events": self.events,
            "metadata": self.meta_data,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_domain_aggregate(self) -> Any:
        """Convert model to domain aggregate."""
        # Placeholder implementation
        return None

    @classmethod
    def from_domain_aggregate(cls, aggregate: Any) -> "WorldStateModel":
        """Create model from domain aggregate."""
        # Placeholder implementation
        return cls(id=str(aggregate.id) if hasattr(aggregate, "id") else "")

    def update_from_domain_aggregate(self, aggregate: Any) -> None:
        """Update model from domain aggregate."""
        # Placeholder implementation
        pass

    def validate(self) -> list[str]:
        """Validate the model."""
        return []

    def soft_delete(self) -> None:
        """Soft delete the model."""
        self.is_deleted = True  # type: ignore[assignment]

    def get_entity_count(self) -> int:
        """Get entity count."""
        return 0

    def get_entity_types_summary(self) -> dict[str, int]:
        """Get entity types summary."""
        return {}


class WorldStateVersionModel(Base):
    """SQLAlchemy model for WorldState version history."""

    __tablename__ = "world_state_versions"

    id = Column(String, primary_key=True)
    world_state_id = Column(String, nullable=False)
    version_number = Column(Integer, default=1)
    previous_version = Column(Integer, nullable=True)
    change_reason = Column(String, nullable=True)
    change_summary = Column(String, nullable=True)
    changed_by = Column(String, nullable=True)
    version_data = Column(JSON, default=dict)
    entities_added = Column(Integer, default=0)
    entities_removed = Column(Integer, default=0)
    entities_modified = Column(Integer, default=0)
    environment_changed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorldStateSnapshotModel(Base):
    """SQLAlchemy model for WorldState snapshots."""

    __tablename__ = "world_state_snapshots"

    id = Column(String, primary_key=True)
    world_state_id = Column(String, nullable=False)
    snapshot_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
