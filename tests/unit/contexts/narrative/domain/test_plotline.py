"""Unit Tests for Plotline Entity - Director Mode Features.

This test suite covers the Plotline entity for Director Mode,
testing plotline creation, validation, and state transitions.
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.domain.entities.plotline import (
    Plotline,
    PlotlineStatus,
)

pytestmark = pytest.mark.unit


class TestPlotlineCreation:
    """Test suite for Plotline entity creation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_plotline_with_required_fields(self):
        """Test creating a plotline with minimal required fields."""
        plotline = Plotline(
            name="Romance Arc",
            color="#ff5733",
        )

        assert plotline.name == "Romance Arc"
        assert plotline.color == "#ff5733"
        assert plotline.description == ""
        assert plotline.status == PlotlineStatus.ACTIVE  # default
        assert plotline.id is not None
        assert plotline.created_at is not None
        assert plotline.updated_at is not None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_plotline_with_all_fields(self):
        """Test creating a plotline with all fields specified."""
        plotline = Plotline(
            name="Mystery Investigation",
            color="#00ff88",
            description="Detective tracks the killer",
            status=PlotlineStatus.RESOLVED,
        )

        assert plotline.name == "Mystery Investigation"
        assert plotline.color == "#00ff88"
        assert plotline.description == "Detective tracks the killer"
        assert plotline.status == PlotlineStatus.RESOLVED

    @pytest.mark.unit
    def test_create_plotline_with_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Plotline name cannot be empty"):
            Plotline(
                name="",
                color="#ff5733",
            )

    @pytest.mark.unit
    def test_create_plotline_with_whitespace_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Plotline name cannot be empty"):
            Plotline(
                name="   ",
                color="#ff5733",
            )

    @pytest.mark.unit
    def test_create_plotline_with_invalid_color_no_hash_raises_error(self):
        """Test that color without # raises ValueError."""
        with pytest.raises(ValueError, match="Plotline color must be a hex color code"):
            Plotline(
                name="Test",
                color="ff5733",
            )

    @pytest.mark.unit
    def test_create_plotline_with_invalid_color_length_raises_error(self):
        """Test that invalid color length raises ValueError."""
        with pytest.raises(
            ValueError, match="Plotline color must be 3, 6, or 8 hex characters"
        ):
            Plotline(
                name="Test",
                color="#ff57",
            )

    @pytest.mark.unit
    def test_create_plotline_with_invalid_color_chars_raises_error(self):
        """Test that invalid hex characters raise ValueError."""
        with pytest.raises(
            ValueError, match="Plotline color contains invalid hex characters"
        ):
            Plotline(
                name="Test",
                color="#gggggg",
            )


class TestPlotlineColorFormats:
    """Test suite for valid color format variations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_plotline_with_short_hex_color(self):
        """Test creating a plotline with 3-character hex color."""
        plotline = Plotline(
            name="Test",
            color="#f00",
        )
        assert plotline.color == "#f00"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_plotline_with_standard_hex_color(self):
        """Test creating a plotline with 6-character hex color."""
        plotline = Plotline(
            name="Test",
            color="#ff0000",
        )
        assert plotline.color == "#ff0000"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_plotline_with_alpha_hex_color(self):
        """Test creating a plotline with 8-character hex color (with alpha)."""
        plotline = Plotline(
            name="Test",
            color="#ff000080",
        )
        assert plotline.color == "#ff000080"


class TestPlotlineStatus:
    """Test suite for Plotline status states."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_status_is_active(self):
        """Test that new plotlines default to active status."""
        plotline = Plotline(
            name="Hero's Journey",
            color="#3366ff",
        )
        assert plotline.status == PlotlineStatus.ACTIVE
        assert plotline.is_active

    @pytest.mark.unit
    @pytest.mark.fast
    def test_resolve_plotline(self):
        """Test resolving a plotline."""
        plotline = Plotline(
            name="Side Quest",
            color="#33ff66",
        )
        original_updated_at = plotline.updated_at

        plotline.resolve()

        assert plotline.status == PlotlineStatus.RESOLVED
        assert plotline.is_resolved
        assert not plotline.is_active
        assert plotline.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_abandon_plotline(self):
        """Test abandoning a plotline."""
        plotline = Plotline(
            name="Cut Content",
            color="#999999",
        )

        plotline.abandon()

        assert plotline.status == PlotlineStatus.ABANDONED
        assert not plotline.is_active
        assert not plotline.is_resolved

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reactivate_resolved_plotline(self):
        """Test reactivating a resolved plotline."""
        plotline = Plotline(
            name="Series",
            color="#ff33ff",
            status=PlotlineStatus.RESOLVED,
        )

        plotline.reactivate()

        assert plotline.status == PlotlineStatus.ACTIVE
        assert plotline.is_active

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reactivate_abandoned_plotline(self):
        """Test reactivating an abandoned plotline."""
        plotline = Plotline(
            name="B Plot",
            color="#33ffff",
            status=PlotlineStatus.ABANDONED,
        )

        plotline.reactivate()

        assert plotline.status == PlotlineStatus.ACTIVE
        assert plotline.is_active


class TestPlotlineUpdates:
    """Test suite for Plotline update methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_name(self):
        """Test updating plotline name."""
        plotline = Plotline(
            name="Original Name",
            color="#ff5733",
        )
        original_updated_at = plotline.updated_at

        plotline.update_name("New Name")

        assert plotline.name == "New Name"
        assert plotline.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_name_with_empty_raises_error(self):
        """Test that updating to empty name raises ValueError."""
        plotline = Plotline(
            name="Original",
            color="#ff5733",
        )

        with pytest.raises(ValueError, match="Plotline name cannot be empty"):
            plotline.update_name("")

    @pytest.mark.unit
    def test_update_name_with_whitespace_raises_error(self):
        """Test that updating to whitespace-only name raises ValueError."""
        plotline = Plotline(
            name="Original",
            color="#ff5733",
        )

        with pytest.raises(ValueError, match="Plotline name cannot be empty"):
            plotline.update_name("   ")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_description(self):
        """Test updating plotline description."""
        plotline = Plotline(
            name="Test",
            color="#ff5733",
            description="Original description",
        )
        original_updated_at = plotline.updated_at

        plotline.update_description("New description")

        assert plotline.description == "New description"
        assert plotline.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_color(self):
        """Test updating plotline color."""
        plotline = Plotline(
            name="Test",
            color="#ff0000",
        )
        original_updated_at = plotline.updated_at

        plotline.update_color("#00ff00")

        assert plotline.color == "#00ff00"
        assert plotline.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_color_with_invalid_format_raises_error(self):
        """Test that updating to invalid color raises ValueError."""
        plotline = Plotline(
            name="Test",
            color="#ff0000",
        )

        with pytest.raises(ValueError, match="Plotline color must be a hex color code"):
            plotline.update_color("invalid")

    @pytest.mark.unit
    def test_update_color_with_invalid_chars_raises_error(self):
        """Test that updating to color with invalid chars raises ValueError."""
        plotline = Plotline(
            name="Test",
            color="#ff0000",
        )

        with pytest.raises(
            ValueError, match="Plotline color contains invalid hex characters"
        ):
            plotline.update_color("#gggggg")


class TestPlotlineProperties:
    """Test suite for Plotline convenience properties."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_active_property(self):
        """Test is_active property."""
        active_plotline = Plotline(
            name="Active",
            color="#ff5733",
            status=PlotlineStatus.ACTIVE,
        )
        resolved_plotline = Plotline(
            name="Resolved",
            color="#ff5733",
            status=PlotlineStatus.RESOLVED,
        )
        abandoned_plotline = Plotline(
            name="Abandoned",
            color="#ff5733",
            status=PlotlineStatus.ABANDONED,
        )

        assert active_plotline.is_active
        assert not resolved_plotline.is_active
        assert not abandoned_plotline.is_active

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_resolved_property(self):
        """Test is_resolved property."""
        active_plotline = Plotline(
            name="Active",
            color="#ff5733",
            status=PlotlineStatus.ACTIVE,
        )
        resolved_plotline = Plotline(
            name="Resolved",
            color="#ff5733",
            status=PlotlineStatus.RESOLVED,
        )

        assert not active_plotline.is_resolved
        assert resolved_plotline.is_resolved


class TestPlotlineStringRepresentations:
    """Test suite for Plotline string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation includes key info."""
        plotline = Plotline(
            name="Love Story",
            color="#ff69b4",
        )
        str_repr = str(plotline)

        assert "Plotline" in str_repr
        assert "Love Story" in str_repr
        assert "#ff69b4" in str_repr
        assert "active" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr includes full debugging info."""
        plotline = Plotline(
            name="Test Plotline",
            color="#123456",
        )
        repr_str = repr(plotline)

        assert "Plotline" in repr_str
        assert "id=" in repr_str
        assert "name='Test Plotline'" in repr_str
        assert "color=#123456" in repr_str
        assert "status=active" in repr_str


class TestPlotlineEnums:
    """Test suite for Plotline enum values."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_plotline_status_enum_values(self):
        """Test all PlotlineStatus enum values."""
        assert PlotlineStatus.ACTIVE.value == "active"
        assert PlotlineStatus.RESOLVED.value == "resolved"
        assert PlotlineStatus.ABANDONED.value == "abandoned"
