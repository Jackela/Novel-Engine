#!/usr/bin/env python3
"""
Proposal Application Service

Application service for proposal operations using Result pattern.
Handles proposal lifecycle, analysis, and optimization.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from .....core.result import Err, Ok, Result
from ....interactions.domain.services.negotiation_service import NegotiationService
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.proposal_terms import ProposalTerms, TermCondition
from .shared.errors import (
    NotFoundError,
    ProposalError,
    ValidationError,
)


class ProposalService:
    """
    Application service for proposal operations.
    
    Provides business operations for proposal analysis, viability assessment,
    optimization, and lifecycle management with Result pattern.
    """

    def __init__(self, negotiation_service: Optional[NegotiationService] = None) -> None:
        """Initialize with domain negotiation service."""
        self.negotiation_service = negotiation_service or NegotiationService()

    def analyze_proposal_viability(
        self,
        proposal: ProposalTerms,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Analyze proposal viability for given parties.

        Args:
            proposal: Proposal terms to analyze
            parties: List of negotiating parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing viability analysis or error
        """
        if proposal is None:
            return Err(ProposalError(
                message="Proposal is required for viability analysis",
                recoverable=True,
            ))

        if not parties:
            return Err(ProposalError(
                message="At least one party required for viability analysis",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))

        try:
            analysis = self.negotiation_service.analyze_proposal_viability(
                proposal=proposal,
                parties=parties,
                negotiation_domain=negotiation_domain,
            )

            # Convert Decimal values to float for JSON serialization
            analysis["overall_viability_score"] = float(analysis["overall_viability_score"])
            analysis["acceptance_probability"] = float(analysis["acceptance_probability"])

            # Convert party-specific analysis
            for party_id, party_analysis in analysis["party_specific_analysis"].items():
                party_analysis["acceptance_score"] = float(
                    party_analysis["acceptance_score"]
                )

            return Ok(analysis)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to analyze proposal viability: {e!s}",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))

    def optimize_proposal_terms(
        self,
        proposal: ProposalTerms,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
        max_modifications: int = 5,
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Optimize proposal terms for better acceptance.

        Args:
            proposal: Original proposal terms
            parties: List of negotiating parties
            negotiation_domain: Optional domain context
            max_modifications: Maximum number of terms to modify

        Returns:
            Result containing optimization results or error
        """
        if proposal is None:
            return Err(ProposalError(
                message="Proposal is required for optimization",
                recoverable=True,
            ))

        if not parties:
            return Err(ProposalError(
                message="At least one party required for optimization",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))

        if max_modifications < 1:
            return Err(ValidationError(
                message="max_modifications must be at least 1",
                field="max_modifications",
                field_value=max_modifications,
                recoverable=True,
            ))

        try:
            optimization = self.negotiation_service.optimize_proposal_terms(
                proposal=proposal,
                parties=parties,
                negotiation_domain=negotiation_domain,
            )

            # Convert Decimal values
            optimization["expected_improvement"] = float(optimization["expected_improvement"])

            # Limit modifications if needed
            optimized_terms = optimization.get("optimized_terms", [])
            if len(optimized_terms) > max_modifications:
                optimization["optimized_terms"] = optimized_terms[:max_modifications]
                optimization["modifications_limited"] = True

            return Ok(optimization)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to optimize proposal: {e!s}",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))

    def compare_proposals(
        self,
        proposals: List[ProposalTerms],
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Compare multiple proposals for viability.

        Args:
            proposals: List of proposals to compare
            parties: List of negotiating parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing comparison results or error
        """
        if not proposals:
            return Err(ProposalError(
                message="At least one proposal required for comparison",
                recoverable=True,
            ))

        if not parties:
            return Err(ProposalError(
                message="At least one party required for comparison",
                recoverable=True,
            ))

        try:
            comparison_results: List[Dict[str, Any]] = []
            
            for proposal in proposals:
                analysis = self.negotiation_service.analyze_proposal_viability(
                    proposal=proposal,
                    parties=parties,
                    negotiation_domain=negotiation_domain,
                )
                
                comparison_results.append({
                    "proposal_id": str(proposal.proposal_id),
                    "proposal_title": proposal.title,
                    "viability_score": float(analysis["overall_viability_score"]),
                    "acceptance_probability": float(analysis["acceptance_probability"]),
                    "risk_factors": analysis["risk_factors"],
                    "critical_issues": analysis["critical_issues"],
                })

            # Sort by viability score
            comparison_results.sort(
                key=lambda x: x["viability_score"],
                reverse=True
            )

            result = {
                "proposals_compared": len(proposals),
                "party_count": len(parties),
                "rankings": comparison_results,
                "best_proposal_id": comparison_results[0]["proposal_id"] if comparison_results else None,
                "average_viability": sum(r["viability_score"] for r in comparison_results) / len(comparison_results) if comparison_results else 0.0,
            }
            
            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to compare proposals: {e!s}",
                recoverable=True,
            ))

    def validate_proposal_terms(
        self,
        proposal: ProposalTerms,
        min_terms: int = 1,
        max_terms: int = 50,
    ) -> Result[Dict[str, Any], ValidationError]:
        """
        Validate proposal terms structure.

        Args:
            proposal: Proposal to validate
            min_terms: Minimum number of terms required
            max_terms: Maximum number of terms allowed

        Returns:
            Result containing validation results or error
        """
        if proposal is None:
            return Err(ValidationError(
                message="Proposal is required for validation",
                field="proposal",
                recoverable=True,
            ))

        validation_errors: List[str] = []
        warnings: List[str] = []

        # Check term count
        term_count = len(proposal.terms)
        if term_count < min_terms:
            validation_errors.append(
                f"Proposal must have at least {min_terms} term(s), found {term_count}"
            )
        elif term_count > max_terms:
            validation_errors.append(
                f"Proposal exceeds maximum of {max_terms} terms, found {term_count}"
            )

        # Check for duplicate term IDs
        term_ids = [term.term_id for term in proposal.terms]
        if len(term_ids) != len(set(term_ids)):
            validation_errors.append("Duplicate term IDs found in proposal")

        # Check critical terms ratio
        critical_terms = proposal.get_critical_terms()
        if critical_terms and term_count > 0:
            critical_ratio = len(critical_terms) / term_count
            if critical_ratio > 0.8:
                warnings.append(
                    f"High ratio of critical terms ({critical_ratio:.0%}) may reduce flexibility"
                )

        # Check non-negotiable terms
        non_negotiable = proposal.get_non_negotiable_terms()
        if non_negotiable and term_count > 0:
            non_neg_ratio = len(non_negotiable) / term_count
            if non_neg_ratio > 0.7:
                warnings.append(
                    f"High proportion of non-negotiable terms ({non_neg_ratio:.0%})"
                )

        # Check expiration
        if proposal.is_expired:
            validation_errors.append("Proposal has expired")

        result = {
            "proposal_id": str(proposal.proposal_id),
            "is_valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": warnings,
            "term_count": term_count,
            "critical_terms_count": len(critical_terms),
            "non_negotiable_count": len(non_negotiable),
        }

        if validation_errors:
            return Err(ValidationError(
                message=f"Proposal validation failed: {'; '.join(validation_errors)}",
                field="proposal",
                recoverable=True,
                details={"validation_result": result},
            ))

        return Ok(result)

    def estimate_proposal_acceptance(
        self,
        proposal: ProposalTerms,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], ProposalError]:
        """
        Estimate acceptance likelihood for a proposal.

        Args:
            proposal: Proposal to estimate
            parties: List of negotiating parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing acceptance estimate or error
        """
        if proposal is None:
            return Err(ProposalError(
                message="Proposal is required for acceptance estimation",
                recoverable=True,
            ))

        if not parties:
            return Err(ProposalError(
                message="At least one party required for estimation",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))

        try:
            analysis = self.negotiation_service.analyze_proposal_viability(
                proposal=proposal,
                parties=parties,
                negotiation_domain=negotiation_domain,
            )

            acceptance_prob = float(analysis["acceptance_probability"])
            viability_score = float(analysis["overall_viability_score"])

            # Determine recommendation
            if acceptance_prob >= 80:
                recommendation = "proceed"
                confidence = "high"
            elif acceptance_prob >= 60:
                recommendation = "proceed_with_caution"
                confidence = "medium"
            elif acceptance_prob >= 40:
                recommendation = "review_and_refine"
                confidence = "medium"
            else:
                recommendation = "major_revision_needed"
                confidence = "high"

            result = {
                "proposal_id": str(proposal.proposal_id),
                "acceptance_probability": acceptance_prob,
                "viability_score": viability_score,
                "recommendation": recommendation,
                "confidence": confidence,
                "risk_factors": analysis["risk_factors"],
                "success_factors": analysis["success_factors"],
            }

            return Ok(result)
        except Exception as e:
            return Err(ProposalError(
                message=f"Failed to estimate acceptance: {e!s}",
                proposal_id=str(proposal.proposal_id),
                recoverable=True,
            ))
