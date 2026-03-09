#!/usr/bin/env python3
"""
Unit tests for Scene Entity

Comprehensive test suite for the Scene domain entity including:
- Creation and validation
- Title, summary, and location management
- Tension and energy level management
- Status workflow (draft, generating, review, published)
- Story phase management
- Plotline management
- Beat operations
- Smart tags management
"""

import sys
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.narrative.domain.entities.scene import (
    Scene,
    SceneStatus,
    StoryPhase,
)


class TestScene:
    """Test suite for Scene entity."""

    @pytest.fixture
    def sample_chapter_id(self):
        """Create a sample chapter ID."""
        return uuid4()

    @pytest.fixture
    def sample_scene(self, sample_chapter_id):
        """Create a sample scene for testing."""
        return Scene(
            title="Test Scene",
            chapter_id=sample_chapter_id,
            summary="A test scene",
            order_index=0,
        )

    @pytest.fixture
    def sample_plotline_id(self):
        """Create a sample plotline ID."""
        return uuid4()

    def test_scene_creation_success(self, sample_chapter_id):
        """Test successful scene creation with all fields."""
        scene = Scene(
            title="Test Scene",
            chapter_id=sample_chapter_id,
            summary="Test summary",
            order_index=1,
            status=SceneStatus.DRAFT,
            story_phase=StoryPhase.RISING_ACTION,
            location="The Castle",
            tension_level=7,
            energy_level=8,
        )

        assert scene.title == "Test Scene"
        assert scene.chapter_id == sample_chapter_id
        assert scene.summary == "Test summary"
        assert scene.order_index == 1
        assert scene.status == SceneStatus.DRAFT
        assert scene.story_phase == StoryPhase.RISING_ACTION
        assert scene.location == "The Castle"
        assert scene.tension_level == 7
        assert scene.energy_level == 8
        assert isinstance(scene.id, UUID)

    def test_scene_creation_defaults(self, sample_chapter_id):
        """Test scene creation with default values."""
        scene = Scene(
            title="Test Scene",
            chapter_id=sample_chapter_id,
        )

        assert scene.summary == ""
        assert scene.order_index == 0
        assert scene.status == SceneStatus.DRAFT
        assert scene.story_phase == StoryPhase.SETUP
        assert scene.location == ""
        assert scene.tension_level == 5
        assert scene.energy_level == 5
        assert scene.plotline_ids == []
        assert scene.metadata == {}

    def test_scene_creation_empty_title_raises_error(self, sample_chapter_id):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="",
                chapter_id=sample_chapter_id,
            )
        assert "Scene title cannot be empty" in str(exc_info.value)

    def test_scene_creation_whitespace_title_raises_error(self, sample_chapter_id):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="   ",
                chapter_id=sample_chapter_id,
            )
        assert "Scene title cannot be empty" in str(exc_info.value)

    def test_scene_creation_negative_order_raises_error(self, sample_chapter_id):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="Test Scene",
                chapter_id=sample_chapter_id,
                order_index=-1,
            )
        assert "Scene order_index cannot be negative" in str(exc_info.value)

    def test_scene_creation_tension_too_low_raises_error(self, sample_chapter_id):
        """Test that tension_level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="Test Scene",
                chapter_id=sample_chapter_id,
                tension_level=0,
            )
        assert "Scene tension_level must be between 1 and 10" in str(exc_info.value)

    def test_scene_creation_tension_too_high_raises_error(self, sample_chapter_id):
        """Test that tension_level > 10 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="Test Scene",
                chapter_id=sample_chapter_id,
                tension_level=11,
            )
        assert "Scene tension_level must be between 1 and 10" in str(exc_info.value)

    def test_scene_creation_energy_too_low_raises_error(self, sample_chapter_id):
        """Test that energy_level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="Test Scene",
                chapter_id=sample_chapter_id,
                energy_level=0,
            )
        assert "Scene energy_level must be between 1 and 10" in str(exc_info.value)

    def test_scene_creation_energy_too_high_raises_error(self, sample_chapter_id):
        """Test that energy_level > 10 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Scene(
                title="Test Scene",
                chapter_id=sample_chapter_id,
                energy_level=11,
            )
        assert "Scene energy_level must be between 1 and 10" in str(exc_info.value)

    def test_update_title_success(self, sample_scene):
        """Test successful title update."""
        old_updated_at = sample_scene.updated_at

        sample_scene.update_title("New Title")

        assert sample_scene.title == "New Title"
        assert sample_scene.updated_at > old_updated_at

    def test_update_title_strips_whitespace(self, sample_scene):
        """Test that title update strips whitespace."""
        sample_scene.update_title("  New Title  ")
        assert sample_scene.title == "New Title"

    def test_update_title_empty_raises_error(self, sample_scene):
        """Test that empty title update raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.update_title("")
        assert "Scene title cannot be empty" in str(exc_info.value)

    def test_update_summary_success(self, sample_scene):
        """Test successful summary update."""
        old_updated_at = sample_scene.updated_at

        sample_scene.update_summary("New summary")

        assert sample_scene.summary == "New summary"
        assert sample_scene.updated_at > old_updated_at

    def test_update_location_success(self, sample_scene):
        """Test successful location update."""
        sample_scene.update_location("New Location")
        assert sample_scene.location == "New Location"

    def test_update_tension_level_success(self, sample_scene):
        """Test successful tension level update."""
        sample_scene.update_tension_level(8)
        assert sample_scene.tension_level == 8

    def test_update_tension_level_boundary_values(self, sample_scene):
        """Test tension level at boundary values."""
        sample_scene.update_tension_level(1)
        assert sample_scene.tension_level == 1

        sample_scene.update_tension_level(10)
        assert sample_scene.tension_level == 10

    def test_update_tension_level_too_low_raises_error(self, sample_scene):
        """Test that tension level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.update_tension_level(0)
        assert "Scene tension_level must be between 1 and 10" in str(exc_info.value)

    def test_update_tension_level_too_high_raises_error(self, sample_scene):
        """Test that tension level > 10 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.update_tension_level(11)
        assert "Scene tension_level must be between 1 and 10" in str(exc_info.value)

    def test_update_energy_level_success(self, sample_scene):
        """Test successful energy level update."""
        sample_scene.update_energy_level(9)
        assert sample_scene.energy_level == 9

    def test_update_energy_level_too_low_raises_error(self, sample_scene):
        """Test that energy level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.update_energy_level(0)
        assert "Scene energy_level must be between 1 and 10" in str(exc_info.value)

    def test_update_energy_level_too_high_raises_error(self, sample_scene):
        """Test that energy level > 10 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.update_energy_level(11)
        assert "Scene energy_level must be between 1 and 10" in str(exc_info.value)

    def test_start_generation_success(self, sample_scene):
        """Test successful transition to generating status."""
        sample_scene.start_generation()
        assert sample_scene.status == SceneStatus.GENERATING

    def test_complete_generation_success(self, sample_scene):
        """Test successful transition to review status."""
        sample_scene.start_generation()
        sample_scene.complete_generation()
        assert sample_scene.status == SceneStatus.REVIEW

    def test_publish_success(self, sample_scene):
        """Test successful publication."""
        sample_scene.publish()
        assert sample_scene.status == SceneStatus.PUBLISHED

    def test_unpublish_success(self, sample_scene):
        """Test successful unpublish."""
        sample_scene.publish()
        sample_scene.unpublish()
        assert sample_scene.status == SceneStatus.DRAFT

    def test_move_to_position_success(self, sample_scene):
        """Test successful position change."""
        sample_scene.move_to_position(3)
        assert sample_scene.order_index == 3

    def test_move_to_position_negative_raises_error(self, sample_scene):
        """Test that negative position raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_scene.move_to_position(-1)
        assert "Scene order_index cannot be negative" in str(exc_info.value)

    def test_update_story_phase_success(self, sample_scene):
        """Test successful story phase update."""
        sample_scene.update_story_phase(StoryPhase.CLIMAX)
        assert sample_scene.story_phase == StoryPhase.CLIMAX

    def test_add_plotline_success(self, sample_scene, sample_plotline_id):
        """Test successful plotline addition."""
        sample_scene.add_plotline(sample_plotline_id)
        assert sample_plotline_id in sample_scene.plotline_ids

    def test_add_plotline_duplicate_ignored(self, sample_scene, sample_plotline_id):
        """Test that adding duplicate plotline is ignored."""
        sample_scene.add_plotline(sample_plotline_id)
        sample_scene.add_plotline(sample_plotline_id)
        assert sample_scene.plotline_ids.count(sample_plotline_id) == 1

    def test_remove_plotline_success(self, sample_scene, sample_plotline_id):
        """Test successful plotline removal."""
        sample_scene.add_plotline(sample_plotline_id)
        result = sample_scene.remove_plotline(sample_plotline_id)
        assert result is True
        assert sample_plotline_id not in sample_scene.plotline_ids

    def test_remove_plotline_not_found(self, sample_scene, sample_plotline_id):
        """Test removing non-existent plotline returns False."""
        result = sample_scene.remove_plotline(sample_plotline_id)
        assert result is False

    def test_set_plotlines_success(self, sample_scene):
        """Test successful plotlines replacement."""
        new_plotlines = [uuid4(), uuid4()]
        sample_scene.set_plotlines(new_plotlines)
        assert sample_scene.plotline_ids == new_plotlines

    def test_update_metadata_success(self, sample_scene):
        """Test successful metadata update."""
        sample_scene.update_metadata("key", "value")
        assert sample_scene.metadata["key"] == "value"

    def test_get_metadata_existing_key(self, sample_scene):
        """Test getting existing metadata value."""
        sample_scene.update_metadata("key", "value")
        result = sample_scene.get_metadata("key")
        assert result == "value"

    def test_get_metadata_nonexistent_key(self, sample_scene):
        """Test getting non-existent key returns default."""
        result = sample_scene.get_metadata("nonexistent", "default")
        assert result == "default"

    def test_get_metadata_nonexistent_key_no_default(self, sample_scene):
        """Test getting non-existent key without default returns None."""
        result = sample_scene.get_metadata("nonexistent")
        assert result is None

    def test_set_smart_tags_success(self, sample_scene):
        """Test successful smart tags setting."""
        tags = {"genre": ["fantasy"], "mood": ["dark"]}
        sample_scene.set_smart_tags(tags)
        assert sample_scene.get_smart_tags() == tags

    def test_get_smart_tags_empty(self, sample_scene):
        """Test getting smart tags when none set returns empty dict."""
        result = sample_scene.get_smart_tags()
        assert result == {}

    def test_set_manual_smart_tags_success(self, sample_scene):
        """Test successful manual smart tags setting."""
        sample_scene.set_manual_smart_tags("genre", ["sci-fi", "space"])
        result = sample_scene.get_manual_smart_tags_for_category("genre")
        assert "sci-fi" in result
        assert "space" in result

    def test_set_manual_smart_tags_normalizes_case(self, sample_scene):
        """Test that manual tags are normalized to lowercase."""
        sample_scene.set_manual_smart_tags("genre", ["Sci-Fi", "SPACE"])
        result = sample_scene.get_manual_smart_tags_for_category("genre")
        assert "sci-fi" in result
        assert "space" in result

    def test_set_manual_smart_tags_filters_empty(self, sample_scene):
        """Test that empty tags are filtered out."""
        sample_scene.set_manual_smart_tags("genre", ["valid", "", "  "])
        result = sample_scene.get_manual_smart_tags_for_category("genre")
        assert result == ["valid"]

    def test_remove_manual_smart_tag_success(self, sample_scene):
        """Test successful manual tag removal."""
        sample_scene.set_manual_smart_tags("genre", ["fantasy", "sci-fi"])
        result = sample_scene.remove_manual_smart_tag("genre", "fantasy")
        assert result is True
        remaining = sample_scene.get_manual_smart_tags_for_category("genre")
        assert "fantasy" not in remaining

    def test_remove_manual_smart_tag_not_found(self, sample_scene):
        """Test removing non-existent tag returns False."""
        sample_scene.set_manual_smart_tags("genre", ["fantasy"])
        result = sample_scene.remove_manual_smart_tag("genre", "nonexistent")
        assert result is False

    def test_clear_manual_smart_tags_all(self, sample_scene):
        """Test clearing all manual smart tags."""
        sample_scene.set_manual_smart_tags("genre", ["fantasy"])
        sample_scene.set_manual_smart_tags("mood", ["dark"])
        sample_scene.clear_manual_smart_tags()
        assert sample_scene.get_manual_smart_tags() == {}

    def test_clear_manual_smart_tags_specific_category(self, sample_scene):
        """Test clearing specific category of manual smart tags."""
        sample_scene.set_manual_smart_tags("genre", ["fantasy"])
        sample_scene.set_manual_smart_tags("mood", ["dark"])
        sample_scene.clear_manual_smart_tags("genre")
        assert sample_scene.get_manual_smart_tags_for_category("genre") == []
        assert sample_scene.get_manual_smart_tags_for_category("mood") == ["dark"]

    def test_get_effective_smart_tags_combines_auto_and_manual(self, sample_scene):
        """Test that effective tags combine auto and manual tags."""
        sample_scene.set_smart_tags({"genre": ["auto_tag"]})
        sample_scene.set_manual_smart_tags("genre", ["manual_tag"])
        result = sample_scene.get_effective_smart_tags()
        assert "auto_tag" in result["genre"]
        assert "manual_tag" in result["genre"]

    def test_str_representation(self, sample_scene):
        """Test string representation."""
        result = str(sample_scene)
        assert "Test Scene" in result
        assert "draft" in result

    def test_repr_representation(self, sample_scene):
        """Test repr representation."""
        result = repr(sample_scene)
        assert "Scene" in result
        assert "id=" in result
        assert "chapter_id=" in result


class TestSceneStatus:
    """Test SceneStatus enum."""

    def test_status_values(self):
        """Test that enum has correct values."""
        assert SceneStatus.DRAFT.value == "draft"
        assert SceneStatus.GENERATING.value == "generating"
        assert SceneStatus.REVIEW.value == "review"
        assert SceneStatus.PUBLISHED.value == "published"


class TestStoryPhase:
    """Test StoryPhase enum."""

    def test_phase_values(self):
        """Test that enum has correct values."""
        assert StoryPhase.SETUP.value == "setup"
        assert StoryPhase.INCITING_INCIDENT.value == "inciting_incident"
        assert StoryPhase.RISING_ACTION.value == "rising_action"
        assert StoryPhase.CLIMAX.value == "climax"
        assert StoryPhase.RESOLUTION.value == "resolution"
