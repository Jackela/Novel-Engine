#!/usr/bin/env python3
"""
Analytics Application Service

Application service for interaction analytics using Result pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from .....core.result import Err, Ok, Result
from ....interactions.domain.aggregates.negotiation_session import NegotiationSession
from .shared.errors import (
    InteractionError,
    ValidationError,
)


class AnalyticsService:
    """
    Service for interaction analytics and reporting.

    Provides business operations for calculating metrics,
    generating reports, and trend analysis.
    """

    def __init__(self) -> None:
        """Initialize analytics service."""
        pass

    def calculate_session_metrics(
        self,
        session: NegotiationSession,
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Calculate comprehensive metrics for a session.

        Args:
            session: Negotiation session

        Returns:
            Result containing metrics or error
        """
        if session is None:
            return Err(
                ValidationError(
                    message="Session is required",
                    field="session",
                    recoverable=True,
                )
            )

        try:
            # Calculate duration
            if session.status.actual_completion_at:
                duration = (
                    session.status.actual_completion_at - session.created_at
                ).total_seconds()
            else:
                duration = (
                    datetime.now(timezone.utc) - session.created_at
                ).total_seconds()

            # Calculate response rate
            total_responses = sum(
                len(responses) for responses in session.responses.values()
            )
            possible_responses = len(session.parties) * len(session.active_proposals)
            response_rate = (
                total_responses / possible_responses if possible_responses > 0 else 0
            )

            result = {
                "session_id": str(session.session_id),
                "duration_seconds": duration,
                "duration_hours": duration / 3600,
                "party_count": len(session.parties),
                "active_proposals": len(session.active_proposals),
                "total_responses": total_responses,
                "response_rate": response_rate,
                "current_phase": session.status.phase.value,
                "is_active": session.is_active,
                "engagement_score": self._calculate_engagement(session),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                InteractionError(
                    message=f"Failed to calculate metrics: {e!s}",
                    recoverable=True,
                )
            )

    def analyze_session_trends(
        self,
        sessions: List[NegotiationSession],
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Analyze trends across multiple sessions.

        Args:
            sessions: List of sessions

        Returns:
            Result containing trend analysis or error
        """
        if not sessions:
            return Err(
                ValidationError(
                    message="At least one session required",
                    field="sessions",
                    recoverable=True,
                )
            )

        try:
            # Calculate completion rate
            completed = sum(1 for s in sessions if not s.is_active)
            completion_rate = completed / len(sessions)

            # Calculate average duration
            durations: List[float] = []
            for session in sessions:
                if session.status.actual_completion_at:
                    duration = (
                        session.status.actual_completion_at - session.created_at
                    ).total_seconds()
                    durations.append(duration)

            avg_duration = sum(durations) / len(durations) if durations else 0

            # Count by phase
            phase_counts: Dict[str, int] = {}
            for session in sessions:
                phase = session.status.phase.value
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

            result = {
                "total_sessions": len(sessions),
                "completed_sessions": completed,
                "active_sessions": len(sessions) - completed,
                "completion_rate": completion_rate,
                "average_duration_seconds": avg_duration,
                "average_duration_hours": avg_duration / 3600,
                "phase_distribution": phase_counts,
                "trend_direction": self._determine_trend(sessions),
            }

            return Ok(result)
        except Exception as e:
            return Err(
                InteractionError(
                    message=f"Failed to analyze trends: {e!s}",
                    recoverable=True,
                )
            )

    def generate_session_report(
        self,
        session: NegotiationSession,
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Generate a comprehensive session report.

        Args:
            session: Session to report on

        Returns:
            Result containing report or error
        """
        if session is None:
            return Err(
                ValidationError(
                    message="Session is required",
                    field="session",
                    recoverable=True,
                )
            )

        try:
            metrics_result = self.calculate_session_metrics(session)
            if metrics_result.is_error:
                return metrics_result

            metrics = metrics_result.value

            report = {
                "report_type": "session_summary",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "session": {
                    "id": str(session.session_id),
                    "name": session.session_name,
                    "type": session.session_type,
                    "created_at": session.created_at.isoformat(),
                },
                "metrics": metrics,
                "participants": [
                    {
                        "id": str(p.party_id),
                        "name": p.party_name,
                        "role": p.role.value,
                        "is_decision_maker": p.is_decision_maker,
                    }
                    for p in session.parties.values()
                ],
                "proposals": [
                    {
                        "id": str(p.proposal_id),
                        "title": p.title,
                        "type": p.proposal_type.value
                        if hasattr(p.proposal_type, "value")
                        else str(p.proposal_type),
                        "term_count": len(p.terms),
                    }
                    for p in session.active_proposals.values()
                ],
                "status_summary": {
                    "current_phase": session.status.phase.value,
                    "outcome": session.status.outcome.value,
                    "is_active": session.is_active,
                },
            }

            return Ok(report)
        except Exception as e:
            return Err(
                InteractionError(
                    message=f"Failed to generate report: {e!s}",
                    recoverable=True,
                )
            )

    def compare_sessions(
        self,
        sessions: List[NegotiationSession],
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Compare multiple sessions.

        Args:
            sessions: List of sessions to compare

        Returns:
            Result containing comparison or error
        """
        if len(sessions) < 2:
            return Err(
                ValidationError(
                    message="At least two sessions required for comparison",
                    field="sessions",
                    recoverable=True,
                )
            )

        try:
            session_summaries: List[Dict[str, Any]] = []

            for session in sessions:
                metrics_result = self.calculate_session_metrics(session)
                if metrics_result.is_ok:
                    session_summaries.append(
                        {
                            "session_id": str(session.session_id),
                            "name": session.session_name,
                            "metrics": metrics_result.value,
                        }
                    )

            # Find best performing
            best_session = (
                max(
                    session_summaries,
                    key=lambda s: s["metrics"].get("engagement_score", 0),
                )
                if session_summaries
                else None
            )

            result = {
                "compared_sessions": len(sessions),
                "summaries": session_summaries,
                "best_performing": best_session,
                "average_engagement": sum(
                    s["metrics"].get("engagement_score", 0) for s in session_summaries
                )
                / len(session_summaries)
                if session_summaries
                else 0,
            }

            return Ok(result)
        except Exception as e:
            return Err(
                InteractionError(
                    message=f"Failed to compare sessions: {e!s}",
                    recoverable=True,
                )
            )

    def calculate_efficiency_metrics(
        self,
        sessions: List[NegotiationSession],
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Calculate efficiency metrics for sessions.

        Args:
            sessions: List of sessions

        Returns:
            Result containing efficiency metrics or error
        """
        if not sessions:
            return Err(
                ValidationError(
                    message="At least one session required",
                    field="sessions",
                    recoverable=True,
                )
            )

        try:
            # Calculate metrics
            total_duration = 0.0
            total_responses = 0
            completed_count = 0

            for session in sessions:
                if session.status.actual_completion_at:
                    duration = (
                        session.status.actual_completion_at - session.created_at
                    ).total_seconds()
                    total_duration += duration
                    completed_count += 1

                total_responses += sum(len(r) for r in session.responses.values())

            avg_duration = (
                total_duration / completed_count if completed_count > 0 else 0
            )

            # Calculate efficiency score
            # Based on: completion rate, response rate, and duration efficiency
            completion_rate = completed_count / len(sessions)

            result = {
                "total_sessions": len(sessions),
                "completed_count": completed_count,
                "completion_rate": completion_rate,
                "average_duration_seconds": avg_duration,
                "total_responses": total_responses,
                "average_responses_per_session": total_responses / len(sessions),
                "efficiency_score": completion_rate * 100,  # Simplified
            }

            return Ok(result)
        except Exception as e:
            return Err(
                InteractionError(
                    message=f"Failed to calculate efficiency: {e!s}",
                    recoverable=True,
                )
            )

    def _calculate_engagement(self, session: NegotiationSession) -> float:
        """Calculate engagement score for a session."""
        if not session.parties:
            return 0.0

        # Factor 1: Response participation
        participating_parties = sum(
            1 for party_id in session.parties if session.responses.get(party_id)
        )
        participation_rate = participating_parties / len(session.parties)

        # Factor 2: Proposal activity
        proposal_rate = min(1.0, len(session.active_proposals) / 3)

        # Combined score
        return participation_rate * 60 + proposal_rate * 40

    def _determine_trend(self, sessions: List[NegotiationSession]) -> str:
        """Determine overall trend direction."""
        if len(sessions) < 3:
            return "insufficient_data"

        # Simple trend based on completion rate in recent vs older sessions
        mid = len(sessions) // 2
        older = sessions[:mid]
        newer = sessions[mid:]

        older_completed = (
            sum(1 for s in older if not s.is_active) / len(older) if older else 0
        )
        newer_completed = (
            sum(1 for s in newer if not s.is_active) / len(newer) if newer else 0
        )

        if newer_completed > older_completed + 0.1:
            return "improving"
        elif newer_completed < older_completed - 0.1:
            return "declining"
        else:
            return "stable"
