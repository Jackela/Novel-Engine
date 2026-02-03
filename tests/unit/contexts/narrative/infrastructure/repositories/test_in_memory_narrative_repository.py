"""Unit tests for InMemoryNarrativeRepository.

This module tests the in-memory implementation of INarrativeRepository,
verifying that it correctly implements the repository contract.

Why test the in-memory implementation:
    Even though it's primarily for testing, the in-memory repository
    must correctly implement the interface contract. These tests serve
    as a specification that any other implementation must also satisfy.
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.application.ports import INarrativeRepository
from src.contexts.narrative.domain import Chapter, Story
from src.contexts.narrative.infrastructure.repositories import (
    InMemoryNarrativeRepository,
)

pytestmark = pytest.mark.unit


class TestInMemoryNarrativeRepositoryInstantiation:
    """Tests for repository instantiation."""

    def test_creates_empty_repository(self) -> None:
        """Repository should start empty."""
        repo = InMemoryNarrativeRepository()
        assert repo.count == 0

    def test_implements_interface(self) -> None:
        """Repository should implement INarrativeRepository."""
        repo = InMemoryNarrativeRepository()
        assert isinstance(repo, INarrativeRepository)


class TestSaveOperation:
    """Tests for the save() method."""

    def test_save_new_story(self) -> None:
        """Should save a new story successfully."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")

        repo.save(story)

        assert repo.count == 1
        assert repo.exists(story.id)

    def test_save_story_with_chapters(self) -> None:
        """Should save a story including its chapters."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        chapter = Chapter(title="Chapter 1", story_id=story.id, order_index=0)
        story.add_chapter(chapter)

        repo.save(story)

        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        assert loaded.chapter_count == 1
        assert loaded.chapters[0].title == "Chapter 1"

    def test_save_creates_deep_copy(self) -> None:
        """Modifying original after save should not affect stored version."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Original Title")
        repo.save(story)

        # Modify the original
        story.update_title("Modified Title")

        # Stored version should be unchanged
        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        assert loaded.title == "Original Title"

    def test_save_updates_existing_story(self) -> None:
        """Saving an existing story should update it."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Original Title")
        repo.save(story)

        # Modify and save again
        story.update_title("Updated Title")
        repo.save(story)

        assert repo.count == 1  # Still only one story
        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        assert loaded.title == "Updated Title"

    def test_save_multiple_stories(self) -> None:
        """Should handle multiple stories."""
        repo = InMemoryNarrativeRepository()
        story1 = Story(title="Story 1")
        story2 = Story(title="Story 2")

        repo.save(story1)
        repo.save(story2)

        assert repo.count == 2


class TestGetByIdOperation:
    """Tests for the get_by_id() method."""

    def test_get_existing_story(self) -> None:
        """Should return the story when it exists."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        repo.save(story)

        loaded = repo.get_by_id(story.id)

        assert loaded is not None
        assert loaded.id == story.id
        assert loaded.title == "Test Story"

    def test_get_nonexistent_story_returns_none(self) -> None:
        """Should return None when story doesn't exist."""
        repo = InMemoryNarrativeRepository()

        result = repo.get_by_id(uuid4())

        assert result is None

    def test_get_returns_deep_copy(self) -> None:
        """Modifying returned story should not affect stored version."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Original Title")
        repo.save(story)

        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        loaded.update_title("Modified Title")

        # Stored version should be unchanged
        reloaded = repo.get_by_id(story.id)
        assert reloaded is not None
        assert reloaded.title == "Original Title"

    def test_get_includes_chapters(self) -> None:
        """Returned story should include all chapters."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        chapter1 = Chapter(title="Chapter 1", story_id=story.id, order_index=0)
        chapter2 = Chapter(title="Chapter 2", story_id=story.id, order_index=1)
        story.add_chapter(chapter1)
        story.add_chapter(chapter2)
        repo.save(story)

        loaded = repo.get_by_id(story.id)

        assert loaded is not None
        assert loaded.chapter_count == 2
        assert loaded.chapters[0].title == "Chapter 1"
        assert loaded.chapters[1].title == "Chapter 2"


class TestListAllOperation:
    """Tests for the list_all() method."""

    def test_list_empty_repository(self) -> None:
        """Should return empty list when no stories exist."""
        repo = InMemoryNarrativeRepository()

        stories = repo.list_all()

        assert stories == []

    def test_list_all_stories(self) -> None:
        """Should return all stories."""
        repo = InMemoryNarrativeRepository()
        story1 = Story(title="Story 1")
        story2 = Story(title="Story 2")
        repo.save(story1)
        repo.save(story2)

        stories = repo.list_all()

        assert len(stories) == 2
        titles = {s.title for s in stories}
        assert titles == {"Story 1", "Story 2"}

    def test_list_returns_deep_copies(self) -> None:
        """Modifying listed stories should not affect stored versions."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Original Title")
        repo.save(story)

        stories = repo.list_all()
        stories[0].update_title("Modified Title")

        # Stored version should be unchanged
        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        assert loaded.title == "Original Title"

    def test_list_sorted_by_creation_time(self) -> None:
        """Stories should be sorted by creation time (oldest first)."""
        import time

        repo = InMemoryNarrativeRepository()

        # Create stories with slight delay to ensure different timestamps
        story1 = Story(title="First")
        repo.save(story1)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        story2 = Story(title="Second")
        repo.save(story2)

        stories = repo.list_all()

        assert len(stories) == 2
        assert stories[0].title == "First"
        assert stories[1].title == "Second"


class TestDeleteOperation:
    """Tests for the delete() method."""

    def test_delete_existing_story(self) -> None:
        """Should delete an existing story and return True."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        repo.save(story)

        result = repo.delete(story.id)

        assert result is True
        assert repo.count == 0
        assert not repo.exists(story.id)

    def test_delete_nonexistent_story_returns_false(self) -> None:
        """Should return False when story doesn't exist."""
        repo = InMemoryNarrativeRepository()

        result = repo.delete(uuid4())

        assert result is False

    def test_delete_one_of_multiple_stories(self) -> None:
        """Deleting one story should not affect others."""
        repo = InMemoryNarrativeRepository()
        story1 = Story(title="Story 1")
        story2 = Story(title="Story 2")
        repo.save(story1)
        repo.save(story2)

        repo.delete(story1.id)

        assert repo.count == 1
        assert not repo.exists(story1.id)
        assert repo.exists(story2.id)


class TestExistsOperation:
    """Tests for the exists() method."""

    def test_exists_returns_true_for_existing_story(self) -> None:
        """Should return True when story exists."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        repo.save(story)

        assert repo.exists(story.id) is True

    def test_exists_returns_false_for_nonexistent_story(self) -> None:
        """Should return False when story doesn't exist."""
        repo = InMemoryNarrativeRepository()

        assert repo.exists(uuid4()) is False

    def test_exists_after_delete(self) -> None:
        """Should return False after story is deleted."""
        repo = InMemoryNarrativeRepository()
        story = Story(title="Test Story")
        repo.save(story)
        repo.delete(story.id)

        assert repo.exists(story.id) is False


class TestClearOperation:
    """Tests for the clear() method."""

    def test_clear_empty_repository(self) -> None:
        """Clear on empty repository should succeed."""
        repo = InMemoryNarrativeRepository()
        repo.clear()
        assert repo.count == 0

    def test_clear_removes_all_stories(self) -> None:
        """Clear should remove all stories."""
        repo = InMemoryNarrativeRepository()
        repo.save(Story(title="Story 1"))
        repo.save(Story(title="Story 2"))
        repo.save(Story(title="Story 3"))

        repo.clear()

        assert repo.count == 0


class TestIntegrationScenarios:
    """Integration-style tests covering realistic usage patterns."""

    def test_story_lifecycle(self) -> None:
        """Test complete lifecycle: create, update, read, delete."""
        repo = InMemoryNarrativeRepository()

        # Create
        story = Story(title="My Novel")
        chapter = Chapter(title="Chapter 1", story_id=story.id)
        story.add_chapter(chapter)
        repo.save(story)
        assert repo.count == 1

        # Update
        story.update_title("My Great Novel")
        story.add_chapter(Chapter(title="Chapter 2", story_id=story.id, order_index=1))
        repo.save(story)

        # Read and verify
        loaded = repo.get_by_id(story.id)
        assert loaded is not None
        assert loaded.title == "My Great Novel"
        assert loaded.chapter_count == 2

        # Delete
        result = repo.delete(story.id)
        assert result is True
        assert repo.count == 0

    def test_multiple_stories_with_chapters(self) -> None:
        """Test handling multiple stories each with chapters."""
        repo = InMemoryNarrativeRepository()

        # Create two stories with chapters
        story1 = Story(title="Story 1")
        story1.add_chapter(Chapter(title="S1 C1", story_id=story1.id, order_index=0))
        story1.add_chapter(Chapter(title="S1 C2", story_id=story1.id, order_index=1))

        story2 = Story(title="Story 2")
        story2.add_chapter(Chapter(title="S2 C1", story_id=story2.id, order_index=0))

        repo.save(story1)
        repo.save(story2)

        # Verify
        assert repo.count == 2
        loaded1 = repo.get_by_id(story1.id)
        loaded2 = repo.get_by_id(story2.id)

        assert loaded1 is not None
        assert loaded1.chapter_count == 2
        assert loaded2 is not None
        assert loaded2.chapter_count == 1
