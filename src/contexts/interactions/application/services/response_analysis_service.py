#!/usr/bin/env python3
"""
Response Analysis Application Service

Application service for analyzing proposal responses using Result pattern.
"""

from typing import Any, Dict, List
from uuid import UUID

from .....core.result import Err, Ok, Result
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.proposal_response import (
    ProposalResponse,
)
from .shared.errors import (
    NotFoundError,
    ProposalError,
)


class ResponseAnalysisService:
    """
    Service for analyzing proposal responses.
    
    Provides business operations for response pattern analysis,
    acceptance metrics, and trend detection.
    """

    def __init__(self) -> None:
        """Initialize response analysis service."""
        pass

    def analyze_response_patterns(
        self,
        responses: List[ProposalResponse],
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Analyze patterns in proposal responses.

        Args:
            responses: List of proposal responses

        Returns:
            Result containing pattern analysis or error
        """
        if not responses:
            return Err(ProposalError(
                message="At least one response required for pattern analysis",
                recoverable=True,
            ))

        try:
            # Count response types
            response_counts: Dict[str, int] = {}
            for response in responses:
                response_type = response.overall_response.value
                response_counts[response_type] = response_counts.get(response_type, 0) + 1

            # Calculate acceptance metrics
            acceptances = sum(1 for r in responses if r.is_complete_acceptance())
            rejections = sum(
                1 for r in responses 
                if r.overall_response.value == "rejected"
            )
            conditional = len(responses) - acceptances - rejections

            acceptance_rate = acceptances / len(responses) if responses else 0.0

            # Calculate average acceptance percentage
            avg_acceptance = sum(
                r.get_acceptance_percentage() for r in responses
            ) / len(responses) if responses else 0.0

            # Analyze timing patterns
            timestamps = [r.response_timestamp for r in responses]
            time_range = (max(timestamps) - min(timestamps)).total_seconds() if len(timestamps) > 1 else 0
            
            # Detect response clusters
            sorted_responses = sorted(responses, key=lambda r: r.response_timestamp)
            clusters = self._detect_response_clusters(sorted_responses)

            result = {
                "total_responses": len(responses),
                "response_breakdown": response_counts,
                "acceptance_count": acceptances,
                "rejection_count": rejections,
                "conditional_count": conditional,
                "acceptance_rate": acceptance_rate,
                "average_acceptance_percentage": avg_acceptance,
                "time_range_seconds": time_range,
                "response_clusters": clusters,
                "cluster_count": len(clusters),
            }

            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to analyze response patterns: {e!s}",
                recoverable=True,
            ))

    def analyze_party_response_history(
        self,
        party_id: UUID,
        responses: List[ProposalResponse],
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Analyze response history for a specific party.

        Args:
            party_id: Party identifier
            responses: List of all responses

        Returns:
            Result containing party response analysis or error
        """
        if not responses:
            return Err(ProposalError(
                message="At least one response required",
                recoverable=True,
            ))

        try:
            # Filter responses for this party
            party_responses = [
                r for r in responses 
                if r.responding_party_id == party_id
            ]

            if not party_responses:
                return Err(NotFoundError(
                    message=f"No responses found for party {party_id}",
                    entity_type="PartyResponses",
                    entity_id=str(party_id),
                    recoverable=False,
                ))

            # Sort by time
            party_responses.sort(key=lambda r: r.response_timestamp)

            # Calculate metrics
            acceptances = sum(1 for r in party_responses if r.is_complete_acceptance())
            acceptance_rate = acceptances / len(party_responses)

            avg_acceptance = sum(
                r.get_acceptance_percentage() for r in party_responses
            ) / len(party_responses)

            # Analyze trends
            trend = self._calculate_response_trend(party_responses)

            # Time pattern
            time_span = (
                party_responses[-1].response_timestamp - party_responses[0].response_timestamp
            ).total_seconds() if len(party_responses) > 1 else 0

            result = {
                "party_id": str(party_id),
                "total_responses": len(party_responses),
                "acceptance_rate": acceptance_rate,
                "average_acceptance_percentage": avg_acceptance,
                "trend": trend,
                "time_span_seconds": time_span,
                "first_response_at": party_responses[0].response_timestamp.isoformat(),
                "last_response_at": party_responses[-1].response_timestamp.isoformat(),
                "responsiveness_score": self._calculate_responsiveness(party_responses),
            }

            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to analyze party response history: {e!s}",
                recoverable=True,
            ))

    def calculate_collective_response_metrics(
        self,
        responses: List[ProposalResponse],
        parties: List[NegotiationParty],
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Calculate collective response metrics across parties.

        Args:
            responses: List of responses
            parties: List of parties

        Returns:
            Result containing collective metrics or error
        """
        if not responses:
            return Err(ProposalError(
                message="At least one response required",
                recoverable=True,
            ))

        if not parties:
            return Err(ProposalError(
                message="At least one party required",
                recoverable=True,
            ))

        try:
            decision_makers = [p for p in parties if p.is_decision_maker]
            total_decision_makers = len(decision_makers)

            # Group responses by proposal
            by_proposal: Dict[UUID, List[ProposalResponse]] = {}
            for response in responses:
                if response.proposal_id not in by_proposal:
                    by_proposal[response.proposal_id] = []
                by_proposal[response.proposal_id].append(response)

            # Calculate per-proposal metrics
            proposal_metrics: List[Dict[str, Any]] = []
            for proposal_id, proposal_responses in by_proposal.items():
                acceptances = sum(
                    1 for r in proposal_responses if r.is_complete_acceptance()
                )
                avg_acceptance = sum(
                    r.get_acceptance_percentage() for r in proposal_responses
                ) / len(proposal_responses)

                responding_parties = len(
                    set(r.responding_party_id for r in proposal_responses)
                )

                proposal_metrics.append({
                    "proposal_id": str(proposal_id),
                    "response_count": len(proposal_responses),
                    "responding_parties": responding_parties,
                    "acceptance_count": acceptances,
                    "average_acceptance": avg_acceptance,
                    "response_rate": responding_parties / total_decision_makers 
                        if total_decision_makers > 0 else 0,
                })

            # Overall consensus
            all_acceptances = sum(1 for r in responses if r.is_complete_acceptance())
            consensus_level = all_acceptances / len(responses) if responses else 0

            result = {
                "total_responses": len(responses),
                "unique_proposals": len(by_proposal),
                "decision_makers": total_decision_makers,
                "consensus_level": consensus_level,
                "proposal_metrics": proposal_metrics,
                "overall_acceptance_rate": sum(
                    1 for r in responses if r.is_complete_acceptance()
                ) / len(responses) if responses else 0,
            }

            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to calculate collective metrics: {e!s}",
                recoverable=True,
            ))

    def identify_response_outliers(
        self,
        responses: List[ProposalResponse],
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Identify outlier responses that deviate from the norm.

        Args:
            responses: List of responses to analyze

        Returns:
            Result containing outlier analysis or error
        """
        if len(responses) < 3:
            return Err(ProposalError(
                message="At least 3 responses required for outlier detection",
                recoverable=True,
            ))

        try:
            # Calculate statistics
            acceptance_percentages = [r.get_acceptance_percentage() for r in responses]
            mean = sum(acceptance_percentages) / len(acceptance_percentages)
            variance = sum((x - mean) ** 2 for x in acceptance_percentages) / len(acceptance_percentages)
            std_dev = variance ** 0.5

            # Identify outliers (beyond 2 standard deviations)
            outliers: List[Dict[str, Any]] = []
            for response in responses:
                pct = response.get_acceptance_percentage()
                z_score = (pct - mean) / std_dev if std_dev > 0 else 0
                
                if abs(z_score) > 2:
                    outliers.append({
                        "response_id": str(response.response_id),
                        "proposal_id": str(response.proposal_id),
                        "party_id": str(response.responding_party_id),
                        "acceptance_percentage": pct,
                        "z_score": z_score,
                        "deviation_direction": "high" if z_score > 0 else "low",
                    })

            result = {
                "total_responses": len(responses),
                "mean_acceptance": mean,
                "standard_deviation": std_dev,
                "outlier_count": len(outliers),
                "outliers": outliers,
                "outlier_rate": len(outliers) / len(responses) if responses else 0,
            }

            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to identify outliers: {e!s}",
                recoverable=True,
            ))

    def _detect_response_clusters(
        self, sorted_responses: List[ProposalResponse]
    ) -> List[Dict[str, Any]]:
        """Detect clusters of responses in time."""
        if len(sorted_responses) < 2:
            return []

        clusters: List[Dict[str, Any]] = []
        current_cluster = [sorted_responses[0]]
        cluster_threshold = 3600  # 1 hour

        for i in range(1, len(sorted_responses)):
            time_diff = (
                sorted_responses[i].response_timestamp - sorted_responses[i-1].response_timestamp
            ).total_seconds()

            if time_diff <= cluster_threshold:
                current_cluster.append(sorted_responses[i])
            else:
                if len(current_cluster) > 1:
                    clusters.append({
                        "size": len(current_cluster),
                        "start_time": current_cluster[0].response_timestamp.isoformat(),
                        "end_time": current_cluster[-1].response_timestamp.isoformat(),
                    })
                current_cluster = [sorted_responses[i]]

        # Don't forget the last cluster
        if len(current_cluster) > 1:
            clusters.append({
                "size": len(current_cluster),
                "start_time": current_cluster[0].response_timestamp.isoformat(),
                "end_time": current_cluster[-1].response_timestamp.isoformat(),
            })

        return clusters

    def _calculate_response_trend(
        self, sorted_responses: List[ProposalResponse]
    ) -> str:
        """Calculate trend in response acceptance."""
        if len(sorted_responses) < 3:
            return "insufficient_data"

        # Split into halves
        mid = len(sorted_responses) // 2
        first_half = sorted_responses[:mid]
        second_half = sorted_responses[mid:]

        first_avg = sum(r.get_acceptance_percentage() for r in first_half) / len(first_half)
        second_avg = sum(r.get_acceptance_percentage() for r in second_half) / len(second_half)

        diff = second_avg - first_avg
        if diff > 15:
            return "improving"
        elif diff < -15:
            return "declining"
        else:
            return "stable"

    def _calculate_responsiveness(self, responses: List[ProposalResponse]) -> float:
        """Calculate responsiveness score based on timing."""
        if len(responses) < 2:
            return 100.0

        # Calculate average time between responses
        sorted_responses = sorted(responses, key=lambda r: r.response_timestamp)
        time_diffs = []
        for i in range(1, len(sorted_responses)):
            diff = (
                sorted_responses[i].response_timestamp - sorted_responses[i-1].response_timestamp
            ).total_seconds()
            time_diffs.append(diff)

        avg_diff = sum(time_diffs) / len(time_diffs)
        
        # Score based on responsiveness (lower is better)
        # Scale: <1 hour = excellent, 1-24 hours = good, >24 hours = poor
        if avg_diff < 3600:
            return 100.0
        elif avg_diff < 86400:
            return 70.0
        else:
            return 40.0
