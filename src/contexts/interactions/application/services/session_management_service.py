#!/usr/bin/env python3
"""
Session Management Application Service

Application service for negotiation session lifecycle operations using Result pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from .....core.result import Err, Ok, Result
from ....interactions.domain.aggregates.negotiation_session import NegotiationSession
from ....interactions.domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from ....interactions.domain.value_objects.interaction_id import InteractionId
from ....interactions.domain.value_objects.negotiation_party import NegotiationParty
from ....interactions.domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    TerminationReason,
)
from .shared.errors import (
    NotFoundError,
    SessionError,
)


class SessionManagementService:
    """
    Service for negotiation session lifecycle management.

    Provides business operations for session creation, configuration,
    lifecycle management, and state transitions.
    """

    def __init__(self, session_repository: NegotiationSessionRepository) -> None:
        """Initialize with session repository."""
        self.session_repository = session_repository

    async def create_session(
        self,
        session_name: str,
        session_type: str,
        created_by: UUID,
        negotiation_domain: Optional[str] = None,
        max_parties: int = 10,
        session_timeout_hours: int = 72,
        session_context: Optional[Dict[str, Any]] = None,
        auto_advance_phases: bool = True,
        require_unanimous_agreement: bool = False,
        allow_partial_agreements: bool = True,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Create a new negotiation session.

        Args:
            session_name: Name of the session
            session_type: Type/category of session
            created_by: ID of user creating the session
            negotiation_domain: Optional domain context
            max_parties: Maximum number of parties allowed
            session_timeout_hours: Session timeout in hours
            session_context: Optional context dictionary
            auto_advance_phases: Whether to auto-advance phases
            require_unanimous_agreement: Whether unanimity is required
            allow_partial_agreements: Whether partial agreements are allowed

        Returns:
            Result containing created session info or error
        """
        # Validation
        if not session_name or not session_name.strip():
            return Err(
                SessionError(
                    message="Session name is required",
                    recoverable=True,
                )
            )

        if not session_type or not session_type.strip():
            return Err(
                SessionError(
                    message="Session type is required",
                    recoverable=True,
                )
            )

        if max_parties < 2:
            return Err(
                SessionError(
                    message=f"Maximum parties must be at least 2, got {max_parties}",
                    recoverable=True,
                )
            )

        if session_timeout_hours <= 0:
            return Err(
                SessionError(
                    message=f"Session timeout must be positive, got {session_timeout_hours}",
                    recoverable=True,
                )
            )

        try:
            session = NegotiationSession.create(
                session_name=session_name.strip(),
                session_type=session_type.strip(),
                created_by=created_by,
                negotiation_domain=negotiation_domain,
                max_parties=max_parties,
                session_timeout_hours=session_timeout_hours,
                session_context=session_context or {},
            )

            # Apply additional configuration
            session.auto_advance_phases = auto_advance_phases
            session.require_unanimous_agreement = require_unanimous_agreement
            session.allow_partial_agreements = allow_partial_agreements

            # Persist
            await self.session_repository.save(session)

            result = {
                "session_id": str(session.session_id),
                "session_name": session.session_name,
                "session_type": session.session_type,
                "created_at": session.created_at.isoformat(),
                "created_by": str(created_by),
                "status": session.status.phase.value,
                "configuration": {
                    "max_parties": session.max_parties,
                    "timeout_hours": session.session_timeout_hours,
                    "auto_advance_phases": session.auto_advance_phases,
                    "require_unanimous": session.require_unanimous_agreement,
                    "allow_partial": session.allow_partial_agreements,
                },
            }

            return Ok(result)
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Failed to create session: {e!s}",
                    recoverable=True,
                )
            )

    async def get_session(
        self, session_id: UUID
    ) -> Result[NegotiationSession, NotFoundError]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Result containing session or error
        """
        try:
            session = await self.session_repository.get_by_id(InteractionId(session_id))

            if session is None:
                return Err(
                    NotFoundError(
                        message=f"Session {session_id} not found",
                        entity_type="NegotiationSession",
                        entity_id=str(session_id),
                        recoverable=False,
                    )
                )

            return Ok(session)
        except Exception as e:
            return Err(
                NotFoundError(
                    message=f"Failed to retrieve session: {e!s}",
                    entity_type="NegotiationSession",
                    entity_id=str(session_id),
                    recoverable=True,
                )
            )

    async def add_party_to_session(
        self,
        session_id: UUID,
        party: NegotiationParty,
        added_by: UUID,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Add a party to an existing session.

        Args:
            session_id: Session identifier
            party: Party to add
            added_by: ID of user adding the party

        Returns:
            Result containing operation result or error
        """
        if party is None:
            return Err(
                SessionError(
                    message="Party is required",
                    recoverable=True,
                )
            )

        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        session = session_result.value
        if session is None:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        if not session.is_active:
            return Err(
                SessionError(
                    message="Cannot add party to inactive session",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )

        if len(session.parties) >= session.max_parties:
            return Err(
                SessionError(
                    message=f"Session at maximum capacity ({session.max_parties} parties)",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

        if party.party_id in session.parties:
            return Err(
                SessionError(
                    message=f"Party {party.party_id} already in session",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

        try:
            session.add_party(party)
            await self.session_repository.save(session)

            result = {
                "session_id": str(session_id),
                "party_id": str(party.party_id),
                "party_name": party.party_name,
                "total_parties": len(session.parties),
                "can_start": len(session.parties) >= 2,
            }

            return Ok(result)
        except ValueError as e:
            return Err(
                SessionError(
                    message=f"Failed to add party: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Unexpected error adding party: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

    async def remove_party_from_session(
        self,
        session_id: UUID,
        party_id: UUID,
        removed_by: UUID,
        reason: Optional[str] = None,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Remove a party from a session.

        Args:
            session_id: Session identifier
            party_id: Party to remove
            removed_by: ID of user removing the party
            reason: Optional removal reason

        Returns:
            Result containing operation result or error
        """
        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        session = session_result.value
        if session is None:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        if party_id not in session.parties:
            return Err(
                SessionError(
                    message=f"Party {party_id} not found in session",
                    recoverable=False,
                )
            )

        if len(session.parties) <= 2:
            return Err(
                SessionError(
                    message="Cannot remove party: minimum 2 parties required",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

        party = session.parties[party_id]

        try:
            session.remove_party(party_id, reason)
            await self.session_repository.save(session)

            result = {
                "session_id": str(session_id),
                "removed_party_id": str(party_id),
                "removed_party_name": party.party_name,
                "remaining_parties": len(session.parties),
                "reason": reason,
            }

            return Ok(result)
        except ValueError as e:
            return Err(
                SessionError(
                    message=f"Failed to remove party: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Unexpected error removing party: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

    async def advance_session_phase(
        self,
        session_id: UUID,
        target_phase: NegotiationPhase,
        advanced_by: UUID,
        force: bool = False,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Advance session to a new phase.

        Args:
            session_id: Session identifier
            target_phase: Phase to advance to
            advanced_by: ID of user advancing the phase
            force: Whether to force advancement

        Returns:
            Result containing operation result or error
        """
        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        session = session_result.value
        if session is None:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        if not session.is_active:
            return Err(
                SessionError(
                    message="Cannot advance phase of inactive session",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )

        if session.status.phase == target_phase:
            return Err(
                SessionError(
                    message=f"Session is already in {target_phase.value} phase",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )

        try:
            old_phase = session.status.phase
            session.advance_phase(target_phase, forced=force)
            await self.session_repository.save(session)

            result = {
                "session_id": str(session_id),
                "from_phase": old_phase.value,
                "to_phase": target_phase.value,
                "forced": force,
                "current_phase": session.status.phase.value,
            }

            return Ok(result)
        except ValueError as e:
            return Err(
                SessionError(
                    message=f"Failed to advance phase: {e!s}",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Unexpected error advancing phase: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

    async def terminate_session(
        self,
        session_id: UUID,
        outcome: NegotiationOutcome,
        termination_reason: TerminationReason,
        terminated_by: UUID,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Terminate a negotiation session.

        Args:
            session_id: Session identifier
            outcome: Negotiation outcome
            termination_reason: Reason for termination
            terminated_by: ID of user terminating

        Returns:
            Result containing operation result or error
        """
        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        session = session_result.value
        if session is None:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        if not session.is_active:
            return Err(
                SessionError(
                    message="Session is already inactive",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )

        if terminated_by not in session.parties:
            return Err(
                SessionError(
                    message="Only session participants can terminate",
                    recoverable=False,
                )
            )

        try:
            session.terminate_negotiation(outcome, termination_reason, terminated_by)
            await self.session_repository.save(session)

            result = {
                "session_id": str(session_id),
                "outcome": outcome.value,
                "termination_reason": termination_reason.value,
                "terminated_at": datetime.now(timezone.utc).isoformat(),
                "terminated_by": str(terminated_by),
            }

            return Ok(result)
        except ValueError as e:
            return Err(
                SessionError(
                    message=f"Failed to terminate session: {e!s}",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Unexpected error terminating session: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

    async def update_session_configuration(
        self,
        session_id: UUID,
        updated_by: UUID,
        max_parties: Optional[int] = None,
        session_timeout_hours: Optional[int] = None,
        auto_advance_phases: Optional[bool] = None,
        require_unanimous_agreement: Optional[bool] = None,
        allow_partial_agreements: Optional[bool] = None,
    ) -> Result[Dict[str, Any], SessionError]:
        """
        Update session configuration.

        Args:
            session_id: Session identifier
            updated_by: ID of user updating
            max_parties: New maximum parties
            session_timeout_hours: New timeout
            auto_advance_phases: New auto-advance setting
            require_unanimous_agreement: New unanimity setting
            allow_partial_agreements: New partial agreement setting

        Returns:
            Result containing operation result or error
        """
        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        session = session_result.value
        if session is None:
            return Err(
                SessionError(
                    message=f"Session {session_id} not found",
                    session_id=str(session_id),
                    recoverable=False,
                )
            )

        if not session.is_active:
            return Err(
                SessionError(
                    message="Cannot configure inactive session",
                    session_id=str(session_id),
                    session_status=session.status.phase.value,
                    recoverable=True,
                )
            )

        # Validate inputs
        if max_parties is not None and max_parties < len(session.parties):
            return Err(
                SessionError(
                    message=f"Cannot set max_parties below current party count ({len(session.parties)})",
                    recoverable=True,
                )
            )

        try:
            updates_made: List[str] = []

            if max_parties is not None:
                session.max_parties = max_parties
                updates_made.append("max_parties")

            if session_timeout_hours is not None:
                session.session_timeout_hours = session_timeout_hours
                updates_made.append("session_timeout_hours")

            if auto_advance_phases is not None:
                session.auto_advance_phases = auto_advance_phases
                updates_made.append("auto_advance_phases")

            if require_unanimous_agreement is not None:
                session.require_unanimous_agreement = require_unanimous_agreement
                updates_made.append("require_unanimous_agreement")

            if allow_partial_agreements is not None:
                session.allow_partial_agreements = allow_partial_agreements
                updates_made.append("allow_partial_agreements")

            await self.session_repository.save(session)

            result = {
                "session_id": str(session_id),
                "updates_made": updates_made,
                "current_config": {
                    "max_parties": session.max_parties,
                    "session_timeout_hours": session.session_timeout_hours,
                    "auto_advance_phases": session.auto_advance_phases,
                    "require_unanimous_agreement": session.require_unanimous_agreement,
                    "allow_partial_agreements": session.allow_partial_agreements,
                },
            }

            return Ok(result)
        except Exception as e:
            return Err(
                SessionError(
                    message=f"Failed to update configuration: {e!s}",
                    session_id=str(session_id),
                    recoverable=True,
                )
            )

    async def get_session_summary(
        self, session_id: UUID
    ) -> Result[Dict[str, Any], NotFoundError]:
        """
        Get comprehensive session summary.

        Args:
            session_id: Session identifier

        Returns:
            Result containing session summary or error
        """
        session_result = await self.get_session(session_id)
        if session_result.is_error:
            return session_result  # type: ignore

        session = session_result.value
        if session is None:
            return Err(
                NotFoundError(
                    message=f"Session {session_id} not found",
                    entity_type="NegotiationSession",
                    entity_id=str(session_id),
                    recoverable=False,
                )
            )

        summary = session.get_session_summary()
        return Ok(summary)
