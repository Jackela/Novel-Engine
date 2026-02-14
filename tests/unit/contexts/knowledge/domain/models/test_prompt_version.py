"""
Unit Tests for PromptVersion Entity

Warzone 4: AI Brain - BRAIN-016A
Tests for PromptVersion and VersionDiff value objects.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.domain.models.prompt_version import (
    PromptVersion,
    VersionDiff,
)

pytestmark = pytest.mark.unit

class TestVersionDiff:
    """Tests for VersionDiff value object."""

    def test_create_no_changes_diff(self) -> None:
        """Should create a diff with no changes."""
        diff = VersionDiff.no_changes()
        assert diff.content_changed is False
        assert diff.variables_changed is False
        assert diff.model_config_changed is False
        assert diff.metadata_changed is False
        assert diff.description == "No changes"
        assert bool(diff) is False

    def test_create_content_change_diff(self) -> None:
        """Should create a diff with content changes."""
        diff = VersionDiff(
            content_changed=True,
            variables_changed=False,
            model_config_changed=False,
            metadata_changed=False,
            description="Updated prompt content",
        )
        assert diff.content_changed is True
        assert bool(diff) is True

    def test_create_multiple_changes_diff(self) -> None:
        """Should create a diff with multiple changes."""
        diff = VersionDiff(
            content_changed=True,
            variables_changed=True,
            model_config_changed=False,
            metadata_changed=True,
            description="Major update",
        )
        assert diff.content_changed is True
        assert diff.variables_changed is True
        assert diff.metadata_changed is True
        assert diff.model_config_changed is False

    def test_bool_conversion(self) -> None:
        """Should return False when no changes, True otherwise."""
        no_changes = VersionDiff(
            content_changed=False,
            variables_changed=False,
            model_config_changed=False,
            metadata_changed=False,
        )
        assert bool(no_changes) is False

        with_changes = VersionDiff(
            content_changed=False,
            variables_changed=False,
            model_config_changed=True,
            metadata_changed=False,
        )
        assert bool(with_changes) is True


class TestPromptVersion:
    """Tests for PromptVersion entity."""

    def test_create_first_version(self) -> None:
        """Should create a valid first version."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        assert version.id == "version-1"
        assert version.template_id == "template-1"
        assert version.version_number == 1
        assert version.template_snapshot_id == "snapshot-1"
        assert version.parent_version_id is None
        assert version.is_first_version() is True

    def test_create_second_version_with_parent(self) -> None:
        """Should create a valid second version with parent reference."""
        version = PromptVersion(
            id="version-2",
            template_id="template-1",
            version_number=2,
            template_snapshot_id="snapshot-2",
            parent_version_id="snapshot-1",
        )

        assert version.version_number == 2
        assert version.parent_version_id == "snapshot-1"
        assert version.is_first_version() is False

    def test_id_cannot_be_empty(self) -> None:
        """Should raise error for empty ID."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            PromptVersion(
                id="",
                template_id="template-1",
                version_number=1,
                template_snapshot_id="snapshot-1",
            )

    def test_template_id_cannot_be_empty(self) -> None:
        """Should raise error for empty template_id."""
        with pytest.raises(ValueError, match="template_id cannot be empty"):
            PromptVersion(
                id="version-1",
                template_id="",
                version_number=1,
                template_snapshot_id="snapshot-1",
            )

    def test_template_snapshot_id_cannot_be_empty(self) -> None:
        """Should raise error for empty template_snapshot_id."""
        with pytest.raises(ValueError, match="template_snapshot_id cannot be empty"):
            PromptVersion(
                id="version-1",
                template_id="template-1",
                version_number=1,
                template_snapshot_id="",
            )

    def test_version_number_must_be_positive(self) -> None:
        """Should raise error for non-positive version_number."""
        with pytest.raises(ValueError, match="version_number must be positive"):
            PromptVersion(
                id="version-1",
                template_id="template-1",
                version_number=0,
                template_snapshot_id="snapshot-1",
            )

        with pytest.raises(ValueError, match="version_number must be positive"):
            PromptVersion(
                id="version-1",
                template_id="template-1",
                version_number=-1,
                template_snapshot_id="snapshot-1",
            )

    def test_first_version_cannot_have_parent(self) -> None:
        """Should raise error when version 1 has a parent."""
        with pytest.raises(ValueError, match="version_number=1 cannot have a parent"):
            PromptVersion(
                id="version-1",
                template_id="template-1",
                version_number=1,
                template_snapshot_id="snapshot-1",
                parent_version_id="snapshot-0",
            )

    def test_cannot_reference_self_as_parent(self) -> None:
        """Should raise error when parent_version_id references self."""
        with pytest.raises(ValueError, match="parent_version_id cannot reference itself"):
            PromptVersion(
                id="version-2",
                template_id="template-1",
                version_number=2,
                template_snapshot_id="snapshot-2",
                parent_version_id="snapshot-2",
            )

    def test_tags_are_normalized_to_tuple(self) -> None:
        """Should convert list tags to tuple."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
            tags=["stable", "production"],
        )

        assert isinstance(version.tags, tuple)
        assert version.tags == ("stable", "production")

    def test_get_lineage_description_first_version(self) -> None:
        """Should return correct lineage description for first version."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        assert version.get_lineage_description() == "v1 (initial)"

    def test_get_lineage_description_later_version(self) -> None:
        """Should return correct lineage description for later version."""
        version = PromptVersion(
            id="version-3",
            template_id="template-1",
            version_number=3,
            template_snapshot_id="snapshot-3",
            parent_version_id="snapshot-2",
        )

        assert version.get_lineage_description() == "v3 (from v2)"

    def test_get_lineage_description_orphan_version(self) -> None:
        """Should handle version without parent gracefully."""
        version = PromptVersion(
            id="version-2",
            template_id="template-1",
            version_number=2,
            template_snapshot_id="snapshot-2",
            parent_version_id=None,  # No parent even though version > 1
        )

        assert version.get_lineage_description() == "v2 (from unknown)"

    def test_is_rollback_target_with_stable_tag(self) -> None:
        """Should identify stable tagged versions as rollback targets."""
        version = PromptVersion(
            id="version-5",
            template_id="template-1",
            version_number=5,
            template_snapshot_id="snapshot-5",
            tags=["stable", "production"],
        )

        assert version.is_rollback_target() is True

    def test_is_rollback_target_with_rollback_tag(self) -> None:
        """Should identify rollback tagged versions."""
        version = PromptVersion(
            id="version-5",
            template_id="template-1",
            version_number=5,
            template_snapshot_id="snapshot-5",
            tags=["rollback"],
        )

        assert version.is_rollback_target() is True

    def test_is_rollback_target_without_tags(self) -> None:
        """Should return False for versions without special tags."""
        version = PromptVersion(
            id="version-3",
            template_id="template-1",
            version_number=3,
            template_snapshot_id="snapshot-3",
        )

        assert version.is_rollback_target() is False

    def test_add_tag_new_tag(self) -> None:
        """Should add a new tag."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        result = version.add_tag("tested")
        assert "tested" in result.tags
        assert result is version  # Returns self for chaining

    def test_add_tag_duplicate(self) -> None:
        """Should not add duplicate tags."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
            tags=["stable"],
        )

        version.add_tag("stable")
        assert version.tags.count("stable") == 1

    def test_add_tag_chaining(self) -> None:
        """Should support method chaining for multiple tags."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        version.add_tag("tested").add_tag("approved")
        assert "tested" in version.tags
        assert "approved" in version.tags

    def test_to_dict_serialization(self) -> None:
        """Should serialize to dictionary correctly."""
        now = datetime.now(timezone.utc)
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
            change_description="Initial version",
            diff=VersionDiff(
                content_changed=True,
                variables_changed=False,
                model_config_changed=False,
                metadata_changed=False,
                description="Content updated",
            ),
            created_at=now,
            created_by="user-1",
            tags=("stable",),
        )

        data = version.to_dict()
        assert data["id"] == "version-1"
        assert data["template_id"] == "template-1"
        assert data["version_number"] == 1
        assert data["template_snapshot_id"] == "snapshot-1"
        assert data["parent_version_id"] is None
        assert data["change_description"] == "Initial version"
        assert data["diff"]["content_changed"] is True
        assert data["diff"]["description"] == "Content updated"
        assert data["created_at"] == now.isoformat()
        assert data["created_by"] == "user-1"
        assert data["tags"] == ["stable"]

    def test_to_dict_without_diff(self) -> None:
        """Should serialize without diff when None."""
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        data = version.to_dict()
        assert data["diff"] is None

    def test_from_template_factory(self) -> None:
        """Should create PromptVersion using factory method."""
        version = PromptVersion.from_template(
            template_id="template-1",
            version_number=2,
            template_snapshot_id="snapshot-2",
            parent_version_id="snapshot-1",
            change_description="Updated variables",
            diff=VersionDiff(
                content_changed=False,
                variables_changed=True,
                model_config_changed=False,
                metadata_changed=False,
            ),
            created_by="user-1",
            tags=["tested"],
        )

        assert version.template_id == "template-1"
        assert version.version_number == 2
        assert version.template_snapshot_id == "snapshot-2"
        assert version.parent_version_id == "snapshot-1"
        assert version.change_description == "Updated variables"
        assert version.diff is not None
        assert version.diff.variables_changed is True
        assert version.created_by == "user-1"
        assert "tested" in version.tags

    def test_from_template_auto_generates_id(self) -> None:
        """Should auto-generate ID when not provided."""
        version = PromptVersion.from_template(
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
        )

        assert version.id is not None
        assert len(version.id) > 0
        assert "-" in version.id  # UUID format

    def test_timestamp_normalized_to_utc(self) -> None:
        """Should normalize naive timestamps to UTC."""
        naive_time = datetime(2024, 1, 1, 12, 0, 0)
        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
            created_at=naive_time,
        )

        assert version.created_at.tzinfo == timezone.utc

    def test_timestamp_converts_to_utc(self) -> None:
        """Should convert non-UTC timestamps to UTC."""
        # Create a timestamp in a different timezone
        eastern = timezone(timedelta(hours=-5))
        eastern_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=eastern)

        version = PromptVersion(
            id="version-1",
            template_id="template-1",
            version_number=1,
            template_snapshot_id="snapshot-1",
            created_at=eastern_time,
        )

        assert version.created_at.tzinfo == timezone.utc
        # The time should be converted (12:00 EST = 17:00 UTC)
        assert version.created_at.hour == 17


class TestPromptVersionWithTemplate:
    """Integration tests for PromptVersion with PromptTemplate."""

    def test_create_version_from_template(self) -> None:
        """Should create PromptVersion tracking template changes."""
        # Create original template
        v1 = PromptTemplate.create(
            name="test-prompt",
            content="Original content: {{input}}",
            provider="openai",
            model_name="gpt-4",
        )

        # Create new version
        v2 = v1.create_new_version(content="Updated content: {{input}}")

        # Create version info for v2
        diff = VersionDiff(
            content_changed=True,
            variables_changed=False,
            model_config_changed=False,
            metadata_changed=False,
            description="Updated prompt content",
        )

        version = PromptVersion.from_template(
            template_id=v1.id,  # Track lineage by original template ID
            version_number=v2.version,
            template_snapshot_id=v2.id,
            parent_version_id=v1.id,
            change_description="Updated content",
            diff=diff,
        )

        assert version.version_number == 2
        assert version.parent_version_id == v1.id
        assert version.template_snapshot_id == v2.id
        assert version.diff is not None
        assert version.diff.content_changed is True

    def test_version_chain_multiple_updates(self) -> None:
        """Should track chain of multiple version updates."""
        # Create initial template
        v1 = PromptTemplate.create(
            name="test-prompt",
            content="v1: {{input}}",
        )

        # Create version chain
        v2 = v1.create_new_version(content="v2: {{input}}")
        v3 = v2.create_new_version(content="v3: {{input}}")

        # Create version records
        version_1 = PromptVersion.from_template(
            template_id=v1.id,
            version_number=v1.version,
            template_snapshot_id=v1.id,
        )
        version_2 = PromptVersion.from_template(
            template_id=v1.id,
            version_number=v2.version,
            template_snapshot_id=v2.id,
            parent_version_id=v1.id,
        )
        version_3 = PromptVersion.from_template(
            template_id=v1.id,
            version_number=v3.version,
            template_snapshot_id=v3.id,
            parent_version_id=v2.id,
        )

        # Verify chain
        assert version_1.version_number == 1
        assert version_1.parent_version_id is None

        assert version_2.version_number == 2
        assert version_2.parent_version_id == v1.id

        assert version_3.version_number == 3
        assert version_3.parent_version_id == v2.id

    def test_create_version_diff_from_template(self) -> None:
        """Should use PromptTemplate's create_version_diff method."""
        template = PromptTemplate.create(
            name="test-prompt",
            content="Original content",
            tags=("v1",),
        )

        diff_info = template.create_version_diff(
            content="New content",
            tags=("v2",),
        )

        assert diff_info["content_changed"] is True
        assert diff_info["tags_changed"] is True
        assert diff_info["variables_changed"] is False
        assert diff_info["model_config_changed"] is False
