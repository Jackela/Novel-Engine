#!/usr/bin/env python3
"""
Tests for Proposal Service (ProposalTerms, TermCondition).

This module contains comprehensive tests for proposal management
including term validation, proposal lifecycle, and operations.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.contexts.interactions.domain.value_objects.proposal_terms import (
    ProposalPriority,
    ProposalTerms,
    ProposalType,
    TermCondition,
    TermType,
)

pytestmark = pytest.mark.unit


class TestProposalType:
    """Test suite for ProposalType enumeration."""

    def test_proposal_type_values(self):
        """Test proposal type enumeration values."""
        assert ProposalType.TRADE_OFFER.value == "trade_offer"
        assert ProposalType.ALLIANCE_REQUEST.value == "alliance_request"
        assert ProposalType.TERRITORIAL_AGREEMENT.value == "territorial_agreement"
        assert ProposalType.RESOURCE_EXCHANGE.value == "resource_exchange"
        assert ProposalType.DIPLOMATIC_PACT.value == "diplomatic_pact"
        assert ProposalType.CEASEFIRE_PROPOSAL.value == "ceasefire_proposal"
        assert ProposalType.TRIBUTE_DEMAND.value == "tribute_demand"
        assert ProposalType.TECHNOLOGY_TRANSFER.value == "technology_transfer"
        assert ProposalType.CUSTOM.value == "custom"


class TestTermType:
    """Test suite for TermType enumeration."""

    def test_term_type_values(self):
        """Test term type enumeration values."""
        assert TermType.RESOURCE_QUANTITY.value == "resource_quantity"
        assert TermType.MONETARY_VALUE.value == "monetary_value"
        assert TermType.TIME_DURATION.value == "time_duration"
        assert TermType.TERRITORIAL_CLAIM.value == "territorial_claim"
        assert TermType.TECHNOLOGY_ACCESS.value == "technology_access"
        assert TermType.MILITARY_SUPPORT.value == "military_support"
        assert TermType.DIPLOMATIC_STATUS.value == "diplomatic_status"
        assert TermType.TRADE_ROUTE.value == "trade_route"
        assert TermType.INFORMATION_SHARING.value == "information_sharing"
        assert TermType.CUSTOM_CONDITION.value == "custom_condition"


class TestProposalPriority:
    """Test suite for ProposalPriority enumeration."""

    def test_priority_values(self):
        """Test priority enumeration values."""
        assert ProposalPriority.CRITICAL.value == "critical"
        assert ProposalPriority.HIGH.value == "high"
        assert ProposalPriority.MEDIUM.value == "medium"
        assert ProposalPriority.LOW.value == "low"
        assert ProposalPriority.OPTIONAL.value == "optional"


class TestTermConditionCreation:
    """Test suite for TermCondition creation."""

    def test_create_basic_term(self):
        """Test creating a basic term condition."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="100 units of wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        assert term.term_id == "term_1"
        assert term.term_type == TermType.RESOURCE_QUANTITY
        assert term.value == 100
        assert term.priority == ProposalPriority.HIGH
        assert term.is_negotiable is True  # Default

    def test_create_non_negotiable_term(self):
        """Test creating a non-negotiable term."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.MONETARY_VALUE,
            description="500 gold",
            value=500,
            priority=ProposalPriority.CRITICAL,
            is_negotiable=False,
        )

        assert term.is_negotiable is False

    def test_create_term_with_constraints(self):
        """Test creating a term with constraints."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood quantity",
            value=100,
            priority=ProposalPriority.HIGH,
            constraints={"min": 50, "max": 200},
        )

        assert term.constraints == {"min": 50, "max": 200}

    def test_create_term_with_dependencies(self):
        """Test creating a term with dependencies."""
        term = TermCondition(
            term_id="term_2",
            term_type=TermType.MONETARY_VALUE,
            description="Payment",
            value=500,
            priority=ProposalPriority.HIGH,
            dependencies=["term_1"],
        )

        assert term.dependencies == ["term_1"]


class TestTermConditionValidation:
    """Test suite for TermCondition validation."""

    def test_validation_empty_term_id(self):
        """Test validation with empty term ID."""
        with pytest.raises(ValueError, match="term_id cannot be empty"):
            TermCondition(
                term_id="",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Test",
                value=100,
                priority=ProposalPriority.HIGH,
            )

    def test_validation_empty_description(self):
        """Test validation with empty description."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="",
                value=100,
                priority=ProposalPriority.HIGH,
            )

    def test_validation_negative_resource_quantity(self):
        """Test validation with negative resource quantity."""
        with pytest.raises(ValueError, match="non-negative"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Test",
                value=-100,
                priority=ProposalPriority.HIGH,
            )

    def test_validation_negative_monetary_value(self):
        """Test validation with negative monetary value."""
        with pytest.raises(ValueError, match="non-negative"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.MONETARY_VALUE,
                description="Test",
                value=-500,
                priority=ProposalPriority.HIGH,
            )

    def test_validation_zero_time_duration(self):
        """Test validation with zero time duration."""
        with pytest.raises(ValueError, match="positive"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.TIME_DURATION,
                description="Test",
                value=0,
                priority=ProposalPriority.HIGH,
            )

    def test_validation_invalid_constraints_type(self):
        """Test validation with invalid constraints type."""
        with pytest.raises(ValueError, match="constraints must be a dictionary"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Test",
                value=100,
                priority=ProposalPriority.HIGH,
                constraints="invalid",  # type: ignore
            )

    def test_validation_invalid_dependencies(self):
        """Test validation with invalid dependencies."""
        with pytest.raises(ValueError, match="non-empty strings"):
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Test",
                value=100,
                priority=ProposalPriority.HIGH,
                dependencies=[""],
            )


class TestTermConditionImmutability:
    """Test suite for TermCondition immutability."""

    def test_with_value(self):
        """Test creating term with new value."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        new_term = term.with_value(150)

        assert new_term.value == 150
        assert term.value == 100  # Original unchanged
        assert new_term.term_id == term.term_id

    def test_with_priority(self):
        """Test creating term with new priority."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.MEDIUM,
        )

        new_term = term.with_priority(ProposalPriority.HIGH)

        assert new_term.priority == ProposalPriority.HIGH
        assert term.priority == ProposalPriority.MEDIUM

    def test_make_non_negotiable(self):
        """Test making term non-negotiable."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
            is_negotiable=True,
        )

        fixed_term = term.make_non_negotiable()

        assert fixed_term.is_negotiable is False
        assert term.is_negotiable is True


class TestTermConditionProperties:
    """Test suite for TermCondition properties."""

    def test_numeric_value(self):
        """Test getting numeric value."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        assert term.numeric_value == 100

    def test_numeric_value_non_numeric(self):
        """Test getting numeric value from non-numeric term."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.DIPLOMATIC_STATUS,
            description="Status",
            value="ally",
            priority=ProposalPriority.HIGH,
        )

        assert term.numeric_value is None

    def test_string_value(self):
        """Test getting string value."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.DIPLOMATIC_STATUS,
            description="Status",
            value="ally",
            priority=ProposalPriority.HIGH,
        )

        assert term.string_value == "ally"

    def test_string_value_non_string(self):
        """Test getting string value from non-string term."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        assert term.string_value is None

    def test_boolean_value(self):
        """Test getting boolean value."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.CUSTOM_CONDITION,
            description="Condition",
            value=True,
            priority=ProposalPriority.HIGH,
        )

        assert term.boolean_value is True

    def test_boolean_value_non_boolean(self):
        """Test getting boolean value from non-boolean term."""
        term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        assert term.boolean_value is None


class TestProposalTermsCreation:
    """Test suite for ProposalTerms creation."""

    def test_create_basic_proposal(self):
        """Test creating a basic proposal."""
        terms = [
            TermCondition(
                term_id="term_1",
                term_type=TermType.RESOURCE_QUANTITY,
                description="Wood",
                value=100,
                priority=ProposalPriority.HIGH,
            )
        ]

        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade Offer",
            summary="Exchange resources",
            terms=terms,
        )

        assert proposal.proposal_type == ProposalType.TRADE_OFFER
        assert proposal.title == "Trade Offer"
        assert len(proposal.terms) == 1
        assert proposal.proposal_id is not None
        assert proposal.created_at is not None

    def test_create_proposal_with_validity_period(self):
        """Test creating a proposal with validity period."""
        validity = datetime.now(timezone.utc) + timedelta(days=7)

        proposal = ProposalTerms.create(
            proposal_type=ProposalType.ALLIANCE_REQUEST,
            title="Alliance Request",
            summary="Form alliance",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.DIPLOMATIC_STATUS,
                    description="Alliance",
                    value="ally",
                    priority=ProposalPriority.CRITICAL,
                )
            ],
            validity_period=validity,
        )

        assert proposal.validity_period == validity

    def test_create_proposal_with_metadata(self):
        """Test creating a proposal with metadata."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade Offer",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
            metadata={"created_by": "player_1", "urgency": "high"},
        )

        assert proposal.metadata == {"created_by": "player_1", "urgency": "high"}


class TestProposalTermsValidation:
    """Test suite for ProposalTerms validation."""

    def test_validation_empty_title(self):
        """Test validation with empty title."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            ProposalTerms(
                proposal_id=uuid4(),
                proposal_type=ProposalType.TRADE_OFFER,
                title="",
                summary="Exchange",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                    )
                ],
            )

    def test_validation_empty_summary(self):
        """Test validation with empty summary."""
        with pytest.raises(ValueError, match="summary cannot be empty"):
            ProposalTerms(
                proposal_id=uuid4(),
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                    )
                ],
            )

    def test_validation_no_terms(self):
        """Test validation with no terms."""
        with pytest.raises(ValueError, match="at least one term"):
            ProposalTerms(
                proposal_id=uuid4(),
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="Exchange",
                terms=[],
            )

    def test_validation_naive_created_at(self):
        """Test validation with naive created_at timestamp."""
        with pytest.raises(ValueError, match="timezone-aware"):
            ProposalTerms(
                proposal_id=uuid4(),
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="Exchange",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                    )
                ],
                created_at=datetime.now(),  # Naive datetime
            )

    def test_validation_invalid_dependency(self):
        """Test validation with invalid term dependency."""
        with pytest.raises(ValueError, match="invalid dependency"):
            ProposalTerms.create(
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="Exchange",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                        dependencies=["nonexistent_term"],
                    )
                ],
            )

    def test_validation_circular_dependency(self):
        """Test validation with circular dependency."""
        with pytest.raises(ValueError, match="Circular dependency"):
            ProposalTerms.create(
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="Exchange",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                        dependencies=["term_2"],
                    ),
                    TermCondition(
                        term_id="term_2",
                        term_type=TermType.MONETARY_VALUE,
                        description="Gold",
                        value=500,
                        priority=ProposalPriority.HIGH,
                        dependencies=["term_1"],
                    ),
                ],
            )

    def test_validation_validity_period_before_created(self):
        """Test validation with validity period before created_at."""
        created = datetime.now(timezone.utc)
        validity = created - timedelta(days=1)

        with pytest.raises(ValueError, match="validity_period must be after"):
            ProposalTerms(
                proposal_id=uuid4(),
                proposal_type=ProposalType.TRADE_OFFER,
                title="Trade",
                summary="Exchange",
                terms=[
                    TermCondition(
                        term_id="term_1",
                        term_type=TermType.RESOURCE_QUANTITY,
                        description="Wood",
                        value=100,
                        priority=ProposalPriority.HIGH,
                    )
                ],
                created_at=created,
                validity_period=validity,
            )


class TestProposalTermsQueries:
    """Test suite for ProposalTerms query methods."""

    def test_get_term_by_id(self):
        """Test getting term by ID."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                ),
            ],
        )

        term = proposal.get_term_by_id("term_2")

        assert term is not None
        assert term.term_id == "term_2"
        assert term.term_type == TermType.MONETARY_VALUE

    def test_get_term_by_id_not_found(self):
        """Test getting non-existent term."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        term = proposal.get_term_by_id("nonexistent")

        assert term is None

    def test_get_terms_by_type(self):
        """Test getting terms by type."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Stone",
                    value=50,
                    priority=ProposalPriority.MEDIUM,
                ),
                TermCondition(
                    term_id="term_3",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                ),
            ],
        )

        resource_terms = proposal.get_terms_by_type(TermType.RESOURCE_QUANTITY)

        assert len(resource_terms) == 2
        assert all(t.term_type == TermType.RESOURCE_QUANTITY for t in resource_terms)

    def test_get_terms_by_priority(self):
        """Test getting terms by priority."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.CRITICAL,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.HIGH,
                ),
            ],
        )

        critical_terms = proposal.get_terms_by_priority(ProposalPriority.CRITICAL)

        assert len(critical_terms) == 1
        assert critical_terms[0].term_id == "term_1"

    def test_get_critical_terms(self):
        """Test getting critical terms."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.CRITICAL,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.HIGH,
                ),
            ],
        )

        critical_terms = proposal.get_critical_terms()

        assert len(critical_terms) == 1
        assert critical_terms[0].priority == ProposalPriority.CRITICAL

    def test_get_negotiable_terms(self):
        """Test getting negotiable terms."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                    is_negotiable=True,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                    is_negotiable=False,
                ),
            ],
        )

        negotiable = proposal.get_negotiable_terms()
        non_negotiable = proposal.get_non_negotiable_terms()

        assert len(negotiable) == 1
        assert len(non_negotiable) == 1
        assert negotiable[0].term_id == "term_1"
        assert non_negotiable[0].term_id == "term_2"


class TestProposalTermsImmutability:
    """Test suite for ProposalTerms immutability."""

    def test_update_term(self):
        """Test updating a term."""
        original_term = TermCondition(
            term_id="term_1",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=100,
            priority=ProposalPriority.HIGH,
        )

        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[original_term],
        )

        updated_term = original_term.with_value(150)
        new_proposal = proposal.update_term("term_1", updated_term)

        assert new_proposal.get_term_by_id("term_1").value == 150
        assert proposal.get_term_by_id("term_1").value == 100  # Original unchanged

    def test_update_term_id_mismatch(self):
        """Test updating term with ID mismatch."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        wrong_term = TermCondition(
            term_id="different_id",
            term_type=TermType.RESOURCE_QUANTITY,
            description="Wood",
            value=150,
            priority=ProposalPriority.HIGH,
        )

        with pytest.raises(ValueError, match="Updated term ID must match"):
            proposal.update_term("term_1", wrong_term)

    def test_add_term(self):
        """Test adding a new term."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        new_term = TermCondition(
            term_id="term_2",
            term_type=TermType.MONETARY_VALUE,
            description="Gold",
            value=500,
            priority=ProposalPriority.CRITICAL,
        )

        new_proposal = proposal.add_term(new_term)

        assert len(new_proposal.terms) == 2
        assert len(proposal.terms) == 1  # Original unchanged
        assert new_proposal.get_term_by_id("term_2") is not None

    def test_add_term_duplicate_id(self):
        """Test adding term with duplicate ID."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        duplicate_term = TermCondition(
            term_id="term_1",
            term_type=TermType.MONETARY_VALUE,
            description="Gold",
            value=500,
            priority=ProposalPriority.CRITICAL,
        )

        with pytest.raises(ValueError, match="already exists"):
            proposal.add_term(duplicate_term)

    def test_remove_term(self):
        """Test removing a term."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                ),
            ],
        )

        new_proposal = proposal.remove_term("term_1")

        assert len(new_proposal.terms) == 1
        assert len(proposal.terms) == 2  # Original unchanged
        assert new_proposal.get_term_by_id("term_1") is None

    def test_remove_term_with_dependents(self):
        """Test removing term with dependent terms."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold payment for wood",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                    dependencies=["term_1"],
                ),
            ],
        )

        with pytest.raises(ValueError, match="has dependents"):
            proposal.remove_term("term_1")

    def test_remove_last_term(self):
        """Test removing the last term."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        with pytest.raises(ValueError, match="Cannot remove last term"):
            proposal.remove_term("term_1")


class TestProposalTermsProperties:
    """Test suite for ProposalTerms properties."""

    def test_is_expired_true(self):
        """Test expired proposal detection."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        proposal = ProposalTerms(
            proposal_id=uuid4(),
            proposal_type=ProposalType.TRADE_OFFER,
            title="Expired",
            summary="This has expired",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
            validity_period=past_date,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )

        assert proposal.is_expired is True

    def test_is_expired_false(self):
        """Test non-expired proposal detection."""
        future_date = datetime.now(timezone.utc) + timedelta(days=7)

        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Valid",
            summary="This is still valid",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
            validity_period=future_date,
        )

        assert proposal.is_expired is False

    def test_is_expired_no_validity(self):
        """Test proposal without validity period."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="No Expiry",
            summary="Never expires",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        assert proposal.is_expired is False

    def test_total_terms_count(self):
        """Test total terms count property."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                ),
            ],
        )

        assert proposal.total_terms_count == 2

    def test_negotiable_terms_count(self):
        """Test negotiable terms count property."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                    is_negotiable=True,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.CRITICAL,
                    is_negotiable=False,
                ),
            ],
        )

        assert proposal.negotiable_terms_count == 1

    def test_critical_terms_count(self):
        """Test critical terms count property."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.CRITICAL,
                ),
                TermCondition(
                    term_id="term_2",
                    term_type=TermType.MONETARY_VALUE,
                    description="Gold",
                    value=500,
                    priority=ProposalPriority.HIGH,
                ),
            ],
        )

        assert proposal.critical_terms_count == 1


class TestProposalTermsEquality:
    """Test suite for ProposalTerms equality."""

    def test_equality_same(self):
        """Test equality of identical proposals."""
        proposal_id = uuid4()
        created_at = datetime.now(timezone.utc)

        proposal1 = ProposalTerms(
            proposal_id=proposal_id,
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
            created_at=created_at,
        )

        proposal2 = ProposalTerms(
            proposal_id=proposal_id,
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
            created_at=created_at,
        )

        assert proposal1 == proposal2

    def test_equality_different(self):
        """Test inequality of different proposals."""
        proposal1 = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade 1",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        proposal2 = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade 2",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        assert proposal1 != proposal2

    def test_equality_different_type(self):
        """Test equality with different type."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        assert proposal != "not a proposal"

    def test_str(self):
        """Test string representation."""
        proposal = ProposalTerms.create(
            proposal_type=ProposalType.TRADE_OFFER,
            title="Trade",
            summary="Exchange",
            terms=[
                TermCondition(
                    term_id="term_1",
                    term_type=TermType.RESOURCE_QUANTITY,
                    description="Wood",
                    value=100,
                    priority=ProposalPriority.HIGH,
                )
            ],
        )

        repr_str = str(proposal)

        assert "ProposalTerms" in repr_str
        assert "trade_offer" in repr_str
