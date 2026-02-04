"""
Prompt Version Entity

Warzone 4: AI Brain - BRAIN-016A
Domain entity for tracking prompt template versions.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class VersionDiff:
    """
    Value object representing changes between versions.

    Why frozen:
        Immutable diff snapshot prevents accidental modification.

    Attributes:
        content_changed: Whether the content was modified
        variables_changed: Whether variables were modified
        model_config_changed: Whether model config was modified
        metadata_changed: Whether metadata (name, description, tags) was modified
        description: Human-readable description of the changes
    """

    content_changed: bool
    variables_changed: bool
    model_config_changed: bool
    metadata_changed: bool
    description: str = ""

    def __bool__(self) -> bool:
        """Return True if any changes were made."""
        return (
            self.content_changed
            or self.variables_changed
            or self.model_config_changed
            or self.metadata_changed
        )

    @classmethod
    def no_changes(cls) -> VersionDiff:
        """Create a diff representing no changes."""
        return cls(
            content_changed=False,
            variables_changed=False,
            model_config_changed=False,
            metadata_changed=False,
            description="No changes",
        )


@dataclass
class PromptVersion:
    """
    Entity representing a version of a prompt template.

    Why not frozen:
        Entity may need to update metadata (e.g., description, changelog).

    Why separate from PromptTemplate:
        - Provides explicit version tracking and lineage
        - Enables version-specific operations (rollback, diff, comparison)
        - Separates version metadata from template content

    Attributes:
        id: Unique identifier for this version record (UUID)
        template_id: ID of the PromptTemplate this version belongs to
        version_number: Version number (1-indexed)
        template_snapshot_id: ID of the actual PromptTemplate entity for this version
        parent_version_id: ID of the previous version (None for v1)
        change_description: Human-readable description of what changed
        diff: Structured diff of changes from previous version
        created_at: Timestamp when this version was created
        created_by: Optional identifier of who created this version
        tags: Tags associated with this version (e.g., "stable", "beta", "rollback")

    Invariants:
        - id must be non-empty
        - template_id must be non-empty
        - version_number must be positive
        - template_snapshot_id must be non-empty
        - parent_version_id must differ from template_snapshot_id (no self-reference)
    """

    id: str
    template_id: str
    version_number: int
    template_snapshot_id: str
    parent_version_id: Optional[str] = None
    change_description: str = ""
    diff: Optional[VersionDiff] = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[str] = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate version invariants."""
        if not self.id or not self.id.strip():
            raise ValueError("PromptVersion.id cannot be empty")

        if not self.template_id or not self.template_id.strip():
            raise ValueError("PromptVersion.template_id cannot be empty")

        if self.version_number < 1:
            raise ValueError(
                f"PromptVersion.version_number must be positive, got: {self.version_number}"
            )

        if not self.template_snapshot_id or not self.template_snapshot_id.strip():
            raise ValueError("PromptVersion.template_snapshot_id cannot be empty")

        # Ensure tags is a tuple (immutable)
        if isinstance(self.tags, list):  # type: ignore[unreachable]
            object.__setattr__(self, "tags", tuple(self.tags))

        # No self-reference in parent
        if self.parent_version_id == self.template_snapshot_id:
            raise ValueError("PromptVersion.parent_version_id cannot reference itself")

        # First version should not have a parent
        if self.version_number == 1 and self.parent_version_id is not None:
            raise ValueError("PromptVersion.version_number=1 cannot have a parent_version_id")

        # Later versions should have a parent
        if self.version_number > 1 and self.parent_version_id is None:
            # This is allowed for cases where we import existing versions
            pass

        # Normalize timestamp to UTC
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "created_at", self.created_at.astimezone(timezone.utc))

    def is_first_version(self) -> bool:
        """Check if this is the first version."""
        return self.version_number == 1

    def is_rollback_target(self) -> bool:
        """Check if this version is tagged as a rollback target."""
        return "rollback" in self.tags or "stable" in self.tags

    def get_lineage_description(self) -> str:
        """
        Get a human-readable description of this version's lineage.

        Returns:
            Description like "v1 (initial)" or "v3 (from v2)"
        """
        if self.is_first_version():
            return f"v{self.version_number} (initial)"
        parent_v = "unknown" if self.parent_version_id is None else f"v{self.version_number - 1}"
        return f"v{self.version_number} (from {parent_v})"

    def add_tag(self, tag: str) -> PromptVersion:
        """
        Add a tag to this version.

        Args:
            tag: Tag to add

        Returns:
            Self for method chaining
        """
        current_tags = list(self.tags)
        if tag not in current_tags:
            current_tags.append(tag)
        object.__setattr__(self, "tags", tuple(current_tags))
        return self

    def to_dict(self) -> dict:
        """
        Convert version to dictionary for serialization.

        Returns:
            Dictionary representation of the version
        """
        return {
            "id": self.id,
            "template_id": self.template_id,
            "version_number": self.version_number,
            "template_snapshot_id": self.template_snapshot_id,
            "parent_version_id": self.parent_version_id,
            "change_description": self.change_description,
            "diff": {
                "content_changed": self.diff.content_changed if self.diff else False,
                "variables_changed": self.diff.variables_changed if self.diff else False,
                "model_config_changed": self.diff.model_config_changed if self.diff else False,
                "metadata_changed": self.diff.metadata_changed if self.diff else False,
                "description": self.diff.description if self.diff else "",
            } if self.diff else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "tags": list(self.tags),
        }

    @classmethod
    def from_template(
        cls,
        template_id: str,
        version_number: int,
        template_snapshot_id: str,
        parent_version_id: str | None = None,
        change_description: str = "",
        diff: VersionDiff | None = None,
        created_by: str | None = None,
        tags: tuple[str, ...] | None = None,
        id: str | None = None,
    ) -> PromptVersion:
        """
        Create a PromptVersion from template information.

        Why factory method:
            Convenient creation when you have template data available.

        Args:
            template_id: ID of the template this version belongs to
            version_number: Version number
            template_snapshot_id: ID of the actual template snapshot
            parent_version_id: ID of the previous version
            change_description: Description of changes
            diff: Structured diff of changes
            created_by: Optional creator identifier
            tags: Tags for this version
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            PromptVersion instance
        """
        return cls(
            id=id or str(uuid4()),
            template_id=template_id,
            version_number=version_number,
            template_snapshot_id=template_snapshot_id,
            parent_version_id=parent_version_id,
            change_description=change_description,
            diff=diff,
            created_by=created_by,
            tags=tags or (),
        )


__all__ = [
    "PromptVersion",
    "VersionDiff",
]
