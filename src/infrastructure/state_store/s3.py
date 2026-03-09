"""S3 State Store.

S3-based implementation of the StateStore interface for large files.
"""

import json
import pickle
from typing import Any, List, Optional

import structlog

from src.infrastructure.state_store.base import StateStore
from src.infrastructure.state_store.config import StateKey, StateStoreConfig

# Import boto3 if available
try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception

logger = structlog.get_logger(__name__)


class S3StateStore(StateStore):
    """S3-based state store for large files and documents."""

    def __init__(self, config: StateStoreConfig) -> None:
        """Initialize S3 state store.

        Args:
            config: State store configuration
        """
        self.config = config
        self.s3_client = None
        self._connected = False

        if not BOTO3_AVAILABLE:
            logger.warning("boto3_not_available")

    async def connect(self) -> None:
        """Initialize S3 client."""
        if self._connected or not BOTO3_AVAILABLE:
            return

        try:
            session = boto3.Session(
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
                region_name=self.config.s3_region,
            )

            self.s3_client = session.client("s3")

            # Test connection and create bucket if not exists
            try:
                await self._ensure_bucket_exists()
                self._connected = True
                logger.info("s3_connection_established")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "NoCredentialsError":
                    logger.warning("s3_credentials_not_configured")
                    self._connected = False
                else:
                    raise

        except Exception as e:
            logger.error("s3_connection_failed", error=str(e))
            raise

    async def _ensure_bucket_exists(self) -> None:
        """Ensure S3 bucket exists."""
        if not self.s3_client:
            return

        try:
            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "404")
            if error_code == "404":
                # Create bucket
                try:
                    if self.config.s3_region == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.config.s3_bucket)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.config.s3_bucket,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.config.s3_region
                            },
                        )
                    logger.info("s3_bucket_created", bucket=self.config.s3_bucket)
                except Exception as e:
                    logger.error("s3_bucket_creation_failed", error=str(e))
                    raise
            else:
                raise

    def _get_s3_key(self, key: StateKey) -> str:
        """Convert StateKey to S3 key.

        Args:
            key: State key

        Returns:
            S3 object key
        """
        return f"{key.namespace}/{key.entity_type}/{key.entity_id}"

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from S3.

        Args:
            key: State key to look up

        Returns:
            Stored value or None
        """
        if not self._connected:
            await self.connect()

        if not self.s3_client:
            return None

        try:
            s3_key = self._get_s3_key(key)
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket, Key=s3_key
            )
            data = response["Body"].read()

            # Try to deserialize
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                try:
                    # nosec B301 - pickle used for internal S3 cache data only
                    # Data is stored by trusted application code with proper access controls
                    return pickle.loads(data)  # nosec B301
                except Exception:
                    return data.decode("utf-8") if isinstance(data, bytes) else data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                return None
            logger.error("s3_get_failed", key=key.to_string(), error=str(e))
            return None
        except Exception as e:
            logger.error("s3_get_failed", key=key.to_string(), error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in S3.

        Args:
            key: State key
            value: Value to store
            ttl: Optional time-to-live (not directly supported by S3, use lifecycle policies)

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        if not self.s3_client:
            return False

        try:
            s3_key = self._get_s3_key(key)

            # Serialize value
            if isinstance(value, (dict, list)):
                data = json.dumps(value, default=str).encode("utf-8")
                content_type = "application/json"
            elif isinstance(value, str):
                data = value.encode("utf-8")
                content_type = "text/plain"
            else:
                data = pickle.dumps(value)
                content_type = "application/octet-stream"

            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
            )
            return True

        except Exception as e:
            logger.error("s3_set_failed", key=key.to_string(), error=str(e))
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from S3.

        Args:
            key: State key to delete

        Returns:
            True if deleted
        """
        if not self._connected:
            await self.connect()

        if not self.s3_client:
            return False

        try:
            s3_key = self._get_s3_key(key)
            self.s3_client.delete_object(Bucket=self.config.s3_bucket, Key=s3_key)
            return True

        except Exception as e:
            logger.error("s3_delete_failed", key=key.to_string(), error=str(e))
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in S3.

        Args:
            key: State key to check

        Returns:
            True if exists
        """
        if not self._connected:
            await self.connect()

        if not self.s3_client:
            return False

        try:
            s3_key = self._get_s3_key(key)
            self.s3_client.head_object(Bucket=self.config.s3_bucket, Key=s3_key)
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return False
            logger.error("s3_exists_check_failed", key=key.to_string(), error=str(e))
            return False
        except Exception as e:
            logger.error("s3_exists_check_failed", key=key.to_string(), error=str(e))
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching prefix.

        Args:
            pattern: Prefix pattern (S3 uses prefixes, not wildcards)

        Returns:
            List of matching keys
        """
        if not self._connected:
            await self.connect()

        if not self.s3_client:
            return []

        try:
            # Convert pattern to prefix (S3 only supports prefixes)
            prefix = pattern.replace("*", "").replace("?", "")

            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket, Prefix=prefix
            )

            keys = []
            for obj in response.get("Contents", []):
                key_str = obj["Key"]
                # Convert S3 key back to StateKey format
                parts = key_str.split("/")
                if len(parts) >= 3:
                    keys.append(
                        StateKey(
                            namespace=parts[0],
                            entity_type=parts[1],
                            entity_id="/".join(parts[2:]),
                        )
                    )

            return keys

        except Exception as e:
            logger.error("s3_list_keys_failed", pattern=pattern, error=str(e))
            return []

    async def increment(self, key: StateKey, amount: int = 1) -> Optional[int]:
        """Increment counter value (not atomically supported in S3).

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value or None
        """
        # S3 doesn't support atomic increments
        # This is a best-effort implementation
        current = await self.get(key)
        if current is None:
            current = 0
        try:
            new_value = int(current) + amount
            await self.set(key, new_value)
            return new_value
        except (ValueError, TypeError):
            logger.error("s3_increment_failed", key=key.to_string())
            return None

    async def expire(self, key: StateKey, ttl: int) -> bool:
        """Set TTL for existing key (not directly supported by S3).

        Args:
            key: State key
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        # S3 doesn't support per-object TTL
        # This would require lifecycle policies at bucket level
        logger.warning("s3_expire_not_supported", key=key.to_string())
        return True

    async def health_check(self) -> bool:
        """Check S3 health.

        Returns:
            True if healthy
        """
        try:
            if not self._connected:
                await self.connect()

            if not self.s3_client:
                return False

            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
            return True

        except Exception as e:
            logger.error("s3_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close S3 client."""
        if self.s3_client:
            # boto3 client doesn't need explicit close
            self._connected = False
            logger.info("s3_connection_closed")
