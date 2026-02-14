"""Unit tests for MemoryStore.

Tests cover the three main operations:
- store(): Storing memory entries
- retrieve(): Retrieving memory entries by ID
- delete(): Deleting memory entries
"""

import pytest

from src.contexts.character.infrastructure.persistence.memory_store import (
    MemoryEntry,
    MemoryStore,
)


@pytest.mark.unit
class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_memory_entry_creation(self):
        """MemoryEntry can be created with required fields."""
        entry = MemoryEntry(
            memory_id="mem-001",
            content="Test memory content",
        )
        assert entry.memory_id == "mem-001"
        assert entry.content == "Test memory content"
        assert entry.metadata == {}
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_memory_entry_with_metadata(self):
        """MemoryEntry can include optional metadata."""
        entry = MemoryEntry(
            memory_id="mem-002",
            content="Memory with metadata",
            metadata={"importance": 5, "tags": ["important", "story"]},
        )
        assert entry.metadata["importance"] == 5
        assert "important" in entry.metadata["tags"]


class TestMemoryStoreStore:
    """Tests for MemoryStore.store() method."""

    @pytest.mark.unit
    def test_store_creates_new_entry(self):
        """store() creates a new memory entry."""
        store = MemoryStore()
        store.store("mem-001", "First memory")

        entry = store.retrieve("mem-001")
        assert entry is not None
        assert entry.content == "First memory"

    @pytest.mark.unit
    def test_store_with_metadata(self):
        """store() preserves metadata."""
        store = MemoryStore()
        metadata = {"importance": 10, "character": "Alice"}
        store.store("mem-002", "Important memory", metadata=metadata)

        entry = store.retrieve("mem-002")
        assert entry is not None
        assert entry.metadata["importance"] == 10
        assert entry.metadata["character"] == "Alice"

    @pytest.mark.unit
    def test_store_updates_existing_entry(self):
        """store() updates an existing entry while preserving created_at."""
        store = MemoryStore()
        store.store("mem-003", "Original content")
        original_entry = store.retrieve("mem-003")
        original_created_at = original_entry.created_at

        store.store("mem-003", "Updated content")

        updated_entry = store.retrieve("mem-003")
        assert updated_entry.content == "Updated content"
        assert updated_entry.created_at == original_created_at
        assert updated_entry.updated_at >= original_entry.updated_at

    @pytest.mark.unit
    def test_store_empty_string_content(self):
        """store() accepts empty string content."""
        store = MemoryStore()
        store.store("mem-empty", "")

        entry = store.retrieve("mem-empty")
        assert entry is not None
        assert entry.content == ""

    @pytest.mark.unit
    def test_store_none_metadata_defaults_to_empty_dict(self):
        """store() converts None metadata to empty dict."""
        store = MemoryStore()
        store.store("mem-none-meta", "Content", metadata=None)

        entry = store.retrieve("mem-none-meta")
        assert entry is not None
        assert entry.metadata == {}


class TestMemoryStoreRetrieve:
    """Tests for MemoryStore.retrieve() method."""

    @pytest.mark.unit
    def test_retrieve_existing_entry(self):
        """retrieve() returns the entry if it exists."""
        store = MemoryStore()
        store.store("mem-retrieve-001", "Retrievable content")

        entry = store.retrieve("mem-retrieve-001")
        assert entry is not None
        assert entry.content == "Retrievable content"

    @pytest.mark.unit
    def test_retrieve_nonexistent_entry_returns_none(self):
        """retrieve() returns None for nonexistent IDs."""
        store = MemoryStore()

        entry = store.retrieve("nonexistent-id")
        assert entry is None

    @pytest.mark.unit
    def test_retrieve_after_delete_returns_none(self):
        """retrieve() returns None after entry is deleted."""
        store = MemoryStore()
        store.store("mem-to-delete", "Will be deleted")
        store.delete("mem-to-delete")

        entry = store.retrieve("mem-to-delete")
        assert entry is None


class TestMemoryStoreDelete:
    """Tests for MemoryStore.delete() method."""

    @pytest.mark.unit
    def test_delete_existing_entry_returns_true(self):
        """delete() returns True when entry is deleted."""
        store = MemoryStore()
        store.store("mem-del-001", "To be deleted")

        result = store.delete("mem-del-001")
        assert result is True

    @pytest.mark.unit
    def test_delete_removes_entry(self):
        """delete() actually removes the entry from the store."""
        store = MemoryStore()
        store.store("mem-del-002", "To be removed")
        store.delete("mem-del-002")

        entry = store.retrieve("mem-del-002")
        assert entry is None

    @pytest.mark.unit
    def test_delete_nonexistent_entry_returns_false(self):
        """delete() returns False when entry doesn't exist."""
        store = MemoryStore()

        result = store.delete("nonexistent-id")
        assert result is False

    @pytest.mark.unit
    def test_delete_twice_returns_false_second_time(self):
        """delete() returns False on second call for same ID."""
        store = MemoryStore()
        store.store("mem-del-twice", "Content")

        first_result = store.delete("mem-del-twice")
        second_result = store.delete("mem-del-twice")

        assert first_result is True
        assert second_result is False


class TestMemoryStoreHelperMethods:
    """Tests for MemoryStore helper methods."""

    @pytest.mark.unit
    def test_clear_removes_all_entries(self):
        """clear() removes all entries from the store."""
        store = MemoryStore()
        store.store("mem-1", "One")
        store.store("mem-2", "Two")
        store.store("mem-3", "Three")

        store.clear()

        assert store.count() == 0

    @pytest.mark.unit
    def test_count_returns_correct_number(self):
        """count() returns the number of stored entries."""
        store = MemoryStore()
        assert store.count() == 0

        store.store("mem-1", "One")
        assert store.count() == 1

        store.store("mem-2", "Two")
        assert store.count() == 2

    @pytest.mark.unit
    def test_list_all_returns_sorted_entries(self):
        """list_all() returns entries sorted by created_at descending."""
        store = MemoryStore()
        store.store("mem-old", "Older memory")
        store.store("mem-new", "Newer memory")

        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        store.store("mem-newest", "Newest memory")

        entries = store.list_all()
        assert len(entries) == 3
        # Newest should be first (descending order)
        assert entries[0].memory_id == "mem-newest"
