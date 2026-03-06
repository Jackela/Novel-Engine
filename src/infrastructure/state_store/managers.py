class ConfigurationManager:
    """Unified configuration manager"""

    def __init__(self, config_paths: Optional[List[str]] = None) -> None:
        self.config_paths = config_paths or [
            "/etc/novel-engine/config/environments/development.yaml",
            "./config/environments/development.yaml",
            "./config/environments/environments.yaml",
        ]
        self.config_data: Dict[str, Any] = {}
        self.environment = os.getenv("ENVIRONMENT", "development")

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from files and environment"""

        # Start with default configuration
        self.config_data = self._get_default_config()

        # Load from config files
        for config_path in self.config_paths:
            if Path(config_path).exists():
                try:
                    with open(config_path, "r") as f:
                        file_config = yaml.safe_load(f)
                        if file_config:
                            self._merge_config(self.config_data, file_config)
                            logger.info(f"Loaded configuration from {config_path}")
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")

        # Apply environment-specific overrides
        env_config = self.config_data.get("environments", {}).get(self.environment, {})
        if env_config:
            self._merge_config(self.config_data, env_config)

        # Override with environment variables
        self._apply_env_overrides()

        return self.config_data

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "state_store": {
                "redis_url": "",  # Set via REDIS_URL environment variable
                "postgres_url": "",  # Set via POSTGRES_URL environment variable
                "s3_bucket": "novel-engine-storage",
                "s3_region": "us-east-1",
                "cache_ttl": 3600,
                "max_retries": 3,
                "connection_timeout": 30,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4,
            },  # nosec B104 - default config
            "security": {
                "encryption_key": None,
                "jwt_secret": None,
                "cors_origins": ["http://localhost:3000"],
            },
        }

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        env_mappings = {
            "REDIS_URL": ["state_store", "redis_url"],
            "POSTGRES_URL": ["state_store", "postgres_url"],
            "S3_BUCKET": ["state_store", "s3_bucket"],
            "S3_REGION": ["state_store", "s3_region"],
            "AWS_ACCESS_KEY_ID": ["state_store", "aws_access_key"],
            "AWS_SECRET_ACCESS_KEY": ["state_store", "aws_secret_key"],
            "ENCRYPTION_KEY": ["security", "encryption_key"],
            "JWT_SECRET": ["security", "jwt_secret"],
            "API_HOST": ["api", "host"],
            "API_PORT": ["api", "port"],
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Navigate to the nested config key
                current = self.config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Set the value, converting to appropriate type
                final_key = config_path[-1]
                if final_key in [
                    "port",
                    "workers",
                    "cache_ttl",
                    "max_retries",
                    "connection_timeout",
                ]:
                    current[final_key] = int(env_value)
                elif env_value.lower() in ["true", "false"]:
                    current[final_key] = env_value.lower() == "true"
                else:
                    current[final_key] = env_value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = key_path.split(".")
        current = self.config_data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def get_state_store_config(self) -> StateStoreConfig:
        """Get state store configuration"""
        state_config = self.config_data.get("state_store", {})
        return StateStoreConfig(**state_config)


# Factory functions
