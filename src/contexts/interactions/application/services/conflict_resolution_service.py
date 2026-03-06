#!/usr/bin/env python3
"""
Conflict Resolution Application Service

Application service for conflict detection and resolution using Result pattern.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ......core.result import Err, Ok, Result
from ....interactions.domain.services.negotiation_service import NegotiationService
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.proposal_response import ProposalResponse
from .shared.errors import (
    ConflictError,
    InteractionError,
    ValidationError,
)


class ConflictResolutionService:
    """
    Service for conflict detection and resolution.
    
    Provides business operations for identifying conflicts, suggesting
    resolutions, and mediating disputes.
    """

    def __init__(self, negotiation_service: Optional[NegotiationService] = None) -> None:
        """Initialize with domain negotiation service."""
        self.negotiation_service = negotiation_service or NegotiationService()

    def analyze_conflicts(
        self,
        parties: List[NegotiationParty],
        responses: Optional[List[ProposalResponse]] = None,
    ) -> Result[Dict[str, Any], ConflictError]:
        """
        Analyze conflicts between parties.

        Args:
            parties: List of negotiating parties
            responses: Optional proposal responses

        Returns:
            Result containing conflict analysis or error
        """
        if not parties:
            return Err(ConflictError(
                message="At least one party required for conflict analysis",
                recoverable=True,
            ))

        try:
            all_responses = responses or []
            conflicts = self.negotiation_service.detect_negotiation_conflicts(
                parties, all_responses
            )

            # Categorize conflicts
            by_type: Dict[str, List[Dict[str, Any]]] = {}
            by_severity: Dict[str, List[Dict[str, Any]]] = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
            }

            for conflict in conflicts:
                conflict_type = conflict.get("type", "unknown")
                severity = conflict.get("severity", "low")

                if conflict_type not in by_type:
                    by_type[conflict_type] = []
                by_type[conflict_type].append(conflict)

                if severity in by_severity:
                    by_severity[severity].append(conflict)

            result = {
                "total_conflicts": len(conflicts),
                "by_type": by_type,
                "by_severity": by_severity,
                "critical_count": len(by_severity["critical"]),
                "high_count": len(by_severity["high"]),
                "medium_count": len(by_severity["medium"]),
                "low_count": len(by_severity["low"]),
                "has_critical_conflicts": len(by_severity["critical"]) > 0,
                "conflict_intensity": self._calculate_intensity(by_severity),
            }

            return Ok(result)
        except Exception as e:
            return Err(ConflictError(
                message=f"Failed to analyze conflicts: {e!s}",
                recoverable=True,
            ))

    def suggest_conflict_resolutions(
        self,
        conflict: Dict[str, Any],
        parties: List[NegotiationParty],
    ) -> Result[Dict[str, Any], ConflictError]:
        """
        Suggest resolutions for a specific conflict.

        Args:
            conflict: Conflict to resolve
            parties: Involved parties

        Returns:
            Result containing resolution suggestions or error
        """
        if not conflict:
            return Err(ValidationError(
                message="Conflict is required",
                field="conflict",
                recoverable=True,
            ))

        try:
            conflict_type = conflict.get("type", "unknown")
            severity = conflict.get("severity", "low")

            # Generate suggestions based on conflict type
            suggestions: List[Dict[str, Any]] = []

            if conflict_type == "negotiation_style_conflict":
                suggestions.append({
                    "approach": "mediation",
                    "description": "Use neutral mediator to bridge style differences",
                    "effectiveness": "high",
                })
                suggestions.append({
                    "approach": "protocol",
                    "description": "Establish common ground rules",
                    "effectiveness": "medium",
                })
            elif conflict_type == "authority_conflict":
                suggestions.append({
                    "approach": "escalation",
                    "description": "Escalate to decision makers",
                    "effectiveness": "high",
                })
                suggestions.append({
                    "approach": "delegation",
                    "description": "Grant limited authority to representatives",
                    "effectiveness": "medium",
                })
            elif conflict_type == "response_conflict":
                suggestions.append({
                    "approach": "renegotiation",
                    "description": "Revisit conflicting terms",
                    "effectiveness": "high",
                })
            else:
                suggestions.append({
                    "approach": "dialogue",
                    "description": "Facilitate open discussion",
                    "effectiveness": "medium",
                })

            result = {
                "conflict_type": conflict_type,
                "severity": severity,
                "suggestions": suggestions,
                "best_approach": suggestions[0] if suggestions else None,
                "estimated_resolution_time": self._estimate_resolution_time(severity),
            }

            return Ok(result)
        except Exception as e:
            return Err(ConflictError(
                message=f"Failed to suggest resolutions: {e!s}",
                recoverable=True,
            ))

    def assess_mediation_needed(
        self,
        parties: List[NegotiationParty],
        conflicts: List[Dict[str, Any]],
    ) -> Result[Dict[str, Any], ConflictError]:
        """
        Assess whether mediation is needed.

        Args:
            parties: List of parties
            conflicts: List of detected conflicts

        Returns:
            Result containing mediation assessment or error
        """
        if not parties:
            return Err(ConflictError(
                message="At least one party required",
                recoverable=True,
            ))

        try:
            # Calculate mediation score
            mediation_score = 0
            reasons: List[str] = []

            # Factor 1: Conflict severity
            critical_count = sum(1 for c in conflicts if c.get("severity") == "critical")
            if critical_count > 0:
                mediation_score += 30 * critical_count
                reasons.append(f"{critical_count} critical conflict(s) detected")

            high_count = sum(1 for c in conflicts if c.get("severity") == "high")
            if high_count > 2:
                mediation_score += 15
                reasons.append("Multiple high-severity conflicts")

            # Factor 2: Party count
            if len(parties) > 4:
                mediation_score += 10
                reasons.append("Large number of parties")

            # Factor 3: Incompatible styles
            style_conflicts = [c for c in conflicts if "style" in c.get("type", "")]
            if len(style_conflicts) > 2:
                mediation_score += 20
                reasons.append("Multiple style conflicts")

            mediation_recommended = mediation_score >= 40

            result = {
                "mediation_score": min(100, mediation_score),
                "mediation_recommended": mediation_recommended,
                "urgency": "high" if mediation_score >= 60 else "medium" if mediation_score >= 40 else "low",
                "reasons": reasons,
                "benefits": self._get_mediation_benefits(mediation_score),
            }

            return Ok(result)
        except Exception as e:
            return Err(ConflictError(
                message=f"Failed to assess mediation needs: {e!s}",
                recoverable=True,
            ))

    def generate_de_escalation_plan(
        self,
        conflicts: List[Dict[str, Any]],
        parties: List[NegotiationParty],
    ) -> Result[Dict[str, Any], ConflictError]:
        """
        Generate a plan to de-escalate conflicts.

        Args:
            conflicts: List of conflicts
            parties: Involved parties

        Returns:
            Result containing de-escalation plan or error
        """
        if not conflicts:
            return Err(ConflictError(
                message="At least one conflict required",
                recoverable=True,
            ))

        try:
            # Sort conflicts by severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_conflicts = sorted(
                conflicts,
                key=lambda c: severity_order.get(c.get("severity", "low"), 3)
            )

            # Generate steps
            steps: List[Dict[str, Any]] = []
            
            # Immediate steps for critical conflicts
            critical = [c for c in sorted_conflicts if c.get("severity") == "critical"]
            if critical:
                steps.append({
                    "order": 1,
                    "phase": "immediate",
                    "action": "Address critical conflicts",
                    "description": f"Prioritize resolving {len(critical)} critical conflict(s)",
                    "estimated_time": "1-2 hours",
                })

            # Build rapport
            steps.append({
                "order": 2,
                "phase": "rapport",
                "action": "Rebuild trust",
                "description": "Facilitate open dialogue between parties",
                "estimated_time": "2-4 hours",
            })

            # Address remaining conflicts
            if len(sorted_conflicts) > len(critical):
                steps.append({
                    "order": 3,
                    "phase": "resolution",
                    "action": "Resolve remaining conflicts",
                    "description": f"Address {len(sorted_conflicts) - len(critical)} remaining conflict(s)",
                    "estimated_time": "4-8 hours",
                })

            result = {
                "total_conflicts": len(conflicts),
                "critical_conflicts": len(critical),
                "steps": steps,
                "total_estimated_time": self._estimate_total_time(steps),
                "success_factors": [
                    "Willingness to compromise",
                    "Clear communication",
                    "Neutral facilitation",
                ],
            }

            return Ok(result)
        except Exception as e:
            return Err(ConflictError(
                message=f"Failed to generate de-escalation plan: {e!s}",
                recoverable=True,
            ))

    def _calculate_intensity(
        self, by_severity: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Calculate overall conflict intensity."""
        score = (
            len(by_severity["critical"]) * 4 +
            len(by_severity["high"]) * 3 +
            len(by_severity["medium"]) * 2 +
            len(by_severity["low"]) * 1
        )

        if score >= 10:
            return "high"
        elif score >= 5:
            return "medium"
        else:
            return "low"

    def _estimate_resolution_time(self, severity: str) -> str:
        """Estimate time needed to resolve conflict."""
        estimates = {
            "critical": "4-8 hours",
            "high": "2-4 hours",
            "medium": "1-2 hours",
            "low": "30-60 minutes",
        }
        return estimates.get(severity, "1-2 hours")

    def _get_mediation_benefits(self, score: int) -> List[str]:
        """Get benefits of mediation based on score."""
        benefits = ["Neutral perspective"]
        
        if score >= 40:
            benefits.append("Structured process")
        if score >= 60:
            benefits.append("Professional guidance")
            benefits.append("Faster resolution")

        return benefits

    def _estimate_total_time(self, steps: List[Dict[str, Any]]) -> str:
        """Estimate total time for de-escalation."""
        if not steps:
            return "0 hours"
        
        # Simple estimation
        return "8-16 hours"
