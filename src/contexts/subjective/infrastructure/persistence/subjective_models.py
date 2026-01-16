#!/usr/bin/env python3
"""
Subjective Context SQLAlchemy ORM Models

This module implements SQLAlchemy ORM models for persisting
Subjective bounded context aggregates and related entities.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
)
from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship

try:
    from core_platform.persistence.models import BaseModel, FullAuditModel
except ImportError:
    # Fallback for when platform models aren't available
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Base class for all SQLAlchemy models."""

    class BaseModel(Base):
        __abstract__ = True
        id = Column(String, primary_key=True)
        created_at = Column(DateTime, default=datetime.now, nullable=False)
        updated_at = Column(
            DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
        )

    class FullAuditModel(BaseModel):
        __abstract__ = True
        version = Column(Integer, default=1, nullable=False)


class TurnBriefORM(FullAuditModel):
    """
    SQLAlchemy ORM model for TurnBrief aggregate persistence.

    This model stores the core TurnBrief data and relationships
    to other tables containing detailed perception and knowledge data.
    """

    __tablename__ = "subjective_turn_briefs"

    # Primary key and identity
    turn_brief_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True, unique=True)

    # World state tracking
    world_state_version = Column(Integer, nullable=False, index=True)
    last_world_update = Column(DateTime, nullable=False)
    last_perception_update = Column(DateTime, nullable=False)

    # Awareness state (stored as JSON for flexibility)
    base_alertness = Column(String(50), nullable=False)
    current_alertness = Column(String(50), nullable=False)
    attention_focus = Column(String(50), nullable=False)
    focus_target = Column(String(255), nullable=True)
    awareness_modifiers = Column(JSON, nullable=True)
    fatigue_level = Column(Float, nullable=False, default=0.0)
    stress_level = Column(Float, nullable=False, default=0.0)

    # Perception capabilities (stored as JSON)
    perception_capabilities = Column(JSON, nullable=False)

    # Visible subjects (stored as JSON mapping subject_id -> visibility_level)
    visible_subjects = Column(JSON, nullable=True, default={})

    # Known threats (stored as JSON mapping subject_id -> threat_info)
    known_threats = Column(JSON, nullable=True, default={})

    # Relationships
    knowledge_items = relationship(
        "KnowledgeItemORM",
        back_populates="turn_brief",
        cascade="all, delete-orphan",
        lazy="select",
    )

    perception_records = relationship(
        "PerceptionRecordORM",
        back_populates="turn_brief",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self):
        return (
            f"<TurnBriefORM(turn_brief_id='{self.turn_brief_id}', "
            f"entity_id='{self.entity_id}', "
            f"world_state_version={self.world_state_version})>"
        )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if the TurnBrief is considered active (updated recently)."""
        cutoff = datetime.now().timestamp() - 3600  # 1 hour
        return self.updated_at.timestamp() > cutoff

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "turn_brief_id": str(self.turn_brief_id),
            "entity_id": self.entity_id,
            "world_state_version": self.world_state_version,
            "last_world_update": self.last_world_update.isoformat(),
            "last_perception_update": self.last_perception_update.isoformat(),
            "base_alertness": self.base_alertness,
            "current_alertness": self.current_alertness,
            "attention_focus": self.attention_focus,
            "focus_target": self.focus_target,
            "awareness_modifiers": self.awareness_modifiers,
            "fatigue_level": self.fatigue_level,
            "stress_level": self.stress_level,
            "perception_capabilities": self.perception_capabilities,
            "visible_subjects": self.visible_subjects,
            "known_threats": self.known_threats,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class KnowledgeItemORM(BaseModel):
    """
    SQLAlchemy ORM model for individual knowledge items.

    This model stores detailed knowledge information including
    metadata about reliability, sources, and temporal validity.
    """

    __tablename__ = "subjective_knowledge_items"

    # Primary key
    knowledge_item_id = Column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )

    # Foreign key to TurnBrief
    turn_brief_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjective_turn_briefs.turn_brief_id"),
        nullable=False,
        index=True,
    )

    # Knowledge content
    subject = Column(String(500), nullable=False, index=True)
    information = Column(Text, nullable=False)
    knowledge_type = Column(String(50), nullable=False, index=True)
    certainty_level = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)

    # Temporal information
    acquired_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)

    # Tags (stored as JSON array)
    tags = Column(JSON, nullable=True, default=[])

    # Additional metadata
    reliability_score = Column(Float, nullable=True)
    context_data = Column(JSON, nullable=True)

    # Relationship
    turn_brief = relationship("TurnBriefORM", back_populates="knowledge_items")

    def __repr__(self):
        return (
            f"<KnowledgeItemORM(knowledge_item_id='{self.knowledge_item_id}', "
            f"subject='{self.subject}', "
            f"knowledge_type='{self.knowledge_type}')>"
        )

    @hybrid_property
    def is_current(self) -> bool:
        """Check if the knowledge is still current (not expired)."""
        if not self.expires_at:
            return True
        return datetime.now() < self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "knowledge_item_id": str(self.knowledge_item_id),
            "turn_brief_id": str(self.turn_brief_id),
            "subject": self.subject,
            "information": self.information,
            "knowledge_type": self.knowledge_type,
            "certainty_level": self.certainty_level,
            "source": self.source,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "reliability_score": self.reliability_score,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PerceptionRecordORM(BaseModel):
    """
    SQLAlchemy ORM model for perception records.

    This model stores detailed information about individual
    perceptions including sensory details and environmental context.
    """

    __tablename__ = "subjective_perception_records"

    # Primary key
    perception_record_id = Column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )

    # Foreign key to TurnBrief
    turn_brief_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjective_turn_briefs.turn_brief_id"),
        nullable=False,
        index=True,
    )

    # Perception details
    perceived_subject = Column(String(500), nullable=False, index=True)
    perception_type = Column(String(50), nullable=False, index=True)
    visibility_level = Column(String(50), nullable=False)
    distance = Column(Float, nullable=False)

    # Positions (stored as JSON for 3D coordinates)
    observer_position = Column(JSON, nullable=True)
    target_position = Column(JSON, nullable=True)

    # Environmental context
    environmental_conditions = Column(JSON, nullable=True)
    additional_details = Column(JSON, nullable=True)

    # Temporal information
    perceived_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # Quality indicators
    confidence_score = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)

    # Relationship
    turn_brief = relationship("TurnBriefORM", back_populates="perception_records")

    def __repr__(self):
        return (
            f"<PerceptionRecordORM(perception_record_id='{self.perception_record_id}', "
            f"perceived_subject='{self.perceived_subject}', "
            f"perception_type='{self.perception_type}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "perception_record_id": str(self.perception_record_id),
            "turn_brief_id": str(self.turn_brief_id),
            "perceived_subject": self.perceived_subject,
            "perception_type": self.perception_type,
            "visibility_level": self.visibility_level,
            "distance": self.distance,
            "observer_position": self.observer_position,
            "target_position": self.target_position,
            "environmental_conditions": self.environmental_conditions,
            "additional_details": self.additional_details,
            "perceived_at": self.perceived_at.isoformat(),
            "confidence_score": self.confidence_score,
            "clarity_score": self.clarity_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ThreatAssessmentORM(BaseModel):
    """
    SQLAlchemy ORM model for threat assessments.

    This model stores detailed information about detected threats
    including assessment metadata and tracking history.
    """

    __tablename__ = "subjective_threat_assessments"

    # Primary key
    threat_assessment_id = Column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )

    # Foreign key to TurnBrief
    turn_brief_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjective_turn_briefs.turn_brief_id"),
        nullable=False,
        index=True,
    )

    # Threat identification
    threat_subject = Column(String(500), nullable=False, index=True)
    threat_type = Column(String(100), nullable=False, index=True)
    threat_level = Column(String(50), nullable=False, index=True)

    # Assessment details
    confidence = Column(Float, nullable=False)
    detection_method = Column(String(50), nullable=False)
    estimated_distance = Column(Float, nullable=True)

    # Threat capabilities and metadata
    threat_capabilities = Column(JSON, nullable=True)
    assessment_context = Column(JSON, nullable=True)

    # Temporal tracking
    first_detected = Column(DateTime, nullable=False, default=datetime.now)
    last_seen = Column(DateTime, nullable=False, default=datetime.now)
    lost_at = Column(DateTime, nullable=True, index=True)

    # Status and tracking
    status = Column(
        String(50), nullable=False, default="active"
    )  # active, lost, neutralized
    loss_reason = Column(String(200), nullable=True)
    last_known_position = Column(JSON, nullable=True)

    # Relationship
    turn_brief = relationship(
        "TurnBriefORM",
        backref=backref("threat_assessments", cascade="all, delete-orphan"),
    )

    def __repr__(self):
        return (
            f"<ThreatAssessmentORM(threat_assessment_id='{self.threat_assessment_id}', "
            f"threat_subject='{self.threat_subject}', "
            f"threat_level='{self.threat_level}', "
            f"status='{self.status}')>"
        )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if the threat is currently active."""
        return self.status == "active"

    @hybrid_property
    def tracking_duration(self) -> Optional[float]:
        """Get the duration the threat has been tracked (in seconds)."""
        end_time = self.lost_at or datetime.now()
        return (end_time - self.first_detected).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "threat_assessment_id": str(self.threat_assessment_id),
            "turn_brief_id": str(self.turn_brief_id),
            "threat_subject": self.threat_subject,
            "threat_type": self.threat_type,
            "threat_level": self.threat_level,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "estimated_distance": self.estimated_distance,
            "threat_capabilities": self.threat_capabilities,
            "assessment_context": self.assessment_context,
            "first_detected": self.first_detected.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "lost_at": self.lost_at.isoformat() if self.lost_at else None,
            "status": self.status,
            "loss_reason": self.loss_reason,
            "last_known_position": self.last_known_position,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class InformationSharingLogORM(BaseModel):
    """
    SQLAlchemy ORM model for tracking information sharing between entities.

    This model logs when knowledge is shared between entities,
    providing an audit trail for information propagation.
    """

    __tablename__ = "subjective_information_sharing_log"

    # Primary key
    sharing_log_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)

    # Source and target information
    source_entity_id = Column(String(255), nullable=False, index=True)
    target_entity_id = Column(String(255), nullable=False, index=True)

    # Sharing details
    knowledge_subjects = Column(JSON, nullable=False)  # List of subjects shared
    communication_method = Column(String(100), nullable=False)
    reliability_modifier = Column(Float, nullable=False, default=0.9)

    # Context information
    sharing_context = Column(JSON, nullable=True)
    environmental_conditions = Column(JSON, nullable=True)
    distance_at_sharing = Column(Float, nullable=True)

    # Temporal information
    shared_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # Success metrics
    success_rate = Column(
        Float, nullable=True
    )  # Percentage of knowledge successfully shared
    failure_reasons = Column(JSON, nullable=True)  # Reasons for any failures

    def __repr__(self):
        return (
            f"<InformationSharingLogORM(sharing_log_id='{self.sharing_log_id}', "
            f"source_entity_id='{self.source_entity_id}', "
            f"target_entity_id='{self.target_entity_id}', "
            f"shared_at='{self.shared_at}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sharing_log_id": str(self.sharing_log_id),
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "knowledge_subjects": self.knowledge_subjects,
            "communication_method": self.communication_method,
            "reliability_modifier": self.reliability_modifier,
            "sharing_context": self.sharing_context,
            "environmental_conditions": self.environmental_conditions,
            "distance_at_sharing": self.distance_at_sharing,
            "shared_at": self.shared_at.isoformat(),
            "success_rate": self.success_rate,
            "failure_reasons": self.failure_reasons,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
