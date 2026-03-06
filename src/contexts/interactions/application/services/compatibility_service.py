#!/usr/bin/env python3
"""
Compatibility Application Service

Application service for party compatibility operations using Result pattern.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from .....core.result import Err, Ok, Result
from ....interactions.domain.services.negotiation_service import NegotiationService
from ....interactions.domain.value_objects.negotiation_party import (
    AuthorityLevel,
    CommunicationPreference,
    NegotiationParty,
    NegotiationStyle,
)
from .shared.errors import (
    CompatibilityError,
    NotFoundError,
    ValidationError,
)


class CompatibilityService:
    """
    Service for party compatibility analysis.
    
    Provides business operations for assessing compatibility between
    negotiation parties across multiple dimensions.
    """

    def __init__(self, negotiation_service: Optional[NegotiationService] = None) -> None:
        """Initialize with domain negotiation service."""
        self.negotiation_service = negotiation_service or NegotiationService()

    def assess_party_pair_compatibility(
        self,
        party1: NegotiationParty,
        party2: NegotiationParty,
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], CompatibilityError]:
        """
        Assess compatibility between two parties with detailed breakdown.

        Args:
            party1: First negotiation party
            party2: Second negotiation party
            negotiation_domain: Optional domain context

        Returns:
            Result containing detailed compatibility assessment or error
        """
        if party1 is None or party2 is None:
            return Err(CompatibilityError(
                message="Both parties must be provided",
                recoverable=True,
            ))

        if party1.party_id == party2.party_id:
            return Err(CompatibilityError(
                message="Cannot assess compatibility of a party with itself",
                party_ids=[str(party1.party_id)],
                recoverable=True,
            ))

        try:
            # Get overall score from domain service
            overall_score = self.negotiation_service.assess_party_compatibility(
                party1, party2, negotiation_domain
            )

            # Calculate dimension-specific scores
            authority_score = self._assess_authority_compatibility(party1, party2)
            communication_score = self._assess_communication_compatibility(party1, party2)
            style_score = self._assess_negotiation_style_compatibility(party1, party2)
            time_score = self._assess_time_compatibility(party1, party2)

            # Domain expertise if applicable
            domain_score = None
            if negotiation_domain:
                domain_score = self._assess_domain_compatibility(
                    party1, party2, negotiation_domain
                )

            # Identify strengths and concerns
            strengths: List[str] = []
            concerns: List[str] = []

            if authority_score >= 70:
                strengths.append("Compatible authority levels")
            elif authority_score < 40:
                concerns.append("Authority level mismatch")

            if communication_score >= 70:
                strengths.append("Compatible communication styles")
            elif communication_score < 40:
                concerns.append("Communication style differences")

            if style_score >= 70:
                strengths.append("Compatible negotiation approaches")
            elif style_score < 40:
                concerns.append("Divergent negotiation styles")

            result = {
                "party1_id": str(party1.party_id),
                "party1_name": party1.party_name,
                "party2_id": str(party2.party_id),
                "party2_name": party2.party_name,
                "overall_score": float(overall_score),
                "compatibility_level": self._score_to_level(overall_score),
                "dimension_scores": {
                    "authority": float(authority_score),
                    "communication": float(communication_score),
                    "negotiation_style": float(style_score),
                    "time_preferences": float(time_score),
                },
                "domain_score": float(domain_score) if domain_score else None,
                "strengths": strengths,
                "concerns": concerns,
                "recommendations": self._generate_compatibility_recommendations(
                    overall_score, concerns
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(CompatibilityError(
                message=f"Failed to assess compatibility: {e!s}",
                party_ids=[str(party1.party_id), str(party2.party_id)],
                recoverable=True,
            ))

    def assess_group_compatibility(
        self,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], CompatibilityError]:
        """
        Assess compatibility for a group of parties.

        Args:
            parties: List of negotiation parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing group compatibility assessment or error
        """
        if not parties:
            return Err(CompatibilityError(
                message="At least one party required",
                recoverable=True,
            ))

        if len(parties) < 2:
            return Err(CompatibilityError(
                message="At least two parties required for group compatibility",
                party_ids=[str(p.party_id) for p in parties],
                recoverable=True,
            ))

        try:
            # Calculate all pairwise scores
            pairwise_scores: List[float] = []
            compatibility_pairs: List[Dict[str, Any]] = []

            for i, party1 in enumerate(parties):
                for party2 in parties[i + 1 :]:
                    score = self.negotiation_service.assess_party_compatibility(
                        party1, party2, negotiation_domain
                    )
                    pairwise_scores.append(float(score))
                    
                    compatibility_pairs.append({
                        "party1_id": str(party1.party_id),
                        "party1_name": party1.party_name,
                        "party2_id": str(party2.party_id),
                        "party2_name": party2.party_name,
                        "score": float(score),
                    })

            # Calculate statistics
            avg_score = sum(pairwise_scores) / len(pairwise_scores) if pairwise_scores else 100.0
            min_score = min(pairwise_scores) if pairwise_scores else 100.0
            max_score = max(pairwise_scores) if pairwise_scores else 100.0

            # Find problematic pairs
            problematic_pairs = [
                p for p in compatibility_pairs if p["score"] < 40
            ]

            # Calculate cohesion score
            cohesion = self._calculate_group_cohesion(pairwise_scores)

            result = {
                "party_count": len(parties),
                "pair_count": len(compatibility_pairs),
                "average_compatibility": avg_score,
                "minimum_compatibility": min_score,
                "maximum_compatibility": max_score,
                "compatibility_level": self._score_to_level(Decimal(avg_score)),
                "group_cohesion": cohesion,
                "cohesion_level": self._score_to_level(Decimal(cohesion)),
                "pairwise_results": compatibility_pairs,
                "problematic_pairs": problematic_pairs,
                "problematic_pair_count": len(problematic_pairs),
                "recommendations": self._generate_group_recommendations(
                    avg_score, problematic_pairs, cohesion
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(CompatibilityError(
                message=f"Failed to assess group compatibility: {e!s}",
                party_ids=[str(p.party_id) for p in parties],
                recoverable=True,
            ))

    def find_compatible_parties(
        self,
        reference_party: NegotiationParty,
        candidate_parties: List[NegotiationParty],
        min_compatibility: float = 50.0,
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], CompatibilityError]:
        """
        Find parties compatible with a reference party.

        Args:
            reference_party: Party to match against
            candidate_parties: List of candidate parties
            min_compatibility: Minimum compatibility threshold
            negotiation_domain: Optional domain context

        Returns:
            Result containing compatible parties or error
        """
        if reference_party is None:
            return Err(CompatibilityError(
                message="Reference party is required",
                recoverable=True,
            ))

        if not candidate_parties:
            return Err(CompatibilityError(
                message="At least one candidate party required",
                recoverable=True,
            ))

        if min_compatibility < 0 or min_compatibility > 100:
            return Err(ValidationError(
                message="Compatibility threshold must be between 0 and 100",
                field="min_compatibility",
                field_value=min_compatibility,
                recoverable=True,
            ))

        try:
            compatible_parties: List[Dict[str, Any]] = []
            incompatible_parties: List[Dict[str, Any]] = []

            for candidate in candidate_parties:
                if candidate.party_id == reference_party.party_id:
                    continue

                score = self.negotiation_service.assess_party_compatibility(
                    reference_party, candidate, negotiation_domain
                )
                score_float = float(score)

                party_info = {
                    "party_id": str(candidate.party_id),
                    "party_name": candidate.party_name,
                    "compatibility_score": score_float,
                    "compatibility_level": self._score_to_level(score),
                }

                if score_float >= min_compatibility:
                    compatible_parties.append(party_info)
                else:
                    incompatible_parties.append(party_info)

            # Sort by compatibility score
            compatible_parties.sort(key=lambda x: x["compatibility_score"], reverse=True)

            result = {
                "reference_party_id": str(reference_party.party_id),
                "reference_party_name": reference_party.party_name,
                "min_compatibility_threshold": min_compatibility,
                "candidates_evaluated": len(candidate_parties),
                "compatible_count": len(compatible_parties),
                "incompatible_count": len(incompatible_parties),
                "compatible_parties": compatible_parties,
                "incompatible_parties": incompatible_parties[:5],  # Top 5 incompatible
                "average_compatible_score": (
                    sum(p["compatibility_score"] for p in compatible_parties) / len(compatible_parties)
                    if compatible_parties else 0.0
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(CompatibilityError(
                message=f"Failed to find compatible parties: {e!s}",
                party_ids=[str(reference_party.party_id)],
                recoverable=True,
            ))

    def _assess_authority_compatibility(
        self, party1: NegotiationParty, party2: NegotiationParty
    ) -> Decimal:
        """Assess authority level compatibility."""
        if party1.can_make_binding_decisions() and party2.can_make_binding_decisions():
            return Decimal("80")
        elif party1.can_make_binding_decisions() or party2.can_make_binding_decisions():
            return Decimal("60")
        else:
            return Decimal("20")

    def _assess_communication_compatibility(
        self, party1: NegotiationParty, party2: NegotiationParty
    ) -> Decimal:
        """Assess communication style compatibility."""
        style1 = party1.preferences.communication_preference
        style2 = party2.preferences.communication_preference

        compatibility_map = {
            (CommunicationPreference.DIRECT, CommunicationPreference.DIRECT): Decimal("90"),
            (CommunicationPreference.DIRECT, CommunicationPreference.DIPLOMATIC): Decimal("60"),
            (CommunicationPreference.DIPLOMATIC, CommunicationPreference.DIPLOMATIC): Decimal("85"),
            (CommunicationPreference.FORMAL, CommunicationPreference.FORMAL): Decimal("80"),
            (CommunicationPreference.INFORMAL, CommunicationPreference.INFORMAL): Decimal("75"),
            (CommunicationPreference.ANALYTICAL, CommunicationPreference.ANALYTICAL): Decimal("90"),
        }

        key = (style1, style2)
        if key in compatibility_map:
            return compatibility_map[key]

        reverse_key = (style2, style1)
        if reverse_key in compatibility_map:
            return compatibility_map[reverse_key]

        return Decimal("50")

    def _assess_negotiation_style_compatibility(
        self, party1: NegotiationParty, party2: NegotiationParty
    ) -> Decimal:
        """Assess negotiation style compatibility."""
        style1 = party1.preferences.negotiation_style
        style2 = party2.preferences.negotiation_style

        # High compatibility pairs
        if style1 == NegotiationStyle.COLLABORATIVE and style2 == NegotiationStyle.COLLABORATIVE:
            return Decimal("95")

        if style1 == NegotiationStyle.INTEGRATIVE and style2 == NegotiationStyle.INTEGRATIVE:
            return Decimal("90")

        # Moderate compatibility
        if style1 == NegotiationStyle.COMPROMISING or style2 == NegotiationStyle.COMPROMISING:
            return Decimal("70")

        # Problematic combinations
        if ((style1 == NegotiationStyle.COMPETITIVE and style2 == NegotiationStyle.AVOIDING) or
            (style1 == NegotiationStyle.AVOIDING and style2 == NegotiationStyle.COMPETITIVE)):
            return Decimal("20")

        return Decimal("50")

    def _assess_time_compatibility(
        self, party1: NegotiationParty, party2: NegotiationParty
    ) -> Decimal:
        """Assess time preference compatibility."""
        pref1 = party1.preferences
        pref2 = party2.preferences

        # Check session duration compatibility
        if pref1.maximum_session_duration and pref2.maximum_session_duration:
            min_duration = min(pref1.maximum_session_duration, pref2.maximum_session_duration)
            if min_duration < 30:
                return Decimal("30")

        # Check time pressure sensitivity
        sensitivity_diff = abs(pref1.time_pressure_sensitivity - pref2.time_pressure_sensitivity)
        if sensitivity_diff > 50:
            return Decimal("40")

        return Decimal("70")

    def _assess_domain_compatibility(
        self, party1: NegotiationParty, party2: NegotiationParty, domain: str
    ) -> Decimal:
        """Assess domain expertise compatibility."""
        capabilities1 = party1.get_capabilities_for_domain(domain)
        capabilities2 = party2.get_capabilities_for_domain(domain)

        if not capabilities1 and not capabilities2:
            return Decimal("30")

        if not capabilities1 or not capabilities2:
            return Decimal("60")

        power1 = party1.get_negotiation_power(domain)
        power2 = party2.get_negotiation_power(domain)

        power_ratio = (
            min(power1, power2) / max(power1, power2)
            if max(power1, power2) > 0
            else Decimal("0")
        )

        return Decimal("50") + (power_ratio * Decimal("40"))

    def _calculate_group_cohesion(self, pairwise_scores: List[float]) -> float:
        """Calculate group cohesion from pairwise scores."""
        if not pairwise_scores:
            return 100.0

        # Cohesion considers both average and variance
        avg = sum(pairwise_scores) / len(pairwise_scores)
        variance = sum((s - avg) ** 2 for s in pairwise_scores) / len(pairwise_scores)
        std_dev = variance ** 0.5

        # High cohesion = high average with low variance
        cohesion = avg - (std_dev / 2)
        return max(0.0, min(100.0, cohesion))

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

    def _generate_compatibility_recommendations(
        self, score: Decimal, concerns: List[str]
    ) -> List[str]:
        """Generate recommendations based on compatibility."""
        recommendations: List[str] = []
        
        score_float = float(score)
        if score_float < 40:
            recommendations.append("Consider mediation for this negotiation pair")
        elif score_float < 60:
            recommendations.append("Establish clear communication protocols")

        if "Authority level mismatch" in concerns:
            recommendations.append("Clarify decision-making authority early")
        if "Communication style differences" in concerns:
            recommendations.append("Adapt communication style to match partner")
        if "Divergent negotiation styles" in concerns:
            recommendations.append("Focus on objective criteria and mutual gains")

        return recommendations

    def _generate_group_recommendations(
        self,
        avg_score: float,
        problematic_pairs: List[Dict[str, Any]],
        cohesion: float,
    ) -> List[str]:
        """Generate recommendations for group compatibility."""
        recommendations: List[str] = []
        
        if avg_score < 50:
            recommendations.append("Consider splitting into smaller negotiation groups")
        elif avg_score < 70:
            recommendations.append("Focus on team-building before negotiations")

        if problematic_pairs:
            recommendations.append(
                f"Address {len(problematic_pairs)} low-compatibility pair(s)"
            )

        if cohesion < 50:
            recommendations.append("Work on improving group cohesion")

        return recommendations
