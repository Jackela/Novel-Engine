#!/usr/bin/env python3
"""
Interaction Context Error Types

Domain-specific errors for the interactions bounded context.
These extend the core Error class with interaction-specific error codes.
"""

from typing import Any

from ......core.result import Error


class InteractionError(Error):
    """Base error for interaction context operations."""

    def __init__(
        self,
        message: str,
        code: str = "INTERACTION_ERROR",
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            recoverable=recoverable,
            details=details,
        )


class NegotiationError(InteractionError):
    """Error during negotiation operations."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if session_id:
            full_details["session_id"] = session_id
        super().__init__(
            message=message,
            code="NEGOTIATION_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class ProposalError(InteractionError):
    """Error during proposal operations."""

    def __init__(
        self,
        message: str,
        proposal_id: str | None = None,
        session_id: str | None = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if proposal_id:
            full_details["proposal_id"] = proposal_id
        if session_id:
            full_details["session_id"] = session_id
        super().__init__(
            message=message,
            code="PROPOSAL_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class OutcomeError(InteractionError):
    """Error during outcome calculation or processing."""

    def __init__(
        self,
        message: str,
        outcome_type: str | None = None,
        session_id: str | None = None,
        recoverable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if outcome_type:
            full_details["outcome_type"] = outcome_type
        if session_id:
            full_details["session_id"] = session_id
        super().__init__(
            message=message,
            code="OUTCOME_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class CompatibilityError(InteractionError):
    """Error during party compatibility assessment."""

    def __init__(
        self,
        message: str,
        party_ids: list[str] | None = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if party_ids:
            full_details["party_ids"] = party_ids
        super().__init__(
            message=message,
            code="COMPATIBILITY_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class ConflictError(InteractionError):
    """Error when conflicts are detected that prevent operation."""

    def __init__(
        self,
        message: str,
        conflict_type: str | None = None,
        severity: str = "medium",
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if conflict_type:
            full_details["conflict_type"] = conflict_type
        full_details["severity"] = severity
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class SessionError(InteractionError):
    """Error related to session state or lifecycle."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        session_status: str | None = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if session_id:
            full_details["session_id"] = session_id
        if session_status:
            full_details["session_status"] = session_status
        super().__init__(
            message=message,
            code="SESSION_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class ValidationError(InteractionError):
    """Error when validation fails for interaction operations."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        field_value: Any = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if field:
            full_details["field"] = field
        if field_value is not None:
            full_details["field_value"] = str(field_value)
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            recoverable=recoverable,
            details=full_details,
        )


class NotFoundError(InteractionError):
    """Error when a requested entity is not found."""

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        recoverable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if entity_type:
            full_details["entity_type"] = entity_type
        if entity_id:
            full_details["entity_id"] = entity_id
        super().__init__(
            message=message,
            code="NOT_FOUND",
            recoverable=recoverable,
            details=full_details,
        )


class AuthorizationError(InteractionError):
    """Error when a party lacks authorization for an operation."""

    def __init__(
        self,
        message: str,
        party_id: str | None = None,
        required_permission: str | None = None,
        recoverable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if party_id:
            full_details["party_id"] = party_id
        if required_permission:
            full_details["required_permission"] = required_permission
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            recoverable=recoverable,
            details=full_details,
        )
