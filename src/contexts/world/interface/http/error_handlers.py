"""HTTP Error Handlers for World Context.

提供 Result 错误到 HTTPException 的转换，以及错误处理装饰器。
"""

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

from fastapi import HTTPException, status

from src.contexts.world.application.exceptions import (
    InvalidWorldStateError,
    PropagationError,
    RumorNotFoundError,
    WorldError,
    WorldForbiddenError,
    WorldInternalError,
    WorldStateAlreadyExistsError,
    WorldStateNotFoundError,
    WorldUnauthorizedError,
    WorldValidationError,
)
from src.shared.application.result import Result

# 配置日志记录
logger = logging.getLogger(__name__)

# 错误代码到 HTTP 状态码的映射
ERROR_CODE_TO_HTTP_STATUS: Dict[str, int] = {
    # 客户端错误 (4xx)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "INVALID_STATE": status.HTTP_409_CONFLICT,
    "PROPAGATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "UNPROCESSABLE_ENTITY": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_REQUESTS": status.HTTP_429_TOO_MANY_REQUESTS,
    # 服务端错误 (5xx)
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "NOT_IMPLEMENTED": status.HTTP_501_NOT_IMPLEMENTED,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    # 默认
    "WORLD_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# 错误代码到默认消息的映射
ERROR_CODE_TO_MESSAGE: Dict[str, str] = {
    "VALIDATION_ERROR": "Validation failed",
    "BAD_REQUEST": "Bad request",
    "UNAUTHORIZED": "Unauthorized",
    "FORBIDDEN": "Forbidden",
    "NOT_FOUND": "Resource not found",
    "CONFLICT": "Conflict occurred",
    "INVALID_STATE": "Invalid state",
    "PROPAGATION_ERROR": "Propagation failed",
    "UNPROCESSABLE_ENTITY": "Unprocessable entity",
    "TOO_MANY_REQUESTS": "Too many requests",
    "INTERNAL_ERROR": "Internal server error",
    "NOT_IMPLEMENTED": "Not implemented",
    "SERVICE_UNAVAILABLE": "Service unavailable",
    "WORLD_ERROR": "An error occurred",
}

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


class ResultErrorHandler:
    """Result 错误处理器.

    将 Result 类型的错误转换为 HTTPException。
    """

    @classmethod
    def handle(cls, result: Result[Any], operation: Optional[str] = None) -> None:
        """处理 Result 错误.

        如果 result 包含错误，则抛出相应的 HTTPException。
        """
        if not result.is_error:
            return

        failure = result  # type: ignore
        error_code = failure.code
        error_message = failure.error
        error_details = failure.details if hasattr(failure, "details") else None

        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        detail = error_message or ERROR_CODE_TO_MESSAGE.get(
            error_code, "An error occurred"
        )

        operation_str = f" in {operation}" if operation else ""
        if status_code >= 500:
            logger.error(
                f"Server error{operation_str}: [{error_code}] {detail}",
                extra={"error_code": error_code, "details": error_details},
            )
        elif status_code >= 400:
            logger.warning(
                f"Client error{operation_str}: [{error_code}] {detail}",
                extra={"error_code": error_code, "details": error_details},
            )

        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"X-Error-Code": error_code} if error_details else None,
        )

    @classmethod
    def handle_or_return(cls, result: Result[T], operation: Optional[str] = None) -> T:
        """处理 Result 错误或返回值."""
        cls.handle(result, operation)
        return result.value  # type: ignore


class ErrorConverter:
    """错误转换器."""

    @staticmethod
    def convert(error: WorldError) -> HTTPException:
        """将 WorldError 转换为 HTTPException."""
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error.code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        if status_code >= 500:
            logger.error(
                f"Server error: [{error.code}] {error.message}",
                extra={"error_code": error.code, "details": error.details},
                exc_info=True,
            )
        else:
            logger.warning(
                f"Client error: [{error.code}] {error.message}",
                extra={"error_code": error.code, "details": error.details},
            )

        return HTTPException(
            status_code=status_code,
            detail=error.message,
            headers={"X-Error-Code": error.code} if error.details else None,
        )


def handle_world_errors(func: F) -> F:
    """World 错误处理装饰器."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except WorldValidationError as e:
            logger.warning(f"Validation error: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
            ) from e
        except WorldStateNotFoundError as e:
            logger.warning(
                f"Not found: {e.message}",
                extra={"code": e.code, "world_id": getattr(e, "world_id", None)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.message
            ) from e
        except RumorNotFoundError as e:
            logger.warning(
                f"Rumor not found: {e.message}",
                extra={"code": e.code, "rumor_id": getattr(e, "rumor_id", None)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.message
            ) from e
        except WorldStateAlreadyExistsError as e:
            logger.warning(f"Conflict: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.message
            ) from e
        except InvalidWorldStateError as e:
            logger.warning(f"Invalid state: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.message
            ) from e
        except PropagationError as e:
            logger.warning(f"Propagation error: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message
            ) from e
        except WorldUnauthorizedError as e:
            logger.warning(f"Unauthorized: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
            ) from e
        except WorldForbiddenError as e:
            logger.warning(f"Forbidden: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=e.message
            ) from e
        except WorldInternalError as e:
            logger.error(
                f"Internal error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred",
            ) from e
        except WorldError as e:
            logger.error(
                f"World error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
            ) from e

    return wrapper  # type: ignore


def handle_result_error(operation: Optional[str] = None) -> Callable[[F], F]:
    """Result 错误处理装饰器（带操作名称）."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                op_str = f" in {operation}" if operation else ""
                logger.exception(f"Unexpected error{op_str}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred",
                ) from e

        return wrapper  # type: ignore

    return decorator
