#!/usr/bin/env python3

"""

State Hashing System.



A comprehensive state hashing system for consistency validation,

caching optimization, and state change detection.

"""


import hashlib
import importlib.util
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SHARED_TYPES_AVAILABLE = importlib.util.find_spec("shared_types") is not None

if not SHARED_TYPES_AVAILABLE:

    logging.warning("Shared types not available, using fallback hashing.")


logger = logging.getLogger(__name__)


@dataclass
class StateHash:
    """Represents a computed state hash with metadata."""

    hash_value: str

    timestamp: datetime

    component_type: str

    component_id: Optional[str] = None

    version: int = 1

    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the StateHash to a dictionary."""

        return {
            "hash_value": self.hash_value,
            "timestamp": self.timestamp.isoformat(),
            "component_type": self.component_type,
            "component_id": self.component_id,
            "version": self.version,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateHash":
        """Creates a StateHash from a dictionary."""

        return cls(
            hash_value=data["hash_value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            component_type=data["component_type"],
            component_id=data.get("component_id"),
            version=data.get("version", 1),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class HashingConfig:
    """Configuration for the state hashing system."""

    algorithm: str = "sha256"

    encoding: str = "utf-8"

    enable_incremental_hashing: bool = True

    cache_intermediate_results: bool = True

    max_cache_size: int = 1000

    strict_ordering: bool = True

    enable_debug_logging: bool = False


class StateHasher:
    """Core state hashing engine."""

    def __init__(self, config: Optional[HashingConfig] = None):
        """Initializes the state hasher."""

        self.config = config or HashingConfig()

        self.hash_cache: Dict[str, StateHash] = {}

        self.hasher_class = getattr(hashlib, self.config.algorithm, hashlib.sha256)

        logger.info(f"StateHasher initialized with {self.config.algorithm}.")

    def _compute_hash(self, data: Any) -> str:
        """Computes a hash for the given data."""

        serializable_data = self._make_json_serializable(data)

        json_str = json.dumps(serializable_data, sort_keys=True)

        hasher = self.hasher_class()

        hasher.update(json_str.encode(self.config.encoding))

        return hasher.hexdigest()

    def _make_json_serializable(self, data: Any) -> Any:
        """Converts data to a JSON-serializable format."""

        if isinstance(data, (datetime, Path)):

            return str(data)

        if isinstance(data, dict):

            return {k: self._make_json_serializable(v) for k, v in data.items()}

        if isinstance(data, list):

            return [self._make_json_serializable(v) for v in data]

        if hasattr(data, "to_dict"):

            return data.to_dict()

        return data

    def hash_component(
        self,
        component_data: Any,
        component_type: str,
        component_id: Optional[str] = None,
    ) -> StateHash:
        """Generates a hash for a given component."""

        hash_value = self._compute_hash(component_data)

        state_hash = StateHash(
            hash_value=hash_value,
            timestamp=datetime.now(),
            component_type=component_type,
            component_id=component_id,
        )

        if self.config.cache_intermediate_results:

            self.hash_cache[f"{component_type}_{component_id or 'singleton'}"] = (
                state_hash
            )

        return state_hash

    def clear_cache(self):
        """Clears the hash cache."""

        self.hash_cache.clear()

        logger.info("Hash cache cleared.")
