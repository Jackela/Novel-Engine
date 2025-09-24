#!/usr/bin/env python3
"""
Proposal Terms Value Objects

This module implements value objects for representing and managing
proposal terms within negotiations in the Interaction bounded context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID


class ProposalType(Enum):
    """Enumeration of proposal types."""

    TRADE_OFFER = "trade_offer"
    ALLIANCE_REQUEST = "alliance_request"
    TERRITORIAL_AGREEMENT = "territorial_agreement"
    RESOURCE_EXCHANGE = "resource_exchange"
    DIPLOMATIC_PACT = "diplomatic_pact"
    CEASEFIRE_PROPOSAL = "ceasefire_proposal"
    TRIBUTE_DEMAND = "tribute_demand"
    TECHNOLOGY_TRANSFER = "technology_transfer"
    CUSTOM = "custom"


class TermType(Enum):
    """Enumeration of term types within proposals."""

    RESOURCE_QUANTITY = "resource_quantity"
    MONETARY_VALUE = "monetary_value"
    TIME_DURATION = "time_duration"
    TERRITORIAL_CLAIM = "territorial_claim"
    TECHNOLOGY_ACCESS = "technology_access"
    MILITARY_SUPPORT = "military_support"
    DIPLOMATIC_STATUS = "diplomatic_status"
    TRADE_ROUTE = "trade_route"
    INFORMATION_SHARING = "information_sharing"
    CUSTOM_CONDITION = "custom_condition"


class ProposalPriority(Enum):
    """Enumeration of proposal priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class TermCondition:
    """
    Value object representing a single condition or term within a proposal.
    """

    term_id: str
    term_type: TermType
    description: str
    value: Union[str, int, float, Decimal, bool, Dict[str, Any]]
    priority: ProposalPriority
    is_negotiable: bool = True
    constraints: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate term condition data."""
        if not self.term_id.strip():
            raise ValueError("term_id cannot be empty")

        if not self.description.strip():
            raise ValueError("description cannot be empty")

        # Validate value based on term type
        if self.term_type == TermType.RESOURCE_QUANTITY:
            if (
                not isinstance(self.value, (int, float, Decimal))
                or self.value < 0
            ):
                raise ValueError(
                    "Resource quantity must be non-negative numeric value"
                )

        elif self.term_type == TermType.MONETARY_VALUE:
            if (
                not isinstance(self.value, (int, float, Decimal))
                or self.value < 0
            ):
                raise ValueError(
                    "Monetary value must be non-negative numeric value"
                )

        elif self.term_type == TermType.TIME_DURATION:
            if not isinstance(self.value, int) or self.value <= 0:
                raise ValueError("Time duration must be positive integer")

        # Validate constraints format
        if self.constraints:
            if not isinstance(self.constraints, dict):
                raise ValueError("constraints must be a dictionary")

        # Validate dependencies
        if self.dependencies:
            if not all(
                isinstance(dep, str) and dep.strip()
                for dep in self.dependencies
            ):
                raise ValueError("All dependencies must be non-empty strings")

    def with_value(
        self, new_value: Union[str, int, float, Decimal, bool, Dict[str, Any]]
    ) -> "TermCondition":
        """Create new TermCondition with updated value."""
        return TermCondition(
            term_id=self.term_id,
            term_type=self.term_type,
            description=self.description,
            value=new_value,
            priority=self.priority,
            is_negotiable=self.is_negotiable,
            constraints=self.constraints,
            dependencies=self.dependencies,
        )

    def with_priority(self, new_priority: ProposalPriority) -> "TermCondition":
        """Create new TermCondition with updated priority."""
        return TermCondition(
            term_id=self.term_id,
            term_type=self.term_type,
            description=self.description,
            value=self.value,
            priority=new_priority,
            is_negotiable=self.is_negotiable,
            constraints=self.constraints,
            dependencies=self.dependencies,
        )

    def make_non_negotiable(self) -> "TermCondition":
        """Create new TermCondition marked as non-negotiable."""
        return TermCondition(
            term_id=self.term_id,
            term_type=self.term_type,
            description=self.description,
            value=self.value,
            priority=self.priority,
            is_negotiable=False,
            constraints=self.constraints,
            dependencies=self.dependencies,
        )

    @property
    def numeric_value(self) -> Optional[Union[int, float, Decimal]]:
        """Get numeric value if applicable."""
        if isinstance(self.value, (int, float, Decimal)):
            return self.value
        return None

    @property
    def string_value(self) -> Optional[str]:
        """Get string value if applicable."""
        if isinstance(self.value, str):
            return self.value
        return None

    @property
    def boolean_value(self) -> Optional[bool]:
        """Get boolean value if applicable."""
        if isinstance(self.value, bool):
            return self.value
        return None

    def __eq__(self, other: Any) -> bool:
        """Compare TermCondition instances for equality."""
        if not isinstance(other, TermCondition):
            return False
        return (
            self.term_id == other.term_id
            and self.term_type == other.term_type
            and self.description == other.description
            and self.value == other.value
            and self.priority == other.priority
            and self.is_negotiable == other.is_negotiable
            and self.constraints == other.constraints
            and self.dependencies == other.dependencies
        )


@dataclass(frozen=True)
class ProposalTerms:
    """
    Value object representing the complete terms of a proposal.

    Encapsulates all conditions, constraints, and metadata for a specific
    proposal within a negotiation session.
    """

    proposal_id: UUID
    proposal_type: ProposalType
    title: str
    summary: str
    terms: List[TermCondition]
    validity_period: Optional[datetime] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate proposal terms data."""
        if not self.title.strip():
            raise ValueError("title cannot be empty")

        if not self.summary.strip():
            raise ValueError("summary cannot be empty")

        if not self.terms:
            raise ValueError("proposal must have at least one term")

        # Ensure created_at is timezone-aware
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        # Validate validity period
        if self.validity_period:
            if self.validity_period.tzinfo is None:
                raise ValueError("validity_period must be timezone-aware")
            if self.validity_period <= self.created_at:
                raise ValueError("validity_period must be after created_at")

        # Validate term dependencies
        term_ids = {term.term_id for term in self.terms}
        for term in self.terms:
            for dependency in term.dependencies or []:
                if dependency not in term_ids:
                    raise ValueError(
                        f"Term {term.term_id} has invalid dependency: {dependency}"
                    )

        # Check for circular dependencies
        self._validate_no_circular_dependencies()

    def _validate_no_circular_dependencies(self):
        """Validate that there are no circular dependencies between terms."""

        def has_circular_dependency(
            term_id: str, visited: set, path: set
        ) -> bool:
            if term_id in path:
                return True
            if term_id in visited:
                return False

            visited.add(term_id)
            path.add(term_id)

            term = next((t for t in self.terms if t.term_id == term_id), None)
            if term:
                for dependency in term.dependencies or []:
                    if has_circular_dependency(dependency, visited, path):
                        return True

            path.remove(term_id)
            return False

        # P3 Sprint 2 Pattern: Explicit type annotation for MyPy compatibility
        visited: Set[str] = set()
        for term in self.terms:
            if term.term_id not in visited:
                if has_circular_dependency(term.term_id, visited, set()):
                    raise ValueError(
                        f"Circular dependency detected involving term: {term.term_id}"
                    )

    @classmethod
    def create(
        cls,
        proposal_type: ProposalType,
        title: str,
        summary: str,
        terms: List[TermCondition],
        validity_period: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ProposalTerms":
        """Create new ProposalTerms with generated ID."""
        from uuid import uuid4

        return cls(
            proposal_id=uuid4(),
            proposal_type=proposal_type,
            title=title,
            summary=summary,
            terms=terms,
            validity_period=validity_period,
            metadata=metadata or {},
        )

    def get_term_by_id(self, term_id: str) -> Optional[TermCondition]:
        """Get term by ID."""
        return next(
            (term for term in self.terms if term.term_id == term_id), None
        )

    def get_terms_by_type(self, term_type: TermType) -> List[TermCondition]:
        """Get all terms of specified type."""
        return [term for term in self.terms if term.term_type == term_type]

    def get_terms_by_priority(
        self, priority: ProposalPriority
    ) -> List[TermCondition]:
        """Get all terms with specified priority."""
        return [term for term in self.terms if term.priority == priority]

    def get_critical_terms(self) -> List[TermCondition]:
        """Get all critical terms."""
        return self.get_terms_by_priority(ProposalPriority.CRITICAL)

    def get_negotiable_terms(self) -> List[TermCondition]:
        """Get all negotiable terms."""
        return [term for term in self.terms if term.is_negotiable]

    def get_non_negotiable_terms(self) -> List[TermCondition]:
        """Get all non-negotiable terms."""
        return [term for term in self.terms if not term.is_negotiable]

    def update_term(
        self, term_id: str, updated_term: TermCondition
    ) -> "ProposalTerms":
        """Create new ProposalTerms with updated term."""
        if updated_term.term_id != term_id:
            raise ValueError("Updated term ID must match target term ID")

        updated_terms = [
            updated_term if term.term_id == term_id else term
            for term in self.terms
        ]

        return ProposalTerms(
            proposal_id=self.proposal_id,
            proposal_type=self.proposal_type,
            title=self.title,
            summary=self.summary,
            terms=updated_terms,
            validity_period=self.validity_period,
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def add_term(self, term: TermCondition) -> "ProposalTerms":
        """Create new ProposalTerms with additional term."""
        if any(
            existing_term.term_id == term.term_id
            for existing_term in self.terms
        ):
            raise ValueError(f"Term with ID {term.term_id} already exists")

        return ProposalTerms(
            proposal_id=self.proposal_id,
            proposal_type=self.proposal_type,
            title=self.title,
            summary=self.summary,
            terms=self.terms + [term],
            validity_period=self.validity_period,
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def remove_term(self, term_id: str) -> "ProposalTerms":
        """Create new ProposalTerms with term removed."""
        # Check if other terms depend on this term
        dependent_terms = [
            term
            for term in self.terms
            if term.dependencies and term_id in term.dependencies
        ]

        if dependent_terms:
            dependent_ids = [term.term_id for term in dependent_terms]
            raise ValueError(
                f"Cannot remove term {term_id}: it has dependents {dependent_ids}"
            )

        updated_terms = [
            term for term in self.terms if term.term_id != term_id
        ]

        if len(updated_terms) == len(self.terms):
            raise ValueError(f"Term with ID {term_id} not found")

        if not updated_terms:
            raise ValueError("Cannot remove last term from proposal")

        return ProposalTerms(
            proposal_id=self.proposal_id,
            proposal_type=self.proposal_type,
            title=self.title,
            summary=self.summary,
            terms=updated_terms,
            validity_period=self.validity_period,
            created_at=self.created_at,
            metadata=self.metadata,
        )

    @property
    def is_expired(self) -> bool:
        """Check if proposal has expired."""
        if not self.validity_period:
            return False
        return datetime.now(timezone.utc) > self.validity_period

    @property
    def total_terms_count(self) -> int:
        """Get total number of terms."""
        return len(self.terms)

    @property
    def negotiable_terms_count(self) -> int:
        """Get count of negotiable terms."""
        return len(self.get_negotiable_terms())

    @property
    def critical_terms_count(self) -> int:
        """Get count of critical terms."""
        return len(self.get_critical_terms())

    def __eq__(self, other: Any) -> bool:
        """Compare ProposalTerms instances for equality."""
        if not isinstance(other, ProposalTerms):
            return False
        return (
            self.proposal_id == other.proposal_id
            and self.proposal_type == other.proposal_type
            and self.title == other.title
            and self.summary == other.summary
            and self.terms == other.terms
            and self.validity_period == other.validity_period
            and self.created_at == other.created_at
            and self.metadata == other.metadata
        )

    def __str__(self) -> str:
        """Return string representation of proposal terms."""
        return f"ProposalTerms(id={self.proposal_id}, type={self.proposal_type.value}, terms={len(self.terms)})"
