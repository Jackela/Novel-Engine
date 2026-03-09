#!/usr/bin/env python3
"""
Health Monitoring Application Service

Application service for monitoring negotiation session health using Result pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from .....core.result import Err, Ok, Result
from ....interactions.domain.aggregates.negotiation_session import NegotiationSession
from .shared.errors import (
    SessionError,
)


class HealthMonitoringService:
    """
    Service for monitoring negotiation session health.
    
    Provides business operations for health assessment, alert detection,
    and monitoring recommendations.
    """

    def __init__(self) -> None:
        """Initialize health monitoring service."""
        pass

    def assess_session_health(
        self,
        session: NegotiationSession,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Assess overall health of a negotiation session.

        Args:
            session: Negotiation session to assess

        Returns:
            Result containing health assessment or error
        """
        if session is None:
            return Err(SessionError(
                message="Session is required for health assessment",
                recoverable=True,
            ))

        try:
            # Calculate base health score
            health_score = 100.0
            alerts: List[Dict[str, Any]] = []

            # Check activity
            time_since_activity = session.status.time_since_last_activity
            if time_since_activity > 86400:  # 24 hours
                health_score -= 20
                alerts.append({
                    "type": "inactivity",
                    "severity": "high",
                    "message": f"No activity for {time_since_activity // 3600} hours",
                })
            elif time_since_activity > 14400:  # 4 hours
                health_score -= 10
                alerts.append({
                    "type": "inactivity",
                    "severity": "medium",
                    "message": f"No activity for {time_since_activity // 3600} hours",
                })

            # Check timeout
            if session.is_timeout_approaching(24):
                health_score -= 15
                alerts.append({
                    "type": "timeout_warning",
                    "severity": "high",
                    "message": "Session timeout approaching",
                })

            # Check phase appropriateness
            phase = session.status.phase.value
            if phase in ["bargaining", "closing"] and len(session.active_proposals) == 0:
                health_score -= 15
                alerts.append({
                    "type": "phase_mismatch",
                    "severity": "medium",
                    "message": f"No active proposals in {phase} phase",
                })

            # Check party count
            if len(session.parties) < 2:
                health_score -= 30
                alerts.append({
                    "type": "insufficient_parties",
                    "severity": "critical",
                    "message": "Insufficient parties for negotiation",
                })

            # Normalize score
            health_score = max(0.0, min(100.0, health_score))

            result = {
                "session_id": str(session.session_id),
                "health_score": health_score,
                "health_status": self._score_to_status(health_score),
                "is_healthy": health_score >= 70,
                "alerts": alerts,
                "alert_count": len(alerts),
                "critical_alerts": sum(1 for a in alerts if a["severity"] == "critical"),
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            }

            return Ok(result)
        except Exception as e:
            return Err(SessionError(
                message=f"Failed to assess health: {e!s}",
                session_id=str(session.session_id),
                recoverable=True,
            ))

    def detect_health_issues(
        self,
        session: NegotiationSession,
        include_warnings: bool = True,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Detect health issues in a session.

        Args:
            session: Session to check
            include_warnings: Whether to include warnings

        Returns:
            Result containing detected issues or error
        """
        if session is None:
            return Err(SessionError(
                message="Session is required",
                recoverable=True,
            ))

        try:
            issues: List[Dict[str, Any]] = []

            # Check session status
            if not session.is_active:
                issues.append({
                    "category": "status",
                    "severity": "critical",
                    "issue": "session_inactive",
                    "message": "Session is no longer active",
                })

            # Check activity timeout
            if session.status.time_since_last_activity > 86400:
                issues.append({
                    "category": "activity",
                    "severity": "high",
                    "issue": "activity_timeout",
                    "message": "Session has been inactive for over 24 hours",
                })

            # Check proposal status
            if session.status.phase.value in ["bargaining", "closing"]:
                if len(session.active_proposals) == 0:
                    issues.append({
                        "category": "proposals",
                        "severity": "high",
                        "issue": "no_active_proposals",
                        "message": f"No active proposals in {session.status.phase.value} phase",
                    })

            # Check response status
            for proposal_id in session.active_proposals:
                responses = session.get_proposal_responses(proposal_id)
                if not responses:
                    if include_warnings:
                        issues.append({
                            "category": "responses",
                            "severity": "medium",
                            "issue": "no_responses",
                            "message": f"Proposal {proposal_id} has no responses",
                        })

            # Check party participation
            for party_id in session.parties:
                if party_id not in session.responses or not session.responses[party_id]:
                    if include_warnings:
                        party = session.parties[party_id]
                        issues.append({
                            "category": "participation",
                            "severity": "low",
                            "issue": "no_participation",
                            "message": f"Party {party.party_name} has not responded",
                            "party_id": str(party_id),
                        })

            result = {
                "session_id": str(session.session_id),
                "issue_count": len(issues),
                "critical_issues": [i for i in issues if i["severity"] == "critical"],
                "high_issues": [i for i in issues if i["severity"] == "high"],
                "medium_issues": [i for i in issues if i["severity"] == "medium"],
                "low_issues": [i for i in issues if i["severity"] == "low"],
                "all_issues": issues,
                "has_critical_issues": any(i["severity"] == "critical" for i in issues),
            }

            return Ok(result)
        except Exception as e:
            return Err(SessionError(
                message=f"Failed to detect health issues: {e!s}",
                session_id=str(session.session_id),
                recoverable=True,
            ))

    def generate_health_recommendations(
        self,
        session: NegotiationSession,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Generate recommendations to improve session health.

        Args:
            session: Session to generate recommendations for

        Returns:
            Result containing recommendations or error
        """
        if session is None:
            return Err(SessionError(
                message="Session is required",
                recoverable=True,
            ))

        try:
            recommendations: List[Dict[str, Any]] = []

            # Activity recommendations
            if session.status.time_since_last_activity > 14400:  # 4 hours
                recommendations.append({
                    "priority": "high",
                    "category": "activity",
                    "action": "schedule_followup",
                    "description": "Schedule follow-up to re-engage parties",
                })

            # Proposal recommendations
            if len(session.active_proposals) == 0 and session.is_active:
                recommendations.append({
                    "priority": "high",
                    "category": "proposals",
                    "action": "submit_proposal",
                    "description": "Submit initial proposal to start negotiation",
                })

            # Participation recommendations
            non_responsive_parties = []
            for party_id, party_responses in session.responses.items():
                if not party_responses:
                    party = session.parties.get(party_id)
                    if party:
                        non_responsive_parties.append(party.party_name)

            if non_responsive_parties:
                recommendations.append({
                    "priority": "medium",
                    "category": "participation",
                    "action": "encourage_participation",
                    "description": f"Encourage participation from: {', '.join(non_responsive_parties)}",
                })

            # Timeout recommendations
            if session.is_timeout_approaching(24):
                recommendations.append({
                    "priority": "high",
                    "category": "timeout",
                    "action": "extend_or_close",
                    "description": "Consider extending deadline or accelerating closure",
                })

            result = {
                "session_id": str(session.session_id),
                "recommendation_count": len(recommendations),
                "high_priority": [r for r in recommendations if r["priority"] == "high"],
                "medium_priority": [r for r in recommendations if r["priority"] == "medium"],
                "low_priority": [r for r in recommendations if r["priority"] == "low"],
                "all_recommendations": recommendations,
            }

            return Ok(result)
        except Exception as e:
            return Err(SessionError(
                message=f"Failed to generate recommendations: {e!s}",
                session_id=str(session.session_id),
                recoverable=True,
            ))

    def monitor_multiple_sessions(
        self,
        sessions: List[NegotiationSession],
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Monitor health of multiple sessions.

        Args:
            sessions: List of sessions to monitor

        Returns:
            Result containing monitoring results or error
        """
        if not sessions:
            return Err(SessionError(
                message="At least one session required for monitoring",
                recoverable=True,
            ))

        try:
            session_healths: List[Dict[str, Any]] = []
            healthy_count = 0
            at_risk_count = 0
            critical_count = 0

            for session in sessions:
                health_result = self.assess_session_health(session)
                if health_result.is_ok:
                    health = health_result.value
                    session_healths.append({
                        "session_id": str(session.session_id),
                        "health_score": health["health_score"],
                        "status": health["health_status"],
                    })

                    if health["health_score"] >= 70:
                        healthy_count += 1
                    elif health["health_score"] >= 40:
                        at_risk_count += 1
                    else:
                        critical_count += 1

            result = {
                "total_sessions": len(sessions),
                "healthy_count": healthy_count,
                "at_risk_count": at_risk_count,
                "critical_count": critical_count,
                "health_rate": healthy_count / len(sessions) if sessions else 0,
                "session_healths": session_healths,
                "summary_status": self._determine_summary_status(
                    healthy_count, at_risk_count, critical_count, len(sessions)
                ),
            }

            return Ok(result)
        except Exception as e:
            return Err(SessionError(
                message=f"Failed to monitor sessions: {e!s}",
                recoverable=True,
            ))

    def _score_to_status(self, score: float) -> str:
        """Convert health score to status."""
        if score >= 80:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 50:
            return "fair"
        elif score >= 35:
            return "poor"
        else:
            return "critical"

    def _determine_summary_status(
        self,
        healthy: int,
        at_risk: int,
        critical: int,
        total: int,
    ) -> str:
        """Determine overall status from counts."""
        if critical > total * 0.3:
            return "critical"
        elif at_risk + critical > total * 0.5:
            return "concerning"
        elif healthy > total * 0.7:
            return "healthy"
        else:
            return "mixed"
