#!/usr/bin/env python3
"""
Specialized SQLAlchemy Type Decorators for Interactions Context

This module provides enhanced SQLAlchemy type decorators that work with the
ORM-specific type patterns to resolve Column[T] vs T conflicts while maintaining
full domain value object functionality.

P3 Sprint 3 SQLAlchemy Decorators:
1. Enhanced TypeDecorator base with proper typing
2. Domain-specific decorators for interactions value objects
3. Validation and conversion patterns
4. Error handling and fallback mechanisms
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Union
from uuid import UUID

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgreUUID
from sqlalchemy.engine import Dialect

# Import domain value objects
from ..domain.value_objects.interaction_id import InteractionId
from ..domain.value_objects.negotiation_party import (
    AuthorityLevel,
    CommunicationPreference,
    NegotiationCapability,
    NegotiationParty,
    NegotiationStyle,
    PartyPreferences,
    PartyRole,
)
from ..domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    NegotiationStatus,
    TerminationReason,
)
from ..domain.value_objects.proposal_response import (
    ConfidenceLevel,
    ProposalResponse,
    ResponseReason,
    ResponseType,
    TermResponse,
)
from ..domain.value_objects.proposal_terms import (
    ProposalPriority,
    ProposalTerms,
    ProposalType,
    TermCondition,
    TermType,
)

# Import base patterns
from .sqlalchemy_types import ValueObjectConverterTyping

# Type variables
T = TypeVar("T")
ValueObjectType = TypeVar("ValueObjectType")


class EnhancedTypeDecorator(TypeDecorator[T]):
    """
    Enhanced TypeDecorator base class with improved type safety.

    P3 Sprint 3 enhancement: Provides proper typing and error handling
    for all domain value object converters.
    """

    cache_ok = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._converter_typing = ValueObjectConverterTyping()

    def process_bind_param(
        self, value: Optional[T], dialect: Optional[Dialect]
    ) -> Optional[Any]:
        """Enhanced bind parameter processing with proper typing."""
        return self._safe_bind_param(value, dialect)

    def process_result_value(
        self, value: Optional[Any], dialect: Optional[Dialect]
    ) -> Optional[T]:
        """Enhanced result value processing with proper typing."""
        return self._safe_result_value(value, dialect)

    def _safe_bind_param(
        self, value: Optional[T], dialect: Optional[Dialect]
    ) -> Optional[Any]:
        """Override in subclasses for specific bind parameter logic."""
        return value

    def _safe_result_value(
        self, value: Optional[Any], dialect: Optional[Dialect]
    ) -> Optional[T]:
        """Override in subclasses for specific result value logic."""
        return value


class EnhancedInteractionIdType(EnhancedTypeDecorator[InteractionId]):
    """
    Enhanced InteractionId type decorator with improved error handling.

    P3 Sprint 3 enhancement: Adds validation and fallback mechanisms.
    """

    impl = PostgreUUID(as_uuid=True)

    def _safe_bind_param(
        self,
        value: Optional[Union[InteractionId, UUID, str]],
        dialect: Optional[Dialect],
    ) -> Optional[UUID]:
        """Convert InteractionId to UUID for database storage."""
        if value is None:
            return None

        if isinstance(value, InteractionId):
            return value.value

        if isinstance(value, UUID):
            return value

        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError(
                    f"Invalid UUID string for InteractionId: {value}"
                )

        raise ValueError(
            f"Expected InteractionId, UUID, or str, got {type(value)}"
        )

    def _safe_result_value(
        self, value: Optional[UUID], dialect: Optional[Dialect]
    ) -> Optional[InteractionId]:
        """Convert UUID from database to InteractionId."""
        if value is None:
            return None

        try:
            return InteractionId(value)
        except Exception as e:
            raise ValueError(
                f"Failed to create InteractionId from UUID {value}: {e}"
            )


class EnhancedNegotiationStatusType(EnhancedTypeDecorator[NegotiationStatus]):
    """
    Enhanced NegotiationStatus type decorator with comprehensive validation.

    P3 Sprint 3 enhancement: Improved error handling and default value management.
    """

    impl = JSON

    def _safe_bind_param(
        self, value: Optional[NegotiationStatus], dialect: Optional[Dialect]
    ) -> Optional[Dict[str, Any]]:
        """Convert NegotiationStatus to JSON for database storage."""
        if value is None:
            return None

        if not isinstance(value, NegotiationStatus):
            raise ValueError(f"Expected NegotiationStatus, got {type(value)}")

        try:
            return {
                "phase": value.phase.value,
                "outcome": value.outcome.value,
                "started_at": value.started_at.isoformat()
                if value.started_at
                else None,
                "last_activity_at": value.last_activity_at.isoformat()
                if value.last_activity_at
                else None,
                "expected_completion_at": value.expected_completion_at.isoformat()
                if value.expected_completion_at
                else None,
                "actual_completion_at": value.actual_completion_at.isoformat()
                if value.actual_completion_at
                else None,
                "termination_reason": value.termination_reason.value
                if value.termination_reason
                else None,
            }
        except Exception as e:
            raise ValueError(f"Failed to serialize NegotiationStatus: {e}")

    def _safe_result_value(
        self, value: Optional[Dict[str, Any]], dialect: Optional[Dialect]
    ) -> Optional[NegotiationStatus]:
        """Convert JSON from database to NegotiationStatus."""
        if value is None:
            return None

        try:
            # Provide safe defaults for required fields
            now = datetime.now(timezone.utc)

            # Parse datetime fields with fallbacks
            started_at = (
                self._parse_datetime(value.get("started_at"), now) or now
            )
            last_activity_at = (
                self._parse_datetime(value.get("last_activity_at"), started_at)
                or started_at
            )
            expected_completion_at = self._parse_datetime(
                value.get("expected_completion_at")
            )
            actual_completion_at = self._parse_datetime(
                value.get("actual_completion_at")
            )

            # Parse enum fields with validation
            phase = NegotiationPhase(value.get("phase", "preparation"))
            outcome = NegotiationOutcome(value.get("outcome", "pending"))

            termination_reason = None
            if value.get("termination_reason"):
                termination_reason = TerminationReason(
                    value["termination_reason"]
                )

            return NegotiationStatus(
                phase=phase,
                outcome=outcome,
                started_at=started_at,
                last_activity_at=last_activity_at,
                expected_completion_at=expected_completion_at,
                actual_completion_at=actual_completion_at,
                termination_reason=termination_reason,
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize NegotiationStatus: {e}")

    def _parse_datetime(
        self, value: Optional[str], default: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Parse datetime string with fallback to default."""
        if value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return default
        return default


class EnhancedNegotiationPartyType(EnhancedTypeDecorator[NegotiationParty]):
    """
    Enhanced NegotiationParty type decorator with comprehensive validation.

    P3 Sprint 3 enhancement: Robust serialization/deserialization with error recovery.
    """

    impl = JSON

    def _safe_bind_param(
        self, value: Optional[NegotiationParty], dialect: Optional[Dialect]
    ) -> Optional[Dict[str, Any]]:
        """Convert NegotiationParty to JSON for database storage."""
        if value is None:
            return None

        if not isinstance(value, NegotiationParty):
            raise ValueError(f"Expected NegotiationParty, got {type(value)}")

        try:
            return {
                "party_id": str(value.party_id),
                "entity_id": str(value.entity_id),
                "party_name": value.party_name,
                "role": value.role.value,
                "authority_level": value.authority_level.value,
                "capabilities": [
                    {
                        "capability_name": cap.capability_name,
                        "proficiency_level": str(cap.proficiency_level),
                        "confidence_modifier": str(cap.confidence_modifier),
                        "applicable_domains": list(cap.applicable_domains),
                        "prerequisites": list(cap.prerequisites)
                        if cap.prerequisites
                        else [],
                    }
                    for cap in value.capabilities
                ],
                "preferences": {
                    "negotiation_style": value.preferences.negotiation_style.value,
                    "communication_preference": value.preferences.communication_preference.value,
                    "risk_tolerance": str(value.preferences.risk_tolerance),
                    "time_pressure_sensitivity": str(
                        value.preferences.time_pressure_sensitivity
                    ),
                    "preferred_session_duration": value.preferences.preferred_session_duration,
                    "maximum_session_duration": value.preferences.maximum_session_duration,
                    "cultural_considerations": list(
                        value.preferences.cultural_considerations
                    ),
                    "taboo_topics": list(value.preferences.taboo_topics),
                    "preferred_meeting_times": value.preferences.preferred_meeting_times,
                    "language_preferences": list(
                        value.preferences.language_preferences
                    ),
                },
                "constraints": value.constraints or {},
                "reputation_modifiers": {
                    k: str(v) for k, v in value.reputation_modifiers.items()
                },
                "active_mandates": list(value.active_mandates),
            }
        except Exception as e:
            raise ValueError(f"Failed to serialize NegotiationParty: {e}")

    def _safe_result_value(
        self, value: Optional[Dict[str, Any]], dialect: Optional[Dialect]
    ) -> Optional[NegotiationParty]:
        """Convert JSON from database to NegotiationParty."""
        if value is None:
            return None

        try:
            # Reconstruct capabilities with safe defaults
            capabilities = []
            for cap_data in value.get("capabilities", []):
                capability = NegotiationCapability(
                    capability_name=cap_data.get("capability_name", "unknown"),
                    proficiency_level=Decimal(
                        cap_data.get("proficiency_level", "0.5")
                    ),
                    confidence_modifier=Decimal(
                        cap_data.get("confidence_modifier", "1.0")
                    ),
                    applicable_domains=set(
                        cap_data.get("applicable_domains", [])
                    ),
                    prerequisites=set(cap_data.get("prerequisites", [])),
                )
                capabilities.append(capability)

            # Reconstruct preferences with safe defaults
            pref_data = value.get("preferences", {})
            preferences = PartyPreferences(
                negotiation_style=NegotiationStyle(
                    pref_data.get("negotiation_style", "collaborative")
                ),
                communication_preference=CommunicationPreference(
                    pref_data.get("communication_preference", "direct")
                ),
                risk_tolerance=Decimal(pref_data.get("risk_tolerance", "0.5")),
                time_pressure_sensitivity=Decimal(
                    pref_data.get("time_pressure_sensitivity", "0.5")
                ),
                preferred_session_duration=pref_data.get(
                    "preferred_session_duration"
                ),
                maximum_session_duration=pref_data.get(
                    "maximum_session_duration"
                ),
                cultural_considerations=set(
                    pref_data.get("cultural_considerations", [])
                ),
                taboo_topics=set(pref_data.get("taboo_topics", [])),
                preferred_meeting_times=pref_data.get(
                    "preferred_meeting_times"
                ),
                language_preferences=set(
                    pref_data.get("language_preferences", [])
                ),
            )

            return NegotiationParty(
                party_id=UUID(value["party_id"]),
                entity_id=UUID(value["entity_id"]),
                party_name=value["party_name"],
                role=PartyRole(value.get("role", "participant")),
                authority_level=AuthorityLevel(
                    value.get("authority_level", "limited")
                ),
                capabilities=capabilities,
                preferences=preferences,
                constraints=value.get("constraints", {}),
                reputation_modifiers={
                    k: Decimal(str(v))
                    for k, v in value.get("reputation_modifiers", {}).items()
                },
                active_mandates=set(value.get("active_mandates", [])),
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize NegotiationParty: {e}")


class EnhancedProposalTermsType(EnhancedTypeDecorator[ProposalTerms]):
    """Enhanced ProposalTerms type decorator with validation and error recovery."""

    impl = JSON

    def _safe_bind_param(
        self, value: Optional[ProposalTerms], dialect: Optional[Dialect]
    ) -> Optional[Dict[str, Any]]:
        """Convert ProposalTerms to JSON for database storage."""
        if value is None:
            return None

        if not isinstance(value, ProposalTerms):
            raise ValueError(f"Expected ProposalTerms, got {type(value)}")

        try:
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
                        "dependencies": list(term.dependencies)
                        if term.dependencies
                        else [],
                    }
                    for term in value.terms
                ],
                "created_at": value.created_at.isoformat(),
                "validity_period": value.validity_period.isoformat()
                if value.validity_period
                else None,
                "metadata": value.metadata or {},
            }
        except Exception as e:
            raise ValueError(f"Failed to serialize ProposalTerms: {e}")

    def _safe_result_value(
        self, value: Optional[Dict[str, Any]], dialect: Optional[Dialect]
    ) -> Optional[ProposalTerms]:
        """Convert JSON from database to ProposalTerms."""
        if value is None:
            return None

        try:
            # Reconstruct terms with validation
            terms = []
            for term_data in value.get("terms", []):
                term = TermCondition(
                    term_id=term_data.get("term_id", "unknown"),
                    term_type=TermType(term_data.get("term_type", "resource")),
                    description=term_data.get("description", ""),
                    value=term_data.get("value"),
                    priority=ProposalPriority(
                        term_data.get("priority", "medium")
                    ),
                    is_negotiable=term_data.get("is_negotiable", True),
                    constraints=term_data.get("constraints"),
                    dependencies=term_data.get("dependencies"),
                )
                terms.append(term)

            return ProposalTerms(
                proposal_id=UUID(value["proposal_id"]),
                proposal_type=ProposalType(
                    value.get("proposal_type", "standard")
                ),
                title=value.get("title", "Untitled Proposal"),
                summary=value.get("summary", ""),
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


class EnhancedProposalResponseType(EnhancedTypeDecorator[ProposalResponse]):
    """Enhanced ProposalResponse type decorator with comprehensive validation."""

    impl = JSON

    def _safe_bind_param(
        self, value: Optional[ProposalResponse], dialect: Optional[Dialect]
    ) -> Optional[Dict[str, Any]]:
        """Convert ProposalResponse to JSON for database storage."""
        if value is None:
            return None

        if not isinstance(value, ProposalResponse):
            raise ValueError(f"Expected ProposalResponse, got {type(value)}")

        try:
            return {
                "response_id": str(value.response_id),
                "proposal_id": str(value.proposal_id),
                "responding_party_id": str(value.responding_party_id),
                "overall_response": value.overall_response.value,
                "overall_reason": value.overall_reason.value
                if value.overall_reason
                else None,
                "overall_comments": value.overall_comments,
                "confidence_level": value.confidence_level.value,
                "response_timestamp": value.response_timestamp.isoformat(),
                "expires_at": value.expires_at.isoformat()
                if value.expires_at
                else None,
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
                "conditions": list(value.conditions)
                if value.conditions
                else [],
                "metadata": value.metadata or {},
            }
        except Exception as e:
            raise ValueError(f"Failed to serialize ProposalResponse: {e}")

    def _safe_result_value(
        self, value: Optional[Dict[str, Any]], dialect: Optional[Dialect]
    ) -> Optional[ProposalResponse]:
        """Convert JSON from database to ProposalResponse."""
        if value is None:
            return None

        try:
            # Reconstruct term responses with safe defaults
            term_responses = []
            for tr_data in value.get("term_responses", []):
                reason = None
                if tr_data.get("reason"):
                    reason = ResponseReason(tr_data["reason"])

                confidence_level = ConfidenceLevel(
                    tr_data.get("confidence_level", "moderate")
                )

                term_response = TermResponse(
                    term_id=tr_data.get("term_id", "unknown"),
                    response_type=ResponseType(
                        tr_data.get("response_type", "accept")
                    ),
                    reason=reason,
                    comments=tr_data.get("comments"),
                    suggested_modification=tr_data.get(
                        "suggested_modification"
                    ),
                    confidence_level=confidence_level,
                )
                term_responses.append(term_response)

            # Parse other fields with safe defaults
            overall_reason = None
            if value.get("overall_reason"):
                overall_reason = ResponseReason(value["overall_reason"])

            confidence_level = ConfidenceLevel(
                value.get("confidence_level", "moderate")
            )

            expires_at = None
            if value.get("expires_at"):
                expires_at = datetime.fromisoformat(value["expires_at"])

            return ProposalResponse(
                response_id=UUID(value["response_id"]),
                proposal_id=UUID(value["proposal_id"]),
                responding_party_id=UUID(value["responding_party_id"]),
                overall_response=ResponseType(
                    value.get("overall_response", "accept")
                ),
                term_responses=term_responses,
                overall_reason=overall_reason,
                overall_comments=value.get("overall_comments"),
                confidence_level=confidence_level,
                response_timestamp=datetime.fromisoformat(
                    value["response_timestamp"]
                ),
                expires_at=expires_at,
                conditions=value.get("conditions", []),
                metadata=value.get("metadata", {}),
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize ProposalResponse: {e}")


# Export enhanced decorators for use in infrastructure layer
__all__ = [
    "EnhancedTypeDecorator",
    "EnhancedInteractionIdType",
    "EnhancedNegotiationStatusType",
    "EnhancedNegotiationPartyType",
    "EnhancedProposalTermsType",
    "EnhancedProposalResponseType",
]
