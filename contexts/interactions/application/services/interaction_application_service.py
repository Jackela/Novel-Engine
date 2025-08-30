#!/usr/bin/env python3
"""
Interaction Application Service

This module implements the main application service for the Interaction
bounded context, providing a high-level API that orchestrates business
operations through command handlers and domain services.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ...domain.aggregates.negotiation_session import NegotiationSession
from ...domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from ...domain.services.negotiation_service import NegotiationService
from ...domain.value_objects.interaction_id import InteractionId
from ...domain.value_objects.negotiation_party import NegotiationParty
from ...domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    TerminationReason,
)
from ...domain.value_objects.proposal_response import ProposalResponse
from ...domain.value_objects.proposal_terms import ProposalTerms
from ..commands.interaction_command_handlers import InteractionCommandHandler
from ..commands.interaction_commands import (
    AddPartyToSessionCommand,
    AdvanceNegotiationPhaseCommand,
    AnalyzeProposalViabilityCommand,
    AssessPartyCompatibilityCommand,
    CalculateNegotiationMomentumCommand,
    CreateNegotiationSessionCommand,
    DetectNegotiationConflictsCommand,
    RecommendNegotiationStrategyCommand,
    SubmitProposalCommand,
    SubmitProposalResponseCommand,
    TerminateNegotiationSessionCommand,
)


class InteractionApplicationService:
    """
    Main application service for Interaction bounded context.

    Provides high-level business operations and orchestrates interactions
    between command handlers, domain services, and external systems.
    """

    def __init__(
        self,
        session_repository: NegotiationSessionRepository,
        negotiation_service: Optional[NegotiationService] = None,
    ):
        """Initialize application service with required dependencies."""
        self.session_repository = session_repository
        self.negotiation_service = negotiation_service or NegotiationService()
        self.command_handler = InteractionCommandHandler(
            session_repository=session_repository,
            negotiation_service=self.negotiation_service,
        )

    # High-Level Business Operations

    async def create_negotiation_session(
        self, session_name: str, session_type: str, created_by: UUID, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new negotiation session with specified parameters.

        Returns session information and status.
        """
        command = CreateNegotiationSessionCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=created_by,
            session_name=session_name,
            session_type=session_type,
            negotiation_domain=kwargs.get("negotiation_domain"),
            max_parties=kwargs.get("max_parties", 10),
            session_timeout_hours=kwargs.get("session_timeout_hours", 72),
            auto_advance_phases=kwargs.get("auto_advance_phases", True),
            require_unanimous_agreement=kwargs.get(
                "require_unanimous_agreement", False
            ),
            allow_partial_agreements=kwargs.get("allow_partial_agreements", True),
            session_context=kwargs.get("session_context"),
            priority_level=kwargs.get("priority_level", "medium"),
            confidentiality_level=kwargs.get("confidentiality_level", "standard"),
        )

        result = await self.command_handler.handle_create_negotiation_session(command)

        return {
            "operation": "create_negotiation_session",
            "success": True,
            "session_id": result["session_id"],
            "session_name": result["session_name"],
            "created_at": result["created_at"],
            "status": result["status"],
            "configuration": {
                "max_parties": result["max_parties"],
                "timeout_hours": kwargs.get("session_timeout_hours", 72),
                "auto_advance_phases": kwargs.get("auto_advance_phases", True),
                "require_unanimous": kwargs.get("require_unanimous_agreement", False),
            },
            "events_generated": result["events"],
        }

    async def add_party_to_negotiation(
        self,
        session_id: UUID,
        party: NegotiationParty,
        initiated_by: UUID,
        validate_compatibility: bool = True,
    ) -> Dict[str, Any]:
        """
        Add a party to an existing negotiation session.

        Performs compatibility checks and updates session state.
        """
        command = AddPartyToSessionCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            party=party,
            validate_compatibility=validate_compatibility,
        )

        result = await self.command_handler.handle_add_party_to_session(command)

        return {
            "operation": "add_party_to_negotiation",
            "success": True,
            "session_id": result["session_id"],
            "party_added": {
                "party_id": result["party_id"],
                "party_name": result["party_name"],
                "party_role": result["party_role"],
                "compatibility_score": result["compatibility_score"],
            },
            "session_status": {
                "total_parties": result["total_parties"],
                "can_start": result["total_parties"] >= 2,
            },
            "events_generated": result["events"],
        }

    async def submit_proposal(
        self,
        session_id: UUID,
        proposal: ProposalTerms,
        submitted_by: UUID,
        submission_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a proposal to a negotiation session.

        Validates proposal and updates session phase if appropriate.
        """
        # Pre-submission analysis
        analysis_command = AnalyzeProposalViabilityCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=submitted_by,
            session_id=session_id,
            proposal_id=proposal.proposal_id,
            analysis_depth="standard",
        )

        analysis_result = await self.command_handler.handle_analyze_proposal_viability(
            analysis_command
        )

        # Submit proposal
        command = SubmitProposalCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=submitted_by,
            session_id=session_id,
            proposal=proposal,
            submission_notes=submission_notes,
        )

        result = await self.command_handler.handle_submit_proposal(command)

        return {
            "operation": "submit_proposal",
            "success": True,
            "session_id": result["session_id"],
            "proposal_submitted": {
                "proposal_id": result["proposal_id"],
                "proposal_title": result["proposal_title"],
                "proposal_type": result["proposal_type"],
                "terms_count": result["terms_count"],
                "viability_score": analysis_result["analysis_result"][
                    "overall_viability_score"
                ],
                "acceptance_probability": analysis_result["analysis_result"][
                    "acceptance_probability"
                ],
            },
            "session_status": {
                "current_phase": result["current_phase"],
                "submitted_by": result["submitted_by"],
            },
            "pre_submission_analysis": analysis_result["analysis_result"],
            "events_generated": result["events"],
        }

    async def submit_proposal_response(
        self, session_id: UUID, response: ProposalResponse, submitted_by: UUID
    ) -> Dict[str, Any]:
        """
        Submit a response to a proposal.

        Processes response and checks for completion conditions.
        """
        command = SubmitProposalResponseCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=submitted_by,
            session_id=session_id,
            response=response,
        )

        result = await self.command_handler.handle_submit_proposal_response(command)

        # Check momentum after response
        momentum_command = CalculateNegotiationMomentumCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=submitted_by,
            session_id=session_id,
            analysis_window_hours=24,
        )

        momentum_result = (
            await self.command_handler.handle_calculate_negotiation_momentum(
                momentum_command
            )
        )

        return {
            "operation": "submit_proposal_response",
            "success": True,
            "session_id": result["session_id"],
            "response_submitted": {
                "response_id": result["response_id"],
                "proposal_id": result["proposal_id"],
                "responding_party_id": result["responding_party_id"],
                "overall_response": result["overall_response"],
                "acceptance_percentage": result["acceptance_percentage"],
                "requires_follow_up": result["requires_follow_up"],
            },
            "session_status": {
                "current_phase": result["current_phase"],
                "momentum": momentum_result["momentum_analysis"],
            },
            "events_generated": result["events"],
        }

    async def advance_negotiation_phase(
        self,
        session_id: UUID,
        target_phase: NegotiationPhase,
        initiated_by: UUID,
        force_advancement: bool = False,
    ) -> Dict[str, Any]:
        """
        Advance negotiation to a specific phase.

        Validates phase transition rules unless forced.
        """
        command = AdvanceNegotiationPhaseCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            target_phase=target_phase,
            force_advancement=force_advancement,
        )

        result = await self.command_handler.handle_advance_negotiation_phase(command)

        return {
            "operation": "advance_negotiation_phase",
            "success": True,
            "session_id": result["session_id"],
            "phase_transition": {
                "from_phase": result["from_phase"],
                "to_phase": result["to_phase"],
                "forced": result["forced"],
                "advancement_reason": result["advancement_reason"],
            },
            "events_generated": result["events"],
        }

    async def complete_negotiation(
        self,
        session_id: UUID,
        outcome: NegotiationOutcome,
        termination_reason: TerminationReason,
        initiated_by: UUID,
        completion_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete a negotiation with specified outcome.

        Finalizes session and generates completion report.
        """
        # Get final momentum and conflict analysis
        momentum_command = CalculateNegotiationMomentumCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            analysis_window_hours=48,
        )

        final_momentum = (
            await self.command_handler.handle_calculate_negotiation_momentum(
                momentum_command
            )
        )

        conflicts_command = DetectNegotiationConflictsCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            severity_threshold="low",
        )

        final_conflicts = (
            await self.command_handler.handle_detect_negotiation_conflicts(
                conflicts_command
            )
        )

        # Terminate session
        command = TerminateNegotiationSessionCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            outcome=outcome,
            termination_reason=termination_reason,
            completion_notes=completion_notes,
        )

        result = await self.command_handler.handle_terminate_negotiation_session(
            command
        )

        return {
            "operation": "complete_negotiation",
            "success": True,
            "session_id": result["session_id"],
            "completion_summary": {
                "outcome": result["outcome"],
                "termination_reason": result["termination_reason"],
                "terminated_at": result["terminated_at"],
                "total_duration": result["duration"],
                "completion_notes": completion_notes,
            },
            "final_analysis": {
                "momentum": final_momentum["momentum_analysis"],
                "conflicts": final_conflicts["conflicts_detected"],
            },
            "events_generated": result["events"],
        }

    # Analytical Operations

    async def get_negotiation_insights(
        self,
        session_id: UUID,
        initiated_by: UUID,
        analysis_depth: str = "comprehensive",
    ) -> Dict[str, Any]:
        """
        Get comprehensive insights about a negotiation session.

        Combines multiple analyses for complete picture.
        """
        # Party compatibility assessment
        compatibility_command = AssessPartyCompatibilityCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            include_recommendations=True,
        )

        compatibility_result = (
            await self.command_handler.handle_assess_party_compatibility(
                compatibility_command
            )
        )

        # Strategy recommendation
        strategy_command = RecommendNegotiationStrategyCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            strategy_focus="balanced",
            include_tactics=True,
        )

        strategy_result = (
            await self.command_handler.handle_recommend_negotiation_strategy(
                strategy_command
            )
        )

        # Conflict detection
        conflicts_command = DetectNegotiationConflictsCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            severity_threshold="medium",
            include_resolution_suggestions=True,
        )

        conflicts_result = (
            await self.command_handler.handle_detect_negotiation_conflicts(
                conflicts_command
            )
        )

        # Momentum analysis
        momentum_command = CalculateNegotiationMomentumCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            analysis_window_hours=24,
            include_predictions=True,
        )

        momentum_result = (
            await self.command_handler.handle_calculate_negotiation_momentum(
                momentum_command
            )
        )

        return {
            "operation": "get_negotiation_insights",
            "success": True,
            "session_id": str(session_id),
            "analysis_depth": analysis_depth,
            "insights": {
                "party_compatibility": compatibility_result,
                "recommended_strategy": strategy_result["strategy_recommendation"],
                "detected_conflicts": conflicts_result["conflicts_detected"],
                "momentum_analysis": momentum_result["momentum_analysis"],
            },
            "overall_assessment": {
                "compatibility_score": compatibility_result["overall_compatibility"],
                "conflict_level": len(conflicts_result["conflicts_detected"]),
                "momentum_direction": momentum_result["momentum_analysis"]["direction"],
                "success_probability": self._calculate_success_probability(
                    compatibility_result["overall_compatibility"],
                    len(conflicts_result["conflicts_detected"]),
                    momentum_result["momentum_analysis"]["momentum_score"],
                ),
            },
            "recommendations": self._generate_recommendations(
                compatibility_result, strategy_result, conflicts_result, momentum_result
            ),
        }

    async def optimize_active_proposals(
        self,
        session_id: UUID,
        initiated_by: UUID,
        optimization_target: str = "maximize_acceptance",
    ) -> Dict[str, Any]:
        """
        Optimize all active proposals in a session.

        Analyzes and suggests improvements for better acceptance rates.
        """
        # Get session to find active proposals
        session = await self.session_repository.get_by_id(InteractionId(session_id))
        if not session:
            raise ValueError(f"Session {session_id} not found")

        optimization_results = []

        for proposal_id in session.active_proposals.keys():
            # Analyze current proposal
            analysis_command = AnalyzeProposalViabilityCommand(
                command_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                initiated_by=initiated_by,
                session_id=session_id,
                proposal_id=proposal_id,
                include_optimization_suggestions=True,
            )

            analysis_result = (
                await self.command_handler.handle_analyze_proposal_viability(
                    analysis_command
                )
            )

            optimization_results.append(
                {
                    "proposal_id": str(proposal_id),
                    "current_viability": analysis_result["analysis_result"][
                        "overall_viability_score"
                    ],
                    "optimization_suggestions": analysis_result["analysis_result"][
                        "optimization_suggestions"
                    ],
                    "risk_factors": analysis_result["analysis_result"]["risk_factors"],
                    "success_factors": analysis_result["analysis_result"][
                        "success_factors"
                    ],
                }
            )

        # Calculate overall optimization potential
        total_viability = sum(
            result["current_viability"] for result in optimization_results
        )
        avg_viability = (
            total_viability / len(optimization_results) if optimization_results else 0
        )

        return {
            "operation": "optimize_active_proposals",
            "success": True,
            "session_id": str(session_id),
            "optimization_target": optimization_target,
            "proposals_analyzed": len(optimization_results),
            "average_viability": avg_viability,
            "proposal_optimizations": optimization_results,
            "overall_recommendations": self._generate_proposal_optimization_recommendations(
                optimization_results
            ),
        }

    async def monitor_session_health(
        self, session_id: UUID, initiated_by: UUID
    ) -> Dict[str, Any]:
        """
        Monitor the health and status of a negotiation session.

        Provides real-time health indicators and alerts.
        """
        # Get session basic info
        session = await self.session_repository.get_by_id(InteractionId(session_id))
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check for timeout issues
        timeout_approaching = session.is_timeout_approaching(24)  # 24-hour warning
        time_since_activity = session.status.time_since_last_activity

        # Detect conflicts
        conflicts_command = DetectNegotiationConflictsCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            severity_threshold="low",
        )

        conflicts_result = (
            await self.command_handler.handle_detect_negotiation_conflicts(
                conflicts_command
            )
        )

        # Calculate momentum
        momentum_command = CalculateNegotiationMomentumCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            initiated_by=initiated_by,
            session_id=session_id,
            analysis_window_hours=12,
        )

        momentum_result = (
            await self.command_handler.handle_calculate_negotiation_momentum(
                momentum_command
            )
        )

        # Determine health status
        health_score = self._calculate_health_score(
            session,
            conflicts_result["conflicts_detected"],
            momentum_result["momentum_analysis"],
        )

        health_alerts = []

        if timeout_approaching:
            health_alerts.append(
                {
                    "type": "timeout_warning",
                    "severity": "high",
                    "message": "Session approaching timeout deadline",
                }
            )

        if time_since_activity > 14400:  # 4 hours
            health_alerts.append(
                {
                    "type": "inactivity_warning",
                    "severity": "medium",
                    "message": f"No activity for {time_since_activity // 3600} hours",
                }
            )

        if len(conflicts_result["conflicts_detected"]) > 3:
            health_alerts.append(
                {
                    "type": "conflict_warning",
                    "severity": "high",
                    "message": f"High number of conflicts detected ({len(conflicts_result['conflicts_detected'])})",
                }
            )

        if momentum_result["momentum_analysis"]["direction"] == "negative":
            health_alerts.append(
                {
                    "type": "momentum_warning",
                    "severity": "medium",
                    "message": "Negative momentum detected",
                }
            )

        return {
            "operation": "monitor_session_health",
            "success": True,
            "session_id": str(session_id),
            "health_summary": {
                "health_score": health_score,
                "health_status": self._get_health_status(health_score),
                "active_alerts": health_alerts,
                "session_age_hours": int(
                    (datetime.now(timezone.utc) - session.created_at).total_seconds()
                    // 3600
                ),
                "time_since_last_activity_hours": time_since_activity // 3600,
            },
            "key_metrics": {
                "total_parties": len(session.parties),
                "active_proposals": len(session.active_proposals),
                "total_responses": session.total_responses,
                "current_phase": session.status.phase.value,
                "momentum_direction": momentum_result["momentum_analysis"]["direction"],
                "conflict_count": len(conflicts_result["conflicts_detected"]),
            },
            "recommendations": self._generate_health_recommendations(
                health_score, health_alerts
            ),
        }

    # Private Helper Methods

    def _calculate_success_probability(
        self, compatibility_score: float, conflict_count: int, momentum_score: float
    ) -> float:
        """Calculate overall probability of negotiation success."""
        # Weighted factors
        compatibility_weight = 0.4
        conflict_weight = 0.3
        momentum_weight = 0.3

        # Normalize conflict impact (more conflicts = lower score)
        conflict_impact = max(0, 100 - (conflict_count * 10))

        success_probability = (
            (compatibility_score * compatibility_weight)
            + (conflict_impact * conflict_weight)
            + (momentum_score * momentum_weight)
        )

        return min(100.0, max(0.0, success_probability))

    def _generate_recommendations(
        self,
        compatibility_result: Dict[str, Any],
        strategy_result: Dict[str, Any],
        conflicts_result: Dict[str, Any],
        momentum_result: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations based on analysis results."""
        recommendations = []

        # Compatibility recommendations
        if compatibility_result["overall_compatibility"] < 50:
            recommendations.append(
                "Consider mediation or conflict resolution strategies due to low party compatibility"
            )

        # Strategy recommendations
        recommendations.extend(
            strategy_result["strategy_recommendation"].get("key_tactics", [])
        )

        # Conflict resolution recommendations
        for conflict in conflicts_result["conflicts_detected"]:
            if conflict.get("severity") in ["high", "critical"]:
                recommendations.extend(conflict.get("resolution_suggestions", []))

        # Momentum recommendations
        momentum_recs = momentum_result["momentum_analysis"].get("recommendations", [])
        recommendations.extend(momentum_recs)

        # Remove duplicates and limit to top 10
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:10]

    def _generate_proposal_optimization_recommendations(
        self, optimization_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for proposal optimization."""
        recommendations = []

        # Analyze common issues across proposals
        all_suggestions = []
        for result in optimization_results:
            all_suggestions.extend(result["optimization_suggestions"])

        # Find most common suggestions
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

        # Add most common suggestions as recommendations
        common_suggestions = sorted(
            suggestion_counts.items(), key=lambda x: x[1], reverse=True
        )
        for suggestion, count in common_suggestions[:5]:
            if count > 1:  # Appears in multiple proposals
                recommendations.append(
                    f"Common issue across {count} proposals: {suggestion}"
                )

        # Add viability-based recommendations
        low_viability_count = sum(
            1 for result in optimization_results if result["current_viability"] < 50
        )
        if low_viability_count > 0:
            recommendations.append(
                f"{low_viability_count} proposals have low viability - consider major revisions"
            )

        return recommendations

    def _calculate_health_score(
        self,
        session: NegotiationSession,
        conflicts: List[Dict[str, Any]],
        momentum_analysis: Dict[str, Any],
    ) -> float:
        """Calculate overall health score for a session."""
        base_score = 100.0

        # Deduct for conflicts
        for conflict in conflicts:
            severity = conflict.get("severity", "low")
            if severity == "critical":
                base_score -= 20
            elif severity == "high":
                base_score -= 15
            elif severity == "medium":
                base_score -= 10
            else:  # low
                base_score -= 5

        # Adjust for momentum
        momentum_score = momentum_analysis.get("momentum_score", 50)
        if momentum_score < 30:
            base_score -= 15
        elif momentum_score < 50:
            base_score -= 5
        elif momentum_score > 80:
            base_score += 5

        # Adjust for activity level
        time_since_activity = session.status.time_since_last_activity
        if time_since_activity > 86400:  # 24 hours
            base_score -= 20
        elif time_since_activity > 14400:  # 4 hours
            base_score -= 10

        # Adjust for phase appropriateness
        if (
            session.status.phase.value in ["bargaining", "closing"]
            and len(session.active_proposals) == 0
        ):
            base_score -= 15  # Should have proposals in these phases

        return max(0.0, min(100.0, base_score))

    def _get_health_status(self, health_score: float) -> str:
        """Convert health score to status description."""
        if health_score >= 80:
            return "excellent"
        elif health_score >= 65:
            return "good"
        elif health_score >= 50:
            return "fair"
        elif health_score >= 35:
            return "poor"
        else:
            return "critical"

    def _generate_health_recommendations(
        self, health_score: float, health_alerts: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for improving session health."""
        recommendations = []

        # Address specific alerts
        for alert in health_alerts:
            if alert["type"] == "timeout_warning":
                recommendations.append(
                    "Extend session timeline or accelerate decision-making"
                )
            elif alert["type"] == "inactivity_warning":
                recommendations.append(
                    "Schedule immediate follow-up meeting or send status inquiry"
                )
            elif alert["type"] == "conflict_warning":
                recommendations.append(
                    "Implement conflict resolution procedures immediately"
                )
            elif alert["type"] == "momentum_warning":
                recommendations.append(
                    "Introduce new proposals or change negotiation approach"
                )

        # General health recommendations
        if health_score < 50:
            recommendations.extend(
                [
                    "Consider bringing in neutral mediator",
                    "Review and possibly revise negotiation strategy",
                    "Schedule stakeholder alignment meeting",
                ]
            )
        elif health_score < 70:
            recommendations.extend(
                [
                    "Increase communication frequency",
                    "Focus on building consensus on key issues",
                ]
            )

        return recommendations[:8]  # Limit to most important recommendations
