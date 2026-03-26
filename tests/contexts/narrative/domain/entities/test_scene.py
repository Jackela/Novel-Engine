"""Tests for the Scene entity.

This module contains comprehensive tests for the Scene domain entity,
covering choice management, content updates, and decision logic.
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

import pytest

from src.contexts.narrative.domain.entities.choice import Choice
from src.contexts.narrative.domain.entities.scene import Scene


@pytest.fixture
def valid_scene() -> Scene:
    """Create a valid scene for testing."""
    return Scene(
        chapter_id="chapter-123",
        scene_number=1,
        title="Test Scene",
        content="This is the scene content.",
        scene_type="narrative",
    )


@pytest.fixture
def valid_choice() -> Choice:
    """Create a valid choice for testing."""
    return Choice(
        scene_id="scene-123",
        text="Go left",
        next_scene_id="scene-next",
    )


class TestScene:
    """Test cases for Scene entity."""

    def test_create_scene_with_valid_data(self) -> None:
        """Test scene creation with valid data."""
        scene = Scene(
            chapter_id="chapter-456",
            scene_number=2,
            title="Scene Two",
            content="The adventure continues...",
            scene_type="action",
            metadata={"location": "forest"},
        )

        assert scene.chapter_id == "chapter-456"
        assert scene.scene_number == 2
        assert scene.title == "Scene Two"
        assert scene.content == "The adventure continues..."
        assert scene.scene_type == "action"
        assert scene.metadata == {"location": "forest"}
        assert scene.choices == []
        assert isinstance(scene.id, UUID)

    def test_create_scene_with_minimal_data(self) -> None:
        """Test scene creation with minimal data."""
        scene = Scene(
            chapter_id="chapter-123",
            scene_number=1,
            content="Simple content.",
        )

        assert scene.title is None
        assert scene.scene_type == "narrative"  # Default
        assert scene.metadata == {}
        assert scene.choices == []

    def test_create_with_empty_chapter_id_raises_error(self) -> None:
        """Test that empty chapter_id raises ValueError."""
        with pytest.raises(ValueError, match="must belong to a chapter"):
            Scene(chapter_id="", scene_number=1, content="Test")

    def test_create_with_invalid_scene_number_raises_error(self) -> None:
        """Test that invalid scene number raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            Scene(chapter_id="chapter-123", scene_number=0, content="Test")

        with pytest.raises(ValueError, match="must be positive"):
            Scene(chapter_id="chapter-123", scene_number=-1, content="Test")

    def test_create_with_too_long_content_raises_error(self) -> None:
        """Test that content exceeding 50000 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 50000 characters"):
            Scene(
                chapter_id="chapter-123",
                scene_number=1,
                content="x" * 50001,
            )

    def test_create_with_invalid_scene_type_raises_error(self) -> None:
        """Test that invalid scene type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid scene type"):
            Scene(
                chapter_id="chapter-123",
                scene_number=1,
                content="Test",
                scene_type="invalid-type",
            )

    def test_create_with_valid_scene_types(self) -> None:
        """Test creating scenes with all valid scene types."""
        valid_types = [
            "opening",
            "narrative",
            "dialogue",
            "action",
            "decision",
            "climax",
            "ending",
        ]

        for i, scene_type in enumerate(valid_types, 1):
            scene = Scene(
                chapter_id=f"chapter-{i}",
                scene_number=i,
                content=f"Content for {scene_type}",
                scene_type=scene_type,
            )
            assert scene.scene_type == scene_type


class TestSceneChoices:
    """Test cases for choice management."""

    def test_add_choice(self, valid_scene: Scene, valid_choice: Choice) -> None:
        """Test adding a choice."""
        valid_scene.add_choice(valid_choice)

        assert len(valid_scene.choices) == 1
        assert valid_scene.choices[0].text == "Go left"
        assert valid_scene.is_decision_point is True

    def test_add_multiple_choices(self, valid_scene: Scene) -> None:
        """Test adding multiple choices."""
        choice1 = Choice(scene_id=str(valid_scene.id), text="Go left")
        choice2 = Choice(scene_id=str(valid_scene.id), text="Go right")
        choice3 = Choice(scene_id=str(valid_scene.id), text="Stay put")

        valid_scene.add_choice(choice1)
        valid_scene.add_choice(choice2)
        valid_scene.add_choice(choice3)

        assert len(valid_scene.choices) == 3

    def test_add_choice_beyond_maximum_raises_error(self, valid_scene: Scene) -> None:
        """Test that adding more than 5 choices raises ValueError."""
        # Add 5 choices
        for i in range(5):
            choice = Choice(scene_id=str(valid_scene.id), text=f"Choice {i + 1}")
            valid_scene.add_choice(choice)

        assert len(valid_scene.choices) == 5

        # 6th choice should fail
        extra_choice = Choice(scene_id=str(valid_scene.id), text="Extra")
        with pytest.raises(ValueError, match="cannot have more than 5 choices"):
            valid_scene.add_choice(extra_choice)

    def test_remove_choice(self, valid_scene: Scene) -> None:
        """Test removing a choice."""
        choice = Choice(scene_id=str(valid_scene.id), text="To be removed")
        valid_scene.add_choice(choice)

        assert len(valid_scene.choices) == 1

        valid_scene.remove_choice(str(choice.id))

        assert len(valid_scene.choices) == 0
        assert valid_scene.is_decision_point is False

    def test_remove_nonexistent_choice_does_nothing(self, valid_scene: Scene) -> None:
        """Test removing non-existent choice does nothing."""
        choice = Choice(scene_id=str(valid_scene.id), text="Choice")
        valid_scene.add_choice(choice)

        valid_scene.remove_choice("nonexistent-id")

        assert len(valid_scene.choices) == 1


class TestSceneDecisionLogic:
    """Test cases for decision logic and choice selection."""

    def test_get_available_choices(self, valid_scene: Scene) -> None:
        """Test getting available choices."""
        choice1 = Choice(scene_id=str(valid_scene.id), text="Always available")
        choice2 = Choice(scene_id=str(valid_scene.id), text="Conditional")
        choice2.add_condition("has_key", True)

        valid_scene.add_choice(choice1)
        valid_scene.add_choice(choice2)

        # With empty context, only choice1 is available
        context: Dict[str, Any] = {}
        available = valid_scene.get_available_choices(context)

        assert len(available) == 1
        assert available[0] == choice1

    def test_get_available_choices_with_context(self, valid_scene: Scene) -> None:
        """Test getting available choices with context."""
        choice1 = Choice(scene_id=str(valid_scene.id), text="Always available")
        choice2 = Choice(scene_id=str(valid_scene.id), text="With key")
        choice2.add_condition("has_key", True)

        valid_scene.add_choice(choice1)
        valid_scene.add_choice(choice2)

        # With has_key=True, both are available
        context = {"has_key": True}
        available = valid_scene.get_available_choices(context)

        assert len(available) == 2

    def test_get_available_choices_hidden(self, valid_scene: Scene) -> None:
        """Test that hidden choices are not available."""
        choice = Choice(scene_id=str(valid_scene.id), text="Hidden choice")
        choice.hide()

        valid_scene.add_choice(choice)

        available = valid_scene.get_available_choices({})
        assert len(available) == 0

    def test_select_choice(self, valid_scene: Scene) -> None:
        """Test selecting a choice."""
        choice = Choice(
            scene_id=str(valid_scene.id),
            text="Take the treasure",
            next_scene_id="scene-rich",
        )
        choice.add_consequence("has_treasure", True)

        valid_scene.add_choice(choice)

        context: Dict[str, Any] = {}
        selected, updated_context, next_scene = valid_scene.select_choice(
            str(choice.id), context
        )

        assert selected == choice
        assert updated_context["has_treasure"] is True
        assert next_scene == "scene-rich"

    def test_select_nonexistent_choice_raises_error(self, valid_scene: Scene) -> None:
        """Test selecting non-existent choice raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            valid_scene.select_choice("nonexistent-id", {})

    def test_select_unavailable_choice_raises_error(self, valid_scene: Scene) -> None:
        """Test selecting unavailable choice raises ValueError."""
        choice = Choice(scene_id=str(valid_scene.id), text="Needs key")
        choice.add_condition("has_key", True)

        valid_scene.add_choice(choice)

        with pytest.raises(ValueError, match="not available"):
            valid_scene.select_choice(str(choice.id), {})  # No has_key in context


class TestSceneProperties:
    """Test cases for scene properties."""

    def test_is_decision_point_property(self, valid_scene: Scene) -> None:
        """Test is_decision_point property."""
        assert valid_scene.is_decision_point is False

        choice = Choice(scene_id=str(valid_scene.id), text="A choice")
        valid_scene.add_choice(choice)

        assert valid_scene.is_decision_point is True

    def test_has_multiple_paths_property(self, valid_scene: Scene) -> None:
        """Test has_multiple_paths property."""
        # No choices
        assert valid_scene.has_multiple_paths is False

        # One choice with next_scene_id
        choice1 = Choice(
            scene_id=str(valid_scene.id),
            text="Go left",
            next_scene_id="scene-left",
        )
        valid_scene.add_choice(choice1)
        assert valid_scene.has_multiple_paths is False

        # Two choices with next_scene_id
        choice2 = Choice(
            scene_id=str(valid_scene.id),
            text="Go right",
            next_scene_id="scene-right",
        )
        valid_scene.add_choice(choice2)
        assert valid_scene.has_multiple_paths is True

    def test_has_multiple_paths_with_dead_ends(self, valid_scene: Scene) -> None:
        """Test has_multiple_paths with choices that don't lead anywhere."""
        # Choice without next_scene_id
        choice1 = Choice(scene_id=str(valid_scene.id), text="Stay")
        valid_scene.add_choice(choice1)

        assert valid_scene.has_multiple_paths is False

        # Add another choice without next_scene_id
        choice2 = Choice(scene_id=str(valid_scene.id), text="Wait")
        valid_scene.add_choice(choice2)

        # Still False because neither has next_scene_id
        assert valid_scene.has_multiple_paths is False


class TestSceneContentUpdates:
    """Test cases for content updates."""

    def test_update_content(self, valid_scene: Scene) -> None:
        """Test updating scene content."""
        valid_scene.update_content("New content here")

        assert valid_scene.content == "New content here"

    def test_update_content_too_long_raises_error(self, valid_scene: Scene) -> None:
        """Test updating to content exceeding 50000 characters raises error."""
        with pytest.raises(ValueError, match="Content too long"):
            valid_scene.update_content("x" * 50001)


class TestSceneSerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_scene: Scene) -> None:
        """Test converting to dictionary."""
        choice = Choice(scene_id=str(valid_scene.id), text="Test choice")
        valid_scene.add_choice(choice)
        valid_scene.metadata["mood"] = "tense"

        scene_dict = valid_scene.to_dict()

        assert scene_dict["chapter_id"] == "chapter-123"
        assert scene_dict["scene_number"] == 1
        assert scene_dict["title"] == "Test Scene"
        assert scene_dict["content"] == "This is the scene content."
        assert scene_dict["scene_type"] == "narrative"
        assert scene_dict["metadata"] == {"mood": "tense"}
        assert "choices" in scene_dict
        assert len(scene_dict["choices"]) == 1
        assert "id" in scene_dict
        assert "created_at" in scene_dict
        assert "updated_at" in scene_dict


class TestSceneInvariants:
    """Test cases for invariant validation."""

    def test_scene_belongs_to_chapter(self) -> None:
        """Test that scene always belongs to a chapter."""
        scene = Scene(
            chapter_id="chapter-123",
            scene_number=1,
            content="Test content",
        )

        assert scene.chapter_id == "chapter-123"

    def test_scene_number_positive(self) -> None:
        """Test that scene_number is always positive."""
        scene = Scene(
            chapter_id="chapter-123",
            scene_number=5,
            content="Test",
        )

        assert scene.scene_number > 0

    def test_scene_equality(self) -> None:
        """Test scene equality based on ID."""
        scene1 = Scene(
            chapter_id="chapter-1",
            scene_number=1,
            content="Content 1",
        )
        scene2 = Scene(
            chapter_id="chapter-2",
            scene_number=2,
            content="Content 2",
        )

        assert scene1 != scene2

    def test_scene_hash(self) -> None:
        """Test scene hash based on ID."""
        scene1 = Scene(
            chapter_id="chapter-1",
            scene_number=1,
            content="Test",
        )
        scene2 = Scene(
            chapter_id="chapter-1",
            scene_number=1,
            content="Test",
        )

        assert hash(scene1) != hash(scene2)
