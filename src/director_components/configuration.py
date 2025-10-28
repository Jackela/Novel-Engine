"""
Configuration Service
=====================

Centralized configuration management for the DirectorAgent system.
Handles loading, validation, hot-reloading, and environment-specific configs.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Optional imports for advanced features
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


@dataclass
class ConfigSchema:
    """Configuration schema definition."""

    key: str
    required: bool = True
    data_type: type = str
    default_value: Any = None
    validation_rules: List[str] = field(default_factory=list)
    description: str = ""


if WATCHDOG_AVAILABLE:

    class ConfigFileHandler(FileSystemEventHandler):
        """File system event handler for config file changes."""

        def __init__(self, config_service):
            self.config_service = config_service
            self.logger = logging.getLogger(__name__)

        def on_modified(self, event):
            if (
                not event.is_directory
                and event.src_path in self.config_service._watched_files
            ):
                self.logger.info(f"Config file modified: {event.src_path}")
                # Schedule config reload
                asyncio.create_task(
                    self.config_service._handle_file_change(event.src_path)
                )

else:

    class ConfigFileHandler:
        """Dummy handler when watchdog is not available."""

        def __init__(self, config_service):
            pass


class ConfigurationService:
    """
    Centralized configuration management service.

    Features:
    - Multi-format support (JSON, YAML, environment variables)
    - Schema validation and type checking
    - Hot-reloading with file watching
    - Environment-specific configuration
    - Configuration merging and inheritance
    - Secure handling of sensitive values
    """

    def __init__(
        self,
        config_dir: str = "config",
        environment: str = "development",
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.environment = environment

        # Configuration storage
        self._config_data: Dict[str, Any] = {}
        self._config_schema: Dict[str, ConfigSchema] = {}
        self._config_files: List[Path] = []
        self._watched_files: List[str] = []

        # File watching
        self._file_observer: Optional[Observer] = None
        self._hot_reload_enabled = (
            WATCHDOG_AVAILABLE  # Only enable if watchdog available
        )

        # Configuration lock for thread safety
        self._config_lock = asyncio.Lock()

        # Change tracking
        self._config_history: List[Dict[str, Any]] = []
        self._change_callbacks: List[callable] = []

        # Validation
        self._validation_enabled = True
        self._strict_mode = False  # Whether to fail on schema violations

    async def initialize(self) -> bool:
        """Initialize configuration service."""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Define configuration schema
            await self._define_config_schema()

            # Load configuration files
            await self._load_configuration_files()

            # Load environment variables
            await self._load_environment_config()

            # Validate configuration
            if self._validation_enabled:
                validation_result = await self._validate_configuration()
                if not validation_result["valid"] and self._strict_mode:
                    raise ValueError(
                        f"Configuration validation failed: {validation_result['errors']}"
                    )

            # Setup file watching
            if self._hot_reload_enabled:
                await self._setup_file_watching()

            self.logger.info(
                f"Configuration service initialized for environment: {self.environment}"
            )
            return True

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during initialization
            self.logger.error(
                f"File system error during initialization: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (ValueError, TypeError, RuntimeError) as e:
            # Configuration validation, schema, or setup errors
            self.logger.error(
                f"Configuration initialization error: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False

    async def get_config(self) -> Dict[str, Any]:
        """Get complete configuration."""
        async with self._config_lock:
            return self._config_data.copy()

    async def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get specific configuration value with dot notation support.

        Args:
            key: Configuration key (supports dot notation like 'database.host')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            async with self._config_lock:
                return self._get_nested_value(self._config_data, key, default)

        except (AttributeError, KeyError, TypeError) as e:
            # Invalid key or data structure errors
            self.logger.warning(
                f"Invalid data getting config value for key '{key}': {e}",
                extra={"error_type": type(e).__name__},
            )
            return default
        except (ValueError, RuntimeError) as e:
            # Value access or lock errors
            self.logger.warning(
                f"Config value retrieval error for key '{key}': {e}",
                extra={"error_type": type(e).__name__},
            )
            return default

    async def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of configuration updates
        """
        try:
            async with self._config_lock:
                # Backup current config for history
                old_config = self._config_data.copy()

                # Apply updates
                for key, value in updates.items():
                    self._set_nested_value(self._config_data, key, value)

                # Validate updated configuration
                if self._validation_enabled:
                    validation_result = await self._validate_configuration()
                    if not validation_result["valid"]:
                        if self._strict_mode:
                            # Rollback changes
                            self._config_data = old_config
                            raise ValueError(
                                f"Configuration update validation failed: {validation_result['errors']}"
                            )
                        else:
                            self.logger.warning(
                                f"Configuration validation warnings: {validation_result['errors']}"
                            )

                # Record change
                change_record = {
                    "timestamp": datetime.now().isoformat(),
                    "updates": updates,
                    "environment": self.environment,
                    "source": "api_update",
                }
                self._config_history.append(change_record)

                # Notify change callbacks
                await self._notify_config_changes(updates)

                self.logger.info(f"Configuration updated with {len(updates)} changes")

        except (AttributeError, KeyError, TypeError) as e:
            # Invalid updates or data structure errors
            self.logger.error(
                f"Invalid data during configuration update: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise
        except (ValueError, RuntimeError) as e:
            # Validation or configuration application errors
            self.logger.error(
                f"Configuration update error: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise

    async def reload_config(self) -> bool:
        """Reload configuration from files."""
        try:
            self.logger.info("Reloading configuration from files...")

            async with self._config_lock:
                old_config = self._config_data.copy()

                # Clear current config
                self._config_data.clear()

                # Reload from files
                await self._load_configuration_files()
                await self._load_environment_config()

                # Validate reloaded configuration
                if self._validation_enabled:
                    validation_result = await self._validate_configuration()
                    if not validation_result["valid"] and self._strict_mode:
                        # Rollback to old config
                        self._config_data = old_config
                        raise ValueError(
                            f"Configuration reload validation failed: {validation_result['errors']}"
                        )

                # Record reload
                change_record = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "reload",
                    "environment": self.environment,
                    "source": "file_reload",
                }
                self._config_history.append(change_record)

                # Notify changes if config actually changed
                if old_config != self._config_data:
                    await self._notify_config_changes({"_full_reload": True})

                self.logger.info("Configuration reloaded successfully")
                return True

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during reload
            self.logger.error(
                f"File system error during config reload: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (ValueError, RuntimeError) as e:
            # Configuration parsing or validation errors
            self.logger.error(
                f"Configuration reload error: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False

    async def register_change_callback(self, callback: callable) -> None:
        """Register callback for configuration changes."""
        self._change_callbacks.append(callback)

    async def get_config_info(self) -> Dict[str, Any]:
        """Get configuration service information."""
        return {
            "environment": self.environment,
            "config_dir": str(self.config_dir),
            "config_files_count": len(self._config_files),
            "config_keys_count": len(self._config_data),
            "hot_reload_enabled": self._hot_reload_enabled,
            "validation_enabled": self._validation_enabled,
            "strict_mode": self._strict_mode,
            "watched_files": self._watched_files.copy(),
            "change_history_count": len(self._config_history),
            "schema_keys": list(self._config_schema.keys()),
        }

    async def _define_config_schema(self) -> None:
        """Define configuration schema for validation."""
        # Core system configuration
        self._config_schema = {
            "system.max_agents": ConfigSchema(
                key="system.max_agents",
                required=True,
                data_type=int,
                default_value=50,
                validation_rules=["positive"],
                description="Maximum number of agents allowed in the system",
            ),
            "system.log_level": ConfigSchema(
                key="system.log_level",
                required=True,
                data_type=str,
                default_value="INFO",
                validation_rules=["log_level"],
                description="System logging level",
            ),
            "database.host": ConfigSchema(
                key="database.host",
                required=False,
                data_type=str,
                default_value="localhost",
                description="Database host address",
            ),
            "database.port": ConfigSchema(
                key="database.port",
                required=False,
                data_type=int,
                default_value=5432,
                validation_rules=["port_range"],
                description="Database port number",
            ),
            "simulation.turn_timeout": ConfigSchema(
                key="simulation.turn_timeout",
                required=True,
                data_type=float,
                default_value=30.0,
                validation_rules=["positive"],
                description="Maximum turn execution time in seconds",
            ),
            "simulation.auto_save_interval": ConfigSchema(
                key="simulation.auto_save_interval",
                required=True,
                data_type=int,
                default_value=300,
                validation_rules=["positive"],
                description="Auto-save interval in seconds",
            ),
            "narrative.max_events": ConfigSchema(
                key="narrative.max_events",
                required=True,
                data_type=int,
                default_value=500,
                validation_rules=["positive"],
                description="Maximum narrative events to store",
            ),
            "logging.max_memory_entries": ConfigSchema(
                key="logging.max_memory_entries",
                required=True,
                data_type=int,
                default_value=1000,
                validation_rules=["positive"],
                description="Maximum log entries to keep in memory",
            ),
            "performance.enable_profiling": ConfigSchema(
                key="performance.enable_profiling",
                required=False,
                data_type=bool,
                default_value=False,
                description="Enable performance profiling",
            ),
        }

    async def _load_configuration_files(self) -> None:
        """Load configuration from files."""
        # Define file loading order
        config_files = [
            self.config_dir / "default.json",
            self.config_dir / "default.yaml",
            self.config_dir / f"{self.environment}.json",
            self.config_dir / f"{self.environment}.yaml",
            self.config_dir / "local.json",
            self.config_dir / "local.yaml",
        ]

        self._config_files = []

        for config_file in config_files:
            if config_file.exists():
                try:
                    config_data = await self._load_single_config_file(config_file)
                    self._merge_config(config_data)
                    self._config_files.append(config_file)

                    if self._hot_reload_enabled:
                        self._watched_files.append(str(config_file))

                    self.logger.debug(f"Loaded configuration from: {config_file}")

                except (FileNotFoundError, PermissionError, IOError, OSError) as e:
                    # File system errors during file loading
                    self.logger.error(
                        f"File error loading config {config_file}: {e}",
                        extra={"error_type": type(e).__name__},
                    )
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    # File parsing or data format errors
                    self.logger.error(
                        f"Parse error loading config {config_file}: {e}",
                        extra={"error_type": type(e).__name__},
                    )

    async def _load_single_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix.lower() in [".yml", ".yaml"]:
                    if YAML_AVAILABLE:
                        return yaml.safe_load(f) or {}
                    else:
                        self.logger.warning(
                            f"YAML file {file_path} skipped - 'pyyaml' package not available"
                        )
                        return {}
                else:  # Assume JSON
                    return json.load(f) or {}

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during file reading
            self.logger.error(
                f"File error parsing config {file_path}: {e}",
                extra={"error_type": type(e).__name__},
            )
            return {}
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # JSON/YAML parsing or data format errors
            self.logger.error(
                f"Parse error for config file {file_path}: {e}",
                extra={"error_type": type(e).__name__},
            )
            return {}

    async def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        env_prefix = "NOVEL_ENGINE_"

        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert environment variable name to config key
                config_key = key[len(env_prefix) :].lower().replace("_", ".")

                # Try to parse as JSON first, then as string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value

                self._set_nested_value(self._config_data, config_key, parsed_value)
                self.logger.debug(f"Loaded environment config: {config_key}")

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration data with existing configuration."""

        def merge_dicts(base: dict, update: dict) -> dict:
            for key, value in update.items():
                if (
                    isinstance(value, dict)
                    and key in base
                    and isinstance(base[key], dict)
                ):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
            return base

        merge_dicts(self._config_data, new_config)

    def _get_nested_value(
        self, data: Dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = key.split(".")
        current = data

        try:
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = key.split(".")
        current = data

        # Navigate to parent
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        # Set final value
        current[keys[-1]] = value

    async def _validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration against schema."""
        validation_result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Check required keys
            for schema_key, schema in self._config_schema.items():
                current_value = self._get_nested_value(self._config_data, schema_key)

                if schema.required and current_value is None:
                    if schema.default_value is not None:
                        # Set default value
                        self._set_nested_value(
                            self._config_data, schema_key, schema.default_value
                        )
                        validation_result["warnings"].append(
                            f"Using default value for required key '{schema_key}'"
                        )
                    else:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            f"Required configuration key missing: {schema_key}"
                        )
                        continue

                if current_value is not None:
                    # Type checking
                    if not isinstance(current_value, schema.data_type):
                        try:
                            # Try to convert
                            if schema.data_type is int:
                                converted_value = int(current_value)
                            elif schema.data_type is float:
                                converted_value = float(current_value)
                            elif schema.data_type is bool:
                                converted_value = (
                                    bool(current_value)
                                    if not isinstance(current_value, str)
                                    else current_value.lower() in ["true", "1", "yes"]
                                )
                            else:
                                converted_value = schema.data_type(current_value)

                            self._set_nested_value(
                                self._config_data, schema_key, converted_value
                            )
                            validation_result["warnings"].append(
                                f"Converted '{schema_key}' from {type(current_value).__name__} to {schema.data_type.__name__}"
                            )
                            current_value = converted_value
                        except (ValueError, TypeError):
                            validation_result["valid"] = False
                            validation_result["errors"].append(
                                f"Invalid type for '{schema_key}': expected {schema.data_type.__name__}, got {type(current_value).__name__}"
                            )
                            continue

                    # Validation rules
                    for rule in schema.validation_rules:
                        if not await self._apply_validation_rule(
                            schema_key, current_value, rule
                        ):
                            validation_result["valid"] = False
                            validation_result["errors"].append(
                                f"Validation rule '{rule}' failed for key '{schema_key}' with value '{current_value}'"
                            )

            return validation_result

        except (AttributeError, KeyError, TypeError) as e:
            # Invalid schema or data structure errors
            self.logger.error(
                f"Invalid data during validation: {e}",
                extra={"error_type": type(e).__name__},
            )
            return {"valid": False, "errors": [str(e)], "warnings": []}
        except (ValueError, RuntimeError) as e:
            # Validation rule or type conversion errors
            self.logger.error(
                f"Validation processing error: {e}",
                extra={"error_type": type(e).__name__},
            )
            return {"valid": False, "errors": [str(e)], "warnings": []}

    async def _apply_validation_rule(self, key: str, value: Any, rule: str) -> bool:
        """Apply a validation rule to a configuration value."""
        try:
            if rule == "positive":
                return isinstance(value, (int, float)) and value > 0
            elif rule == "port_range":
                return isinstance(value, int) and 1 <= value <= 65535
            elif rule == "log_level":
                return isinstance(value, str) and value.upper() in [
                    "DEBUG",
                    "INFO",
                    "WARNING",
                    "ERROR",
                    "CRITICAL",
                ]
            else:
                self.logger.warning(f"Unknown validation rule: {rule}")
                return True

        except (AttributeError, TypeError, ValueError) as e:
            # Invalid value type or comparison errors
            self.logger.error(
                f"Validation rule data error for '{key}': {e}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (RuntimeError, KeyError) as e:
            # Rule application or value access errors
            self.logger.error(
                f"Validation rule processing error for '{key}': {e}",
                extra={"error_type": type(e).__name__},
            )
            return False

    async def _setup_file_watching(self) -> None:
        """Setup file system watching for configuration files."""
        if not WATCHDOG_AVAILABLE:
            self.logger.info("File watching disabled - watchdog package not available")
            return

        try:
            if not self._watched_files:
                return

            event_handler = ConfigFileHandler(self)
            self._file_observer = Observer()

            # Watch each directory containing config files
            watched_dirs = set()
            for file_path in self._watched_files:
                dir_path = str(Path(file_path).parent)
                if dir_path not in watched_dirs:
                    self._file_observer.schedule(
                        event_handler, dir_path, recursive=False
                    )
                    watched_dirs.add(dir_path)

            self._file_observer.start()
            self.logger.info(
                f"File watching started for {len(watched_dirs)} directories"
            )

        except (AttributeError, TypeError, KeyError) as e:
            # Invalid file paths or observer errors
            self.logger.error(
                f"File watching setup data error: {e}",
                extra={"error_type": type(e).__name__},
            )
        except (RuntimeError, OSError, ImportError) as e:
            # Observer creation or file system errors
            self.logger.error(
                f"File watching setup error: {e}",
                extra={"error_type": type(e).__name__},
            )

    async def _handle_file_change(self, file_path: str) -> None:
        """Handle configuration file change."""
        try:
            # Debounce multiple rapid changes
            await asyncio.sleep(0.5)

            self.logger.info(f"Reloading configuration due to file change: {file_path}")
            success = await self.reload_config()

            if success:
                self.logger.info("Configuration hot-reload completed successfully")
            else:
                self.logger.error("Configuration hot-reload failed")

        except (AttributeError, TypeError) as e:
            # Invalid file path or reload method errors
            self.logger.error(
                f"Config file change handler data error: {e}",
                extra={"error_type": type(e).__name__},
            )
        except (RuntimeError, asyncio.CancelledError) as e:
            # Async operation or reload errors
            self.logger.error(
                f"Config file change handler error: {e}",
                extra={"error_type": type(e).__name__},
            )

    async def _notify_config_changes(self, changes: Dict[str, Any]) -> None:
        """Notify registered callbacks about configuration changes."""
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(changes)
                else:
                    callback(changes)
            except (AttributeError, TypeError) as e:
                # Invalid callback or changes data errors
                self.logger.error(
                    f"Config change callback data error: {e}",
                    extra={"error_type": type(e).__name__},
                )
            except (ValueError, RuntimeError) as e:
                # Callback execution errors
                self.logger.error(
                    f"Config change callback execution error: {e}",
                    extra={"error_type": type(e).__name__},
                )

    async def export_config(self, export_path: str, format: str = "json") -> bool:
        """Export current configuration to file."""
        try:
            async with self._config_lock:
                export_data = {
                    "metadata": {
                        "exported_at": datetime.now().isoformat(),
                        "environment": self.environment,
                        "export_format": format,
                    },
                    "configuration": self._config_data.copy(),
                }

                with open(export_path, "w", encoding="utf-8") as f:
                    if format.lower() == "yaml" and YAML_AVAILABLE:
                        yaml.dump(export_data, f, default_flow_style=False)
                    else:  # JSON (default)
                        json.dump(export_data, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Configuration exported to: {export_path}")
                return True

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during export
            self.logger.error(
                f"File error during config export: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False
        except (json.JSONEncodeError, TypeError, ValueError) as e:
            # JSON/YAML serialization or data format errors
            self.logger.error(
                f"Serialization error during config export: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False

    async def cleanup(self) -> None:
        """Cleanup configuration service."""
        try:
            # Stop file observer
            if self._file_observer:
                self._file_observer.stop()
                self._file_observer.join()

            # Clear data structures
            self._config_data.clear()
            self._config_files.clear()
            self._watched_files.clear()
            self._change_callbacks.clear()

            self.logger.info("Configuration service cleanup completed")

        except (AttributeError, TypeError) as e:
            # Invalid observer or data structure errors
            self.logger.error(
                f"Cleanup data error: {e}", extra={"error_type": type(e).__name__}
            )
        except (RuntimeError, OSError) as e:
            # Observer stop or thread join errors
            self.logger.error(
                f"Cleanup processing error: {e}", extra={"error_type": type(e).__name__}
            )
