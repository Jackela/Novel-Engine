"""
Unit Tests for KnowledgeMetadata Value Object

Tests the structured metadata for knowledge entries.

OPT-006: Domain: Structured Metadata Schema
Tests value object creation, validation, serialization, and timezone handling.

Constitution Compliance:
- Article III (TDD): Tests written to validate value object behavior
- Article I (DDD): Tests value object invariants and behaviors
"""

import datetime
from datetime import timezone, timedelta

import pytest

from src.contexts.knowledge.domain.models.knowledge_metadata import (
    ConfidentialityLevel,
    KnowledgeMetadata,
)


class TestConfidentialityLevel:
    """Unit tests for ConfidentialityLevel enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_confidentiality_levels(self):
        """Test all confidentiality levels are defined."""
        assert ConfidentialityLevel.PUBLIC.value == "public"
        assert ConfidentialityLevel.INTERNAL.value == "internal"
        assert ConfidentialityLevel.RESTRICTED.value == "restricted"
        assert ConfidentialityLevel.SENSITIVE.value == "sensitive"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_confidentiality_from_string(self):
        """Test creating ConfidentialityLevel from string."""
        assert ConfidentialityLevel("public") == ConfidentialityLevel.PUBLIC
        assert ConfidentialityLevel("internal") == ConfidentialityLevel.INTERNAL
        assert ConfidentialityLevel("restricted") == ConfidentialityLevel.RESTRICTED
        assert ConfidentialityLevel("sensitive") == ConfidentialityLevel.SENSITIVE


class TestKnowledgeMetadata:
    """Unit tests for KnowledgeMetadata value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_with_required_fields(self):
        """Test creating metadata with required fields only."""
        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
        )

        assert metadata.world_version == "1.0.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC
        assert metadata.last_accessed is None
        assert metadata.source_version == 1  # Default

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_with_all_fields(self):
        """Test creating metadata with all fields."""
        now = datetime.datetime.now(timezone.utc)
        metadata = KnowledgeMetadata(
            world_version="2.1.0",
            confidentiality_level=ConfidentialityLevel.RESTRICTED,
            last_accessed=now,
            source_version=3,
        )

        assert metadata.world_version == "2.1.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.RESTRICTED
        assert metadata.last_accessed == now
        assert metadata.source_version == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_world_version_is_normalized(self):
        """Test that world_version is stripped of whitespace."""
        metadata = KnowledgeMetadata(
            world_version="  1.5.0  ",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
        )

        assert metadata.world_version == "1.5.0"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_world_version_cannot_be_empty(self):
        """Test that empty world_version raises ValueError."""
        with pytest.raises(ValueError, match="world_version cannot be empty"):
            KnowledgeMetadata(
                world_version="",
                confidentiality_level=ConfidentialityLevel.PUBLIC,
            )

        with pytest.raises(ValueError, match="world_version cannot be empty"):
            KnowledgeMetadata(
                world_version="   ",
                confidentiality_level=ConfidentialityLevel.PUBLIC,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_version_minimum(self):
        """Test that source_version must be at least 1."""
        with pytest.raises(ValueError, match="source_version must be at least 1"):
            KnowledgeMetadata(
                world_version="1.0.0",
                confidentiality_level=ConfidentialityLevel.PUBLIC,
                source_version=0,
            )

        with pytest.raises(ValueError, match="source_version must be at least 1"):
            KnowledgeMetadata(
                world_version="1.0.0",
                confidentiality_level=ConfidentialityLevel.PUBLIC,
                source_version=-1,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_timezone_normalization_for_last_accessed(self):
        """Test that last_accessed is normalized to UTC."""
        # Create a datetime with a different timezone
        eastern = timezone(timedelta(hours=-5))
        local_time = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=eastern)

        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
            last_accessed=local_time,
        )

        # Should be converted to UTC
        assert metadata.last_accessed.tzinfo == timezone.utc
        assert metadata.last_accessed.hour == 17  # 12 PM Eastern = 5 PM UTC

    @pytest.mark.unit
    @pytest.mark.fast
    def test_timezone_added_to_naive_datetime(self):
        """Test that naive datetime gets UTC timezone."""
        naive_time = datetime.datetime(2025, 1, 1, 12, 0, 0)

        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
            last_accessed=naive_time,
        )

        # Should have UTC timezone added
        assert metadata.last_accessed.tzinfo == timezone.utc

    @pytest.mark.unit
    @pytest.mark.fast
    def test_metadata_is_immutable(self):
        """Test that KnowledgeMetadata is frozen (immutable)."""
        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
        )

        # Attempting to modify should raise
        with pytest.raises(Exception):  # FrozenInstanceError
            metadata.world_version = "2.0.0"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_with_access(self):
        """Test with_access returns new instance with updated last_accessed."""
        before = datetime.datetime.now(timezone.utc) - timedelta(hours=1)

        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
            last_accessed=before,
        )

        # Update access time
        updated = metadata.with_access()

        # Original should be unchanged (immutability)
        assert metadata.last_accessed == before

        # Updated should have new timestamp
        assert updated.last_accessed is not None
        assert updated.last_accessed > before

        # Other fields should be the same
        assert updated.world_version == metadata.world_version
        assert updated.confidentiality_level == metadata.confidentiality_level
        assert updated.source_version == metadata.source_version

    @pytest.mark.unit
    @pytest.mark.fast
    def test_with_version(self):
        """Test with_version returns new instance with updated source_version."""
        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
            source_version=1,
        )

        # Update version
        updated = metadata.with_version(5)

        # Original should be unchanged (immutability)
        assert metadata.source_version == 1

        # Updated should have new version
        assert updated.source_version == 5

        # Other fields should be the same
        assert updated.world_version == metadata.world_version
        assert updated.confidentiality_level == metadata.confidentiality_level

    @pytest.mark.unit
    @pytest.mark.fast
    def test_with_version_validates_minimum(self):
        """Test that with_version validates minimum version."""
        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
        )

        with pytest.raises(ValueError, match="source_version must be at least 1"):
            metadata.with_version(0)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        metadata = KnowledgeMetadata(
            world_version="1.5.0",
            confidentiality_level=ConfidentialityLevel.RESTRICTED,
            last_accessed=now,
            source_version=2,
        )

        result = metadata.to_dict()

        assert result == {
            "world_version": "1.5.0",
            "confidentiality_level": "restricted",
            "last_accessed": "2025-01-01T12:00:00+00:00",
            "source_version": 2,
        }

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict_with_none_last_accessed(self):
        """Test serialization with None last_accessed."""
        metadata = KnowledgeMetadata(
            world_version="1.0.0",
            confidentiality_level=ConfidentialityLevel.PUBLIC,
            last_accessed=None,
        )

        result = metadata.to_dict()

        assert result["last_accessed"] is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "world_version": "2.0.0",
            "confidentiality_level": "internal",
            "last_accessed": "2025-01-01T12:00:00+00:00",
            "source_version": 3,
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.world_version == "2.0.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.INTERNAL
        assert metadata.last_accessed == datetime.datetime(
            2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        assert metadata.source_version == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_with_missing_optional_fields(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {
            "world_version": "1.0.0",
            "confidentiality_level": "public",
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.world_version == "1.0.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC
        assert metadata.last_accessed is None
        assert metadata.source_version == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_validates_world_version(self):
        """Test that from_dict requires world_version."""
        with pytest.raises(ValueError, match="world_version is required"):
            KnowledgeMetadata.from_dict({})

        with pytest.raises(ValueError, match="world_version is required"):
            KnowledgeMetadata.from_dict({"world_version": ""})

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_handles_invalid_confidentiality_level(self):
        """Test that invalid confidentiality level defaults to PUBLIC."""
        data = {
            "world_version": "1.0.0",
            "confidentiality_level": "invalid_level",
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_handles_invalid_last_accessed(self):
        """Test that invalid last_accessed is ignored (defaults to None)."""
        data = {
            "world_version": "1.0.0",
            "confidentiality_level": "public",
            "last_accessed": "not-a-date",
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.last_accessed is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_handles_invalid_source_version(self):
        """Test that invalid source_version defaults to 1."""
        data = {
            "world_version": "1.0.0",
            "confidentiality_level": "public",
            "source_version": "not-a-number",
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.source_version == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_handles_negative_source_version(self):
        """Test that negative source_version defaults to 1."""
        data = {
            "world_version": "1.0.0",
            "confidentiality_level": "public",
            "source_version": -5,
        }

        metadata = KnowledgeMetadata.from_dict(data)

        assert metadata.source_version == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict_to_dict_roundtrip(self):
        """Test that from_dict -> to_dict preserves data."""
        original = KnowledgeMetadata(
            world_version="3.2.1",
            confidentiality_level=ConfidentialityLevel.SENSITIVE,
            last_accessed=datetime.datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
            source_version=5,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = KnowledgeMetadata.from_dict(data)

        # Should be equal
        assert restored.world_version == original.world_version
        assert restored.confidentiality_level == original.confidentiality_level
        assert restored.last_accessed == original.last_accessed
        assert restored.source_version == original.source_version

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_default(self):
        """Test create_default factory method."""
        metadata = KnowledgeMetadata.create_default()

        assert metadata.world_version == "1.0.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC
        assert metadata.last_accessed is None
        assert metadata.source_version == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_default_with_custom_world_version(self):
        """Test create_default with custom world_version."""
        metadata = KnowledgeMetadata.create_default(world_version="2.5.0")

        assert metadata.world_version == "2.5.0"
        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_default_with_custom_confidentiality(self):
        """Test create_default with custom confidentiality_level (string)."""
        metadata = KnowledgeMetadata.create_default(
            world_version="1.0.0",
            confidentiality_level="restricted",
        )

        assert metadata.confidentiality_level == ConfidentialityLevel.RESTRICTED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_default_with_invalid_confidentiality(self):
        """Test create_default with invalid confidentiality defaults to PUBLIC."""
        metadata = KnowledgeMetadata.create_default(
            world_version="1.0.0",
            confidentiality_level="invalid",
        )

        assert metadata.confidentiality_level == ConfidentialityLevel.PUBLIC
