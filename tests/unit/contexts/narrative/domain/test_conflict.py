"""Unit Tests for Conflict Entity - Director Mode Features.

This test suite covers the Conflict entity for Director Mode,
testing conflict creation, validation, and state transitions.
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.domain.entities.conflict import (
    Conflict,
    ConflictType,
    ConflictStakes,
    ResolutionStatus,
)


class TestConflictCreation:
    """Test suite for Conflict entity creation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_conflict_with_required_fields(self):
        """Test creating a conflict with minimal required fields."""
        scene_id = uuid4()
        conflict = Conflict(
            scene_id=scene_id,
            conflict_type=ConflictType.INTERNAL,
            description="Character struggles with guilt",
        )

        assert conflict.scene_id == scene_id
        assert conflict.conflict_type == ConflictType.INTERNAL
        assert conflict.description == "Character struggles with guilt"
        assert conflict.stakes == ConflictStakes.MEDIUM  # default
        assert conflict.resolution_status == ResolutionStatus.UNRESOLVED  # default
        assert conflict.id is not None
        assert conflict.created_at is not None
        assert conflict.updated_at is not None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_conflict_with_all_fields(self):
        """Test creating a conflict with all fields specified."""
        scene_id = uuid4()
        conflict = Conflict(
            scene_id=scene_id,
            conflict_type=ConflictType.EXTERNAL,
            stakes=ConflictStakes.CRITICAL,
            description="Storm threatens the ship",
            resolution_status=ResolutionStatus.ESCALATING,
        )

        assert conflict.conflict_type == ConflictType.EXTERNAL
        assert conflict.stakes == ConflictStakes.CRITICAL
        assert conflict.description == "Storm threatens the ship"
        assert conflict.resolution_status == ResolutionStatus.ESCALATING

    @pytest.mark.unit
    def test_create_conflict_with_empty_description_raises_error(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="Conflict description cannot be empty"):
            Conflict(
                scene_id=uuid4(),
                conflict_type=ConflictType.INTERPERSONAL,
                description="",
            )

    @pytest.mark.unit
    def test_create_conflict_with_whitespace_description_raises_error(self):
        """Test that whitespace-only description raises ValueError."""
        with pytest.raises(ValueError, match="Conflict description cannot be empty"):
            Conflict(
                scene_id=uuid4(),
                conflict_type=ConflictType.INTERPERSONAL,
                description="   ",
            )


class TestConflictTypes:
    """Test suite for Conflict type classifications."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_internal_conflict_type(self):
        """Test creating an internal conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Hero questions their morals",
        )
        assert conflict.conflict_type == ConflictType.INTERNAL
        assert conflict.conflict_type.value == "internal"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_external_conflict_type(self):
        """Test creating an external conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            description="Volcano eruption threatens village",
        )
        assert conflict.conflict_type == ConflictType.EXTERNAL
        assert conflict.conflict_type.value == "external"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_interpersonal_conflict_type(self):
        """Test creating an interpersonal conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERPERSONAL,
            description="Rivals compete for promotion",
        )
        assert conflict.conflict_type == ConflictType.INTERPERSONAL
        assert conflict.conflict_type.value == "interpersonal"


class TestConflictStakes:
    """Test suite for Conflict stakes levels."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_low_stakes(self):
        """Test creating a low stakes conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERPERSONAL,
            stakes=ConflictStakes.LOW,
            description="Friends argue over restaurant choice",
        )
        assert conflict.stakes == ConflictStakes.LOW
        assert conflict.stakes.value == "low"
        assert not conflict.is_critical

    @pytest.mark.unit
    @pytest.mark.fast
    def test_medium_stakes(self):
        """Test creating a medium stakes conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERPERSONAL,
            stakes=ConflictStakes.MEDIUM,
            description="Business partnership in jeopardy",
        )
        assert conflict.stakes == ConflictStakes.MEDIUM
        assert not conflict.is_critical

    @pytest.mark.unit
    @pytest.mark.fast
    def test_high_stakes(self):
        """Test creating a high stakes conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            stakes=ConflictStakes.HIGH,
            description="Career-ending scandal looms",
        )
        assert conflict.stakes == ConflictStakes.HIGH
        assert not conflict.is_critical

    @pytest.mark.unit
    @pytest.mark.fast
    def test_critical_stakes(self):
        """Test creating a critical stakes conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            stakes=ConflictStakes.CRITICAL,
            description="Life or death situation",
        )
        assert conflict.stakes == ConflictStakes.CRITICAL
        assert conflict.is_critical


class TestConflictResolution:
    """Test suite for Conflict resolution state transitions."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_resolution_status_is_unresolved(self):
        """Test that new conflicts default to unresolved status."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Hero doubts their abilities",
        )
        assert conflict.resolution_status == ResolutionStatus.UNRESOLVED
        assert not conflict.is_resolved

    @pytest.mark.unit
    @pytest.mark.fast
    def test_escalate_conflict(self):
        """Test escalating a conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERPERSONAL,
            description="Tension between characters",
        )
        original_updated_at = conflict.updated_at

        conflict.escalate()

        assert conflict.resolution_status == ResolutionStatus.ESCALATING
        assert not conflict.is_resolved
        assert conflict.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_resolve_conflict(self):
        """Test resolving a conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            description="Storm threatens ship",
        )
        original_updated_at = conflict.updated_at

        conflict.resolve()

        assert conflict.resolution_status == ResolutionStatus.RESOLVED
        assert conflict.is_resolved
        assert conflict.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reopen_resolved_conflict(self):
        """Test reopening a resolved conflict."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Hero's past trauma",
            resolution_status=ResolutionStatus.RESOLVED,
        )

        conflict.reopen()

        assert conflict.resolution_status == ResolutionStatus.UNRESOLVED
        assert not conflict.is_resolved


class TestConflictUpdates:
    """Test suite for Conflict update methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_description(self):
        """Test updating conflict description."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Original description",
        )
        original_updated_at = conflict.updated_at

        conflict.update_description("Updated description")

        assert conflict.description == "Updated description"
        assert conflict.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_description_with_empty_raises_error(self):
        """Test that updating to empty description raises ValueError."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Original description",
        )

        with pytest.raises(ValueError, match="Conflict description cannot be empty"):
            conflict.update_description("")

    @pytest.mark.unit
    def test_update_description_with_whitespace_raises_error(self):
        """Test that updating to whitespace-only description raises ValueError."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Original description",
        )

        with pytest.raises(ValueError, match="Conflict description cannot be empty"):
            conflict.update_description("   ")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_conflict_type(self):
        """Test updating conflict type."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERNAL,
            description="Character conflict",
        )
        original_updated_at = conflict.updated_at

        conflict.update_conflict_type(ConflictType.EXTERNAL)

        assert conflict.conflict_type == ConflictType.EXTERNAL
        assert conflict.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_stakes(self):
        """Test updating stakes level."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            stakes=ConflictStakes.LOW,
            description="Minor obstacle",
        )
        original_updated_at = conflict.updated_at

        conflict.update_stakes(ConflictStakes.CRITICAL)

        assert conflict.stakes == ConflictStakes.CRITICAL
        assert conflict.is_critical
        assert conflict.updated_at >= original_updated_at


class TestConflictStringRepresentations:
    """Test suite for Conflict string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation includes key info."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.INTERPERSONAL,
            stakes=ConflictStakes.HIGH,
            description="A very long description that should be truncated in the str output",
        )
        str_repr = str(conflict)

        assert "Conflict" in str_repr
        assert "interpersonal" in str_repr
        assert "high" in str_repr
        assert "unresolved" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr includes full debugging info."""
        conflict = Conflict(
            scene_id=uuid4(),
            conflict_type=ConflictType.EXTERNAL,
            stakes=ConflictStakes.MEDIUM,
            description="Test conflict",
        )
        repr_str = repr(conflict)

        assert "Conflict" in repr_str
        assert "id=" in repr_str
        assert "scene_id=" in repr_str
        assert "type=external" in repr_str
        assert "stakes=medium" in repr_str
        assert "status=unresolved" in repr_str


class TestConflictEnums:
    """Test suite for Conflict enum values."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_conflict_type_enum_values(self):
        """Test all ConflictType enum values."""
        assert ConflictType.INTERNAL.value == "internal"
        assert ConflictType.EXTERNAL.value == "external"
        assert ConflictType.INTERPERSONAL.value == "interpersonal"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_conflict_stakes_enum_values(self):
        """Test all ConflictStakes enum values."""
        assert ConflictStakes.LOW.value == "low"
        assert ConflictStakes.MEDIUM.value == "medium"
        assert ConflictStakes.HIGH.value == "high"
        assert ConflictStakes.CRITICAL.value == "critical"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_resolution_status_enum_values(self):
        """Test all ResolutionStatus enum values."""
        assert ResolutionStatus.UNRESOLVED.value == "unresolved"
        assert ResolutionStatus.ESCALATING.value == "escalating"
        assert ResolutionStatus.RESOLVED.value == "resolved"
