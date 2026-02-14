"""
Tests for In-Memory Prompt Usage Repository Adapter

Warzone 4: AI Brain - BRAIN-022A
Tests for the in-memory implementation of IPromptUsageRepository.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.contexts.knowledge.domain.models.prompt_usage import (
    PromptUsage,
    PromptUsageStats,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_usage_repository import (
    InMemoryPromptUsageRepository,
)

pytestmark = pytest.mark.unit


class TestInMemoryPromptUsageRepository:
    """Tests for InMemoryPromptUsageRepository."""

    @pytest.fixture
    def repository(self):
        """Create a fresh repository for each test."""
        return InMemoryPromptUsageRepository()

    @pytest.fixture
    def sample_usage(self):
        """Create a sample usage event."""
        return PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test Prompt",
            prompt_version=1,
            input_tokens=100,
            output_tokens=200,
            latency_ms=1500.0,
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            success=True,
            user_rating=5.0,
            workspace_id="workspace-abc",
            user_id="user-xyz",
        )

    @pytest.mark.asyncio
    async def test_record_usage(self, repository, sample_usage):
        """Test recording a usage event."""
        usage_id = await repository.record(sample_usage)

        assert usage_id == sample_usage.id

        retrieved = await repository.get_usage_by_id(usage_id)
        assert retrieved is not None
        assert retrieved.prompt_id == "prompt-123"
        assert retrieved.prompt_name == "Test Prompt"

    @pytest.mark.asyncio
    async def test_record_batch(self, repository):
        """Test recording multiple usage events."""
        usages = [
            PromptUsage.create(
                prompt_id=f"prompt-{i}",
                prompt_name=f"Prompt {i}",
                prompt_version=1,
                input_tokens=50 * i,
                output_tokens=100 * i,
            )
            for i in range(1, 6)
        ]

        ids = await repository.record_batch(usages)

        assert len(ids) == 5
        for i, usage_id in enumerate(ids, 1):
            usage = await repository.get_usage_by_id(usage_id)
            assert usage is not None
            assert usage.prompt_id == f"prompt-{i}"

    @pytest.mark.asyncio
    async def test_get_stats(self, repository):
        """Test getting aggregated stats."""
        # Record multiple usages
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=100,
                output_tokens=200,
                success=True,
                user_rating=5.0,
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=150,
                output_tokens=250,
                success=True,
                user_rating=4.0,
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                success=False,
            )
        )

        stats = await repository.get_stats("prompt-123")

        assert stats.total_uses == 3
        assert stats.successful_uses == 2
        assert stats.failed_uses == 1
        # First usage: 100 + 200 = 300, Second: 150 + 250 = 400, Third: 0 + 0 = 0 (failed with no tokens)
        assert stats.total_tokens == 700
        assert stats.avg_rating == 4.5  # (5 + 4) / 2

    @pytest.mark.asyncio
    async def test_get_stats_filtered_by_workspace(self, repository):
        """Test getting stats filtered by workspace."""
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=100,
                output_tokens=200,
                workspace_id="workspace-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=150,
                output_tokens=250,
                workspace_id="workspace-b",
            )
        )

        stats_all = await repository.get_stats("prompt-123")
        assert stats_all.total_uses == 2

        stats_a = await repository.get_stats("prompt-123", workspace_id="workspace-a")
        assert stats_a.total_uses == 1

    @pytest.mark.asyncio
    async def test_get_stats_filtered_by_date(self, repository):
        """Test getting stats filtered by date range."""
        now = datetime.now(timezone.utc)
        old_usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
            timestamp=now - timedelta(days=2),
        )
        new_usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
            timestamp=now,
        )

        await repository.record_batch([old_usage, new_usage])

        # Recent stats (last 24 hours)
        recent_stats = await repository.get_stats(
            "prompt-123",
            start_date=now - timedelta(hours=1),
        )
        assert recent_stats.total_uses == 1

    @pytest.mark.asyncio
    async def test_list_by_prompt(self, repository, sample_usage):
        """Test listing usages by prompt ID."""
        # Record multiple usages for the same prompt with different timestamps
        now = datetime.now(timezone.utc)
        for i in range(5):
            await repository.record(
                PromptUsage.create(
                    prompt_id="prompt-123",
                    prompt_name="Test",
                    prompt_version=1,
                    latency_ms=1000.0 + i * 100,
                    timestamp=now
                    - timedelta(seconds=(5 - i) * 10),  # Different timestamps
                )
            )

        usages = await repository.list_by_prompt("prompt-123")

        assert len(usages) == 5
        # Should be sorted by timestamp descending (most recent first)
        # With timestamps: 0s ago (oldest i=4), 10s ago (i=3), ..., 40s ago (i=0, newest)
        # So the first should have the smallest timestamp difference (newest)
        assert usages[0].latency_ms >= usages[-1].latency_ms

    @pytest.mark.asyncio
    async def test_list_by_workspace(self, repository):
        """Test listing usages by workspace."""
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-1",
                prompt_name="Prompt 1",
                prompt_version=1,
                workspace_id="workspace-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-2",
                prompt_name="Prompt 2",
                prompt_version=1,
                workspace_id="workspace-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-3",
                prompt_name="Prompt 3",
                prompt_version=1,
                workspace_id="workspace-b",
            )
        )

        usages_a = await repository.list_by_workspace("workspace-a")

        assert len(usages_a) == 2
        assert all(u.workspace_id == "workspace-a" for u in usages_a)

    @pytest.mark.asyncio
    async def test_list_by_user(self, repository):
        """Test listing usages by user."""
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-1",
                prompt_name="Prompt 1",
                prompt_version=1,
                user_id="user-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-2",
                prompt_name="Prompt 2",
                prompt_version=1,
                user_id="user-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                prompt_id="prompt-3",
                prompt_name="Prompt 3",
                prompt_version=1,
                user_id="user-b",
            )
        )

        usages_a = await repository.list_by_user("user-a")

        assert len(usages_a) == 2
        assert all(u.user_id == "user-a" for u in usages_a)

    @pytest.mark.asyncio
    async def test_list_by_date_range(self, repository):
        """Test listing usages by date range."""
        now = datetime.now(timezone.utc)

        # Create usages at different times
        old_usage = PromptUsage.create(
            prompt_id="prompt-old",
            prompt_name="Old",
            prompt_version=1,
            timestamp=now - timedelta(days=7),
        )
        recent_usage1 = PromptUsage.create(
            prompt_id="prompt-recent",
            prompt_name="Recent 1",
            prompt_version=1,
            timestamp=now - timedelta(hours=2),
        )
        recent_usage2 = PromptUsage.create(
            prompt_id="prompt-recent",
            prompt_name="Recent 2",
            prompt_version=1,
            timestamp=now - timedelta(hours=1),
        )

        await repository.record_batch([old_usage, recent_usage1, recent_usage2])

        # Query last 3 hours
        start = now - timedelta(hours=3)
        end = now
        usages = await repository.list_by_date_range(start, end)

        assert len(usages) == 2
        assert all(start <= u.timestamp <= end for u in usages)

    @pytest.mark.asyncio
    async def test_delete_old_usages(self, repository):
        """Test deleting usages older than a cutoff."""
        now = datetime.now(timezone.utc)

        old_usage = PromptUsage.create(
            prompt_id="prompt-old",
            prompt_name="Old",
            prompt_version=1,
            timestamp=now - timedelta(days=10),
        )
        new_usage = PromptUsage.create(
            prompt_id="prompt-new",
            prompt_name="New",
            prompt_version=1,
            timestamp=now,
        )

        await repository.record_batch([old_usage, new_usage])

        # Delete usages older than 7 days
        cutoff = now - timedelta(days=7)
        deleted = await repository.delete_old_usages(cutoff)

        assert deleted == 1

        # Old usage should be gone
        assert await repository.get_usage_by_id(old_usage.id) is None
        # New usage should remain
        assert await repository.get_usage_by_id(new_usage.id) is not None

    @pytest.mark.asyncio
    async def test_delete_old_usages_filtered_by_workspace(self, repository):
        """Test deleting old usages filtered by workspace."""
        now = datetime.now(timezone.utc)

        await repository.record(
            PromptUsage.create(
                id="old-a",
                prompt_id="prompt-1",
                prompt_name="Prompt 1",
                prompt_version=1,
                timestamp=now - timedelta(days=10),
                workspace_id="workspace-a",
            )
        )
        await repository.record(
            PromptUsage.create(
                id="old-b",
                prompt_id="prompt-2",
                prompt_name="Prompt 2",
                prompt_version=1,
                timestamp=now - timedelta(days=10),
                workspace_id="workspace-b",
            )
        )

        cutoff = now - timedelta(days=7)

        # Only delete from workspace-a
        deleted = await repository.delete_old_usages(cutoff, workspace_id="workspace-a")

        assert deleted == 1
        assert await repository.get_usage_by_id("old-a") is None
        assert await repository.get_usage_by_id("old-b") is not None

    @pytest.mark.asyncio
    async def test_count(self, repository):
        """Test counting usage events."""
        # Count all
        assert await repository.count() == 0

        await repository.record(
            PromptUsage.create(prompt_id="prompt-1", prompt_name="P1", prompt_version=1)
        )
        await repository.record(
            PromptUsage.create(prompt_id="prompt-1", prompt_name="P1", prompt_version=1)
        )
        await repository.record(
            PromptUsage.create(prompt_id="prompt-2", prompt_name="P2", prompt_version=1)
        )

        assert await repository.count() == 3
        assert await repository.count(prompt_id="prompt-1") == 2
        assert await repository.count(prompt_id="prompt-2") == 1

    @pytest.mark.asyncio
    async def test_update_rating(self, repository, sample_usage):
        """Test updating the user rating for a usage event."""
        await repository.record(sample_usage)

        # Update rating
        success = await repository.update_rating(sample_usage.id, 3.0)

        assert success is True

        # Verify update
        updated = await repository.get_usage_by_id(sample_usage.id)
        assert updated is not None
        assert updated.user_rating == 3.0

    @pytest.mark.asyncio
    async def test_update_rating_not_found(self, repository):
        """Test updating rating for non-existent usage."""
        success = await repository.update_rating("non-existent", 5.0)
        assert success is False

    @pytest.mark.asyncio
    async def test_list_by_prompt_with_pagination(self, repository):
        """Test pagination when listing by prompt."""
        # Record 25 usages
        for i in range(25):
            await repository.record(
                PromptUsage.create(
                    prompt_id="prompt-123",
                    prompt_name="Test",
                    prompt_version=1,
                    input_tokens=i * 10,
                )
            )

        # First page
        page1 = await repository.list_by_prompt("prompt-123", limit=10, offset=0)
        assert len(page1) == 10

        # Second page
        page2 = await repository.list_by_prompt("prompt-123", limit=10, offset=10)
        assert len(page2) == 10

        # Third page (partial)
        page3 = await repository.list_by_prompt("prompt-123", limit=10, offset=20)
        assert len(page3) == 5

    @pytest.mark.asyncio
    async def test_clear(self, repository):
        """Test clearing the repository."""
        await repository.record(
            PromptUsage.create(prompt_id="prompt-1", prompt_name="P1", prompt_version=1)
        )
        await repository.record(
            PromptUsage.create(prompt_id="prompt-2", prompt_name="P2", prompt_version=1)
        )

        assert await repository.count() == 2

        repository.clear()

        assert await repository.count() == 0
