#!/usr/bin/env python3
"""
SQLAlchemy Value Object Type Converters for Interaction Domain

This module provides custom SQLAlchemy types and converters for persisting
complex domain value objects as JSON or other appropriate database types.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from uuid import UUID

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgreUUID

# Import domain value objects
from ....domain.value_objects.interaction_id import InteractionId
from ....domain.value_objects.negotiation_party import (
    AuthorityLevel,
    CommunicationPreference,
    NegotiationCapability,
    NegotiationParty,
    NegotiationStyle,
    PartyPreferences,
    PartyRole,
)
from ....domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    NegotiationStatus,
    TerminationReason,
)
from ....domain.value_objects.proposal_response import (
    ConfidenceLevel,
    ProposalResponse,
    ResponseReason,
    ResponseType,
    TermResponse,
)
from ....domain.value_objects.proposal_terms import (
    ProposalPriority,
    ProposalTerms,
    ProposalType,
    TermCondition,
    TermType,
)


class InteractionIdType(TypeDecorator):
    """
    Custom SQLAlchemy type for InteractionId value objects.

    Stores InteractionId as UUID in database and converts to/from
    InteractionId domain objects in Python.
    """

    impl = PostgreUUID(as_uuid=True)
    cache_ok = True

    def process_bind_param(
        self, value: Optional[Union[InteractionId, UUID, str]], dialect
    ) -> Optional[UUID]:
        """Convert InteractionId to UUID for database storage."""
        if value is None:
            return None
        if isinstance(value, InteractionId):
            return value.value
        if isinstance(value, UUID):
            return value
        raise ValueError(f"Expected InteractionId or UUID, got {type(value)}")

    def process_result_value(self, value: Optional[UUID], dialect) -> Optional[InteractionId]:
        """Convert UUID from database to InteractionId."""
        if value is None:
            return None
        return InteractionId(value)


class NegotiationStatusType(TypeDecorator):
    """
    Custom SQLAlchemy type for NegotiationStatus value objects.

    Stores status as JSON in database and converts to/from
    NegotiationStatus domain objects in Python.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Optional[NegotiationStatus], dialect
    ) -> Optional[Dict[str, Any]]:
        """Convert NegotiationStatus to JSON for database storage."""
        if value is None:
            return None

        if isinstance(value, NegotiationStatus):
            return {
                "phase": value.phase.value,
                "outcome": value.outcome.value,
                "started_at": (value.started_at.isoformat() if value.started_at else None),
                "last_activity_at": (
                    value.last_activity_at.isoformat() if value.last_activity_at else None
                ),
                "expected_completion_at": (
                    value.expected_completion_at.isoformat()
                    if value.expected_completion_at
                    else None
                ),
                "actual_completion_at": (
                    value.actual_completion_at.isoformat() if value.actual_completion_at else None
                ),
                "termination_reason": (
                    value.termination_reason.value if value.termination_reason else None
                ),
            }

        raise ValueError(f"Expected NegotiationStatus, got {type(value)}")

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect
    ) -> Optional[NegotiationStatus]:
        """Convert JSON from database to NegotiationStatus."""
        if value is None:
            return None

        try:
            # Convert datetime strings back to datetime objects
            # P3 Sprint 2 ValueObjectFactory Pattern: Provide required defaults
            now = datetime.now(timezone.utc)
            started_at = (
                datetime.fromisoformat(value["started_at"]) if value.get("started_at") else now
            )
            last_activity_at = (
                datetime.fromisoformat(value["last_activity_at"])
                if value.get("last_activity_at")
                else started_at
            )
            expected_completion_at = (
                datetime.fromisoformat(value["expected_completion_at"])
                if value.get("expected_completion_at")
                else None
            )
            actual_completion_at = (
                datetime.fromisoformat(value["actual_completion_at"])
                if value.get("actual_completion_at")
                else None
            )

            # Convert termination reason
            termination_reason = None
            if value.get("termination_reason"):
                termination_reason = TerminationReason(value["termination_reason"])

            return NegotiationStatus(
                phase=NegotiationPhase(value["phase"]),
                outcome=NegotiationOutcome(value["outcome"]),
                started_at=started_at,
                last_activity_at=last_activity_at,
                expected_completion_at=expected_completion_at,
                actual_completion_at=actual_completion_at,
                termination_reason=termination_reason,
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize NegotiationStatus: {e}")


class NegotiationPartyType(TypeDecorator):
    """
    Custom SQLAlchemy type for NegotiationParty value objects.

    Stores party information as JSON in database.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Optional[NegotiationParty], dialect
    ) -> Optional[Dict[str, Any]]:
        """Convert NegotiationParty to JSON for database storage."""
        if value is None:
            return None

        if isinstance(value, NegotiationParty):
            return {
                "party_id": str(value.party_id),
                "entity_id": str(value.entity_id),
                "party_name": value.party_name,
                "role": value.role.value,
                "authority_level": value.authority_level.value,
                "capabilities": [
                    {
                        "capability_name": cap.capability_name,
                        "proficiency_level": float(cap.proficiency_level),
                        "confidence_modifier": float(cap.confidence_modifier),
                        "applicable_domains": list(cap.applicable_domains),
                        "prerequisites": list(cap.prerequisites) if cap.prerequisites else [],
                    }
                    for cap in value.capabilities
                ],
                "preferences": {
                    "negotiation_style": value.preferences.negotiation_style.value,
                    "communication_preference": value.preferences.communication_preference.value,
                    "risk_tolerance": float(value.preferences.risk_tolerance),
                    "time_pressure_sensitivity": float(value.preferences.time_pressure_sensitivity),
                    "preferred_session_duration": value.preferences.preferred_session_duration,
                    "maximum_session_duration": value.preferences.maximum_session_duration,
                    "cultural_considerations": list(value.preferences.cultural_considerations),
                    "taboo_topics": list(value.preferences.taboo_topics),
                    "preferred_meeting_times": value.preferences.preferred_meeting_times,
                    "language_preferences": list(value.preferences.language_preferences),
                },
                "constraints": value.constraints,
                "reputation_modifiers": {
                    k: float(v) for k, v in value.reputation_modifiers.items()
                },
                "active_mandates": list(value.active_mandates),
            }

        raise ValueError(f"Expected NegotiationParty, got {type(value)}")

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect
    ) -> Optional[NegotiationParty]:
        """Convert JSON from database to NegotiationParty."""
        if value is None:
            return None

        try:
            # Reconstruct capabilities
            capabilities = []
            for cap_data in value.get("capabilities", []):
                capability = NegotiationCapability(
                    capability_name=cap_data["capability_name"],
                    proficiency_level=Decimal(str(cap_data["proficiency_level"])),
                    confidence_modifier=Decimal(str(cap_data["confidence_modifier"])),
                    applicable_domains=set(cap_data["applicable_domains"]),
                    prerequisites=set(cap_data.get("prerequisites", [])),
                )
                capabilities.append(capability)

            # Reconstruct preferences
            pref_data = value.get("preferences", {})
            preferences = PartyPreferences(
                negotiation_style=NegotiationStyle(pref_data["negotiation_style"]),
                communication_preference=CommunicationPreference(
                    pref_data["communication_preference"]
                ),
                risk_tolerance=Decimal(str(pref_data["risk_tolerance"])),
                time_pressure_sensitivity=Decimal(str(pref_data["time_pressure_sensitivity"])),
                preferred_session_duration=pref_data.get("preferred_session_duration"),
                maximum_session_duration=pref_data.get("maximum_session_duration"),
                cultural_considerations=set(pref_data.get("cultural_considerations", [])),
                taboo_topics=set(pref_data.get("taboo_topics", [])),
                preferred_meeting_times=pref_data.get("preferred_meeting_times"),
                language_preferences=set(pref_data.get("language_preferences", [])),
            )

            return NegotiationParty(
                party_id=UUID(value["party_id"]),
                entity_id=UUID(value["entity_id"]),
                party_name=value["party_name"],
                role=PartyRole(value["role"]),
                authority_level=AuthorityLevel(value["authority_level"]),
                capabilities=capabilities,
                preferences=preferences,
                constraints=value.get("constraints", {}),
                reputation_modifiers={
                    k: Decimal(str(v)) for k, v in value.get("reputation_modifiers", {}).items()
                },
                active_mandates=set(value.get("active_mandates", [])),
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize NegotiationParty: {e}")


class ProposalTermsType(TypeDecorator):
    """
    Custom SQLAlchemy type for ProposalTerms value objects.

    Stores proposal terms as JSON in database.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Optional[ProposalTerms], dialect
    ) -> Optional[Dict[str, Any]]:
        """Convert ProposalTerms to JSON for database storage."""
        if value is None:
            return None

        if isinstance(value, ProposalTerms):
            return {
                "proposal_id": str(value.proposal_id),
                "proposal_type": value.proposal_type.value,
                "title": value.title,
                "summary": value.summary,
                "terms": [
                    {
                        "term_id": term.term_id,
                        "term_type": term.term_type.value,
                        "description": term.description,
                        "value": term.value,
                        "priority": term.priority.value,
                        "is_negotiable": term.is_negotiable,
                        "constraints": term.constraints,
                        "dependencies": list(term.dependencies) if term.dependencies else [],
                    }
                    for term in value.terms
                ],
                "created_at": value.created_at.isoformat(),
                "validity_period": (
                    value.validity_period.isoformat() if value.validity_period else None
                ),
                "metadata": value.metadata,
            }

        raise ValueError(f"Expected ProposalTerms, got {type(value)}")

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect
    ) -> Optional[ProposalTerms]:
        """Convert JSON from database to ProposalTerms."""
        if value is None:
            return None

        try:
            # Reconstruct terms
            terms = []
            for term_data in value.get("terms", []):
                term = TermCondition(
                    term_id=term_data["term_id"],
                    term_type=TermType(term_data["term_type"]),
                    description=term_data["description"],
                    value=term_data["value"],
                    priority=ProposalPriority(term_data["priority"]),
                    is_negotiable=term_data["is_negotiable"],
                    constraints=term_data.get("constraints"),
                    dependencies=term_data.get("dependencies"),
                )
                terms.append(term)

            return ProposalTerms(
                proposal_id=UUID(value["proposal_id"]),
                proposal_type=ProposalType(value["proposal_type"]),
                title=value["title"],
                summary=value["summary"],
                terms=terms,
                validity_period=(
                    datetime.fromisoformat(value["validity_period"])
                    if value.get("validity_period")
                    else None
                ),
                created_at=datetime.fromisoformat(value["created_at"]),
                metadata=value.get("metadata", {}),
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize ProposalTerms: {e}")


class ProposalResponseType(TypeDecorator):
    """
    Custom SQLAlchemy type for ProposalResponse value objects.

    Stores response information as JSON in database.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Optional[ProposalResponse], dialect
    ) -> Optional[Dict[str, Any]]:
        """Convert ProposalResponse to JSON for database storage."""
        if value is None:
            return None

        if isinstance(value, ProposalResponse):
            return {
                "response_id": str(value.response_id),
                "proposal_id": str(value.proposal_id),
                "responding_party_id": str(value.responding_party_id),
                "overall_response": value.overall_response.value,
                "overall_reason": value.overall_reason.value if value.overall_reason else None,
                "overall_comments": value.overall_comments,
                "confidence_level": value.confidence_level.value,
                "response_timestamp": value.response_timestamp.isoformat(),
                "expires_at": value.expires_at.isoformat() if value.expires_at else None,
                "term_responses": [
                    {
                        "term_id": tr.term_id,
                        "response_type": tr.response_type.value,
                        "reason": tr.reason.value if tr.reason else None,
                        "comments": tr.comments,
                        "suggested_modification": tr.suggested_modification,
                        "confidence_level": tr.confidence_level.value,
                    }
                    for tr in value.term_responses
                ],
                "conditions": list(value.conditions) if value.conditions else [],
                "metadata": value.metadata,
            }

        raise ValueError(f"Expected ProposalResponse, got {type(value)}")

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect
    ) -> Optional[ProposalResponse]:
        """Convert JSON from database to ProposalResponse."""
        if value is None:
            return None

        try:
            # Reconstruct term responses
            term_responses = []
            for tr_data in value.get("term_responses", []):
                reason = None
                if tr_data.get("reason"):
                    reason = ResponseReason(tr_data["reason"])

                confidence_level = ConfidenceLevel.MODERATE
                if tr_data.get("confidence_level"):
                    confidence_level = ConfidenceLevel(tr_data["confidence_level"])

                term_response = TermResponse(
                    term_id=tr_data["term_id"],
                    response_type=ResponseType(tr_data["response_type"]),
                    reason=reason,
                    comments=tr_data.get("comments"),
                    suggested_modification=tr_data.get("suggested_modification"),
                    confidence_level=confidence_level,
                )
                term_responses.append(term_response)

            # Reconstruct other fields
            overall_reason = None
            if value.get("overall_reason"):
                overall_reason = ResponseReason(value["overall_reason"])

            confidence_level = ConfidenceLevel.MODERATE
            if value.get("confidence_level"):
                confidence_level = ConfidenceLevel(value["confidence_level"])

            expires_at = None
            if value.get("expires_at"):
                expires_at = datetime.fromisoformat(value["expires_at"])

            return ProposalResponse(
                response_id=UUID(value["response_id"]),
                proposal_id=UUID(value["proposal_id"]),
                responding_party_id=UUID(value["responding_party_id"]),
                overall_response=ResponseType(value["overall_response"]),
                term_responses=term_responses,
                overall_reason=overall_reason,
                overall_comments=value.get("overall_comments"),
                confidence_level=confidence_level,
                response_timestamp=datetime.fromisoformat(value["response_timestamp"]),
                expires_at=expires_at,
                conditions=value.get("conditions", []),
                metadata=value.get("metadata", {}),
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize ProposalResponse: {e}")


# Additional helper functions for JSON serialization/deserialization


def serialize_decimal(obj):
    """Helper function to serialize Decimal objects to JSON."""
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def deserialize_decimal(value: str) -> Decimal:
    """Helper function to deserialize strings back to Decimal objects."""
    return Decimal(value)
