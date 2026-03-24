"""
Knowledge Application Exceptions

应用层异常定义，用于区分不同类型的业务错误。
这些异常会被 Router 层捕获并转换为适当的 HTTPException。
"""

from typing import Any, Dict, Optional


class KnowledgeError(Exception):
    """Knowledge 应用层基异常

    所有 Knowledge 相关异常的基类。
    """

    def __init__(
        self,
        message: str,
        code: str = "KNOWLEDGE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class KnowledgeValidationError(KnowledgeError):
    """知识库验证错误

    当输入数据验证失败时抛出。
    对应 HTTP 400 Bad Request。
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class KnowledgeBaseNotFoundError(KnowledgeError):
    """知识库未找到错误

    当请求的知识库不存在时抛出。
    对应 HTTP 404 Not Found。
    """

    def __init__(
        self,
        knowledge_base_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Knowledge base with ID '{knowledge_base_id}' not found",
            code="NOT_FOUND",
            details=details or {"knowledge_base_id": knowledge_base_id},
        )
        self.knowledge_base_id = knowledge_base_id


class KnowledgeBaseAlreadyExistsError(KnowledgeError):
    """知识库已存在错误

    当创建已存在的知识库时抛出。
    对应 HTTP 409 Conflict。
    """

    def __init__(self, name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Knowledge base with name '{name}' already exists",
            code="ALREADY_EXISTS",
            details=details or {"name": name},
        )
        self.name = name


class DocumentNotFoundError(KnowledgeError):
    """文档未找到错误

    当请求的文档不存在时抛出。
    对应 HTTP 404 Not Found。
    """

    def __init__(
        self,
        document_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Document with ID '{document_id}' not found",
            code="NOT_FOUND",
            details=details or {"document_id": document_id},
        )
        self.document_id = document_id


class InvalidDocumentError(KnowledgeError):
    """无效文档错误

    当文档数据无效时抛出。
    对应 HTTP 400 Bad Request。
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="INVALID_DOCUMENT", details=details)


class KnowledgeInternalError(KnowledgeError):
    """Knowledge 内部错误

    当发生未预期的内部错误时抛出。
    对应 HTTP 500 Internal Server Error。
    """

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="INTERNAL_ERROR", details=details)
