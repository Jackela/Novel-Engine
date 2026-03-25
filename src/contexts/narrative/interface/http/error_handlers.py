"""HTTP Error Handlers for Narrative Context."""

from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status

from src.contexts.narrative.application.exceptions import (
    ChapterNotFoundError,
    InvalidStoryStateError,
    NarrativeError,
    NarrativeValidationError,
    SceneGenerationError,
    SceneNotFoundError,
    StoryAlreadyExistsError,
    StoryNotFoundError,
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
    """Narrative-specific result error handler."""
    pass


class ErrorConverter(BaseErrorConverter):
    """Convert NarrativeError exceptions to HTTPException."""

    @staticmethod
    def convert(error: Exception) -> HTTPException:
        """Convert NarrativeError to HTTPException."""
        if isinstance(error, StoryNotFoundError):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
        elif isinstance(error, StoryAlreadyExistsError):
            return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Story already exists")
        elif isinstance(error, ChapterNotFoundError):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
        elif isinstance(error, SceneNotFoundError):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
        elif isinstance(error, (NarrativeValidationError, InvalidStoryStateError)):
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
        elif isinstance(error, SceneGenerationError):
            return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scene generation failed")
        elif isinstance(error, NarrativeError):
            return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))

        return BaseErrorConverter.convert(error)


def handle_narrative_errors(func: F) -> F:
    """Narrative error handling decorator."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except NarrativeError as e:
            raise ErrorConverter.convert(e) from e
        except Exception:
            raise

    return wrapper  # type: ignore


def handle_result_error(operation: str | None = None) -> Callable[[F], F]:
    """Result error handling decorator with operation name."""
    return base_handle_result_error(operation)
