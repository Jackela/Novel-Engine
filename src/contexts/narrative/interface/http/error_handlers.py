"""Error handlers for narrative HTTP interface."""

from functools import wraps
from typing import Callable, Optional, TypeVar

from fastapi import HTTPException, status

from src.contexts.narrative.application.exceptions import (
    ChapterNotFoundError,
    InvalidStoryStateError,
    NarrativeError,
    NarrativeValidationError,
    SceneNotFoundError,
    StoryAlreadyExistsError,
    StoryNotFoundError,
)
from src.shared.application.result import Result

F = TypeVar("F", bound=Callable)

ERROR_CODE_TO_HTTP_STATUS = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "INVALID_STATE": status.HTTP_400_BAD_REQUEST,
}


class ResultErrorHandler:
    """Handle Result errors and convert to HTTPException."""

    @staticmethod
    def handle(result: Result, operation: Optional[str] = None):
        """Handle result error or return value."""
        if result.is_error:
            error_code = (
                result.error.code if hasattr(result.error, "code") else "UNKNOWN"
            )
            status_code = ERROR_CODE_TO_HTTP_STATUS.get(
                error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            raise HTTPException(status_code=status_code, detail=str(result.error))
        return result.value


class ErrorConverter:
    """Convert narrative errors to HTTP exceptions."""

    @staticmethod
    def convert(error: NarrativeError) -> HTTPException:
        """Convert narrative error to HTTP exception."""
        if isinstance(error, StoryNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
            )
        elif isinstance(error, ChapterNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
            )
        elif isinstance(error, SceneNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
            )
        elif isinstance(error, StoryAlreadyExistsError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(error)
            )
        elif isinstance(error, (NarrativeValidationError, InvalidStoryStateError)):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
            )
        else:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
            )


def handle_narrative_errors(operation: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to handle narrative errors and convert to HTTPException."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (
                StoryNotFoundError,
                ChapterNotFoundError,
                SceneNotFoundError,
            ) as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                )
            except StoryAlreadyExistsError as e:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            except (NarrativeValidationError, InvalidStoryStateError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal error: {str(e)}",
                )

        return wrapper

    return decorator
