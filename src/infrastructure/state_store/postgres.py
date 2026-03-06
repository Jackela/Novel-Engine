class S3StateStore(StateStore):
    """S3-based state store for large files and documents"""

    def __init__(self, config: StateStoreConfig) -> None:
        self.config = config
        self.s3_client = None
        self._connected = False

    async def connect(self) -> None:
        """Initialize S3 client"""
        if self._connected:
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
                logger.info("S3 connection established")
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoCredentialsError":
                    logger.warning("S3 credentials not configured, S3 storage disabled")
                    self._connected = False
                else:
                    raise

        except Exception as e:
            logger.error("s3_connection_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def _ensure_bucket_exists(self) -> None:
        """Ensure S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
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
                except Exception as create_error:
                    logger.error("s3_bucket_creation_failed", error=str(create_error))
                    raise
            else:
                logger.error("s3_bucket_check_failed", error_code=e.response["Error"]["Code"])
                raise

    def _key_to_s3_key(self, key: StateKey) -> str:
        """Convert StateKey to S3 object key"""
        parts = [key.namespace, key.entity_type, key.entity_id]
        if key.version:
            parts.append(key.version)
        return "/".join(parts)

    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value from S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return None

        s3_key = self._key_to_s3_key(key)

        try:
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket, Key=s3_key
            )

            content = response["Body"].read()

            # Try to deserialize based on content type
            content_type = response.get("ContentType", "application/octet-stream")

            if content_type == "application/json":
                return json.loads(content.decode("utf-8"))
            elif content_type.startswith("text/"):
                return content.decode("utf-8")
            else:
                return content

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                logger.error("s3_get_object_failed", key=s3_key, error_code=e.response["Error"]["Code"])
                return None

        except Exception as e:
            logger.error("s3_get_object_failed", key=s3_key, error=str(e))
            return None

    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            # Prepare content and metadata
            if isinstance(value, str):
                content = value.encode("utf-8")
                content_type = "text/plain"
            elif isinstance(value, (dict, list)):
                content = json.dumps(value, default=str).encode("utf-8")
                content_type = "application/json"
            elif isinstance(value, bytes):
                content = value
                content_type = "application/octet-stream"
            else:
                # Serialize as JSON
                content = json.dumps(value, default=str).encode("utf-8")
                content_type = "application/json"

            # Prepare metadata
            metadata = {
                "namespace": key.namespace,
                "entity-type": key.entity_type,
                "entity-id": key.entity_id,
                "created-at": datetime.now().isoformat(),
            }

            if key.version:
                metadata["version"] = key.version

            # Set expiration if TTL provided
            extra_args = {"ContentType": content_type, "Metadata": metadata}

            if ttl:
                expires = datetime.now() + timedelta(seconds=ttl)
                extra_args["Expires"] = expires

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket, Key=s3_key, Body=content, **extra_args
            )

            return True

        except Exception as e:
            logger.error("s3_set_object_failed", key=s3_key, error=str(e))
            return False

    async def delete(self, key: StateKey) -> bool:
        """Delete value from S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            self.s3_client.delete_object(Bucket=self.config.s3_bucket, Key=s3_key)
            return True

        except Exception as e:
            logger.error("s3_delete_object_failed", key=s3_key, error=str(e))
            return False

    async def exists(self, key: StateKey) -> bool:
        """Check if key exists in S3"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return False

        s3_key = self._key_to_s3_key(key)

        try:
            self.s3_client.head_object(Bucket=self.config.s3_bucket, Key=s3_key)
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error("s3_object_exists_check_failed", key=s3_key, error_code=e.response["Error"]["Code"])
                return False

        except Exception as e:
            logger.error("s3_object_exists_check_failed", key=s3_key, error=str(e))
            return False

    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern"""
        if not self._connected:
            await self.connect()

        if not self._connected:
            return []

        # Convert pattern to S3 prefix
        prefix = pattern.replace("*", "").replace(":", "/")
        if prefix.endswith("/"):
            prefix = prefix[:-1]

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket, Prefix=prefix, MaxKeys=1000
            )

            keys: list[Any] = []
            for obj in response.get("Contents", []):
                s3_key = obj["Key"]
                try:
                    # Convert S3 key back to StateKey
                    parts = s3_key.split("/")
                    if len(parts) >= 3:
                        state_key = StateKey(
                            namespace=parts[0],
                            entity_type=parts[1],
                            entity_id=parts[2],
                            version=parts[3] if len(parts) > 3 else None,
                        )
                        keys.append(state_key)
                except Exception:
                    continue

            return keys

        except Exception as e:
            logger.error("s3_list_keys_failed", prefix=prefix, error=str(e))
            return []

    async def health_check(self) -> bool:
        """Check S3 health"""
        if not self._connected:
            await self.connect()

        try:
            self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
            return True

        except Exception as e:
            logger.error("s3_health_check_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close S3 client"""
        # S3 client doesn't need explicit closing
        self._connected = False
        logger.info("s3_client_closed")


