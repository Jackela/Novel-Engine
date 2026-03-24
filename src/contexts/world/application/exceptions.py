"""World application layer exceptions."""

from typing import Any, Dict, Optional


class WorldError(Exception):
    """Base exception for world context."""

    def __init__(
        self,
        message: str,
        code: str = "WORLD_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class WorldStateNotFoundError(WorldError):
    """World state not found."""

    def __init__(self, world_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"World state with ID '{world_id}' not found",
            code="NOT_FOUND",
            details=details or {"world_id": world_id},
        )
        self.world_id = world_id


class WorldStateAlreadyExistsError(WorldError):
    """World state already exists."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="CONFLICT", details=details)


class RumorNotFoundError(WorldError):
    """Rumor not found."""

    def __init__(self, rumor_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Rumor with ID '{rumor_id}' not found",
            code="NOT_FOUND",
            details=details or {"rumor_id": rumor_id},
        )
        self.rumor_id = rumor_id


class WorldValidationError(WorldError):
    """Validation error for world."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class InvalidWorldStateError(WorldError):
    """Invalid world state."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="INVALID_STATE", details=details)


class PropagationError(WorldError):
    """Error during rumor propagation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="PROPAGATION_ERROR", details=details)


class WorldUnauthorizedError(WorldError):
    """Unauthorized access to world resource."""

    def __init__(
        self,
        message: str = "Unauthorized to perform this action",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="UNAUTHORIZED", details=details)


class WorldForbiddenError(WorldError):
    """Forbidden access to world resource."""

    def __init__(
        self,
        message: str = "Access to this resource is forbidden",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="FORBIDDEN", details=details)


class WorldInternalError(WorldError):
    """Internal error in world context."""

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="INTERNAL_ERROR", details=details)
