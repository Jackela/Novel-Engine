#!/usr/bin/env python3
"""
Proposal Response Value Objects

This module implements value objects for representing responses to proposals
within negotiations in the Interaction bounded context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class ResponseType(Enum):
    """Enumeration of proposal response types."""
    ACCEPT = "accept"
    REJECT = "reject"
    COUNTER_PROPOSAL = "counter_proposal"
    REQUEST_CLARIFICATION = "request_clarification"
    REQUEST_MODIFICATION = "request_modification"
    CONDITIONAL_ACCEPT = "conditional_accept"
    PARTIAL_ACCEPT = "partial_accept"
    DEFER = "defer"
    WITHDRAW = "withdraw"


class ResponseReason(Enum):
    """Enumeration of reasons for specific responses."""
    TERMS_ACCEPTABLE = "terms_acceptable"
    TERMS_UNACCEPTABLE = "terms_unacceptable"
    INSUFFICIENT_AUTHORITY = "insufficient_authority"
    REQUIRES_CONSULTATION = "requires_consultation"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    TIMING_ISSUES = "timing_issues"
    RESOURCE_CONSTRAINTS = "resource_constraints"
    STRATEGIC_CONSIDERATIONS = "strategic_considerations"
    CULTURAL_CONCERNS = "cultural_concerns"
    LEGAL_OBSTACLES = "legal_obstacles"
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    RISK_ASSESSMENT = "risk_assessment"
    BETTER_ALTERNATIVE = "better_alternative"
    CHANGED_CIRCUMSTANCES = "changed_circumstances"


class ConfidenceLevel(Enum):
    """Enumeration of confidence levels in responses."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class TermResponse:
    """
    Value object representing response to a specific term within a proposal.
    """
    
    term_id: str
    response_type: ResponseType
    reason: Optional[ResponseReason] = None
    comments: Optional[str] = None
    suggested_modification: Optional[str] = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    
    def __post_init__(self):
        """Validate term response data."""
        if not self.term_id.strip():
            raise ValueError("term_id cannot be empty")
        
        # Validation based on response type
        if self.response_type == ResponseType.REQUEST_MODIFICATION:
            if not self.suggested_modification:
                raise ValueError("REQUEST_MODIFICATION responses must include suggested_modification")
        
        if self.response_type in [ResponseType.REQUEST_CLARIFICATION, ResponseType.REJECT]:
            if not self.comments:
                raise ValueError(f"{self.response_type.value} responses should include comments")
        
        # Validate string fields
        if self.comments is not None and not self.comments.strip():
            raise ValueError("comments cannot be empty if provided")
        
        if self.suggested_modification is not None and not self.suggested_modification.strip():
            raise ValueError("suggested_modification cannot be empty if provided")
    
    def is_acceptance(self) -> bool:
        """Check if this is an acceptance response."""
        return self.response_type in [
            ResponseType.ACCEPT,
            ResponseType.CONDITIONAL_ACCEPT,
            ResponseType.PARTIAL_ACCEPT
        ]
    
    def is_rejection(self) -> bool:
        """Check if this is a rejection response."""
        return self.response_type == ResponseType.REJECT
    
    def requires_follow_up(self) -> bool:
        """Check if this response requires follow-up action."""
        return self.response_type in [
            ResponseType.REQUEST_CLARIFICATION,
            ResponseType.REQUEST_MODIFICATION,
            ResponseType.COUNTER_PROPOSAL,
            ResponseType.DEFER
        ]
    
    def __eq__(self, other: Any) -> bool:
        """Compare TermResponse instances for equality."""
        if not isinstance(other, TermResponse):
            return False
        return (
            self.term_id == other.term_id and
            self.response_type == other.response_type and
            self.reason == other.reason and
            self.comments == other.comments and
            self.suggested_modification == other.suggested_modification and
            self.confidence_level == other.confidence_level
        )


@dataclass(frozen=True)
class ProposalResponse:
    """
    Value object representing a complete response to a proposal.
    
    Encapsulates the overall response, individual term responses, and
    metadata about the responding party's decision-making process.
    """
    
    response_id: UUID
    proposal_id: UUID
    responding_party_id: UUID
    overall_response: ResponseType
    term_responses: List[TermResponse]
    overall_reason: Optional[ResponseReason] = None
    overall_comments: Optional[str] = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    response_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    conditions: Optional[List[str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate proposal response data."""
        # Ensure response_timestamp is timezone-aware
        if self.response_timestamp.tzinfo is None:
            raise ValueError("response_timestamp must be timezone-aware")
        
        # Validate expires_at
        if self.expires_at:
            if self.expires_at.tzinfo is None:
                raise ValueError("expires_at must be timezone-aware")
            if self.expires_at <= self.response_timestamp:
                raise ValueError("expires_at must be after response_timestamp")
        
        # Validate term responses have unique term IDs
        term_ids = [tr.term_id for tr in self.term_responses]
        if len(term_ids) != len(set(term_ids)):
            raise ValueError("Term responses must have unique term IDs")
        
        # Validate overall response consistency with term responses
        if self.term_responses:
            self._validate_response_consistency()
        
        # Validate conditions for conditional acceptance
        if (self.overall_response == ResponseType.CONDITIONAL_ACCEPT and 
            not self.conditions):
            raise ValueError("Conditional acceptance must include conditions")
        
        # Validate string fields
        if self.overall_comments is not None and not self.overall_comments.strip():
            raise ValueError("overall_comments cannot be empty if provided")
        
        # Validate conditions
        if self.conditions:
            for condition in self.conditions:
                if not isinstance(condition, str) or not condition.strip():
                    raise ValueError("All conditions must be non-empty strings")
    
    def _validate_response_consistency(self):
        """Validate consistency between overall response and term responses."""
        acceptance_count = sum(1 for tr in self.term_responses if tr.is_acceptance())
        rejection_count = sum(1 for tr in self.term_responses if tr.is_rejection())
        total_terms = len(self.term_responses)
        
        if self.overall_response == ResponseType.ACCEPT:
            if acceptance_count != total_terms:
                raise ValueError("ACCEPT overall response requires all terms to be accepted")
        
        elif self.overall_response == ResponseType.REJECT:
            if rejection_count == 0:
                raise ValueError("REJECT overall response requires at least one term to be rejected")
        
        elif self.overall_response == ResponseType.PARTIAL_ACCEPT:
            if acceptance_count == 0 or acceptance_count == total_terms:
                raise ValueError("PARTIAL_ACCEPT requires some but not all terms to be accepted")
        
        elif self.overall_response == ResponseType.CONDITIONAL_ACCEPT:
            if acceptance_count == 0:
                raise ValueError("CONDITIONAL_ACCEPT requires at least some terms to be accepted")
    
    @classmethod
    def create(cls, proposal_id: UUID, responding_party_id: UUID,
               overall_response: ResponseType, term_responses: List[TermResponse],
               overall_reason: Optional[ResponseReason] = None,
               overall_comments: Optional[str] = None,
               conditions: Optional[List[str]] = None,
               expires_at: Optional[datetime] = None,
               metadata: Optional[Dict[str, Any]] = None) -> 'ProposalResponse':
        """Create new ProposalResponse with generated ID."""
        from uuid import uuid4
        
        return cls(
            response_id=uuid4(),
            proposal_id=proposal_id,
            responding_party_id=responding_party_id,
            overall_response=overall_response,
            term_responses=term_responses,
            overall_reason=overall_reason,
            overall_comments=overall_comments,
            conditions=conditions or [],
            expires_at=expires_at,
            metadata=metadata or {}
        )
    
    def get_term_response(self, term_id: str) -> Optional[TermResponse]:
        """Get response for specific term."""
        return next((tr for tr in self.term_responses if tr.term_id == term_id), None)
    
    def get_accepted_terms(self) -> List[TermResponse]:
        """Get all accepted term responses."""
        return [tr for tr in self.term_responses if tr.is_acceptance()]
    
    def get_rejected_terms(self) -> List[TermResponse]:
        """Get all rejected term responses."""
        return [tr for tr in self.term_responses if tr.is_rejection()]
    
    def get_terms_requiring_follow_up(self) -> List[TermResponse]:
        """Get all term responses requiring follow-up."""
        return [tr for tr in self.term_responses if tr.requires_follow_up()]
    
    def get_terms_with_modifications(self) -> List[TermResponse]:
        """Get all term responses with suggested modifications."""
        return [
            tr for tr in self.term_responses 
            if tr.suggested_modification is not None
        ]
    
    def is_complete_acceptance(self) -> bool:
        """Check if response represents complete acceptance."""
        return (self.overall_response == ResponseType.ACCEPT and
                all(tr.is_acceptance() for tr in self.term_responses))
    
    def is_complete_rejection(self) -> bool:
        """Check if response represents complete rejection."""
        return (self.overall_response == ResponseType.REJECT and
                all(tr.is_rejection() for tr in self.term_responses))
    
    def is_partial_response(self) -> bool:
        """Check if response is partial (some accept, some reject)."""
        acceptances = [tr for tr in self.term_responses if tr.is_acceptance()]
        rejections = [tr for tr in self.term_responses if tr.is_rejection()]
        return len(acceptances) > 0 and len(rejections) > 0
    
    def requires_negotiation(self) -> bool:
        """Check if response requires further negotiation."""
        return self.overall_response in [
            ResponseType.COUNTER_PROPOSAL,
            ResponseType.REQUEST_MODIFICATION,
            ResponseType.CONDITIONAL_ACCEPT,
            ResponseType.PARTIAL_ACCEPT
        ]
    
    def requires_clarification(self) -> bool:
        """Check if response requires clarification."""
        return (self.overall_response == ResponseType.REQUEST_CLARIFICATION or
                any(tr.response_type == ResponseType.REQUEST_CLARIFICATION 
                    for tr in self.term_responses))
    
    def has_conditions(self) -> bool:
        """Check if response has conditions."""
        return bool(self.conditions)
    
    def is_expired(self) -> bool:
        """Check if response has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def get_acceptance_percentage(self) -> float:
        """Get percentage of terms accepted."""
        if not self.term_responses:
            return 0.0
        
        accepted_count = len(self.get_accepted_terms())
        return (accepted_count / len(self.term_responses)) * 100.0
    
    def get_response_summary(self) -> Dict[str, Any]:
        """Get summary of response statistics."""
        total_terms = len(self.term_responses)
        accepted_terms = len(self.get_accepted_terms())
        rejected_terms = len(self.get_rejected_terms())
        modified_terms = len(self.get_terms_with_modifications())
        
        return {
            'total_terms': total_terms,
            'accepted_terms': accepted_terms,
            'rejected_terms': rejected_terms,
            'modified_terms': modified_terms,
            'acceptance_percentage': self.get_acceptance_percentage(),
            'overall_response': self.overall_response.value,
            'confidence_level': self.confidence_level.value,
            'has_conditions': self.has_conditions(),
            'requires_follow_up': any(tr.requires_follow_up() for tr in self.term_responses),
            'is_expired': self.is_expired()
        }
    
    def with_updated_term_response(self, term_id: str, term_response: TermResponse) -> 'ProposalResponse':
        """Create new response with updated term response."""
        if term_response.term_id != term_id:
            raise ValueError("Updated term response ID must match target term ID")
        
        updated_term_responses = [
            term_response if tr.term_id == term_id else tr
            for tr in self.term_responses
        ]
        
        return ProposalResponse(
            response_id=self.response_id,
            proposal_id=self.proposal_id,
            responding_party_id=self.responding_party_id,
            overall_response=self.overall_response,
            term_responses=updated_term_responses,
            overall_reason=self.overall_reason,
            overall_comments=self.overall_comments,
            confidence_level=self.confidence_level,
            response_timestamp=self.response_timestamp,
            expires_at=self.expires_at,
            conditions=self.conditions,
            metadata=self.metadata
        )
    
    def with_updated_overall_response(self, overall_response: ResponseType,
                                    overall_reason: Optional[ResponseReason] = None) -> 'ProposalResponse':
        """Create new response with updated overall response."""
        return ProposalResponse(
            response_id=self.response_id,
            proposal_id=self.proposal_id,
            responding_party_id=self.responding_party_id,
            overall_response=overall_response,
            term_responses=self.term_responses,
            overall_reason=overall_reason or self.overall_reason,
            overall_comments=self.overall_comments,
            confidence_level=self.confidence_level,
            response_timestamp=self.response_timestamp,
            expires_at=self.expires_at,
            conditions=self.conditions,
            metadata=self.metadata
        )
    
    @property
    def age_in_seconds(self) -> int:
        """Get age of response in seconds."""
        now = datetime.now(timezone.utc)
        return int((now - self.response_timestamp).total_seconds())
    
    @property
    def time_until_expiry(self) -> Optional[int]:
        """Get time until expiry in seconds, None if no expiry."""
        if not self.expires_at:
            return None
        
        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return 0
        
        return int((self.expires_at - now).total_seconds())
    
    def __eq__(self, other: Any) -> bool:
        """Compare ProposalResponse instances for equality."""
        if not isinstance(other, ProposalResponse):
            return False
        return (
            self.response_id == other.response_id and
            self.proposal_id == other.proposal_id and
            self.responding_party_id == other.responding_party_id and
            self.overall_response == other.overall_response and
            self.term_responses == other.term_responses and
            self.overall_reason == other.overall_reason and
            self.overall_comments == other.overall_comments and
            self.confidence_level == other.confidence_level and
            self.response_timestamp == other.response_timestamp and
            self.expires_at == other.expires_at and
            self.conditions == other.conditions and
            self.metadata == other.metadata
        )
    
    def __str__(self) -> str:
        """Return string representation of proposal response."""
        return (f"ProposalResponse(id={self.response_id}, "
                f"overall={self.overall_response.value}, "
                f"terms={len(self.term_responses)}, "
                f"acceptance={self.get_acceptance_percentage():.1f}%)")