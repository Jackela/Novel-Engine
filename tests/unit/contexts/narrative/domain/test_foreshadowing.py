"""Unit Tests for Foreshadowing Entity - Director Mode Features.

This test suite covers the Foreshadowing entity for Director Mode,
testing foreshadowing creation, validation, and payoff linking.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.contexts.narrative.domain.entities.foreshadowing import (
    Foreshadowing,
    ForeshadowingStatus,
)
from src.contexts.narrative.domain.entities.scene import Scene

pytestmark = pytest.mark.unit


class TestForeshadowingCreation:
    """Test suite for Foreshadowing entity creation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_foreshadowing_with_required_fields(self):
        """Test creating a foreshadowing with minimal required fields."""
        setup_scene_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene_id,
            description="The gun on the wall",
        )

        assert foreshadowing.setup_scene_id == setup_scene_id
        assert foreshadowing.description == "The gun on the wall"
        assert foreshadowing.status == ForeshadowingStatus.PLANTED  # default
        assert foreshadowing.payoff_scene_id is None  # default
        assert foreshadowing.id is not None
        assert foreshadowing.created_at is not None
        assert foreshadowing.updated_at is not None
        assert foreshadowing.is_planted

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_foreshadowing_with_all_fields(self):
        """Test creating a foreshadowing with all fields specified."""
        setup_scene_id = uuid4()
        payoff_scene_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene_id,
            description="The mysterious letter",
            payoff_scene_id=payoff_scene_id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        assert foreshadowing.setup_scene_id == setup_scene_id
        assert foreshadowing.description == "The mysterious letter"
        assert foreshadowing.payoff_scene_id == payoff_scene_id
        assert foreshadowing.status == ForeshadowingStatus.PAID_OFF
        assert foreshadowing.is_paid_off

    @pytest.mark.unit
    def test_create_foreshadowing_with_empty_description_raises_error(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(
            ValueError, match="Foreshadowing description cannot be empty"
        ):
            Foreshadowing(
                setup_scene_id=uuid4(),
                description="",
            )

    @pytest.mark.unit
    def test_create_foreshadowing_with_whitespace_description_raises_error(self):
        """Test that whitespace-only description raises ValueError."""
        with pytest.raises(
            ValueError, match="Foreshadowing description cannot be empty"
        ):
            Foreshadowing(
                setup_scene_id=uuid4(),
                description="   ",
            )

    @pytest.mark.unit
    def test_create_foreshadowing_paid_off_without_payoff_scene_raises_error(self):
        """Test that PAID_OFF status without payoff_scene_id raises ValueError."""
        with pytest.raises(
            ValueError, match="PAID_OFF status must have a payoff_scene_id"
        ):
            Foreshadowing(
                setup_scene_id=uuid4(),
                description="The setup",
                status=ForeshadowingStatus.PAID_OFF,
            )

    @pytest.mark.unit
    def test_create_foreshadowing_with_payoff_but_planted_status_raises_error(self):
        """Test that payoff_scene_id with PLANTED status raises ValueError."""
        with pytest.raises(
            ValueError, match="payoff_scene_id must have PAID_OFF status"
        ):
            Foreshadowing(
                setup_scene_id=uuid4(),
                description="The setup",
                payoff_scene_id=uuid4(),
                status=ForeshadowingStatus.PLANTED,
            )


class TestForeshadowingStatus:
    """Test suite for Foreshadowing status transitions."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_status_is_planted(self):
        """Test that new foreshadowings default to planted status."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The mysterious key",
        )
        assert foreshadowing.status == ForeshadowingStatus.PLANTED
        assert foreshadowing.is_planted
        assert not foreshadowing.is_paid_off
        assert not foreshadowing.is_abandoned

    @pytest.mark.unit
    @pytest.mark.fast
    def test_planted_properties(self):
        """Test planted status properties."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The prophecy",
            status=ForeshadowingStatus.PLANTED,
        )
        assert foreshadowing.is_planted
        assert not foreshadowing.is_paid_off
        assert not foreshadowing.is_abandoned

    @pytest.mark.unit
    @pytest.mark.fast
    def test_paid_off_properties(self):
        """Test paid_off status properties."""
        payoff_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The prophecy",
            payoff_scene_id=payoff_id,
            status=ForeshadowingStatus.PAID_OFF,
        )
        assert not foreshadowing.is_planted
        assert foreshadowing.is_paid_off
        assert not foreshadowing.is_abandoned

    @pytest.mark.unit
    @pytest.mark.fast
    def test_abandoned_properties(self):
        """Test abandoned status properties."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The cut subplot",
            status=ForeshadowingStatus.ABANDONED,
        )
        assert not foreshadowing.is_planted
        assert not foreshadowing.is_paid_off
        assert foreshadowing.is_abandoned


class TestForeshadowingPayoffLinking:
    """Test suite for linking payoff scenes to foreshadowing."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_link_payoff_updates_status_and_payoff_id(self):
        """Test that linking payoff updates status to PAID_OFF."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=0)
        payoff_scene = Scene(title="Payoff Scene", chapter_id=uuid4(), order_index=1)

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The mysterious letter",
        )

        foreshadowing.link_payoff(payoff_scene.id, mock_get_scene)

        assert foreshadowing.status == ForeshadowingStatus.PAID_OFF
        assert foreshadowing.payoff_scene_id == payoff_scene.id
        assert foreshadowing.is_paid_off

    @pytest.mark.unit
    def test_link_payoff_same_scene_raises_error(self):
        """Test that linking to the same scene raises ValueError."""
        setup_scene = Scene(title="Scene", chapter_id=uuid4(), order_index=0)

        def mock_get_scene(scene_id):
            return setup_scene if scene_id == setup_scene.id else None

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
        )

        with pytest.raises(
            ValueError, match="Payoff scene cannot be the same as setup scene"
        ):
            foreshadowing.link_payoff(setup_scene.id, mock_get_scene)

    @pytest.mark.unit
    def test_link_payoff_validates_scene_order(self):
        """Test that payoff must come after setup in story order."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=5)
        payoff_scene = Scene(
            title="Payoff Scene", chapter_id=setup_scene.chapter_id, order_index=2
        )

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
        )

        with pytest.raises(
            ValueError, match="Payoff scene .* must come after setup scene"
        ):
            foreshadowing.link_payoff(payoff_scene.id, mock_get_scene)

    @pytest.mark.unit
    def test_link_payoff_allows_equal_order_in_different_chapters(self):
        """Test that cross-chapter payoffs don't validate order."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=5)
        payoff_scene = Scene(title="Payoff Scene", chapter_id=uuid4(), order_index=1)

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
        )

        # Should not raise - different chapters
        foreshadowing.link_payoff(payoff_scene.id, mock_get_scene)
        assert foreshadowing.is_paid_off

    @pytest.mark.unit
    def test_link_payoff_updates_timestamp(self):
        """Test that linking payoff updates the timestamp."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=0)
        payoff_scene = Scene(title="Payoff Scene", chapter_id=uuid4(), order_index=1)

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
        )
        original_updated_at = foreshadowing.updated_at

        foreshadowing.link_payoff(payoff_scene.id, mock_get_scene)

        assert foreshadowing.updated_at >= original_updated_at


class TestForeshadowingStateTransitions:
    """Test suite for foreshadowing state transition methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_abandon_clears_payoff_and_sets_status(self):
        """Test that abandon clears payoff and sets status to ABANDONED."""
        payoff_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The cut subplot",
            payoff_scene_id=payoff_id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        foreshadowing.abandon()

        assert foreshadowing.status == ForeshadowingStatus.ABANDONED
        assert foreshadowing.payoff_scene_id is None
        assert foreshadowing.is_abandoned

    @pytest.mark.unit
    @pytest.mark.fast
    def test_abandon_updates_timestamp(self):
        """Test that abandon updates the timestamp."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The setup",
            status=ForeshadowingStatus.PLANTED,
        )
        original_updated_at = foreshadowing.updated_at

        foreshadowing.abandon()

        assert foreshadowing.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_replant_clears_payoff_and_sets_status(self):
        """Test that replant clears payoff and sets status to PLANTED."""
        payoff_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The revived subplot",
            payoff_scene_id=payoff_id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        foreshadowing.replant()

        assert foreshadowing.status == ForeshadowingStatus.PLANTED
        assert foreshadowing.payoff_scene_id is None
        assert foreshadowing.is_planted

    @pytest.mark.unit
    @pytest.mark.fast
    def test_replant_from_abandoned(self):
        """Test replanting an abandoned foreshadowing."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The revived subplot",
            status=ForeshadowingStatus.ABANDONED,
        )

        foreshadowing.replant()

        assert foreshadowing.status == ForeshadowingStatus.PLANTED
        assert foreshadowing.is_planted


class TestForeshadowingUpdates:
    """Test suite for Foreshadowing update methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_description(self):
        """Test updating foreshadowing description."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="Original description",
        )
        original_updated_at = foreshadowing.updated_at

        foreshadowing.update_description("Updated description")

        assert foreshadowing.description == "Updated description"
        assert foreshadowing.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_description_with_empty_raises_error(self):
        """Test that updating to empty description raises ValueError."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="Original description",
        )

        with pytest.raises(
            ValueError, match="Foreshadowing description cannot be empty"
        ):
            foreshadowing.update_description("")

    @pytest.mark.unit
    def test_update_description_with_whitespace_raises_error(self):
        """Test that updating to whitespace-only description raises ValueError."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="Original description",
        )

        with pytest.raises(
            ValueError, match="Foreshadowing description cannot be empty"
        ):
            foreshadowing.update_description("   ")


class TestForeshadowingValidation:
    """Test suite for foreshadowing validation logic."""

    @pytest.mark.unit
    def test_validate_scene_order_no_payoff_no_error(self):
        """Test that validation passes when no payoff is set."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=0)

        def mock_get_scene(scene_id):
            return setup_scene if scene_id == setup_scene.id else None

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
        )

        # Should not raise
        foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_payoff_after_setup_passes(self):
        """Test that validation passes when payoff is after setup."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=2)
        payoff_scene = Scene(
            title="Payoff Scene", chapter_id=setup_scene.chapter_id, order_index=5
        )

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
            payoff_scene_id=payoff_scene.id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        # Should not raise
        foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_payoff_before_setup_fails(self):
        """Test that validation fails when payoff is before setup."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=5)
        payoff_scene = Scene(
            title="Payoff Scene", chapter_id=setup_scene.chapter_id, order_index=2
        )

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
            payoff_scene_id=payoff_scene.id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        with pytest.raises(
            ValueError, match="Payoff scene .* must come after setup scene"
        ):
            foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_payoff_equal_to_setup_fails(self):
        """Test that validation fails when payoff has same order as setup."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=3)
        payoff_scene = Scene(
            title="Payoff Scene", chapter_id=setup_scene.chapter_id, order_index=3
        )

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
            payoff_scene_id=payoff_scene.id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        with pytest.raises(
            ValueError, match="Payoff scene .* must come after setup scene"
        ):
            foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_cross_chapter_passes(self):
        """Test that cross-chapter foreshadowing passes validation."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=5)
        payoff_scene = Scene(title="Payoff Scene", chapter_id=uuid4(), order_index=1)

        def mock_get_scene(scene_id):
            return {
                setup_scene.id: setup_scene,
                payoff_scene.id: payoff_scene,
            }.get(scene_id)

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
            payoff_scene_id=payoff_scene.id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        # Should not raise - different chapters skip validation
        foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_missing_setup_scene_fails(self):
        """Test that validation fails when setup scene is missing."""
        payoff_scene = Scene(title="Payoff Scene", chapter_id=uuid4(), order_index=5)

        def mock_get_scene(scene_id):
            return payoff_scene if scene_id == payoff_scene.id else None

        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The setup",
            payoff_scene_id=payoff_scene.id,
            status=ForeshadowingStatus.PAID_OFF,
        )

        with pytest.raises(ValueError, match="Setup scene not found"):
            foreshadowing.validate_scene_order(mock_get_scene)

    @pytest.mark.unit
    def test_validate_scene_order_missing_payoff_scene_fails(self):
        """Test that validation fails when payoff scene is missing."""
        setup_scene = Scene(title="Setup Scene", chapter_id=uuid4(), order_index=0)

        def mock_get_scene(scene_id):
            return setup_scene if scene_id == setup_scene.id else None

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene.id,
            description="The setup",
            payoff_scene_id=uuid4(),
            status=ForeshadowingStatus.PAID_OFF,
        )

        with pytest.raises(ValueError, match="Payoff scene not found"):
            foreshadowing.validate_scene_order(mock_get_scene)


class TestForeshadowingStringRepresentations:
    """Test suite for Foreshadowing string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_without_payoff(self):
        """Test string representation without payoff."""
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="A very long description that should be truncated in the str output",
        )
        str_repr = str(foreshadowing)

        assert "Foreshadowing" in str_repr
        assert "A very long description that s..." in str_repr  # truncated
        assert "(unpaid)" in str_repr
        assert "planted" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_with_payoff(self):
        """Test string representation with payoff."""
        payoff_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=uuid4(),
            description="The prophecy",
            payoff_scene_id=payoff_id,
            status=ForeshadowingStatus.PAID_OFF,
        )
        str_repr = str(foreshadowing)

        assert "Foreshadowing" in str_repr
        assert str(payoff_id) in str_repr
        assert "paid_off" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr includes full debugging info."""
        setup_id = uuid4()
        payoff_id = uuid4()
        foreshadowing = Foreshadowing(
            setup_scene_id=setup_id,
            description="The prophecy",
            payoff_scene_id=payoff_id,
            status=ForeshadowingStatus.PAID_OFF,
        )
        repr_str = repr(foreshadowing)

        assert "Foreshadowing" in repr_str
        assert "id=" in repr_str
        assert "setup_scene_id=" in repr_str
        assert str(setup_id) in repr_str
        assert str(payoff_id) in repr_str
        assert "paid_off" in repr_str


class TestForeshadowingEnums:
    """Test suite for Foreshadowing enum values."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_foreshadowing_status_enum_values(self):
        """Test all ForeshadowingStatus enum values."""
        assert ForeshadowingStatus.PLANTED.value == "planted"
        assert ForeshadowingStatus.PAID_OFF.value == "paid_off"
        assert ForeshadowingStatus.ABANDONED.value == "abandoned"
