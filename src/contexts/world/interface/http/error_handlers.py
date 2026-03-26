"""HTTP Error Handlers for World Context."""

from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status

from src.contexts.world.application.exceptions import (
    InvalidWorldStateError,
    PropagationError,
    RumorNotFoundError,
    WorldError,
    WorldStateAlreadyExistsError,
    WorldStateNotFoundError,
    WorldValidationError,
)
from src.shared.interface.http.error_handlers import (
    BaseErrorConverter,
)
from src.shared.interface.http.error_handlers import (
    ResultErrorHandler as BaseResultErrorHandler,
)
from src.shared.interface.http.error_handlers import (
    handle_result_error as base_handle_result_error,
)

F = TypeVar("F", bound=Callable[..., Any])


class ResultErrorHandler(BaseResultErrorHandler):
    """World-specific result error handler."""
    pass


class ErrorConverter(BaseErrorConverter):
    """Convert WorldError exceptions to HTTPException."""

    @staticmethod
    def convert(error: Exception) -> HTTPException:
        """Convert WorldError to HTTPException."""
        if isinstance(error, WorldStateNotFoundError):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World state not found")
        elif isinstance(error, WorldStateAlreadyExistsError):
            return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="World state already exists")
        elif isinstance(error, RumorNotFoundError):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rumor not found")
        elif isinstance(error, (WorldValidationError, InvalidWorldStateError)):
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
        elif isinstance(error, PropagationError):
            return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rumor propagation failed")
        elif isinstance(error, WorldError):
            return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))

        return BaseErrorConverter.convert(error)


def handle_world_errors(func: F) -> F:
    """World error handling decorator."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except WorldError as e:
            raise ErrorConverter.convert(e) from e
        except Exception:
            raise

    return wrapper  # type: ignore


def handle_result_error(operation: str | None = None) -> Callable[[F], F]:
    """Result error handling decorator with operation name."""
    return base_handle_result_error(operation)
