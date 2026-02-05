"""Unit Tests for Scene Entity.

This test suite covers the Scene entity which represents a dramatic unit
within a Chapter in the Narrative bounded context.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.contexts.narrative.domain.entities.scene import Scene, SceneStatus
from src.contexts.narrative.domain.entities.beat import Beat


class TestSceneCreation:
    """Test suite for Scene instantiation and basic functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_scene_with_required_fields(self):
        """Test creating a Scene with required fields."""
        chapter_id = uuid4()
        scene = Scene(title="Opening Scene", chapter_id=chapter_id)

        assert scene.title == "Opening Scene"
        assert scene.chapter_id == chapter_id
        assert isinstance(scene.id, UUID)
        assert scene.summary == ""
        assert scene.order_index == 0
        assert scene.status == SceneStatus.DRAFT
        assert scene.location == ""
        assert isinstance(scene.created_at, datetime)
        assert isinstance(scene.updated_at, datetime)
        assert scene.beats == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_scene_with_all_attributes(self):
        """Test creating a Scene with all optional attributes."""
        scene_id = uuid4()
        chapter_id = uuid4()
        created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        scene = Scene(
            title="The Confrontation",
            chapter_id=chapter_id,
            id=scene_id,
            summary="Heroes face the villain",
            order_index=3,
            status=SceneStatus.REVIEW,
            location="Dark Castle",
            created_at=created,
            updated_at=created,
        )

        assert scene.title == "The Confrontation"
        assert scene.chapter_id == chapter_id
        assert scene.id == scene_id
        assert scene.summary == "Heroes face the villain"
        assert scene.order_index == 3
        assert scene.status == SceneStatus.REVIEW
        assert scene.location == "Dark Castle"
        assert scene.created_at == created

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_scene_generates_unique_ids(self):
        """Test that each Scene gets a unique ID."""
        chapter_id = uuid4()
        scene1 = Scene(title="Scene 1", chapter_id=chapter_id)
        scene2 = Scene(title="Scene 2", chapter_id=chapter_id)
        scene3 = Scene(title="Scene 3", chapter_id=chapter_id)

        ids = {scene1.id, scene2.id, scene3.id}
        assert len(ids) == 3

    @pytest.mark.unit
    def test_create_scene_with_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Scene title cannot be empty"):
            Scene(title="", chapter_id=uuid4())

    @pytest.mark.unit
    def test_create_scene_with_whitespace_title_raises_error(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="Scene title cannot be empty"):
            Scene(title="   ", chapter_id=uuid4())

    @pytest.mark.unit
    def test_create_scene_with_negative_order_index_raises_error(self):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError, match="order_index cannot be negative"):
            Scene(title="Invalid Scene", chapter_id=uuid4(), order_index=-1)


class TestSceneStatusEnum:
    """Test suite for SceneStatus enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_values(self):
        """Test that SceneStatus has expected values."""
        assert SceneStatus.DRAFT.value == "draft"
        assert SceneStatus.GENERATING.value == "generating"
        assert SceneStatus.REVIEW.value == "review"
        assert SceneStatus.PUBLISHED.value == "published"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_is_string_enum(self):
        """Test that SceneStatus values are strings."""
        assert isinstance(SceneStatus.DRAFT, str)
        assert SceneStatus.DRAFT == "draft"


class TestSceneTitleOperations:
    """Test suite for Scene title operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_title(self):
        """Test updating the scene title."""
        scene = Scene(title="Old Title", chapter_id=uuid4())
        original_updated_at = scene.updated_at

        scene.update_title("New Title")

        assert scene.title == "New Title"
        assert scene.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_title_trims_whitespace(self):
        """Test that title update trims whitespace."""
        scene = Scene(title="Title", chapter_id=uuid4())
        scene.update_title("  Trimmed Title  ")

        assert scene.title == "Trimmed Title"

    @pytest.mark.unit
    def test_update_title_empty_raises_error(self):
        """Test that updating to empty title raises ValueError."""
        scene = Scene(title="Valid Title", chapter_id=uuid4())

        with pytest.raises(ValueError, match="Scene title cannot be empty"):
            scene.update_title("")


class TestSceneSummaryAndLocationOperations:
    """Test suite for Scene summary and location operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary(self):
        """Test updating the scene summary."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        scene.update_summary("A new summary")

        assert scene.summary == "A new summary"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary_allows_empty(self):
        """Test that empty summary is allowed."""
        scene = Scene(title="Scene", chapter_id=uuid4(), summary="Has a summary")
        scene.update_summary("")

        assert scene.summary == ""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_location(self):
        """Test updating the scene location."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        scene.update_location("The Dark Forest")

        assert scene.location == "The Dark Forest"


class TestSceneStatusOperations:
    """Test suite for Scene status operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_start_generation(self):
        """Test starting LLM generation for a scene."""
        scene = Scene(title="Draft Scene", chapter_id=uuid4())
        assert scene.status == SceneStatus.DRAFT

        scene.start_generation()

        assert scene.status == SceneStatus.GENERATING

    @pytest.mark.unit
    @pytest.mark.fast
    def test_complete_generation(self):
        """Test completing LLM generation."""
        scene = Scene(title="Scene", chapter_id=uuid4(), status=SceneStatus.GENERATING)

        scene.complete_generation()

        assert scene.status == SceneStatus.REVIEW

    @pytest.mark.unit
    @pytest.mark.fast
    def test_publish_scene(self):
        """Test publishing a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        scene.publish()

        assert scene.status == SceneStatus.PUBLISHED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_unpublish_scene(self):
        """Test unpublishing a published scene."""
        scene = Scene(
            title="Published Scene", chapter_id=uuid4(), status=SceneStatus.PUBLISHED
        )

        scene.unpublish()

        assert scene.status == SceneStatus.DRAFT


class TestSceneOrderOperations:
    """Test suite for Scene order/position operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_move_to_position(self):
        """Test moving scene to a new position."""
        scene = Scene(title="Scene", chapter_id=uuid4(), order_index=0)

        scene.move_to_position(5)

        assert scene.order_index == 5

    @pytest.mark.unit
    def test_move_to_negative_position_raises_error(self):
        """Test that moving to negative position raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4(), order_index=3)

        with pytest.raises(ValueError, match="order_index cannot be negative"):
            scene.move_to_position(-1)


class TestSceneBeatManagement:
    """Test suite for Scene beat management."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_beat(self):
        """Test adding a beat to a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=scene.id, content="The hero entered.")

        scene.add_beat(beat)

        assert len(scene.beats) == 1
        assert scene.beats[0].id == beat.id

    @pytest.mark.unit
    def test_add_beat_wrong_scene_id_raises_error(self):
        """Test that adding a beat with wrong scene_id raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=uuid4(), content="Wrong scene")

        with pytest.raises(ValueError, match="does not match scene id"):
            scene.add_beat(beat)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_beat(self):
        """Test removing a beat from a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=scene.id, content="To be removed")
        scene.add_beat(beat)

        result = scene.remove_beat(beat.id)

        assert result is True
        assert len(scene.beats) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_nonexistent_beat_returns_false(self):
        """Test that removing nonexistent beat returns False."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        result = scene.remove_beat(uuid4())

        assert result is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_beat(self):
        """Test getting a beat by ID."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=scene.id, content="Find me")
        scene.add_beat(beat)

        found = scene.get_beat(beat.id)

        assert found is not None
        assert found.id == beat.id

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_nonexistent_beat_returns_none(self):
        """Test that getting nonexistent beat returns None."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        found = scene.get_beat(uuid4())

        assert found is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beats_property_returns_sorted_copy(self):
        """Test that beats property returns sorted copy."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat1 = Beat(scene_id=scene.id, content="Third", order_index=2)
        beat2 = Beat(scene_id=scene.id, content="First", order_index=0)
        beat3 = Beat(scene_id=scene.id, content="Second", order_index=1)

        scene.add_beat(beat1)
        scene.add_beat(beat2)
        scene.add_beat(beat3)

        beats = scene.beats
        assert beats[0].content == "First"
        assert beats[1].content == "Second"
        assert beats[2].content == "Third"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beats_property_returns_new_list(self):
        """Test that beats property returns a new list each time."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=scene.id, content="Test")
        scene.add_beat(beat)

        beats1 = scene.beats
        beats2 = scene.beats

        assert beats1 is not beats2


class TestSceneReorderBeats:
    """Test suite for Scene.reorder_beats() method."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reorder_beats_basic(self):
        """Test basic beat reordering."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat1 = Beat(scene_id=scene.id, content="First", order_index=0)
        beat2 = Beat(scene_id=scene.id, content="Second", order_index=1)
        beat3 = Beat(scene_id=scene.id, content="Third", order_index=2)

        scene.add_beat(beat1)
        scene.add_beat(beat2)
        scene.add_beat(beat3)

        # Reverse order
        scene.reorder_beats([beat3.id, beat2.id, beat1.id])

        beats = scene.beats
        assert beats[0].id == beat3.id
        assert beats[0].order_index == 0
        assert beats[1].id == beat2.id
        assert beats[1].order_index == 1
        assert beats[2].id == beat1.id
        assert beats[2].order_index == 2

    @pytest.mark.unit
    def test_reorder_beats_missing_id_raises_error(self):
        """Test that missing beat ID raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat1 = Beat(scene_id=scene.id, content="First", order_index=0)
        beat2 = Beat(scene_id=scene.id, content="Second", order_index=1)

        scene.add_beat(beat1)
        scene.add_beat(beat2)

        # Only provide one ID when two exist
        with pytest.raises(ValueError, match="missing"):
            scene.reorder_beats([beat1.id])

    @pytest.mark.unit
    def test_reorder_beats_extra_id_raises_error(self):
        """Test that extra beat ID raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat = Beat(scene_id=scene.id, content="Only beat", order_index=0)

        scene.add_beat(beat)

        # Provide an extra ID that doesn't exist
        with pytest.raises(ValueError, match="extra"):
            scene.reorder_beats([beat.id, uuid4()])

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reorder_beats_updates_timestamp(self):
        """Test that reordering updates the scene timestamp."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        beat1 = Beat(scene_id=scene.id, content="First", order_index=0)
        beat2 = Beat(scene_id=scene.id, content="Second", order_index=1)

        scene.add_beat(beat1)
        scene.add_beat(beat2)

        original_timestamp = scene.updated_at
        scene.reorder_beats([beat2.id, beat1.id])

        assert scene.updated_at >= original_timestamp

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reorder_beats_empty_scene(self):
        """Test reordering with no beats."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        # Empty list for empty scene should work
        scene.reorder_beats([])

        assert scene.beats == []


class TestSceneStringRepresentation:
    """Test suite for Scene string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation of Scene."""
        scene = Scene(title="The Opening", chapter_id=uuid4(), order_index=0)

        str_repr = str(scene)

        assert "The Opening" in str_repr
        assert "order=0" in str_repr
        assert "draft" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr representation of Scene."""
        chapter_id = uuid4()
        scene = Scene(title="The Opening", chapter_id=chapter_id, order_index=0)
        beat = Beat(scene_id=scene.id, content="Test")
        scene.add_beat(beat)

        repr_str = repr(scene)

        assert "Scene" in repr_str
        assert "The Opening" in repr_str
        assert str(scene.id) in repr_str
        assert "beats=1" in repr_str


class TestSceneTimestamps:
    """Test suite for Scene timestamp behavior."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_operations_touch_timestamp(self):
        """Test that update operations update the timestamp."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        original_timestamp = scene.updated_at

        scene.update_title("New Title")
        assert scene.updated_at >= original_timestamp

        timestamp_after_title = scene.updated_at
        scene.update_summary("Summary")
        assert scene.updated_at >= timestamp_after_title

        timestamp_after_summary = scene.updated_at
        scene.update_location("Location")
        assert scene.updated_at >= timestamp_after_summary

        timestamp_after_location = scene.updated_at
        scene.start_generation()
        assert scene.updated_at >= timestamp_after_location

        timestamp_after_start = scene.updated_at
        scene.complete_generation()
        assert scene.updated_at >= timestamp_after_start

        timestamp_after_complete = scene.updated_at
        scene.move_to_position(3)
        assert scene.updated_at >= timestamp_after_complete


class TestScenePacingLevels:
    """Test suite for Scene pacing level operations (Director Mode)."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_pacing_levels(self):
        """Test that default tension and energy levels are 5."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        assert scene.tension_level == 5
        assert scene.energy_level == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_scene_with_custom_pacing_levels(self):
        """Test creating a scene with custom pacing levels."""
        scene = Scene(
            title="Climax Scene",
            chapter_id=uuid4(),
            tension_level=9,
            energy_level=8,
        )

        assert scene.tension_level == 9
        assert scene.energy_level == 8

    @pytest.mark.unit
    def test_create_scene_with_invalid_tension_level_raises_error(self):
        """Test that invalid tension level raises ValueError."""
        with pytest.raises(ValueError, match="tension_level must be between 1 and 10"):
            Scene(title="Scene", chapter_id=uuid4(), tension_level=0)

        with pytest.raises(ValueError, match="tension_level must be between 1 and 10"):
            Scene(title="Scene", chapter_id=uuid4(), tension_level=11)

    @pytest.mark.unit
    def test_create_scene_with_invalid_energy_level_raises_error(self):
        """Test that invalid energy level raises ValueError."""
        with pytest.raises(ValueError, match="energy_level must be between 1 and 10"):
            Scene(title="Scene", chapter_id=uuid4(), energy_level=0)

        with pytest.raises(ValueError, match="energy_level must be between 1 and 10"):
            Scene(title="Scene", chapter_id=uuid4(), energy_level=11)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_tension_level(self):
        """Test updating scene tension level."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        original_timestamp = scene.updated_at

        scene.update_tension_level(8)

        assert scene.tension_level == 8
        assert scene.updated_at >= original_timestamp

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_energy_level(self):
        """Test updating scene energy level."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        original_timestamp = scene.updated_at

        scene.update_energy_level(3)

        assert scene.energy_level == 3
        assert scene.updated_at >= original_timestamp

    @pytest.mark.unit
    def test_update_tension_level_invalid_raises_error(self):
        """Test that updating to invalid tension level raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        with pytest.raises(ValueError, match="tension_level must be between 1 and 10"):
            scene.update_tension_level(0)

        with pytest.raises(ValueError, match="tension_level must be between 1 and 10"):
            scene.update_tension_level(11)

    @pytest.mark.unit
    def test_update_energy_level_invalid_raises_error(self):
        """Test that updating to invalid energy level raises ValueError."""
        scene = Scene(title="Scene", chapter_id=uuid4())

        with pytest.raises(ValueError, match="energy_level must be between 1 and 10"):
            scene.update_energy_level(0)

        with pytest.raises(ValueError, match="energy_level must be between 1 and 10"):
            scene.update_energy_level(11)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_pacing_levels_boundary_values(self):
        """Test that boundary values (1 and 10) are valid."""
        scene_min = Scene(
            title="Low Scene", chapter_id=uuid4(), tension_level=1, energy_level=1
        )
        scene_max = Scene(
            title="High Scene", chapter_id=uuid4(), tension_level=10, energy_level=10
        )

        assert scene_min.tension_level == 1
        assert scene_min.energy_level == 1
        assert scene_max.tension_level == 10
        assert scene_max.energy_level == 10

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_includes_pacing_levels(self):
        """Test that repr includes tension and energy levels."""
        scene = Scene(
            title="Test", chapter_id=uuid4(), tension_level=7, energy_level=4
        )

        repr_str = repr(scene)

        assert "tension=7" in repr_str
        assert "energy=4" in repr_str


class TestScenePlotlineManagement:
    """Test suite for Scene plotline management (DIR-049)."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_plotline_ids_is_empty(self):
        """Test that new scenes have empty plotline_ids list."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        assert scene.plotline_ids == []
        assert len(scene.plotline_ids) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_plotline(self):
        """Test adding a plotline to a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id = uuid4()
        original_timestamp = scene.updated_at

        scene.add_plotline(plotline_id)

        assert plotline_id in scene.plotline_ids
        assert len(scene.plotline_ids) == 1
        assert scene.updated_at >= original_timestamp

    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_multiple_plotlines(self):
        """Test adding multiple plotlines to a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id_1 = uuid4()
        plotline_id_2 = uuid4()
        plotline_id_3 = uuid4()

        scene.add_plotline(plotline_id_1)
        scene.add_plotline(plotline_id_2)
        scene.add_plotline(plotline_id_3)

        assert plotline_id_1 in scene.plotline_ids
        assert plotline_id_2 in scene.plotline_ids
        assert plotline_id_3 in scene.plotline_ids
        assert len(scene.plotline_ids) == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_duplicate_plotline_no_change(self):
        """Test that adding the same plotline twice doesn't duplicate it."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id = uuid4()
        original_timestamp = scene.updated_at

        scene.add_plotline(plotline_id)
        scene.add_plotline(plotline_id)  # Add same plotline again

        assert scene.plotline_ids.count(plotline_id) == 1
        assert len(scene.plotline_ids) == 1
        # Should not have updated timestamp on no-op
        assert scene.updated_at == original_timestamp

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_plotline(self):
        """Test removing a plotline from a scene."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id = uuid4()
        scene.add_plotline(plotline_id)

        result = scene.remove_plotline(plotline_id)

        assert result is True
        assert plotline_id not in scene.plotline_ids
        assert len(scene.plotline_ids) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_nonexistent_plotline_returns_false(self):
        """Test that removing a non-existent plotline returns False."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id = uuid4()

        result = scene.remove_plotline(plotline_id)

        assert result is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_plotlines_replaces_all(self):
        """Test that set_plotlines replaces all existing plotlines."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id_1 = uuid4()
        plotline_id_2 = uuid4()
        plotline_id_3 = uuid4()

        # Add initial plotlines
        scene.add_plotline(plotline_id_1)
        scene.add_plotline(plotline_id_2)

        # Replace with new list
        new_plotlines = [plotline_id_2, plotline_id_3]
        scene.set_plotlines(new_plotlines)

        assert len(scene.plotline_ids) == 2
        assert plotline_id_2 in scene.plotline_ids
        assert plotline_id_3 in scene.plotline_ids
        assert plotline_id_1 not in scene.plotline_ids

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_plotlines_with_empty_list(self):
        """Test that set_plotlines with empty list clears all plotlines."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id_1 = uuid4()
        plotline_id_2 = uuid4()

        scene.add_plotline(plotline_id_1)
        scene.add_plotline(plotline_id_2)
        scene.set_plotlines([])

        assert len(scene.plotline_ids) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_plotline_operations_touch_timestamp(self):
        """Test that plotline operations update the timestamp."""
        scene = Scene(title="Scene", chapter_id=uuid4())
        plotline_id = uuid4()

        import time
        time.sleep(0.01)  # Small delay to ensure timestamp changes

        scene.add_plotline(plotline_id)

        assert scene.updated_at > scene.created_at


class TestSceneMetadataSmartTags:
    """Tests for Scene metadata and smart tags functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_metadata_adds_key_value(self):
        """Test updating metadata with a key-value pair."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        scene.update_metadata("custom_field", "custom_value")

        assert scene.get_metadata("custom_field") == "custom_value"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_metadata_overwrites_existing(self):
        """Test that updating metadata overwrites existing values."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        scene.update_metadata("key", "value1")
        scene.update_metadata("key", "value2")

        assert scene.get_metadata("key") == "value2"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_metadata_returns_default_for_missing_key(self):
        """Test that get_metadata returns default for missing keys."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())

        assert scene.get_metadata("nonexistent", "default") == "default"
        assert scene.get_metadata("nonexistent") is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_smart_tags_stores_tags(self):
        """Test storing smart tags in metadata."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        tags = {
            "mood": ["tense", "mysterious"],
            "pacing": ["fast"],
        }
        scene.set_smart_tags(tags)

        assert scene.get_smart_tags() == tags

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_smart_tags_empty_when_none_set(self):
        """Test that get_smart_tags returns empty dict when none set."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())

        assert scene.get_smart_tags() == {}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_smart_tags_stored_alongside_other_metadata(self):
        """Test that smart tags coexist with other metadata."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        scene.update_metadata("other_key", "other_value")
        scene.set_smart_tags({"mood": ["tense"]})

        assert scene.get_metadata("other_key") == "other_value"
        assert scene.get_smart_tags() == {"mood": ["tense"]}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_metadata_updates_touch_timestamp(self):
        """Test that metadata updates trigger timestamp change."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        original_timestamp = scene.updated_at

        import time
        time.sleep(0.01)
        scene.update_metadata("test", "value")

        assert scene.updated_at > original_timestamp

    @pytest.mark.unit
    @pytest.mark.fast
    def test_smart_tags_updates_touch_timestamp(self):
        """Test that smart tags updates trigger timestamp change."""
        scene = Scene(title="Test Scene", chapter_id=uuid4())
        original_timestamp = scene.updated_at

        import time
        time.sleep(0.01)
        scene.set_smart_tags({"mood": ["tense"]})

        assert scene.updated_at > original_timestamp
