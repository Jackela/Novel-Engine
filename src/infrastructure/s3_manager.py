#!/usr/bin/env python3
"""
S3 Storage Manager
==================

Enterprise S3-compatible storage manager for file storage, asset management,
and large object storage in the Novel Engine framework.
"""

import hashlib
import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

import aioboto3
import aiofiles

logger = logging.getLogger(__name__)


class S3StorageClass(Enum):
    """S3 storage classes for different use cases."""

    STANDARD = "STANDARD"
    STANDARD_IA = "STANDARD_IA"
    ONEZONE_IA = "ONEZONE_IA"
    REDUCED_REDUNDANCY = "REDUCED_REDUNDANCY"
    GLACIER = "GLACIER"
    DEEP_ARCHIVE = "DEEP_ARCHIVE"
    INTELLIGENT_TIERING = "INTELLIGENT_TIERING"


class S3ContentType(Enum):
    """Common content types for Novel Engine assets."""

    JSON = "application/json"
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    IMAGE_PNG = "image/png"
    IMAGE_JPEG = "image/jpeg"
    IMAGE_GIF = "image/gif"
    AUDIO_MP3 = "audio/mpeg"
    AUDIO_WAV = "audio/wav"
    VIDEO_MP4 = "video/mp4"
    PDF = "application/pdf"
    ZIP = "application/zip"
    BINARY = "application/octet-stream"


@dataclass
class S3Config:
    """S3 configuration for Novel Engine storage."""

    # AWS/S3 settings
    access_key_id: str = ""
    secret_access_key: str = ""
    region_name: str = "us-east-1"
    endpoint_url: Optional[str] = None  # For S3-compatible services

    # Bucket settings
    bucket_name: str = "novel-engine-storage"
    create_bucket_if_not_exists: bool = True

    # Connection settings
    max_pool_connections: int = 50
    retries: Dict[str, Any] = field(
        default_factory=lambda: {"max_attempts": 3, "mode": "adaptive"}
    )
    connect_timeout: float = 60.0
    read_timeout: float = 60.0

    # Storage settings
    default_storage_class: S3StorageClass = S3StorageClass.STANDARD
    enable_versioning: bool = True
    enable_encryption: bool = True
    encryption_key_id: Optional[str] = None

    # Upload settings
    multipart_threshold: int = 8 * 1024 * 1024  # 8MB
    multipart_chunksize: int = 8 * 1024 * 1024  # 8MB
    max_bandwidth: Optional[int] = None  # bytes/second

    # Cache settings
    enable_local_cache: bool = True
    cache_directory: str = "cache/s3_cache"
    max_cache_size: int = 1024 * 1024 * 1024  # 1GB
    cache_ttl: int = 3600  # 1 hour

    # Monitoring
    enable_metrics: bool = True
    enable_logging: bool = True


@dataclass
class S3ObjectInfo:
    """S3 object information."""

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
    """Upload progress tracking."""

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


class S3StorageManager:
    """
    Enterprise S3 storage manager for Novel Engine.

    Features:
    - Multi-part upload support
    - Local caching with TTL
    - Content type detection
    - Storage class optimization
    - Encryption and versioning
    - Upload/download progress tracking
    - Metadata management
    """

    def __init__(self, config: S3Config):
        """Initialize S3 storage manager."""
        self.config = config
        self.session: Optional[aioboto3.Session] = None
        self.s3_client: Optional[Any] = None
        self._initialized = False

        # Cache management
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_directory = Path(config.cache_directory)

        # Metrics
        self._metrics = {
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

    async def initialize(self) -> None:
        """Initialize S3 connection and bucket."""
        if self._initialized:
            return

        try:
            # Create aioboto3 session
            self.session = aioboto3.Session(
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region_name,
            )

            # Create S3 client
            client_config = {
                "region_name": self.config.region_name,
                "config": aioboto3.session.Config(
                    max_pool_connections=self.config.max_pool_connections,
                    retries=self.config.retries,
                    connect_timeout=self.config.connect_timeout,
                    read_timeout=self.config.read_timeout,
                ),
            }

            if self.config.endpoint_url:
                client_config["endpoint_url"] = self.config.endpoint_url

            self.s3_client = self.session.client("s3", **client_config)

            # Ensure bucket exists
            if self.config.create_bucket_if_not_exists:
                await self._ensure_bucket_exists()

            # Setup local cache directory
            if self.config.enable_local_cache:
                self._cache_directory.mkdir(parents=True, exist_ok=True)

            self._initialized = True
            logger.info(
                f"S3 storage manager initialized: bucket={self.config.bucket_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize S3 storage manager: {e}")
            raise

    async def _ensure_bucket_exists(self) -> None:
        """Ensure S3 bucket exists and configure it."""
        try:
            # Check if bucket exists
            await self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            logger.debug(f"S3 bucket exists: {self.config.bucket_name}")

        except Exception:
            # Bucket doesn't exist, create it
            try:
                if self.config.region_name != "us-east-1":
                    await self.s3_client.create_bucket(
                        Bucket=self.config.bucket_name,
                        CreateBucketConfiguration={
                            "LocationConstraint": self.config.region_name
                        },
                    )
                else:
                    await self.s3_client.create_bucket(Bucket=self.config.bucket_name)

                logger.info(f"Created S3 bucket: {self.config.bucket_name}")

                # Configure bucket
                await self._configure_bucket()

            except Exception as e:
                logger.error(
                    f"Failed to create S3 bucket {self.config.bucket_name}: {e}"
                )
                raise

    async def _configure_bucket(self) -> None:
        """Configure bucket settings."""
        try:
            # Enable versioning if requested
            if self.config.enable_versioning:
                await self.s3_client.put_bucket_versioning(
                    Bucket=self.config.bucket_name,
                    VersioningConfiguration={"Status": "Enabled"},
                )
                logger.debug("Enabled S3 bucket versioning")

            # Configure encryption if requested
            if self.config.enable_encryption:
                encryption_config = {
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                }

                if self.config.encryption_key_id:
                    encryption_config["Rules"][0][
                        "ApplyServerSideEncryptionByDefault"
                    ] = {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyID": self.config.encryption_key_id,
                    }

                await self.s3_client.put_bucket_encryption(
                    Bucket=self.config.bucket_name,
                    ServerSideEncryptionConfiguration=encryption_config,
                )
                logger.debug("Enabled S3 bucket encryption")

        except Exception as e:
            logger.warning(f"Failed to configure S3 bucket: {e}")

    def _detect_content_type(self, file_path: Union[str, Path]) -> str:
        """Detect content type from file extension."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or S3ContentType.BINARY.value

    def _generate_cache_key(self, s3_key: str) -> str:
        """Generate cache key for local storage."""
        return hashlib.md5(s3_key.encode()).hexdigest()

    async def _get_from_cache(self, s3_key: str) -> Optional[bytes]:
        """Get object from local cache."""
        if not self.config.enable_local_cache:
            return None

        cache_key = self._generate_cache_key(s3_key)
        cache_file = self._cache_directory / cache_key

        try:
            if cache_file.exists():
                # Check cache TTL
                cache_info = self._local_cache.get(s3_key, {})
                cached_time = cache_info.get("timestamp", datetime.min)

                if (
                    datetime.now() - cached_time
                ).total_seconds() < self.config.cache_ttl:
                    async with aiofiles.open(cache_file, "rb") as f:
                        content = await f.read()

                    self._metrics["cache_hits"] += 1
                    return content
                else:
                    # Cache expired, remove it
                    cache_file.unlink()
                    if s3_key in self._local_cache:
                        del self._local_cache[s3_key]

        except Exception as e:
            logger.debug(f"Cache read failed for {s3_key}: {e}")

        self._metrics["cache_misses"] += 1
        return None

    async def _save_to_cache(self, s3_key: str, content: bytes) -> None:
        """Save object to local cache."""
        if not self.config.enable_local_cache:
            return

        try:
            # Check cache size limit
            current_cache_size = sum(
                f.stat().st_size for f in self._cache_directory.iterdir() if f.is_file()
            )

            if current_cache_size + len(content) > self.config.max_cache_size:
                # Cache eviction will be implemented based on usage patterns
                logger.debug("Cache size limit reached, skipping cache save")
                return

            cache_key = self._generate_cache_key(s3_key)
            cache_file = self._cache_directory / cache_key

            async with aiofiles.open(cache_file, "wb") as f:
                await f.write(content)

            # Update cache metadata
            self._local_cache[s3_key] = {
                "timestamp": datetime.now(),
                "size": len(content),
                "cache_file": str(cache_file),
            }

        except Exception as e:
            logger.debug(f"Cache save failed for {s3_key}: {e}")

    async def upload_file(
        self,
        local_path: Union[str, Path],
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: Optional[S3StorageClass] = None,
        progress_callback: Optional[callable] = None,
    ) -> S3ObjectInfo:
        """Upload file to S3 with progress tracking."""
        if not self._initialized:
            await self.initialize()

        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        start_time = datetime.now()

        try:
            # Detect content type if not provided
            if content_type is None:
                content_type = self._detect_content_type(local_path)

            # Prepare upload parameters
            extra_args = {
                "ContentType": content_type,
                "StorageClass": (
                    storage_class or self.config.default_storage_class
                ).value,
            }

            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            file_size = local_path.stat().st_size
            progress = UploadProgress(total_bytes=file_size)

            def progress_handler(bytes_transferred: int):
                progress.bytes_transferred = bytes_transferred
                progress.percentage = (
                    (bytes_transferred / file_size) * 100 if file_size > 0 else 0
                )

                if progress_callback:
                    progress_callback(progress)

            # Use multipart upload for large files
            if file_size > self.config.multipart_threshold:
                # Progress tracking for multipart uploads to be implemented
                async with aiofiles.open(local_path, "rb") as f:
                    await self.s3_client.upload_fileobj(
                        f,
                        self.config.bucket_name,
                        s3_key,
                        ExtraArgs=extra_args,
                        Callback=progress_handler,
                    )
            else:
                async with aiofiles.open(local_path, "rb") as f:
                    await self.s3_client.upload_fileobj(
                        f,
                        self.config.bucket_name,
                        s3_key,
                        ExtraArgs=extra_args,
                        Callback=progress_handler,
                    )

            # Get object info
            response = await self.s3_client.head_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            # Update metrics
            upload_time = (datetime.now() - start_time).total_seconds()
            self._metrics["uploads"] += 1
            self._metrics["bytes_uploaded"] += file_size
            self._metrics["upload_times"].append(upload_time)

            if len(self._metrics["upload_times"]) > 100:
                self._metrics["upload_times"] = self._metrics["upload_times"][-100:]

            if self._metrics["upload_times"]:
                self._metrics["avg_upload_time"] = sum(
                    self._metrics["upload_times"]
                ) / len(self._metrics["upload_times"])

            logger.info(
                f"Uploaded file to S3: {s3_key} ({file_size} bytes in {upload_time:.2f}s)"
            )

            return S3ObjectInfo(
                key=s3_key,
                size=response["ContentLength"],
                last_modified=response["LastModified"],
                etag=response["ETag"].strip('"'),
                content_type=response["ContentType"],
                storage_class=response.get("StorageClass", "STANDARD"),
                metadata=response.get("Metadata", {}),
                version_id=response.get("VersionId"),
            )

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to upload file {local_path} to S3 key {s3_key}: {e}")
            raise

    async def upload_bytes(
        self,
        content: bytes,
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: Optional[S3StorageClass] = None,
    ) -> S3ObjectInfo:
        """Upload bytes content to S3."""
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()

        try:
            # Prepare upload parameters
            extra_args = {
                "ContentType": content_type or S3ContentType.BINARY.value,
                "StorageClass": (
                    storage_class or self.config.default_storage_class
                ).value,
            }

            if metadata:
                extra_args["Metadata"] = metadata

            # Upload content
            await self.s3_client.put_object(
                Bucket=self.config.bucket_name, Key=s3_key, Body=content, **extra_args
            )

            # Get object info
            response = await self.s3_client.head_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            # Update metrics
            upload_time = (datetime.now() - start_time).total_seconds()
            self._metrics["uploads"] += 1
            self._metrics["bytes_uploaded"] += len(content)
            self._metrics["upload_times"].append(upload_time)

            logger.debug(f"Uploaded bytes to S3: {s3_key} ({len(content)} bytes)")

            return S3ObjectInfo(
                key=s3_key,
                size=response["ContentLength"],
                last_modified=response["LastModified"],
                etag=response["ETag"].strip('"'),
                content_type=response["ContentType"],
                storage_class=response.get("StorageClass", "STANDARD"),
                metadata=response.get("Metadata", {}),
                version_id=response.get("VersionId"),
            )

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to upload bytes to S3 key {s3_key}: {e}")
            raise

    async def download_file(
        self,
        s3_key: str,
        local_path: Union[str, Path],
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """Download file from S3 with progress tracking."""
        if not self._initialized:
            await self.initialize()

        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = datetime.now()

        try:
            # Get object info first
            response = await self.s3_client.head_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            file_size = response["ContentLength"]
            progress = UploadProgress(total_bytes=file_size)

            # Download file
            async with aiofiles.open(local_path, "wb") as f:
                response = await self.s3_client.get_object(
                    Bucket=self.config.bucket_name, Key=s3_key
                )

                async for chunk in response["Body"].iter_chunks(8192):
                    await f.write(chunk)
                    progress.bytes_transferred += len(chunk)
                    progress.percentage = (
                        (progress.bytes_transferred / file_size) * 100
                        if file_size > 0
                        else 0
                    )

                    if progress_callback:
                        progress_callback(progress)

            # Update metrics
            download_time = (datetime.now() - start_time).total_seconds()
            self._metrics["downloads"] += 1
            self._metrics["bytes_downloaded"] += file_size
            self._metrics["download_times"].append(download_time)

            if len(self._metrics["download_times"]) > 100:
                self._metrics["download_times"] = self._metrics["download_times"][-100:]

            if self._metrics["download_times"]:
                self._metrics["avg_download_time"] = sum(
                    self._metrics["download_times"]
                ) / len(self._metrics["download_times"])

            logger.info(
                f"Downloaded file from S3: {s3_key} to {local_path} ({file_size} bytes in {download_time:.2f}s)"
            )
            return True

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to download S3 key {s3_key} to {local_path}: {e}")
            raise

    async def download_bytes(self, s3_key: str, use_cache: bool = True) -> bytes:
        """Download object as bytes with caching."""
        if not self._initialized:
            await self.initialize()

        # Check cache first
        if use_cache:
            cached_content = await self._get_from_cache(s3_key)
            if cached_content is not None:
                return cached_content

        start_time = datetime.now()

        try:
            # Download from S3
            response = await self.s3_client.get_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            content = await response["Body"].read()

            # Cache the content
            if use_cache:
                await self._save_to_cache(s3_key, content)

            # Update metrics
            download_time = (datetime.now() - start_time).total_seconds()
            self._metrics["downloads"] += 1
            self._metrics["bytes_downloaded"] += len(content)
            self._metrics["download_times"].append(download_time)

            logger.debug(f"Downloaded bytes from S3: {s3_key} ({len(content)} bytes)")
            return content

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to download S3 key {s3_key}: {e}")
            raise

    async def delete_object(
        self, s3_key: str, version_id: Optional[str] = None
    ) -> bool:
        """Delete object from S3."""
        if not self._initialized:
            await self.initialize()

        try:
            delete_args = {"Bucket": self.config.bucket_name, "Key": s3_key}

            if version_id:
                delete_args["VersionId"] = version_id

            await self.s3_client.delete_object(**delete_args)

            # Remove from cache
            if s3_key in self._local_cache:
                cache_info = self._local_cache[s3_key]
                cache_file = Path(cache_info["cache_file"])
                if cache_file.exists():
                    cache_file.unlink()
                del self._local_cache[s3_key]

            logger.debug(f"Deleted S3 object: {s3_key}")
            return True

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to delete S3 key {s3_key}: {e}")
            raise

    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List objects with pagination."""
        if not self._initialized:
            await self.initialize()

        try:
            list_args = {"Bucket": self.config.bucket_name, "MaxKeys": max_keys}

            if prefix:
                list_args["Prefix"] = prefix

            if continuation_token:
                list_args["ContinuationToken"] = continuation_token

            response = await self.s3_client.list_objects_v2(**list_args)

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    S3ObjectInfo(
                        key=obj["Key"],
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        etag=obj["ETag"].strip('"'),
                        content_type="",  # Not available in list response
                        storage_class=obj.get("StorageClass", "STANDARD"),
                    )
                )

            return {
                "objects": objects,
                "is_truncated": response.get("IsTruncated", False),
                "next_continuation_token": response.get("NextContinuationToken"),
                "key_count": response.get("KeyCount", 0),
            }

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Failed to list S3 objects with prefix {prefix}: {e}")
            raise

    async def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in S3."""
        if not self._initialized:
            await self.initialize()

        try:
            await self.s3_client.head_object(Bucket=self.config.bucket_name, Key=s3_key)
            return True

        except Exception:
            return False

    async def get_object_info(self, s3_key: str) -> Optional[S3ObjectInfo]:
        """Get object metadata."""
        if not self._initialized:
            await self.initialize()

        try:
            response = await self.s3_client.head_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            return S3ObjectInfo(
                key=s3_key,
                size=response["ContentLength"],
                last_modified=response["LastModified"],
                etag=response["ETag"].strip('"'),
                content_type=response["ContentType"],
                storage_class=response.get("StorageClass", "STANDARD"),
                metadata=response.get("Metadata", {}),
                version_id=response.get("VersionId"),
            )

        except Exception as e:
            logger.debug(f"Failed to get S3 object info for {s3_key}: {e}")
            return None

    # Novel Engine specific operations

    async def store_character_asset(
        self,
        character_id: str,
        asset_type: str,
        content: bytes,
        filename: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Store character-related asset."""
        s3_key = f"characters/{character_id}/assets/{asset_type}/{filename}"

        asset_metadata = {
            "character_id": character_id,
            "asset_type": asset_type,
            "uploaded_at": datetime.now().isoformat(),
        }

        if metadata:
            asset_metadata.update(metadata)

        content_type = self._detect_content_type(filename)

        await self.upload_bytes(
            content=content,
            s3_key=s3_key,
            content_type=content_type,
            metadata=asset_metadata,
            storage_class=S3StorageClass.STANDARD,
        )

        return s3_key

    async def store_narrative_export(
        self,
        narrative_id: str,
        export_format: str,
        content: Union[str, bytes],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Store exported narrative content."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"narratives/{narrative_id}/exports/{export_format}/{timestamp}.{export_format}"

        export_metadata = {
            "narrative_id": narrative_id,
            "export_format": export_format,
            "exported_at": datetime.now().isoformat(),
        }

        if metadata:
            export_metadata.update(metadata)

        # Convert string to bytes if necessary
        if isinstance(content, str):
            content = content.encode("utf-8")

        await self.upload_bytes(
            content=content,
            s3_key=s3_key,
            content_type=(
                S3ContentType.TEXT.value
                if export_format in ["txt", "md"]
                else S3ContentType.JSON.value
            ),
            metadata=export_metadata,
            storage_class=S3StorageClass.STANDARD_IA,  # Infrequent access for exports
        )

        return s3_key

    async def store_backup(
        self, backup_type: str, backup_data: bytes, timestamp: Optional[datetime] = None
    ) -> str:
        """Store system backup."""
        if timestamp is None:
            timestamp = datetime.now()

        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        s3_key = f"backups/{backup_type}/{timestamp_str}.backup"

        backup_metadata = {
            "backup_type": backup_type,
            "created_at": timestamp.isoformat(),
            "system": "novel_engine",
        }

        await self.upload_bytes(
            content=backup_data,
            s3_key=s3_key,
            content_type=S3ContentType.BINARY.value,
            metadata=backup_metadata,
            storage_class=S3StorageClass.GLACIER,  # Long-term storage
        )

        return s3_key

    async def close(self) -> None:
        """Close S3 connections."""
        if self.s3_client:
            await self.s3_client.close()

        self._initialized = False
        logger.info("S3 storage manager closed")

    async def health_check(self) -> Dict[str, Any]:
        """Perform S3 health check."""
        try:
            # Test bucket access
            await self.s3_client.head_bucket(Bucket=self.config.bucket_name)

            # Get bucket statistics
            await self.list_objects(max_keys=1)

            return {
                "healthy": True,
                "bucket": self.config.bucket_name,
                "region": self.config.region_name,
                "endpoint": self.config.endpoint_url,
                "versioning_enabled": self.config.enable_versioning,
                "encryption_enabled": self.config.enable_encryption,
                "metrics": self._metrics,
                "cache_enabled": self.config.enable_local_cache,
                "cache_stats": {
                    "entries": len(self._local_cache),
                    "directory": str(self._cache_directory),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get S3 storage metrics."""
        upload_times = self._metrics["upload_times"]
        download_times = self._metrics["download_times"]

        return {
            "uploads": self._metrics["uploads"],
            "downloads": self._metrics["downloads"],
            "bytes_uploaded": self._metrics["bytes_uploaded"],
            "bytes_downloaded": self._metrics["bytes_downloaded"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "cache_hit_rate": (
                self._metrics["cache_hits"]
                / (self._metrics["cache_hits"] + self._metrics["cache_misses"])
                if (self._metrics["cache_hits"] + self._metrics["cache_misses"]) > 0
                else 0.0
            ),
            "errors": self._metrics["errors"],
            "avg_upload_time": self._metrics["avg_upload_time"],
            "avg_download_time": self._metrics["avg_download_time"],
            "max_upload_time": max(upload_times) if upload_times else 0.0,
            "max_download_time": max(download_times) if download_times else 0.0,
        }


# Factory functions for easy integration
def create_s3_config_from_env() -> S3Config:
    """Create S3 configuration from environment variables."""
    import os

    return S3Config(
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        bucket_name=os.getenv("S3_BUCKET_NAME", "novel-engine-storage"),
        enable_versioning=os.getenv("S3_VERSIONING", "true").lower() == "true",
        enable_encryption=os.getenv("S3_ENCRYPTION", "true").lower() == "true",
        enable_local_cache=os.getenv("S3_LOCAL_CACHE", "true").lower() == "true",
        max_cache_size=int(os.getenv("S3_CACHE_SIZE", "1073741824")),  # 1GB
        cache_ttl=int(os.getenv("S3_CACHE_TTL", "3600")),
    )


async def create_s3_manager(config: Optional[S3Config] = None) -> S3StorageManager:
    """Create and initialize S3 storage manager."""
    if config is None:
        config = create_s3_config_from_env()

    manager = S3StorageManager(config)
    await manager.initialize()
    return manager


__all__ = [
    "S3Config",
    "S3StorageManager",
    "S3StorageClass",
    "S3ContentType",
    "S3ObjectInfo",
    "UploadProgress",
    "create_s3_config_from_env",
    "create_s3_manager",
]
