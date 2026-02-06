"""
KnowledgeMetadata Value Object

Structured metadata for knowledge entries.

Warzone 4: AI Brain - OPT-006
Value object replacing unstructured metadata dicts with a strict schema.

Constitution Compliance:
- Article I (DDD): Value object with equality by value
- Article I (DDD): Self-validating with invariants
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .access_level import AccessLevel


class ConfidentialityLevel(str, Enum):
    """
    Confidentiality levels for knowledge entries.

    Why:
        Provides granular control over knowledge access and visibility.

    Values:
        PUBLIC: Can be shared freely
        INTERNAL: For internal system use only
        RESTRICTED: Requires specific permissions
        SENSITIVE: Highly sensitive, limited access
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


@dataclass(frozen=True, slots=True)
class KnowledgeMetadata:
    """
    Structured metadata for knowledge entries.

    Why frozen:
        Immutable value object prevents accidental modification.

    Why not using SourceMetadata:
        This is a higher-level metadata structure that extends the
        content-specific SourceMetadata with system-level fields.

    Attributes:
        world_version: Version of the world this knowledge belongs to
        confidentiality_level: Access control classification
        last_accessed: UTC timestamp of last access (None if never accessed)
        source_version: Version of the source content (for tracking updates)
    """

    world_version: str
    confidentiality_level: ConfidentialityLevel
    last_accessed: Optional[datetime] = None
    source_version: int = 1

    def __post_init__(self) -> None:
        """Validate metadata invariants."""
        # Normalize world_version
        if self.world_version != self.world_version.strip():
            object.__setattr__(self, "world_version", self.world_version.strip())

        # Validate world_version is not empty
        if not self.world_version:
            raise ValueError("world_version cannot be empty")

        # Normalize last_accessed to UTC
        if self.last_accessed is not None:
            if self.last_accessed.tzinfo is None:
                object.__setattr__(
                    self, "last_accessed", self.last_accessed.replace(tzinfo=timezone.utc)
                )
            else:
                object.__setattr__(
                    self, "last_accessed", self.last_accessed.astimezone(timezone.utc)
                )

        # Validate source_version is positive
        if self.source_version < 1:
            raise ValueError("source_version must be at least 1")

    def with_access(self) -> KnowledgeMetadata:
        """
        Return a new instance with last_accessed set to now.

        Returns:
            New KnowledgeMetadata with last_accessed updated to current UTC time

        Why:
            Provides immutable update pattern for access tracking.
        """
        return replace(self, last_accessed=datetime.now(timezone.utc))

    def with_version(self, version: int) -> KnowledgeMetadata:
        """
        Return a new instance with the specified source_version.

        Args:
            version: New source version (must be >= 1)

        Returns:
            New KnowledgeMetadata with updated source_version

        Raises:
            ValueError: If version is less than 1
        """
        if version < 1:
            raise ValueError("source_version must be at least 1")
        return replace(self, source_version=version)

    def to_dict(self) -> dict[str, str | int | None]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with all metadata fields

        Why:
            Provides consistent serialization format for API and storage.
        """
        return {
            "world_version": self.world_version,
            "confidentiality_level": self.confidentiality_level.value,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "source_version": self.source_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | int | None]) -> KnowledgeMetadata:
        """
        Create from dictionary representation.

        Args:
            data: Dictionary with metadata fields

        Returns:
            New KnowledgeMetadata instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        world_version = data.get("world_version")
        if not isinstance(world_version, str) or not world_version:
            raise ValueError("world_version is required and must be a non-empty string")

        confidentiality_level_str = data.get("confidentiality_level", "public")
        try:
            confidentiality_level = ConfidentialityLevel(confidentiality_level_str)
        except ValueError:
            confidentiality_level = ConfidentialityLevel.PUBLIC

        last_accessed = None
        last_accessed_str = data.get("last_accessed")
        if isinstance(last_accessed_str, str) and last_accessed_str:
            try:
                last_accessed = datetime.fromisoformat(last_accessed_str.replace("Z", "+00:00"))
                # Ensure UTC
                if last_accessed.tzinfo is None:
                    last_accessed = last_accessed.replace(tzinfo=timezone.utc)
                else:
                    last_accessed = last_accessed.astimezone(timezone.utc)
            except ValueError:
                pass  # Keep as None if invalid

        source_version = data.get("source_version", 1)
        if not isinstance(source_version, int) or source_version < 1:
            source_version = 1

        return cls(
            world_version=world_version,
            confidentiality_level=confidentiality_level,
            last_accessed=last_accessed,
            source_version=source_version,
        )

    @classmethod
    def create_default(
        cls,
        world_version: str = "1.0.0",
        confidentiality_level: ConfidentialityLevel | str = ConfidentialityLevel.PUBLIC,
    ) -> KnowledgeMetadata:
        """
        Create with sensible defaults.

        Args:
            world_version: World version string (default "1.0.0")
            confidentiality_level: Access level (default PUBLIC)

        Returns:
            New KnowledgeMetadata with default values
        """
        if isinstance(confidentiality_level, str):
            try:
                confidentiality_level = ConfidentialityLevel(confidentiality_level)
            except ValueError:
                confidentiality_level = ConfidentialityLevel.PUBLIC

        return cls(
            world_version=world_version,
            confidentiality_level=confidentiality_level,
            last_accessed=None,
            source_version=1,
        )


__all__ = [
    "KnowledgeMetadata",
    "ConfidentialityLevel",
]
