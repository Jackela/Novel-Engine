#!/usr/bin/env python3
"""
Strategy Application Service

Application service for negotiation strategy operations using Result pattern.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from .....core.result import Err, Ok, Result
from ....interactions.domain.services.negotiation_service import NegotiationService
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from .shared.errors import (
    NegotiationError,
    ValidationError,
)


class StrategyService:
    """
    Service for negotiation strategy development and recommendation.
    
    Provides business operations for strategy analysis, tactic recommendation,
    and negotiation planning.
    """

    def __init__(self, negotiation_service: Optional[NegotiationService] = None) -> None:
        """Initialize with domain negotiation service."""
        self.negotiation_service = negotiation_service or NegotiationService()

    def develop_negotiation_strategy(
        self,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
        target_outcome: Optional[str] = None,
        strategy_focus: str = "balanced",
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Develop comprehensive negotiation strategy.

        Args:
            parties: List of negotiating parties
            negotiation_domain: Optional domain context
            target_outcome: Desired outcome
            strategy_focus: Strategy focus (balanced, aggressive, conservative)

        Returns:
            Result containing strategy or error
        """
        if not parties:
            return Err(NegotiationError(
                message="At least one party required for strategy development",
                recoverable=True,
            ))

        valid_focuses = ["balanced", "aggressive", "conservative", "collaborative"]
        if strategy_focus not in valid_focuses:
            return Err(ValidationError(
                message=f"Invalid strategy focus. Must be one of: {valid_focuses}",
                field="strategy_focus",
                field_value=strategy_focus,
                recoverable=True,
            ))

        try:
            # Get base strategy from domain service
            base_strategy = self.negotiation_service.recommend_negotiation_strategy(
                parties=parties,
                negotiation_domain=negotiation_domain,
                target_outcome=target_outcome,
            )

            # Enhance with application-level analysis
            enhanced_strategy = self._enhance_strategy(
                base_strategy, parties, strategy_focus
            )

            result = {
                "strategy_focus": strategy_focus,
                "target_outcome": target_outcome,
                "party_count": len(parties),
                "recommended_approach": enhanced_strategy["recommended_approach"],
                "phase_sequence": enhanced_strategy["phase_sequence"],
                "key_tactics": enhanced_strategy["key_tactics"],
                "risk_mitigation": enhanced_strategy["risk_mitigation"],
                "success_metrics": enhanced_strategy["success_metrics"],
                "timeline": enhanced_strategy["timeline"],
                "party_specific_strategies": enhanced_strategy["party_specific_strategies"],
            }

            return Ok(result)
        except Exception as e:
            return Err(NegotiationError(
                message=f"Failed to develop strategy: {e!s}",
                recoverable=True,
            ))

    def recommend_tactics_for_phase(
        self,
        parties: List[NegotiationParty],
        current_phase: str,
        objectives: List[str],
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Recommend tactics for a specific negotiation phase.

        Args:
            parties: List of negotiating parties
            current_phase: Current negotiation phase
            objectives: Phase objectives

        Returns:
            Result containing tactics or error
        """
        if not parties:
            return Err(NegotiationError(
                message="At least one party required",
                recoverable=True,
            ))

        valid_phases = [
            "preparation", "opening", "bargaining", "closing", 
            "implementation", "relationship_building"
        ]
        if current_phase not in valid_phases:
            return Err(ValidationError(
                message=f"Invalid phase. Must be one of: {valid_phases}",
                field="current_phase",
                field_value=current_phase,
                recoverable=True,
            ))

        try:
            tactics = self._generate_phase_tactics(parties, current_phase, objectives)

            result = {
                "phase": current_phase,
                "objectives": objectives,
                "recommended_tactics": tactics,
                "priority_tactic": tactics[0] if tactics else None,
                "contingency_tactics": tactics[2:] if len(tactics) > 2 else [],
            }

            return Ok(result)
        except Exception as e:
            return Err(NegotiationError(
                message=f"Failed to recommend tactics: {e!s}",
                recoverable=True,
            ))

    def analyze_power_dynamics(
        self,
        parties: List[NegotiationParty],
        negotiation_domain: Optional[str] = None,
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Analyze power dynamics between parties.

        Args:
            parties: List of negotiating parties
            negotiation_domain: Optional domain context

        Returns:
            Result containing power analysis or error
        """
        if not parties:
            return Err(NegotiationError(
                message="At least one party required for power analysis",
                recoverable=True,
            ))

        try:
            power_distribution: Dict[str, Any] = {}
            total_power = Decimal("0")

            for party in parties:
                power = party.get_negotiation_power(negotiation_domain or "")
                power_distribution[str(party.party_id)] = {
                    "party_name": party.party_name,
                    "power_score": float(power),
                    "is_decision_maker": party.is_decision_maker,
                    "authority_level": party.authority_level.value,
                }
                total_power += power

            # Find dominant party
            dominant_party = None
            max_power = Decimal("0")
            for party in parties:
                power = party.get_negotiation_power(negotiation_domain or "")
                if power > max_power:
                    max_power = power
                    dominant_party = party

            # Calculate balance
            powers = [p.get_negotiation_power(negotiation_domain or "") for p in parties]
            if powers and max(powers) > 0:
                imbalance = (max(powers) - min(powers)) / max(powers)
            else:
                imbalance = Decimal("0")

            result = {
                "party_count": len(parties),
                "total_power": float(total_power),
                "power_distribution": power_distribution,
                "dominant_party": {
                    "party_id": str(dominant_party.party_id),
                    "party_name": dominant_party.party_name,
                    "power_score": float(max_power),
                } if dominant_party else None,
                "imbalance_score": float(imbalance),
                "balance_assessment": self._assess_balance(imbalance),
            }

            return Ok(result)
        except Exception as e:
            return Err(NegotiationError(
                message=f"Failed to analyze power dynamics: {e!s}",
                recoverable=True,
            ))

    def create_negotiation_plan(
        self,
        parties: List[NegotiationParty],
        objectives: List[str],
        constraints: Optional[Dict[str, Any]] = None,
        timeline_days: int = 14,
    ) -> Result[Dict[str, Any], NegotiationError]:
        """
        Create a detailed negotiation plan.

        Args:
            parties: List of negotiating parties
            objectives: Negotiation objectives
            constraints: Optional constraints
            timeline_days: Timeline in days

        Returns:
            Result containing negotiation plan or error
        """
        if not parties:
            return Err(NegotiationError(
                message="At least one party required for plan creation",
                recoverable=True,
            ))

        if not objectives:
            return Err(ValidationError(
                message="At least one objective required",
                field="objectives",
                recoverable=True,
            ))

        if timeline_days < 1:
            return Err(ValidationError(
                message="Timeline must be at least 1 day",
                field="timeline_days",
                field_value=timeline_days,
                recoverable=True,
            ))

        try:
            # Generate phases
            phases = self._generate_negotiation_phases(timeline_days, parties)

            # Assign responsibilities
            responsibilities = self._assign_responsibilities(parties)

            # Create milestones
            milestones = self._create_milestones(phases)

            result = {
                "objectives": objectives,
                "timeline_days": timeline_days,
                "party_count": len(parties),
                "phases": phases,
                "milestones": milestones,
                "responsibilities": responsibilities,
                "key_success_factors": self._identify_success_factors(parties),
                "risk_factors": self._identify_risk_factors(parties),
            }

            return Ok(result)
        except Exception as e:
            return Err(NegotiationError(
                message=f"Failed to create negotiation plan: {e!s}",
                recoverable=True,
            ))

    def _enhance_strategy(
        self,
        base_strategy: Dict[str, Any],
        parties: List[NegotiationParty],
        strategy_focus: str,
    ) -> Dict[str, Any]:
        """Enhance base strategy with application-level insights."""
        enhanced = dict(base_strategy)

        # Adjust tactics based on focus
        if strategy_focus == "aggressive":
            enhanced["key_tactics"] = [
                "Set firm deadlines",
                "Highlight alternatives",
                "Focus on competitive advantages",
            ] + enhanced.get("key_tactics", [])
        elif strategy_focus == "conservative":
            enhanced["key_tactics"] = [
                "Build relationships first",
                "Seek incremental progress",
                "Emphasize shared interests",
            ] + enhanced.get("key_tactics", [])

        return enhanced

    def _generate_phase_tactics(
        self,
        parties: List[NegotiationParty],
        phase: str,
        objectives: List[str],
    ) -> List[str]:
        """Generate tactics for a specific phase."""
        tactics: List[str] = []

        if phase == "preparation":
            tactics = [
                "Research all parties' positions",
                "Identify BATNA for each party",
                "Prepare opening statements",
            ]
        elif phase == "opening":
            tactics = [
                "Establish rapport",
                "Clarify objectives",
                "Set agenda",
            ]
        elif phase == "bargaining":
            tactics = [
                "Use objective criteria",
                "Make conditional offers",
                "Explore multiple options",
            ]
        elif phase == "closing":
            tactics = [
                "Summarize agreements",
                "Confirm next steps",
                "Document decisions",
            ]

        # Add party-specific tactics
        analytical_parties = [
            p for p in parties 
            if p.preferences.communication_preference.value == "analytical"
        ]
        if analytical_parties:
            tactics.append("Provide detailed data and analysis")

        return tactics

    def _assess_balance(self, imbalance: Decimal) -> str:
        """Assess power balance level."""
        if imbalance < Decimal("0.3"):
            return "well_balanced"
        elif imbalance < Decimal("0.5"):
            return "moderately_balanced"
        elif imbalance < Decimal("0.7"):
            return "imbalanced"
        else:
            return "highly_imbalanced"

    def _generate_negotiation_phases(
        self, timeline_days: int, parties: List[NegotiationParty]
    ) -> List[Dict[str, Any]]:
        """Generate negotiation phases."""
        # Adjust based on timeline
        if timeline_days < 7:
            return [
                {"name": "preparation", "duration_days": 1, "order": 1},
                {"name": "bargaining", "duration_days": timeline_days - 2, "order": 2},
                {"name": "closing", "duration_days": 1, "order": 3},
            ]
        else:
            return [
                {"name": "preparation", "duration_days": 2, "order": 1},
                {"name": "opening", "duration_days": 2, "order": 2},
                {"name": "bargaining", "duration_days": timeline_days - 6, "order": 3},
                {"name": "closing", "duration_days": 2, "order": 4},
            ]

    def _assign_responsibilities(
        self, parties: List[NegotiationParty]
    ) -> Dict[str, List[str]]:
        """Assign responsibilities to parties."""
        responsibilities: Dict[str, List[str]] = {}

        for party in parties:
            party_resp: List[str] = []
            
            if party.is_decision_maker:
                party_resp.append("Final decision making")
            
            if party.authority_level.value in ["high", "executive"]:
                party_resp.append("Policy approval")
            
            responsibilities[str(party.party_id)] = party_resp

        return responsibilities

    def _create_milestones(self, phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create milestones from phases."""
        milestones = []
        cumulative_days = 0

        for phase in phases:
            cumulative_days += phase["duration_days"]
            milestones.append({
                "name": f"Complete {phase['name']}",
                "target_day": cumulative_days,
                "phase": phase["name"],
            })

        return milestones

    def _identify_success_factors(self, parties: List[NegotiationParty]) -> List[str]:
        """Identify key success factors."""
        factors = [
            "Clear communication",
            "Well-defined objectives",
        ]

        decision_makers = [p for p in parties if p.is_decision_maker]
        if len(decision_makers) >= 2:
            factors.append("Multiple decision makers present")

        return factors

    def _identify_risk_factors(self, parties: List[NegotiationParty]) -> List[str]:
        """Identify potential risk factors."""
        risks: List[str] = []

        competitive_count = sum(
            1 for p in parties 
            if p.preferences.negotiation_style.value == "competitive"
        )
        if competitive_count > len(parties) // 2:
            risks.append("Competitive style majority")

        return risks
