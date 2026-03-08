"""
Knowledge Domain Errors

Domain-specific error types for the knowledge context.
These errors represent failures that can occur during knowledge operations
like ingestion, retrieval, embedding, and processing.

Why separate error types:
    - Domain clarity: Each error type represents a specific failure mode
    - Type safety: Callers can match on specific error types
    - Observability: Error codes make it easy to track failure modes
    - Recovery: Different errors may need different recovery strategies

Constitution Compliance:
- Article II (Hexagonal): Domain errors are part of the domain layer
- Article V (SOLID): Each error type has a single responsibility
"""

from __future__ import annotations

from typing import Any

from src.core.result import Error


class KnowledgeError(Error):
    """Base error for all knowledge domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            recoverable=recoverable,
            details=details,
        )


class ValidationError(KnowledgeError):
    """Error raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if field:
            full_details["field"] = field
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class ProcessingError(KnowledgeError):
    """Error raised when document processing fails."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if source_id:
            full_details["source_id"] = source_id
        super().__init__(
            code="PROCESSING_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class NotFoundError(KnowledgeError):
    """Error raised when a requested knowledge entry is not found."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if source_id:
            full_details["source_id"] = source_id
        super().__init__(
            code="NOT_FOUND",
            message=message,
            recoverable=False,
            details=full_details,
        )


class ConfigurationError(KnowledgeError):
    """Error raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if config_key:
            full_details["config_key"] = config_key
        super().__init__(
            code="CONFIGURATION_ERROR",
            message=message,
            recoverable=False,
            details=full_details,
        )


class EmbeddingError(KnowledgeError):
    """Error raised when embedding generation fails."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if source_id:
            full_details["source_id"] = source_id
        super().__init__(
            code="EMBEDDING_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class RetrievalError(KnowledgeError):
    """Error raised when knowledge retrieval fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if query:
            full_details["query"] = query
        super().__init__(
            code="RETRIEVAL_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class VectorStoreError(KnowledgeError):
    """Error raised when vector store operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if operation:
            full_details["operation"] = operation
        super().__init__(
            code="VECTOR_STORE_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class IngestionError(KnowledgeError):
    """Error raised when knowledge ingestion fails."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        source_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if source_id:
            full_details["source_id"] = source_id
        if source_type:
            full_details["source_type"] = source_type
        super().__init__(
            code="INGESTION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class ExtractionError(KnowledgeError):
    """Error raised when entity extraction fails."""

    def __init__(
        self,
        message: str,
        text_length: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if text_length is not None:
            full_details["text_length"] = text_length
        super().__init__(
            code="EXTRACTION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class OptimizationError(KnowledgeError):
    """Error raised when context optimization fails."""

    def __init__(
        self,
        message: str,
        chunk_count: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if chunk_count is not None:
            full_details["chunk_count"] = chunk_count
        super().__init__(
            code="OPTIMIZATION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class BM25Error(KnowledgeError):
    """Error raised when BM25 operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if operation:
            full_details["operation"] = operation
        super().__init__(
            code="BM25_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class RerankError(KnowledgeError):
    """Error raised when reranking fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if query:
            full_details["query"] = query
        super().__init__(
            code="RERANK_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


__all__ = [
    "KnowledgeError",
    "ValidationError",
    "ProcessingError",
    "NotFoundError",
    "ConfigurationError",
    "EmbeddingError",
    "RetrievalError",
    "VectorStoreError",
    "IngestionError",
    "ExtractionError",
    "OptimizationError",
    "BM25Error",
    "RerankError",
]
