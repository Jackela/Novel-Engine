#!/usr/bin/env python3
"""
Negotiation Application Service

Application-level service for negotiation operations using Result pattern.
Wraps domain NegotiationService with application-level orchestration.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from .....core.result import Err, Ok, Result
from ....interactions.domain.services.negotiation_service import NegotiationService
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.negotiation_status import NegotiationPhase
from ....interactions.domain.value_objects.proposal_response import ProposalResponse
from .shared.errors import (
    CompatibilityError,
    ConflictError,
    NegotiationError,
    ValidationError,
)


class NegotiationApplicationService:
    """
    Application service for negotiation operations with Result pattern.

    Provides business operations for negotiation analysis, compatibility
    assessment, conflict detection, and momentum calculation.
    """

    def __init__(
        self, negotiation_service: Optional[NegotiationService] = None
    ) -> None:
        """Initialize with domain negotiation service."""
        self.negotiation_service = negotiation_service or NegotiationService()

    def assess_party_compatibility(
        self,
        party1: NegotiationParty,
        party2: NegotiationParty,
        negotiation_domain: Optional[str] = None,
    ) -> Result[Decimal, CompatibilityError]:
        """
        Assess compatibility between two parties.

        Args:
            party1: First negotiation party
            party2: Second negotiation party
            negotiation_domain: Optional domain context

        Returns:
            Result containing compatibility score (0-100) or error
        """
        # Validation
        if party1 is None or party2 is None:
            return Err(
                CompatibilityError(
                    message="Both parties must be provided for compatibility assessment",
                    recoverable=True,
                )
            )

        if party1.party_id == party2.party_id:
            return Err(
                CompatibilityError(
                    message="Cannot assess compatibility of a party with itself",
                    party_ids=[str(party1.party_id)],
                    recoverable=True,
                )
            )

        try:
            score = self.negotiation_service.assess_party_compatibility(
                party1, party2, negotiation_domain
            )
            return Ok(score)
        except Exception as e:
            return Err(
                CompatibilityError(
                    message=f"Failed to assess compatibility: {e!s}",
                    party_ids=[str(party1.party_id), str(party2.party_id)],
                    recoverable=True,
                )
            )

    def analyze_party_compatibility_matrix(
        self,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], CompatibilityError]:
        """
        Analyze compatibility matrix for all party pairs.

        Args:
            parties: List of negotiation parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing compatibility matrix or error
        """
        if not parties:
            return Err(
                CompatibilityError(
                    message="At least two parties required for compatibility matrix",
                    recoverable=True,
                )
            )

        if len(parties) < 2:
            return Err(
                CompatibilityError(
                    message="At least two parties required for compatibility matrix",
                    party_ids=[str(p.party_id) for p in parties],
                    recoverable=True,
                )
            )

        try:
            compatibility_matrix: Dict[str, Any] = {}

            for i, party1 in enumerate(parties):
                for party2 in parties[i + 1 :]:
                    score = self.negotiation_service.assess_party_compatibility(
                        party1, party2, negotiation_domain
                    )

                    pair_key = f"{party1.party_id}_{party2.party_id}"
                    compatibility_matrix[pair_key] = {
                        "party1_id": str(party1.party_id),
                        "party1_name": party1.party_name,
                        "party2_id": str(party2.party_id),
                        "party2_name": party2.party_name,
                        "compatibility_score": float(score),
                        "compatibility_level": self._score_to_level(score),
                    }

            # Calculate overall compatibility
            if compatibility_matrix:
                scores = [
                    comp["compatibility_score"]
                    for comp in compatibility_matrix.values()
                ]
                overall_compatibility = sum(scores) / len(scores)
            else:
                overall_compatibility = 100.0

            result = {
                "compatibility_matrix": compatibility_matrix,
                "overall_compatibility": overall_compatibility,
                "compatibility_level": self._score_to_level(
                    Decimal(overall_compatibility)
                ),
                "party_count": len(parties),
                "pair_count": len(compatibility_matrix),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                CompatibilityError(
                    message=f"Failed to analyze compatibility matrix: {e!s}",
                    party_ids=[str(p.party_id) for p in parties],
                    recoverable=True,
                )
            )

    def detect_negotiation_conflicts(
        self,
        parties: List[NegotiationParty],
        responses: Optional[List[ProposalResponse]] = None,
        severity_threshold: str = "low",
    ) -> Result[Dict[str, Any], ConflictError]:
        """
        Detect conflicts in negotiation.

        Args:
            parties: List of negotiation parties
            responses: Optional list of proposal responses
            severity_threshold: Minimum severity to report (low, medium, high, critical)

        Returns:
            Result containing detected conflicts or error
        """
        if not parties:
            return Err(
                ConflictError(
                    message="At least one party required for conflict detection",
                    recoverable=True,
                )
            )

        valid_thresholds = ["low", "medium", "high", "critical"]
        if severity_threshold not in valid_thresholds:
            return Err(
                ValidationError(
                    message=f"Invalid severity threshold: {severity_threshold}",
                    field="severity_threshold",
                    field_value=severity_threshold,
                    recoverable=True,
                )
            )

        try:
            all_responses = responses or []
            conflicts = self.negotiation_service.detect_negotiation_conflicts(
                parties, all_responses
            )

            # Filter by severity threshold
            severity_order = ["low", "medium", "high", "critical"]
            threshold_index = severity_order.index(severity_threshold)

            filtered_conflicts = [
                conflict
                for conflict in conflicts
                if severity_order.index(conflict.get("severity", "low"))
                >= threshold_index
            ]

            # Convert UUID objects to strings for JSON serialization
            for conflict in filtered_conflicts:
                if "parties" in conflict:
                    conflict["parties"] = [
                        str(party_id) for party_id in conflict["parties"]
                    ]

            result = {
                "conflicts_detected": filtered_conflicts,
                "total_conflicts": len(filtered_conflicts),
                "severity_threshold": severity_threshold,
                "critical_count": sum(
                    1 for c in filtered_conflicts if c.get("severity") == "critical"
                ),
                "high_count": sum(
                    1 for c in filtered_conflicts if c.get("severity") == "high"
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                ConflictError(
                    message=f"Failed to detect conflicts: {e!s}",
                    recoverable=True,
                )
            )

    def calculate_negotiation_momentum(
        self,
        responses: List[ProposalResponse],
        current_phase: NegotiationPhase,
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Calculate negotiation momentum and trajectory.

        Args:
            responses: List of recent proposal responses
            current_phase: Current negotiation phase

        Returns:
            Result containing momentum analysis or error
        """
        try:
            momentum = self.negotiation_service.calculate_negotiation_momentum(
                responses=responses,
                phase=current_phase,
            )

            # Convert Decimal values to float for JSON serialization
            momentum["momentum_score"] = float(momentum["momentum_score"])

            return Ok(momentum)
        except Exception as e:
            return Err(
                NegotiationError(
                    message=f"Failed to calculate momentum: {e!s}",
                    recoverable=True,
                )
            )

    def recommend_negotiation_strategy(
        self,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
        target_outcome: Optional[str] = None,
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Recommend negotiation strategy.

        Args:
            parties: List of negotiation parties
            negotiation_domain: Optional domain context
            target_outcome: Optional desired outcome

        Returns:
            Result containing strategy recommendation or error
        """
        if not parties:
            return Err(
                NegotiationError(
                    message="At least one party required for strategy recommendation",
                    recoverable=True,
                )
            )

        try:
            strategy = self.negotiation_service.recommend_negotiation_strategy(
                parties=parties,
                negotiation_domain=negotiation_domain,
                target_outcome=target_outcome,
            )
            return Ok(strategy)
        except Exception as e:
            return Err(
                NegotiationError(
                    message=f"Failed to generate strategy: {e!s}",
                    recoverable=True,
                )
            )

    def _score_to_level(self, score: Decimal) -> str:
        """Convert numeric score to compatibility level."""
        score_float = float(score)
        if score_float >= 80:
            return "excellent"
        elif score_float >= 65:
            return "good"
        elif score_float >= 50:
            return "moderate"
        elif score_float >= 35:
            return "poor"
        else:
            return "critical"
