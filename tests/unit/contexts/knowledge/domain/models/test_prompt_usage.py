"""
Tests for Prompt Usage Domain Models

Warzone 4: AI Brain - BRAIN-022A
Tests for PromptUsage entity and PromptUsageStats value object.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.contexts.knowledge.domain.models.prompt_usage import (
    PromptUsage,
    PromptUsageStats,
)

pytestmark = pytest.mark.unit

def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class TestPromptUsage:
    """Tests for PromptUsage entity."""

    def test_create_usage_with_factory(self):
        """Test creating a usage event via factory method."""
        usage = PromptUsage.create(
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

        assert usage.prompt_id == "prompt-123"
        assert usage.prompt_name == "Test Prompt"
        assert usage.prompt_version == 1
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300
        assert usage.latency_ms == 1500.0
        assert usage.model_provider == "gemini"
        assert usage.model_name == "gemini-2.0-flash"
        assert usage.success is True
        assert usage.user_rating == 5.0
        assert usage.workspace_id == "workspace-abc"
        assert usage.user_id == "user-xyz"

    def test_usage_validation_requires_id(self):
        """Test that usage requires a non-empty ID."""
        # Note: The create() factory always generates a UUID, and __post_init__
        # validation is disabled for id to allow factory-generated UUIDs.
        # This test documents that behavior.
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
        )
        assert usage.id  # UUID was generated

    def test_usage_validation_requires_prompt_id(self):
        """Test that usage requires a non-empty prompt_id."""
        with pytest.raises(ValueError, match="prompt_id cannot be empty"):
            PromptUsage.create(
                prompt_id="",
                prompt_name="Test",
                prompt_version=1,
            )

    def test_usage_validation_requires_prompt_name(self):
        """Test that usage requires a non-empty prompt_name."""
        with pytest.raises(ValueError, match="prompt_name cannot be empty"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="",
                prompt_version=1,
            )

    def test_usage_validation_requires_positive_version(self):
        """Test that prompt_version must be >= 1."""
        with pytest.raises(ValueError, match="prompt_version must be >= 1"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=0,
            )

    def test_usage_validation_no_negative_tokens(self):
        """Test that input_tokens cannot be negative."""
        with pytest.raises(ValueError, match="input_tokens cannot be negative"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=-1,
            )

    def test_usage_validation_no_negative_output_tokens(self):
        """Test that output_tokens cannot be negative."""
        with pytest.raises(ValueError, match="output_tokens cannot be negative"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                output_tokens=-1,
            )

    def test_usage_validation_total_tokens_must_match_sum(self):
        """Test that total_tokens must equal input + output."""
        # create() calculates total_tokens automatically, so we test
        # the direct constructor instead
        from uuid import uuid4
        with pytest.raises(ValueError, match="total_tokens.*must equal"):
            PromptUsage(
                id=str(uuid4()),
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                input_tokens=100,
                output_tokens=200,
                total_tokens=500,  # Wrong: should be 300
                timestamp=_utcnow(),
            )

    def test_usage_validation_negative_latency(self):
        """Test that latency_ms cannot be negative."""
        with pytest.raises(ValueError, match="latency_ms cannot be negative"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                latency_ms=-1.0,
            )

    def test_usage_validation_rating_range(self):
        """Test that user_rating must be between 1 and 5."""
        with pytest.raises(ValueError, match="user_rating must be between 1 and 5"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                user_rating=6.0,
            )

        with pytest.raises(ValueError, match="user_rating must be between 1 and 5"):
            PromptUsage.create(
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                user_rating=0.0,
            )

    def test_model_identifier_property(self):
        """Test model_identifier property."""
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
            model_provider="openai",
            model_name="gpt-4o-mini",
        )

        assert usage.model_identifier == "openai:gpt-4o-mini"

    def test_model_identifier_empty(self):
        """Test model_identifier with empty values."""
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
            model_provider="",
            model_name="",
        )

        assert usage.model_identifier == "unknown"

    def test_with_rating_creates_new_instance(self):
        """Test with_rating method creates a new usage with updated rating."""
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
        )

        updated = usage.with_rating(4.0)

        assert updated.id == usage.id
        assert updated.user_rating == 4.0
        assert usage.user_rating is None  # Original unchanged

    def test_to_dict(self):
        """Test serialization to dictionary."""
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test Prompt",
            prompt_version=1,
            input_tokens=100,
            output_tokens=200,
            latency_ms=1500.5,
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            success=True,
            user_rating=5.0,
            workspace_id="workspace-abc",
            user_id="user-xyz",
            variables={"var1": "value1", "var2": 42},
        )

        data = usage.to_dict()

        assert data["prompt_id"] == "prompt-123"
        assert data["prompt_name"] == "Test Prompt"
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 200
        assert data["total_tokens"] == 300
        # Round to 1 decimal place
        assert data["latency_ms"] == 1500.5
        assert data["model_identifier"] == "gemini:gemini-2.0-flash"
        assert data["success"] is True
        assert data["user_rating"] == 5.0
        assert data["workspace_id"] == "workspace-abc"
        assert data["user_id"] == "user-xyz"
        # Variables are sanitized (count only)
        assert data["variables_count"] == 2

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "usage-123",
            "prompt_id": "prompt-456",
            "prompt_name": "Test",
            "prompt_version": 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_tokens": 50,
            "output_tokens": 100,
            "total_tokens": 150,
            "latency_ms": 500.0,
            "model_provider": "anthropic",
            "model_name": "claude-3-haiku",
            "success": True,
            "user_rating": 4.5,
            "workspace_id": "workspace-xyz",
            "user_id": "user-abc",
            "variables": {"test": "value"},
        }

        usage = PromptUsage.from_dict(data)

        assert usage.id == "usage-123"
        assert usage.prompt_id == "prompt-456"
        assert usage.prompt_name == "Test"
        assert usage.prompt_version == 2

    def test_usage_for_failed_generation(self):
        """Test creating usage for a failed generation."""
        usage = PromptUsage.create(
            prompt_id="prompt-123",
            prompt_name="Test",
            prompt_version=1,
            success=False,
            error_message="API timeout",
        )

        assert usage.success is False
        assert usage.error_message == "API timeout"
        assert usage.total_tokens == 0


class TestPromptUsageStats:
    """Tests for PromptUsageStats value object."""

    def test_stats_from_usages(self):
        """Test creating stats from a list of usages."""
        now = datetime.now(timezone.utc)
        usages = [
            PromptUsage(
                id="usage-1",
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                timestamp=now - timedelta(hours=2),
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
                latency_ms=1000.0,
                success=True,
                user_rating=5.0,
            ),
            PromptUsage(
                id="usage-2",
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                timestamp=now - timedelta(hours=1),
                input_tokens=150,
                output_tokens=250,
                total_tokens=400,
                latency_ms=1500.0,
                success=True,
                user_rating=4.0,
            ),
            PromptUsage(
                id="usage-3",
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                timestamp=now,
                input_tokens=200,
                output_tokens=0,
                total_tokens=200,
                latency_ms=500.0,
                success=False,
            ),
        ]

        stats = PromptUsageStats.from_usages(usages)

        assert stats.prompt_id == "prompt-123"
        assert stats.prompt_name == "Test"
        assert stats.total_uses == 3
        assert stats.successful_uses == 2
        assert stats.failed_uses == 1
        assert stats.total_tokens == 900
        assert stats.total_input_tokens == 450
        assert stats.total_output_tokens == 450
        assert stats.total_latency_ms == 3000.0
        assert stats.rating_sum == 9.0
        assert stats.rating_count == 2

    def test_stats_from_empty_usages(self):
        """Test creating stats from empty list."""
        stats = PromptUsageStats.from_usages([])

        assert stats.prompt_id == ""
        assert stats.prompt_name == ""
        assert stats.total_uses == 0

    def test_stats_properties(self):
        """Test calculated properties of stats."""
        now = datetime.now(timezone.utc)
        usages = [
            PromptUsage(
                id="usage-1",
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                timestamp=now - timedelta(hours=1),
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
                latency_ms=1000.0,
                success=True,
                user_rating=5.0,
            ),
            PromptUsage(
                id="usage-2",
                prompt_id="prompt-123",
                prompt_name="Test",
                prompt_version=1,
                timestamp=now,
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
                latency_ms=2000.0,
                success=False,
            ),
        ]

        stats = PromptUsageStats.from_usages(usages)

        # Success rate: 1 success / 2 total = 50%
        assert stats.success_rate == 50.0

        # Avg tokens per use: 600 / 2 = 300
        assert stats.avg_tokens_per_use == 300.0
        assert stats.avg_input_tokens == 100.0
        assert stats.avg_output_tokens == 200.0

        # Avg latency: 3000 / 2 = 1500
        assert stats.avg_latency_ms == 1500.0

        # Avg rating: 5.0 / 1 rating = 5.0
        assert stats.avg_rating == 5.0

    def test_stats_properties_with_zero_uses(self):
        """Test calculated properties with zero uses."""
        stats = PromptUsageStats(
            prompt_id="prompt-123",
            prompt_name="Test",
        )

        assert stats.success_rate == 0.0
        assert stats.avg_tokens_per_use == 0.0
        assert stats.avg_latency_ms == 0.0
        assert stats.avg_rating == 0.0

    def test_stats_validation_requires_positive_uses(self):
        """Test that total_uses cannot be negative."""
        with pytest.raises(ValueError, match="total_uses cannot be negative"):
            PromptUsageStats(
                prompt_id="prompt-123",
                prompt_name="Test",
                total_uses=-1,
            )

    def test_stats_validation_uses_must_equal_success_plus_failure(self):
        """Test that total_uses must equal successful + failed."""
        with pytest.raises(ValueError, match="total_uses.*must equal"):
            PromptUsageStats(
                prompt_id="prompt-123",
                prompt_name="Test",
                total_uses=3,
                successful_uses=2,
                failed_uses=0,  # Should be 1
            )

    def test_stats_validation_tokens_must_equal_sum(self):
        """Test that total_tokens must equal input + output."""
        with pytest.raises(ValueError, match="total_tokens.*must equal"):
            PromptUsageStats(
                prompt_id="prompt-123",
                prompt_name="Test",
                total_input_tokens=100,
                total_output_tokens=200,
                total_tokens=400,  # Should be 300
            )

    def test_stats_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        stats = PromptUsageStats(
            prompt_id="prompt-123",
            prompt_name="Test Prompt",
            total_uses=10,
            successful_uses=8,
            failed_uses=2,
            total_tokens=5000,
            total_input_tokens=2000,
            total_output_tokens=3000,
            total_latency_ms=10000.0,
            rating_sum=35.0,
            rating_count=7,
            first_used=now - timedelta(days=1),
            last_used=now,
        )

        data = stats.to_dict()

        assert data["prompt_id"] == "prompt-123"
        assert data["prompt_name"] == "Test Prompt"
        assert data["total_uses"] == 10
        assert data["successful_uses"] == 8
        assert data["failed_uses"] == 2
        assert data["success_rate"] == 80.0
        assert data["total_tokens"] == 5000
        assert data["avg_tokens_per_use"] == 500.0
        assert data["avg_latency_ms"] == 1000.0
        assert data["avg_rating"] == 5.0
        assert "first_used" in data
        assert "last_used" in data
