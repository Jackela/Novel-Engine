#!/usr/bin/env python3
"""
Storage Type Definitions
========================

Type definitions and protocols for storage operations in Novel Engine.
Provides type-safe interfaces for S3 operations, metrics, and storage protocols.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    TypedDict,
    Union,
)

from typing_extensions import NotRequired

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client
else:
    S3Client = Any


# Metrics Type Safety
class StorageMetrics(TypedDict):
    """Type-safe storage metrics structure."""

    uploads: int
    downloads: int
    bytes_uploaded: int
    bytes_downloaded: int
    cache_hits: int
    cache_misses: int
    errors: int
    avg_upload_time: float
    avg_download_time: float
    upload_times: List[float]
    download_times: List[float]


@dataclass
class S3ObjectInfo:
    """S3 object information with proper typing."""

    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: str
    storage_class: str
    metadata: Dict[str, str] = field(default_factory=dict)
    version_id: Optional[str] = None


@dataclass
class UploadProgress:
    """Upload progress tracking with type safety."""

    bytes_transferred: int = 0
    total_bytes: int = 0
    percentage: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def transfer_rate(self) -> float:
        """Get transfer rate in bytes/second."""
        elapsed = self.elapsed_seconds
        return self.bytes_transferred / elapsed if elapsed > 0 else 0.0


# Progress Callback Protocol
class ProgressCallback(Protocol):
    """Protocol for upload/download progress callbacks."""

    def __call__(self, progress: UploadProgress) -> None:
        """Called with progress updates."""
        ...


# Storage Client Protocol
class StorageClient(Protocol):
    """Protocol defining storage client operations."""

    async def head_bucket(self, *, Bucket: str) -> Dict[str, Any]:
        """Check if bucket exists."""
        ...

    async def create_bucket(
        self,
        *,
        Bucket: str,
        CreateBucketConfiguration: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create storage bucket."""
        ...

    async def put_bucket_versioning(
        self, *, Bucket: str, VersioningConfiguration: Dict[str, str]
    ) -> Dict[str, Any]:
        """Configure bucket versioning."""
        ...

    async def put_bucket_encryption(
        self, *, Bucket: str, ServerSideEncryptionConfiguration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure bucket encryption."""
        ...

    async def upload_fileobj(
        self,
        fileobj: Any,
        bucket: str,
        key: str,
        *,
        ExtraArgs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Upload file object to storage."""
        ...

    async def put_object(
        self, *, Bucket: str, Key: str, Body: bytes, **kwargs: Any
    ) -> Dict[str, Any]:
        """Put object in storage."""
        ...

    async def head_object(self, *, Bucket: str, Key: str) -> Dict[str, Any]:
        """Get object metadata."""
        ...

    async def get_object(self, *, Bucket: str, Key: str) -> Dict[str, Any]:
        """Get object from storage."""
        ...

    async def delete_object(
        self, *, Bucket: str, Key: str, VersionId: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete object from storage."""
        ...

    async def list_objects_v2(
        self,
        *,
        Bucket: str,
        MaxKeys: Optional[int] = None,
        Prefix: Optional[str] = None,
        ContinuationToken: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List objects in storage."""
        ...

    async def close(self) -> None:
        """Close storage client connection."""
        ...


# Storage Manager Protocol
class StorageManager(Protocol):
    """Protocol defining high-level storage operations."""

    async def initialize(self) -> None:
        """Initialize storage connection."""
        ...

    async def upload_file(
        self,
        local_path: Union[str, Path],
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> S3ObjectInfo:
        """Upload file to storage."""
        ...

    async def upload_bytes(
        self,
        content: bytes,
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> S3ObjectInfo:
        """Upload bytes to storage."""
        ...

    async def download_file(
        self,
        s3_key: str,
        local_path: Union[str, Path],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """Download file from storage."""
        ...

    async def download_bytes(
        self, s3_key: str, use_cache: bool = True
    ) -> bytes:
        """Download bytes from storage."""
        ...

    async def delete_object(
        self, s3_key: str, version_id: Optional[str] = None
    ) -> bool:
        """Delete object from storage."""
        ...

    async def object_exists(self, s3_key: str) -> bool:
        """Check if object exists."""
        ...

    async def get_object_info(self, s3_key: str) -> Optional[S3ObjectInfo]:
        """Get object metadata."""
        ...

    def get_metrics(self) -> StorageMetrics:
        """Get storage metrics."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        ...

    async def close(self) -> None:
        """Close storage connections."""
        ...


# Type Guards for S3Client
def ensure_s3_client(client: Optional[StorageClient]) -> StorageClient:
    """Type guard to ensure S3 client is initialized."""
    if client is None:
        raise RuntimeError("S3 client not initialized")
    return client


# Metrics Management
class MetricsManager:
    """Type-safe metrics management for storage operations."""

    def __init__(self) -> None:
        self._metrics: StorageMetrics = {
            "uploads": 0,
            "downloads": 0,
            "bytes_uploaded": 0,
            "bytes_downloaded": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "avg_upload_time": 0.0,
            "avg_download_time": 0.0,
            "upload_times": [],
            "download_times": [],
        }

    def increment_uploads(self, bytes_count: int) -> None:
        """Increment upload metrics."""
        self._metrics["uploads"] += 1
        self._metrics["bytes_uploaded"] += bytes_count

    def increment_downloads(self, bytes_count: int) -> None:
        """Increment download metrics."""
        self._metrics["downloads"] += 1
        self._metrics["bytes_downloaded"] += bytes_count

    def increment_cache_hits(self) -> None:
        """Increment cache hit count."""
        self._metrics["cache_hits"] += 1

    def increment_cache_misses(self) -> None:
        """Increment cache miss count."""
        self._metrics["cache_misses"] += 1

    def increment_errors(self) -> None:
        """Increment error count."""
        self._metrics["errors"] += 1

    def add_upload_time(self, duration: float) -> None:
        """Add upload time and update averages."""
        self._metrics["upload_times"].append(duration)

        # Keep only last 100 measurements
        if len(self._metrics["upload_times"]) > 100:
            self._metrics["upload_times"] = self._metrics["upload_times"][
                -100:
            ]

        # Update average
        if self._metrics["upload_times"]:
            self._metrics["avg_upload_time"] = sum(
                self._metrics["upload_times"]
            ) / len(self._metrics["upload_times"])

    def add_download_time(self, duration: float) -> None:
        """Add download time and update averages."""
        self._metrics["download_times"].append(duration)

        # Keep only last 100 measurements
        if len(self._metrics["download_times"]) > 100:
            self._metrics["download_times"] = self._metrics["download_times"][
                -100:
            ]

        # Update average
        if self._metrics["download_times"]:
            self._metrics["avg_download_time"] = sum(
                self._metrics["download_times"]
            ) / len(self._metrics["download_times"])

    def get_metrics(self) -> StorageMetrics:
        """Get current metrics snapshot."""
        return self._metrics.copy()

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_cache_operations = (
            self._metrics["cache_hits"] + self._metrics["cache_misses"]
        )
        if total_cache_operations == 0:
            return 0.0
        return self._metrics["cache_hits"] / total_cache_operations

    def get_max_upload_time(self) -> float:
        """Get maximum upload time."""
        return (
            max(self._metrics["upload_times"])
            if self._metrics["upload_times"]
            else 0.0
        )

    def get_max_download_time(self) -> float:
        """Get maximum download time."""
        return (
            max(self._metrics["download_times"])
            if self._metrics["download_times"]
            else 0.0
        )


__all__ = [
    "StorageMetrics",
    "S3ObjectInfo",
    "UploadProgress",
    "ProgressCallback",
    "StorageClient",
    "StorageManager",
    "ensure_s3_client",
    "MetricsManager",
]
