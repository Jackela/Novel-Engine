#!/usr/bin/env python3
"""
Outcome Calculator Service

Application service for calculating and analyzing negotiation outcomes
using Result pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from .....core.result import Err, Ok, Result
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.negotiation_status import NegotiationOutcome
from ....interactions.domain.value_objects.proposal_response import ProposalResponse
from .shared.errors import (
    OutcomeError,
    ValidationError,
)


class OutcomeCalculator:
    """
    Service for calculating negotiation outcomes and results.

    Provides business operations for determining negotiation results,
    calculating outcome metrics, and analyzing success factors.
    """

    def __init__(self) -> None:
        """Initialize outcome calculator."""
        pass

    def calculate_outcome_from_responses(
        self,
        proposal_id: UUID,
        responses: List[ProposalResponse],
        parties: List[NegotiationParty],
        require_unanimous: bool = False,
    ) -> Result[Dict[str, Any], OutcomeError]:
        """
        Calculate negotiation outcome based on responses.

        Args:
            proposal_id: ID of the proposal
            responses: List of proposal responses
            parties: List of negotiating parties
            require_unanimous: Whether unanimous agreement is required

        Returns:
            Result containing outcome calculation or error
        """
        if not responses:
            return Err(
                OutcomeError(
                    message="No responses provided for outcome calculation",
                    outcome_type="pending",
                    recoverable=True,
                )
            )

        if not parties:
            return Err(
                OutcomeError(
                    message="At least one party required for outcome calculation",
                    outcome_type="error",
                    recoverable=True,
                )
            )

        try:
            decision_makers = [p for p in parties if p.is_decision_maker]
            if not decision_makers:
                return Err(
                    OutcomeError(
                        message="No decision makers found in parties",
                        outcome_type="blocked",
                        recoverable=True,
                    )
                )

            # Filter responses for the specific proposal
            proposal_responses = [r for r in responses if r.proposal_id == proposal_id]

            if not proposal_responses:
                return Err(
                    OutcomeError(
                        message=f"No responses found for proposal {proposal_id}",
                        outcome_type="pending",
                        recoverable=True,
                    )
                )

            # Count acceptances
            acceptances = [r for r in proposal_responses if r.is_complete_acceptance()]
            rejections = [
                r for r in proposal_responses if r.overall_response.value == "rejected"
            ]

            total_decision_makers = len(decision_makers)
            acceptance_count = len(acceptances)
            rejection_count = len(rejections)

            # Determine outcome
            if require_unanimous:
                if acceptance_count == total_decision_makers:
                    outcome = NegotiationOutcome.AGREEMENT_REACHED
                    outcome_status = "agreement"
                elif rejection_count > 0:
                    outcome = NegotiationOutcome.REJECTED
                    outcome_status = "rejected"
                else:
                    outcome = NegotiationOutcome.PENDING
                    outcome_status = "pending"
            else:
                if acceptance_count > total_decision_makers // 2:
                    outcome = NegotiationOutcome.AGREEMENT_REACHED
                    outcome_status = "agreement"
                elif rejection_count > total_decision_makers // 2:
                    outcome = NegotiationOutcome.REJECTED
                    outcome_status = "rejected"
                else:
                    outcome = NegotiationOutcome.PENDING
                    outcome_status = "pending"

            # Calculate metrics
            acceptance_rate = (
                acceptance_count / total_decision_makers
                if total_decision_makers > 0
                else 0
            )

            # Calculate average acceptance percentage
            avg_acceptance = (
                sum(r.get_acceptance_percentage() for r in proposal_responses)
                / len(proposal_responses)
                if proposal_responses
                else 0
            )

            result = {
                "proposal_id": str(proposal_id),
                "outcome": outcome.value,
                "outcome_status": outcome_status,
                "acceptance_count": acceptance_count,
                "rejection_count": rejection_count,
                "pending_count": total_decision_makers
                - acceptance_count
                - rejection_count,
                "total_decision_makers": total_decision_makers,
                "acceptance_rate": acceptance_rate,
                "average_acceptance_percentage": avg_acceptance,
                "require_unanimous": require_unanimous,
                "is_complete": outcome != NegotiationOutcome.PENDING,
            }

            return Ok(result)
        except Exception as e:
            return Err(
                OutcomeError(
                    message=f"Failed to calculate outcome: {e!s}",
                    outcome_type="error",
                    recoverable=True,
                )
            )

    def calculate_negotiation_success_metrics(
        self,
        outcome: NegotiationOutcome,
        parties: List[NegotiationParty],
        responses: List[ProposalResponse],
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Result[Dict[str, Any], OutcomeError]:
        """
        Calculate success metrics for a completed negotiation.

        Args:
            outcome: Final negotiation outcome
            parties: List of negotiating parties
            responses: List of all responses
            start_time: When negotiation started
            end_time: When negotiation ended (defaults to now)

        Returns:
            Result containing success metrics or error
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        if start_time > end_time:
            return Err(
                ValidationError(
                    message="Start time cannot be after end time",
                    field="start_time",
                    recoverable=True,
                )
            )

        try:
            # Calculate duration
            duration = (end_time - start_time).total_seconds()
            duration_hours = duration / 3600

            # Calculate party participation
            participating_parties = len(set(r.responding_party_id for r in responses))
            total_parties = len(parties)
            participation_rate = (
                participating_parties / total_parties if total_parties > 0 else 0
            )

            # Calculate response quality metrics
            if responses:
                avg_acceptance = sum(
                    r.get_acceptance_percentage() for r in responses
                ) / len(responses)

                complete_responses = sum(
                    1 for r in responses if r.is_complete_acceptance()
                )
                response_quality = complete_responses / len(responses)
            else:
                avg_acceptance = 0.0
                response_quality = 0.0

            # Determine success level
            if outcome == NegotiationOutcome.AGREEMENT_REACHED:
                success_level = "full_success"
                success_score = 100.0
            elif outcome == NegotiationOutcome.PARTIAL_AGREEMENT:
                success_level = "partial_success"
                success_score = 60.0
            elif outcome == NegotiationOutcome.COMPROMISE:
                success_level = "compromise"
                success_score = 50.0
            elif outcome == NegotiationOutcome.REJECTED:
                success_level = "failure"
                success_score = 0.0
            elif outcome == NegotiationOutcome.TIMEOUT:
                success_level = "timeout"
                success_score = 20.0
            else:
                success_level = "unknown"
                success_score = 0.0

            result = {
                "outcome": outcome.value,
                "success_level": success_level,
                "success_score": success_score,
                "duration_seconds": duration,
                "duration_hours": duration_hours,
                "participation_rate": participation_rate,
                "participating_parties": participating_parties,
                "total_parties": total_parties,
                "total_responses": len(responses),
                "average_acceptance_percentage": avg_acceptance,
                "response_quality": response_quality,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                OutcomeError(
                    message=f"Failed to calculate success metrics: {e!s}",
                    outcome_type=outcome.value,
                    recoverable=True,
                )
            )

    def analyze_outcome_factors(
        self,
        outcome: NegotiationOutcome,
        parties: List[NegotiationParty],
        responses: List[ProposalResponse],
    ) -> Result[Dict[str, Any], OutcomeError]:
        """
        Analyze factors that contributed to the outcome.

        Args:
            outcome: Final negotiation outcome
            parties: List of negotiating parties
            responses: List of all responses

        Returns:
            Result containing factor analysis or error
        """
        try:
            positive_factors: List[str] = []
            negative_factors: List[str] = []

            # Analyze party composition
            decision_makers = [p for p in parties if p.is_decision_maker]
            if len(decision_makers) >= 2:
                positive_factors.append("Multiple decision makers participated")
            elif len(decision_makers) == 0:
                negative_factors.append("No parties had decision-making authority")
            else:
                negative_factors.append("Only one decision maker present")

            # Analyze response patterns
            if responses:
                acceptance_rate = sum(
                    1 for r in responses if r.is_complete_acceptance()
                ) / len(responses)

                if acceptance_rate > 0.7:
                    positive_factors.append("High acceptance rate among responses")
                elif acceptance_rate < 0.3:
                    negative_factors.append("Low acceptance rate among responses")

                # Check for consensus
                if all(r.is_complete_acceptance() for r in responses):
                    positive_factors.append("Complete consensus achieved")
                elif any(r.overall_response.value == "rejected" for r in responses):
                    negative_factors.append("At least one party rejected the proposal")

            # Analyze party styles
            collaborative_count = sum(
                1
                for p in parties
                if p.preferences.negotiation_style.value == "collaborative"
            )
            if collaborative_count > len(parties) // 2:
                positive_factors.append("Majority of parties have collaborative style")

            competitive_count = sum(
                1
                for p in parties
                if p.preferences.negotiation_style.value == "competitive"
            )
            if competitive_count > len(parties) // 2:
                negative_factors.append("Majority of parties have competitive style")

            result = {
                "outcome": outcome.value,
                "positive_factors": positive_factors,
                "negative_factors": negative_factors,
                "factor_balance": len(positive_factors) - len(negative_factors),
                "recommendations": self._generate_outcome_recommendations(
                    outcome, positive_factors, negative_factors
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                OutcomeError(
                    message=f"Failed to analyze outcome factors: {e!s}",
                    outcome_type=outcome.value,
                    recoverable=True,
                )
            )

    def predict_outcome_likelihood(
        self,
        parties: List[NegotiationParty],
        current_responses: List[ProposalResponse],
        total_expected_responses: int,
    ) -> Result[Dict[str, Any], OutcomeError]:
        """
        Predict likelihood of different outcomes based on current state.

        Args:
            parties: List of negotiating parties
            current_responses: Responses received so far
            total_expected_responses: Total number of expected responses

        Returns:
            Result containing outcome predictions or error
        """
        if total_expected_responses <= 0:
            return Err(
                ValidationError(
                    message="Total expected responses must be positive",
                    field="total_expected_responses",
                    field_value=total_expected_responses,
                    recoverable=True,
                )
            )

        try:
            current_count = len(current_responses)

            if current_count == 0:
                # No data yet - base on party composition
                decision_makers = [p for p in parties if p.is_decision_maker]
                if len(decision_makers) >= 2:
                    agreement_prob = 0.5
                    partial_prob = 0.3
                    reject_prob = 0.2
                else:
                    agreement_prob = 0.2
                    partial_prob = 0.3
                    reject_prob = 0.5
            else:
                # Calculate based on current responses
                acceptances = sum(
                    1 for r in current_responses if r.is_complete_acceptance()
                )
                rejections = sum(
                    1
                    for r in current_responses
                    if r.overall_response.value == "rejected"
                )

                # Current rates
                current_accept_rate = acceptances / current_count
                current_reject_rate = rejections / current_count

                # Project to total
                projected_accepts = current_accept_rate * total_expected_responses
                projected_rejects = current_reject_rate * total_expected_responses

                # Calculate probabilities
                if projected_accepts > total_expected_responses / 2:
                    agreement_prob = 0.7
                    partial_prob = 0.2
                    reject_prob = 0.1
                elif projected_rejects > total_expected_responses / 2:
                    agreement_prob = 0.1
                    partial_prob = 0.2
                    reject_prob = 0.7
                else:
                    agreement_prob = 0.3
                    partial_prob = 0.5
                    reject_prob = 0.2

            result = {
                "current_responses": current_count,
                "total_expected": total_expected_responses,
                "completion_percentage": (current_count / total_expected_responses)
                * 100,
                "predictions": {
                    "agreement_likelihood": agreement_prob,
                    "partial_agreement_likelihood": partial_prob,
                    "rejection_likelihood": reject_prob,
                },
                "most_likely_outcome": max(
                    [
                        ("agreement", agreement_prob),
                        ("partial_agreement", partial_prob),
                        ("rejection", reject_prob),
                    ],
                    key=lambda x: x[1],
                )[0],
                "confidence": "low"
                if current_count < total_expected_responses / 2
                else "medium",
            }

            return Ok(result)
        except Exception as e:
            return Err(
                OutcomeError(
                    message=f"Failed to predict outcome: {e!s}",
                    outcome_type="prediction",
                    recoverable=True,
                )
            )

    def _generate_outcome_recommendations(
        self,
        outcome: NegotiationOutcome,
        positive_factors: List[str],
        negative_factors: List[str],
    ) -> List[str]:
        """Generate recommendations based on outcome factors."""
        recommendations: List[str] = []

        if outcome == NegotiationOutcome.AGREEMENT_REACHED:
            recommendations.append("Document agreement terms clearly")
            recommendations.append("Establish implementation timeline")
        elif outcome == NegotiationOutcome.REJECTED:
            if negative_factors:
                recommendations.append(
                    "Address identified negative factors before retry"
                )
            recommendations.append("Consider mediation for future negotiations")
        elif outcome == NegotiationOutcome.PENDING:
            if len(negative_factors) > len(positive_factors):
                recommendations.append("Focus on building consensus")
            recommendations.append("Schedule follow-up discussions")

        return recommendations
