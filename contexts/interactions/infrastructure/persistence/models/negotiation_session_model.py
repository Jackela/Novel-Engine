#!/usr/bin/env python3
"""
SQLAlchemy Model for NegotiationSession Aggregate

This module provides the SQLAlchemy ORM model for persisting NegotiationSession
aggregates and their associated value objects to a relational database.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, cast
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreUUID
from sqlalchemy.orm import validates

# Import domain objects for conversion
from ....domain.aggregates.negotiation_session import NegotiationSession
from ....domain.value_objects.interaction_id import InteractionId
from ..sqlalchemy_decorators import (
    EnhancedInteractionIdType,
    EnhancedNegotiationPartyType,
    EnhancedNegotiationStatusType,
    EnhancedProposalResponseType,
    EnhancedProposalTermsType,
)

# P3 Sprint 3 ORM Pattern imports
from ..sqlalchemy_types import (
    ColumnMappingMixin,
    ModelUpdatePattern,
    SqlAlchemyModelBase,
)

# Enhanced converters imported above

# P3 Sprint 3 Pattern: Use enhanced base class with proper typing


class NegotiationSessionModel(SqlAlchemyModelBase, ColumnMappingMixin):
    """
    SQLAlchemy model for NegotiationSession aggregate root.

    This model persists the NegotiationSession domain aggregate using
    custom types for complex value objects and JSON storage for
    collections and nested data structures.
    """

    __tablename__ = "negotiation_sessions"

    # Primary identifier
    session_id: Column[Any] = Column(
        EnhancedInteractionIdType,
        primary_key=True,
        default=lambda: InteractionId.generate(),
        doc="Unique identifier for the negotiation session",
    )

    # Basic session information
    session_name = Column(
        String(255),
        nullable=False,
        doc="Human-readable name for the negotiation session",
    )

    session_type = Column(
        String(100),
        nullable=False,
        doc="Type/category of the negotiation session",
    )

    # Session status (complex value object)
    status: Column[Any] = Column(
        EnhancedNegotiationStatusType,
        nullable=False,
        doc="Current negotiation status with phase and outcome information",
    )

    # Session metadata
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when the session was created",
    )

    created_by = Column(
        PostgreUUID(as_uuid=True),
        nullable=False,
        doc="UUID of the user who created this session",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Timestamp when the session was last updated",
    )

    # Session configuration
    max_parties = Column(
        Integer,
        nullable=False,
        default=10,
        doc="Maximum number of parties allowed in this session",
    )

    session_timeout_hours = Column(
        Integer, nullable=False, default=72, doc="Session timeout in hours"
    )

    auto_advance_phases = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether to automatically advance negotiation phases",
    )

    require_unanimous_agreement = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether unanimous agreement is required for acceptance",
    )

    allow_partial_agreements = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether partial agreements on some terms are allowed",
    )

    priority_level = Column(
        String(50),
        nullable=False,
        default="medium",
        doc="Priority level of this negotiation session",
    )

    confidentiality_level = Column(
        String(50),
        nullable=False,
        default="standard",
        doc="Confidentiality level requirements",
    )

    # Domain-specific information
    negotiation_domain = Column(
        String(200),
        nullable=True,
        doc="Specific domain or area of this negotiation",
    )

    session_context = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Additional context information for this session",
    )

    # Parties (stored as JSON mapping)
    parties = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Dictionary mapping party IDs to NegotiationParty value objects",
    )

    # Active proposals (stored as JSON mapping)
    active_proposals = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Dictionary mapping proposal IDs to active ProposalTerms",
    )

    # Proposal history (stored as JSON array)
    proposal_history = Column(
        JSON,
        nullable=False,
        default=list,
        doc="Historical list of all proposals submitted",
    )

    # Response data (stored as JSON mapping)
    responses = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Dictionary mapping party IDs to lists of ProposalResponse objects",
    )

    # Session statistics and metrics
    total_parties = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Current number of parties in the session",
    )

    total_proposals = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of proposals submitted",
    )

    total_responses = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of responses received",
    )

    # Version for optimistic locking
    version = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Version number for optimistic concurrency control",
    )

    # Indexes for common queries
    __table_args__ = (
        # Index for finding sessions by creator
        Index("ix_negotiation_sessions_created_by", created_by),
        # Index for finding sessions by type and domain
        Index(
            "ix_negotiation_sessions_type_domain",
            session_type,
            negotiation_domain,
        ),
        # Index for finding sessions by status
        Index("ix_negotiation_sessions_status", "status"),  # Will work on JSON field in PostgreSQL
        # Index for finding sessions by priority
        Index("ix_negotiation_sessions_priority", priority_level),
        # Index for time-based queries
        Index("ix_negotiation_sessions_created_at", created_at),
        Index("ix_negotiation_sessions_updated_at", updated_at),
        # Constraints
        CheckConstraint("max_parties > 0", name="ck_max_parties_positive"),
        CheckConstraint("session_timeout_hours > 0", name="ck_timeout_positive"),
        CheckConstraint("total_parties >= 0", name="ck_total_parties_non_negative"),
        CheckConstraint("total_proposals >= 0", name="ck_total_proposals_non_negative"),
        CheckConstraint("total_responses >= 0", name="ck_total_responses_non_negative"),
        CheckConstraint("version > 0", name="ck_version_positive"),
        # Unique constraint on session name per creator for organization
        UniqueConstraint("session_name", "created_by", name="uq_session_name_creator"),
        {"extend_existing": True},
    )

    # Validation methods
    @validates("session_name")
    def validate_session_name(self, key, session_name):
        """Validate session name is not empty and within length limits."""
        if not session_name or not session_name.strip():
            raise ValueError("Session name cannot be empty")
        if len(session_name.strip()) > 255:
            raise ValueError("Session name too long (max 255 characters)")
        return session_name.strip()

    @validates("session_type")
    def validate_session_type(self, key, session_type):
        """Validate session type is not empty."""
        if not session_type or not session_type.strip():
            raise ValueError("Session type cannot be empty")
        return session_type.strip()

    @validates("priority_level")
    def validate_priority_level(self, key, priority_level):
        """Validate priority level is one of the allowed values."""
        allowed_priorities = {"low", "medium", "high", "critical"}
        if priority_level not in allowed_priorities:
            raise ValueError(f"Priority level must be one of: {allowed_priorities}")
        return priority_level

    @validates("confidentiality_level")
    def validate_confidentiality_level(self, key, confidentiality_level):
        """Validate confidentiality level is one of the allowed values."""
        allowed_levels = {
            "public",
            "internal",
            "confidential",
            "restricted",
            "top_secret",
        }
        if confidentiality_level not in allowed_levels:
            raise ValueError(f"Confidentiality level must be one of: {allowed_levels}")
        return confidentiality_level

    def to_domain_entity(self) -> NegotiationSession:
        """
        Convert SQLAlchemy model instance to domain entity.

        Returns:
            NegotiationSession domain aggregate
        """
        # Convert parties from JSON storage
        domain_parties = {}
        for party_id_str, party_data in self.parties.items():
            party_id = UUID(party_id_str)
            # Use the enhanced type converter to reconstruct the party (P3 Sprint 3 Pattern)
            party_converter = EnhancedNegotiationPartyType()
            party = party_converter.process_result_value(party_data, None)
            if party:  # Only add non-None values
                domain_parties[party_id] = party

        # Convert active proposals from JSON storage
        domain_active_proposals = {}
        for proposal_id_str, proposal_data in self.active_proposals.items():
            proposal_id = UUID(proposal_id_str)
            # Use the enhanced type converter to reconstruct the proposal (P3 Sprint 3 Pattern)
            proposal_converter = EnhancedProposalTermsType()
            proposal = proposal_converter.process_result_value(proposal_data, None)
            if proposal:  # Only add non-None values
                domain_active_proposals[proposal_id] = proposal

        # Convert proposal history
        domain_proposal_history = []
        for proposal_data in cast(List[Any], self.proposal_history):
            proposal_converter = EnhancedProposalTermsType()
            proposal = proposal_converter.process_result_value(proposal_data, None)
            if proposal:  # Only add non-None values (P3 Sprint 2 Pattern)
                domain_proposal_history.append(proposal)

        # Convert responses from JSON storage
        domain_responses = {}
        for party_id_str, responses_data in self.responses.items():
            party_id = UUID(party_id_str)
            party_responses = []
            response_converter = EnhancedProposalResponseType()
            for response_data in responses_data:
                response = response_converter.process_result_value(response_data, None)
                if response:  # Only add non-None values (P3 Sprint 2 Pattern)
                    party_responses.append(response)
            domain_responses[party_id] = party_responses

        # Create and return domain entity (P3 Sprint 2 Cast Pattern for SQLAlchemy values)
        return NegotiationSession(
            session_id=cast(Any, self.session_id),
            session_name=cast(str, self.session_name),
            session_type=cast(str, self.session_type),
            status=cast(Any, self.status),
            parties=domain_parties,
            active_proposals=domain_active_proposals,
            proposal_history=domain_proposal_history,
            responses=domain_responses,
            created_at=cast(datetime, self.created_at),
            created_by=cast(Any, self.created_by),
            max_parties=cast(int, self.max_parties),
            session_timeout_hours=cast(int, self.session_timeout_hours),
            auto_advance_phases=cast(bool, self.auto_advance_phases),
            require_unanimous_agreement=cast(bool, self.require_unanimous_agreement),
            allow_partial_agreements=cast(bool, self.allow_partial_agreements),
            priority_level=cast(str, self.priority_level),
            confidentiality_level=cast(str, self.confidentiality_level),
            negotiation_domain=cast(str, self.negotiation_domain),
            session_context=cast(Dict[str, Any], self.session_context),
        )

    @classmethod
    def from_domain_entity(cls, session: NegotiationSession) -> "NegotiationSessionModel":
        """
        Create SQLAlchemy model instance from domain entity.

        Args:
            session: NegotiationSession domain aggregate

        Returns:
            NegotiationSessionModel instance ready for persistence
        """
        # Convert parties to JSON storage format
        parties_json = {}
        party_converter = EnhancedNegotiationPartyType()
        for party_id, party in session.parties.items():
            parties_json[str(party_id)] = party_converter.process_bind_param(party, None)

        # Convert active proposals to JSON storage format
        active_proposals_json = {}
        proposal_converter = EnhancedProposalTermsType()
        for proposal_id, proposal in session.active_proposals.items():
            active_proposals_json[str(proposal_id)] = proposal_converter.process_bind_param(
                proposal, None
            )

        # Convert proposal history to JSON storage format
        proposal_history_json = []
        for proposal in session.proposal_history:
            proposal_history_json.append(proposal_converter.process_bind_param(proposal, None))

        # Convert responses to JSON storage format
        responses_json = {}
        response_converter = EnhancedProposalResponseType()
        for party_id, responses in session.responses.items():
            party_responses_json = []
            for response in responses:
                party_responses_json.append(response_converter.process_bind_param(response, None))
            responses_json[str(party_id)] = party_responses_json

        # Create model instance
        return cls(
            session_id=session.session_id,
            session_name=session.session_name,
            session_type=session.session_type,
            status=session.status,
            created_at=session.created_at,
            created_by=session.created_by,
            updated_at=datetime.now(timezone.utc),  # Set current timestamp for updates
            max_parties=session.max_parties,
            session_timeout_hours=session.session_timeout_hours,
            auto_advance_phases=session.auto_advance_phases,
            require_unanimous_agreement=session.require_unanimous_agreement,
            allow_partial_agreements=session.allow_partial_agreements,
            priority_level=session.priority_level,
            confidentiality_level=session.confidentiality_level,
            negotiation_domain=session.negotiation_domain,
            session_context=session.session_context,
            parties=parties_json,
            active_proposals=active_proposals_json,
            proposal_history=proposal_history_json,
            responses=responses_json,
            total_parties=len(session.parties),
            total_proposals=len(session.proposal_history),
            total_responses=session.total_responses,
            version=1,  # Initial version
        )

    def update_from_domain_entity(self, session: NegotiationSession) -> None:
        """
        Update existing model instance with data from domain entity.

        This method is used for updates and handles version incrementing
        for optimistic concurrency control.

        Args:
            session: Updated NegotiationSession domain aggregate
        """
        # P3 Sprint 3 Pattern: Use type-safe model update pattern to avoid Column[T] vs T conflicts
        field_mappings = {
            "session_name": "session_name",
            "session_type": "session_type",
            "status": "status",
            "max_parties": "max_parties",
            "session_timeout_hours": "session_timeout_hours",
            "auto_advance_phases": "auto_advance_phases",
            "require_unanimous_agreement": "require_unanimous_agreement",
            "allow_partial_agreements": "allow_partial_agreements",
            "priority_level": "priority_level",
            "confidentiality_level": "confidentiality_level",
            "negotiation_domain": "negotiation_domain",
            "session_context": "session_context",
        }

        ModelUpdatePattern.update_model_from_domain(
            model_instance=self,
            domain_entity=session,
            field_mappings=field_mappings,
        )

        # Use safe column assignment for timestamp
        self._safe_column_assign(self, updated_at=datetime.now(timezone.utc))

        # Update complex data using enhanced converters
        party_converter = EnhancedNegotiationPartyType()
        proposal_converter = EnhancedProposalTermsType()
        response_converter = EnhancedProposalResponseType()

        # Update parties using safe assignment
        parties_json = {}
        for party_id, party in session.parties.items():
            parties_json[str(party_id)] = party_converter.process_bind_param(party, None)
        self._safe_column_assign(self, parties=parties_json)

        # Update active proposals using safe assignment
        active_proposals_json = {}
        for proposal_id, proposal in session.active_proposals.items():
            active_proposals_json[str(proposal_id)] = proposal_converter.process_bind_param(
                proposal, None
            )
        self._safe_column_assign(self, active_proposals=active_proposals_json)

        # Update proposal history using safe assignment
        proposal_history_json = []
        for proposal in session.proposal_history:
            proposal_history_json.append(proposal_converter.process_bind_param(proposal, None))
        self._safe_column_assign(self, proposal_history=proposal_history_json)

        # Update responses using safe assignment
        responses_json = {}
        for party_id, responses in session.responses.items():
            party_responses_json = []
            for response in responses:
                party_responses_json.append(response_converter.process_bind_param(response, None))
            responses_json[str(party_id)] = party_responses_json
        self._safe_column_assign(self, responses=responses_json)

        # Update statistics using safe assignment
        self._safe_column_assign(
            self,
            total_parties=len(session.parties),
            total_proposals=len(session.proposal_history),
            total_responses=session.total_responses,
            version=self.version + 1,
        )

    def __repr__(self) -> str:
        """String representation of the model for debugging."""
        return (
            f"<NegotiationSessionModel("
            f"session_id={self.session_id}, "
            f"name='{self.session_name}', "
            f"type='{self.session_type}', "
            f"parties={self.total_parties}, "
            f"proposals={self.total_proposals}, "
            f"version={self.version}"
            f")>"
        )
