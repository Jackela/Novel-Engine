"""
Tests for Prompt Router Service Analytics

Warzone 4: AI Brain - BRAIN-022B
Unit tests for the prompt analytics functionality.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.services.prompt_router_service import PromptRouterService
from src.contexts.knowledge.domain.models.prompt_template import (
    PromptTemplate,
)
from src.contexts.knowledge.domain.models.prompt_usage import (
    PromptUsage,
    PromptUsageStats,
)

pytestmark = pytest.mark.unit


class MockPromptRepository:
    """Mock repository for testing."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._deleted_ids: set[str] = set()

    async def save(self, template: PromptTemplate) -> str:
        self._templates[template.id] = template
        return template.id

    async def get_by_id(self, template_id: str) -> PromptTemplate | None:
        if template_id in self._deleted_ids:
            return None
        return self._templates.get(template_id)

    async def get_by_name(
        self, name: str, version: int | None = None
    ) -> PromptTemplate | None:
        for template in self._templates.values():
            if template.name == name and template.id not in self._deleted_ids:
                if version is None or template.version == version:
                    return template
        return None

    async def list_all(
        self,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptTemplate]:
        results = [t for t in self._templates.values() if t.id not in self._deleted_ids]

        if tags:
            for t in self._templates.values():
                if t.id not in self._deleted_ids and all(tag in t.tags for tag in tags):
                    results.append(t)

        return results[offset : offset + limit]

    async def delete(self, template_id: str) -> bool:
        if template_id in self._templates and template_id not in self._deleted_ids:
            self._deleted_ids.add(template_id)
            return True
        return False

    async def count(self) -> int:
        return len(
            [t for t in self._templates.values() if t.id not in self._deleted_ids]
        )

    async def search(self, query: str, limit: int = 20) -> list[PromptTemplate]:
        query_lower = query.lower()
        results = []
        for t in self._templates.values():
            if t.id not in self._deleted_ids:
                if (
                    query_lower in t.name.lower()
                    or query_lower in (t.description or "").lower()
                ):
                    results.append(t)
                    if len(results) >= limit:
                        break
        return results

    async def get_version_history(self, prompt_id: str) -> list[PromptTemplate]:
        return [
            t
            for t in self._templates.values()
            if (t.id == prompt_id or t.parent_version_id == prompt_id)
            and t.id not in self._deleted_ids
        ]


class MockPromptUsageRepository:
    """Mock usage repository for testing analytics."""

    def __init__(self) -> None:
        self._usages: list = []

    async def record(self, usage):
        from src.contexts.knowledge.domain.models.prompt_usage import PromptUsage

        # Convert dict to PromptUsage if needed
        if isinstance(usage, dict):
            usage = PromptUsage.create(**usage)

        self._usages.append(usage)
        return usage.id

    async def get_stats(
        self,
        prompt_id: str,
        workspace_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        from src.contexts.knowledge.domain.models.prompt_usage import PromptUsageStats

        # Filter usages by prompt_id
        filtered = [u for u in self._usages if u.prompt_id == prompt_id]

        # Apply workspace filter
        if workspace_id:
            filtered = [u for u in filtered if u.workspace_id == workspace_id]

        # Apply date filters
        if start_date:
            filtered = [u for u in filtered if u.timestamp >= start_date]
        if end_date:
            filtered = [u for u in filtered if u.timestamp <= end_date]

        return PromptUsageStats.from_usages(filtered)

    async def list_by_prompt(
        self,
        prompt_id: str,
        limit: int = 100,
        offset: int = 0,
        workspace_id: str | None = None,
    ):
        # Filter usages by prompt_id
        filtered = [u for u in self._usages if u.prompt_id == prompt_id]

        # Apply workspace filter
        if workspace_id:
            filtered = [u for u in filtered if u.workspace_id == workspace_id]

        # Sort by timestamp descending
        filtered = sorted(filtered, key=lambda u: u.timestamp, reverse=True)

        return filtered[offset : offset + limit]


class TestPromptRouterServiceAnalytics:
    """Tests for prompt analytics functionality (BRAIN-022B)."""

    @pytest.fixture
    async def service_with_usage(self) -> tuple[PromptRouterService, str]:
        """Create service with mock usage repository and test data."""
        repo = MockPromptRepository()
        usage_repo = MockPromptUsageRepository()
        service = PromptRouterService(repo, usage_repo)

        # Create a test prompt
        prompt = PromptTemplate.create(
            name="Analytics Test Prompt",
            content="Generate {{output_type}} for {{topic}}",
        )
        prompt_id = await service.save_prompt(prompt)

        # Add usage data with different timestamps
        base_time = datetime.now(timezone.utc)

        usage_data = [
            {
                "prompt_id": prompt_id,
                "prompt_name": "Analytics Test Prompt",
                "prompt_version": 1,
                "timestamp": base_time - timedelta(days=5),
                "input_tokens": 100,
                "output_tokens": 200,
                "latency_ms": 1500.0,
                "model_provider": "gemini",
                "model_name": "gemini-2.0-flash",
                "success": True,
                "user_rating": 5.0,
            },
            {
                "prompt_id": prompt_id,
                "prompt_name": "Analytics Test Prompt",
                "prompt_version": 1,
                "timestamp": base_time - timedelta(days=3),
                "input_tokens": 150,
                "output_tokens": 250,
                "latency_ms": 1800.0,
                "model_provider": "gemini",
                "model_name": "gemini-2.0-flash",
                "success": True,
                "user_rating": 4.0,
            },
            {
                "prompt_id": prompt_id,
                "prompt_name": "Analytics Test Prompt",
                "prompt_version": 1,
                "timestamp": base_time - timedelta(days=1),
                "input_tokens": 120,
                "output_tokens": 180,
                "latency_ms": 1400.0,
                "model_provider": "gemini",
                "model_name": "gemini-2.0-flash",
                "success": True,
                "user_rating": None,  # No rating
            },
            {
                "prompt_id": prompt_id,
                "prompt_name": "Analytics Test Prompt",
                "prompt_version": 1,
                "timestamp": base_time,
                "input_tokens": 80,
                "output_tokens": 150,
                "latency_ms": 1200.0,
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "success": True,
                "user_rating": 5.0,
            },
            {
                "prompt_id": prompt_id,
                "prompt_name": "Analytics Test Prompt",
                "prompt_version": 1,
                "timestamp": base_time,
                "input_tokens": 90,
                "output_tokens": 0,
                "latency_ms": 500.0,
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "success": False,
                "error_message": "Rate limit exceeded",
            },
        ]

        for usage in usage_data:
            await usage_repo.record(usage)

        return service, prompt_id

    @pytest.mark.asyncio
    async def test_get_prompt_analytics_basic(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test basic analytics retrieval."""
        service, prompt_id = service_with_usage

        analytics = await service.get_prompt_analytics(prompt_id)

        assert analytics["prompt_id"] == prompt_id
        assert analytics["total_uses"] == 5
        assert analytics["successful_uses"] == 4
        assert analytics["failed_uses"] == 1
        assert analytics["success_rate"] == 80.0
        assert analytics["total_tokens"] > 0
        assert analytics["rating_count"] == 3
        assert analytics["avg_rating"] == pytest.approx(14.0 / 3, abs=0.01)

    @pytest.mark.asyncio
    async def test_get_prompt_analytics_rating_distribution(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test rating distribution in analytics."""
        service, prompt_id = service_with_usage

        analytics = await service.get_prompt_analytics(prompt_id)

        dist = analytics["rating_distribution"]
        assert dist["five_star"] == 2
        assert dist["four_star"] == 1
        assert dist["three_star"] == 0
        assert dist["two_star"] == 0
        assert dist["one_star"] == 0

    @pytest.mark.asyncio
    async def test_get_prompt_analytics_latency_metrics(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test latency metrics in analytics."""
        service, prompt_id = service_with_usage

        analytics = await service.get_prompt_analytics(prompt_id)

        assert analytics["min_latency_ms"] == 500.0
        assert analytics["max_latency_ms"] == 1800.0
        assert analytics["avg_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_get_prompt_analytics_no_usage_repository(
        self,
    ) -> None:
        """Test analytics raises error when usage repository not configured."""
        repo = MockPromptRepository()
        service = PromptRouterService(repo, None)  # No usage repository
        """Test analytics raises error when usage repository not configured."""
        # Create a prompt without usage repository
        prompt = PromptTemplate.create(
            name="No Usage Prompt",
            content="Test: {{input}}",
        )
        prompt_id = await service.save_prompt(prompt)

        with pytest.raises(ValueError, match="Usage repository is not configured"):
            await service.get_prompt_analytics(prompt_id)

    @pytest.mark.asyncio
    async def test_export_analytics_csv(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test CSV export of analytics."""
        service, prompt_id = service_with_usage

        csv_data = await service.export_analytics_csv(prompt_id)

        assert csv_data is not None
        assert "Timestamp" in csv_data
        assert "Prompt ID" in csv_data
        assert "Input Tokens" in csv_data
        assert "Output Tokens" in csv_data
        assert "Total Tokens" in csv_data
        assert "Latency (ms)" in csv_data

        # Check for data rows
        lines = csv_data.strip().split("\n")
        assert len(lines) >= 6  # Header + 5 data rows

    @pytest.mark.asyncio
    async def test_calculate_rating_distribution(
        self,
    ) -> None:
        """Test rating distribution calculation."""
        repo = MockPromptRepository()
        usage_repo = MockPromptUsageRepository()
        service = PromptRouterService(repo, usage_repo)
        """Test rating distribution calculation."""
        usages = [
            PromptUsage.create(
                prompt_id="test",
                prompt_name="Test",
                prompt_version=1,
                user_rating=5.0,
            ),
            PromptUsage.create(
                prompt_id="test",
                prompt_name="Test",
                prompt_version=1,
                user_rating=5.0,
            ),
            PromptUsage.create(
                prompt_id="test",
                prompt_name="Test",
                prompt_version=1,
                user_rating=3.0,
            ),
            PromptUsage.create(
                prompt_id="test",
                prompt_name="Test",
                prompt_version=1,
                # No rating
            ),
        ]

        dist = service._calculate_rating_distribution(usages)

        assert dist["five_star"] == 2
        assert dist["four_star"] == 0
        assert dist["three_star"] == 1
        assert dist["two_star"] == 0
        assert dist["one_star"] == 0

    @pytest.mark.asyncio
    async def test_build_time_series_day_period(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test time series building with day period."""
        service, prompt_id = service_with_usage

        # Get usages for time series
        usages = await service._usage_repository.list_by_prompt(prompt_id, limit=100)

        time_series = service._build_time_series(usages, "day", limit=10)

        # Should have at least 2 unique days
        assert len(time_series) >= 2

        # Check data point structure
        for point in time_series:
            assert "period" in point
            assert "total_uses" in point
            assert "successful_uses" in point
            assert "avg_latency_ms" in point
            assert "avg_rating" in point

    @pytest.mark.asyncio
    async def test_build_time_series_all_period(
        self, service_with_usage: tuple[PromptRouterService, str]
    ) -> None:
        """Test time series with 'all' period returns empty."""
        service, prompt_id = service_with_usage

        usages = await service._usage_repository.list_by_prompt(prompt_id, limit=100)

        time_series = service._build_time_series(usages, "all", limit=10)

        # 'all' period should return empty time series
        assert len(time_series) == 0
