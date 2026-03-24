"""
HTTP Error Handlers for Knowledge Context

提供 Result 错误到 HTTPException 的转换，以及错误处理装饰器。
"""

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

from fastapi import HTTPException, status

# 类型变量定义
T = TypeVar("T")
"""泛型类型变量，用于成功返回值类型"""

from src.contexts.knowledge.application.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentError,
    KnowledgeBaseAlreadyExistsError,
    KnowledgeBaseNotFoundError,
    KnowledgeError,
    KnowledgeInternalError,
    KnowledgeValidationError,
)
from src.shared.application.result import Result

# 配置日志记录
logger = logging.getLogger(__name__)

# 错误代码到 HTTP 状态码的映射
ERROR_CODE_TO_HTTP_STATUS: Dict[str, int] = {
    # 客户端错误 (4xx)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "INVALID_DOCUMENT": status.HTTP_400_BAD_REQUEST,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "CONFLICT": status.HTTP_409_CONFLICT,
    # 服务端错误 (5xx)
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    # 默认
    "KNOWLEDGE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# 错误代码到默认消息的映射
ERROR_CODE_TO_MESSAGE: Dict[str, str] = {
    "VALIDATION_ERROR": "Validation failed",
    "INVALID_DOCUMENT": "Invalid document data",
    "BAD_REQUEST": "Bad request",
    "NOT_FOUND": "Resource not found",
    "ALREADY_EXISTS": "Resource already exists",
    "CONFLICT": "Conflict occurred",
    "INTERNAL_ERROR": "Internal server error",
    "KNOWLEDGE_ERROR": "An error occurred",
}

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


class ResultErrorHandler:
    """Result 错误处理器

    将 Result 类型的错误转换为 HTTPException。

    Usage:
        result = await service.create_knowledge_base(...)
        ResultErrorHandler.handle(result)  # 自动转换错误
        return result.value
    """

    @classmethod
    def handle(cls, result: Result[Any], operation: Optional[str] = None) -> None:
        """处理 Result 错误

        如果 result 包含错误，则抛出相应的 HTTPException。

        Args:
            result: 要处理的 Result 对象
            operation: 操作名称（用于日志记录）

        Raises:
            HTTPException: 当 result 包含错误时
        """
        if not result.is_error:
            return

        # result 是 Failure 类型
        failure = result  # type: ignore
        error_code = failure.code
        error_message = failure.error
        error_details = failure.details if hasattr(failure, "details") else None

        # 获取 HTTP 状态码
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # 获取默认消息（如果错误消息为空）
        detail = error_message or ERROR_CODE_TO_MESSAGE.get(
            error_code, "An error occurred"
        )

        # 记录日志
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

        # 抛出 HTTPException
        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"X-Error-Code": error_code} if error_details else None,
        )

    @classmethod
    def handle_or_return(cls, result: Result[T], operation: Optional[str] = None) -> T:
        """处理 Result 错误或返回值

        如果 result 包含错误，则抛出 HTTPException。
        否则返回 result 中的值。

        Args:
            result: 要处理的 Result 对象
            operation: 操作名称（用于日志记录）

        Returns:
            Result 中的值

        Raises:
            HTTPException: 当 result 包含错误时
        """
        cls.handle(result, operation)
        # 此时 result 一定是 Success
        return result.value  # type: ignore


class ErrorConverter:
    """错误转换器

    将 KnowledgeError 异常转换为 HTTPException。
    """

    @staticmethod
    def convert(error: KnowledgeError) -> HTTPException:
        """将 KnowledgeError 转换为 HTTPException

        Args:
            error: KnowledgeError 异常

        Returns:
            对应的 HTTPException
        """
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error.code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # 记录日志
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


def handle_knowledge_errors(func: F) -> F:
    """Knowledge 错误处理装饰器

    自动捕获 KnowledgeError 异常并转换为 HTTPException。
    推荐用于 Router 端点函数。

    Usage:
        @router.post("/")
        @handle_knowledge_errors
        async def create_knowledge_base(...):
            result = await service.create_knowledge_base(...)
            ResultErrorHandler.handle(result)
            return result.value
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except KnowledgeValidationError as e:
            logger.warning(f"Validation error: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
            ) from e
        except KnowledgeBaseNotFoundError as e:
            logger.warning(
                f"Not found: {e.message}",
                extra={
                    "code": e.code,
                    "knowledge_base_id": getattr(e, "knowledge_base_id", None),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.message
            ) from e
        except DocumentNotFoundError as e:
            logger.warning(
                f"Not found: {e.message}",
                extra={
                    "code": e.code,
                    "document_id": getattr(e, "document_id", None),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.message
            ) from e
        except KnowledgeBaseAlreadyExistsError as e:
            logger.warning(f"Already exists: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.message
            ) from e
        except InvalidDocumentError as e:
            logger.warning(f"Invalid document: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
            ) from e
        except KnowledgeInternalError as e:
            logger.error(
                f"Internal error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred",
            ) from e
        except KnowledgeError as e:
            # 其他 KnowledgeError
            logger.error(
                f"Knowledge error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
            ) from e

    return wrapper  # type: ignore


def handle_result_error(operation: Optional[str] = None) -> Callable[[F], F]:
    """Result 错误处理装饰器（带操作名称）

    自动处理 Result 类型的错误，将其转换为 HTTPException。

    Usage:
        @router.post("/")
        @handle_result_error("create_knowledge_base")
        async def create_knowledge_base(...):
            result = await service.create_knowledge_base(...)
            return ResultErrorHandler.handle_or_return(result, "create_knowledge_base")
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # 如果已经是 HTTPException，直接抛出
                raise
            except Exception as e:
                # 捕获其他异常
                op_str = f" in {operation}" if operation else ""
                logger.exception(f"Unexpected error{op_str}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred",
                ) from e

        return wrapper  # type: ignore

    return decorator
