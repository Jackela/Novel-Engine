"""HTTP Error Handlers for Knowledge Context."""

from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status

from src.contexts.knowledge.application.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentError,
    KnowledgeBaseAlreadyExistsError,
    KnowledgeBaseNotFoundError,
    KnowledgeError,
    KnowledgeValidationError,
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
    """Knowledge-specific result error handler."""

    pass


class ErrorConverter(BaseErrorConverter):
    """Convert KnowledgeError exceptions to HTTPException."""

    @staticmethod
    def convert(error: Exception) -> HTTPException:
        """Convert KnowledgeError to HTTPException."""
        if isinstance(error, KnowledgeBaseNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )
        elif isinstance(error, KnowledgeBaseAlreadyExistsError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Knowledge base already exists",
            )
        elif isinstance(error, DocumentNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
        elif isinstance(error, InvalidDocumentError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document"
            )
        elif isinstance(error, KnowledgeValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
            )
        elif isinstance(error, KnowledgeError):
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
            )

        return BaseErrorConverter.convert(error)


def handle_knowledge_errors(func: F) -> F:
    """Knowledge error handling decorator."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except KnowledgeError as e:
            raise ErrorConverter.convert(e) from e
        except Exception:
            raise

    return wrapper  # type: ignore


def handle_result_error(operation: str | None = None) -> Callable[[F], F]:
    """Result error handling decorator with operation name."""
    return base_handle_result_error(operation)
