"""
Tests for Prompt Router Service

Warzone 4: AI Brain - BRAIN-015
Unit tests for the prompt router service layer.
"""

from __future__ import annotations

import pytest

from src.api.services.prompt_router_service import PromptRouterService
from src.contexts.knowledge.application.ports.i_prompt_repository import (
    PromptNotFoundError,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
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
            results = [t for t in results if all(tag in t.tags for tag in tags)]
        return results[offset : offset + limit]

    async def delete(self, template_id: str) -> bool:
        if template_id in self._templates and template_id not in self._deleted_ids:
            self._deleted_ids.add(template_id)
            return True
        return False

    async def get_version_history(self, template_id: str) -> list[PromptTemplate]:
        if template_id not in self._templates:
            return []
        template = self._templates[template_id]
        versions = [
            t
            for t in self._templates.values()
            if t.name == template.name and t.id not in self._deleted_ids
        ]
        return sorted(versions, key=lambda t: t.version)

    async def get_by_tag(self, tag: str, limit: int = 50) -> list[PromptTemplate]:
        results = [
            t
            for t in self._templates.values()
            if tag in t.tags and t.id not in self._deleted_ids
        ]
        return results[:limit]

    async def count(self) -> int:
        return sum(1 for t in self._templates.values() if t.id not in self._deleted_ids)

    async def search(self, query: str, limit: int = 20) -> list[PromptTemplate]:
        query_lower = query.lower()
        results = [
            t
            for t in self._templates.values()
            if t.id not in self._deleted_ids
            and (query_lower in t.name.lower() or query_lower in t.description.lower())
        ]
        return results[:limit]


@pytest.fixture
def mock_repo() -> MockPromptRepository:
    """Create a mock repository with sample prompts."""
    repo = MockPromptRepository()
    repo._templates["test-1"] = PromptTemplate(
        id="test-1",
        name="Test Prompt 1",
        content="Hello {{name}}, you are {{age}} years old.",
        description="A test prompt",
        tags=("test", "greeting"),
        variables=(
            VariableDefinition(name="name", type=VariableType.STRING, required=True),
            VariableDefinition(name="age", type=VariableType.INTEGER, required=True),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
    )
    repo._templates["test-2"] = PromptTemplate(
        id="test-2",
        name="Story Generator",
        content="Write a {{genre}} story about {{topic}}.",
        description="Generate stories based on genre and topic",
        tags=("creative", "story", "model:gpt-4"),
        variables=(
            VariableDefinition(name="genre", type=VariableType.STRING, required=True),
            VariableDefinition(name="topic", type=VariableType.STRING, required=True),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
    )
    return repo


@pytest.fixture
def service(mock_repo: MockPromptRepository) -> PromptRouterService:
    """Create a prompt router service with mock repository."""
    return PromptRouterService(mock_repo)


class TestPromptRouterService:
    """Tests for PromptRouterService."""

    @pytest.mark.asyncio
    async def test_list_prompts(
        self, service: PromptRouterService, mock_repo: MockPromptRepository
    ) -> None:
        """Test listing prompts."""
        prompts = await service.list_prompts()
        assert len(prompts) == 2
        assert prompts[0].name == "Test Prompt 1"
        assert prompts[1].name == "Story Generator"

    @pytest.mark.asyncio
    async def test_list_prompts_with_tags(self, service: PromptRouterService) -> None:
        """Test listing prompts filtered by tags."""
        prompts = await service.list_prompts(tags=["test"])
        assert len(prompts) == 1
        assert prompts[0].name == "Test Prompt 1"

    @pytest.mark.asyncio
    async def test_list_prompts_with_pagination(
        self, service: PromptRouterService
    ) -> None:
        """Test listing prompts with pagination."""
        prompts = await service.list_prompts(limit=1, offset=0)
        assert len(prompts) == 1

        prompts = await service.list_prompts(limit=1, offset=1)
        assert len(prompts) == 1

    @pytest.mark.asyncio
    async def test_search_prompts(self, service: PromptRouterService) -> None:
        """Test searching prompts."""
        prompts = await service.search_prompts("story")
        assert len(prompts) == 1
        assert prompts[0].name == "Story Generator"

    @pytest.mark.asyncio
    async def test_search_prompts_by_description(
        self, service: PromptRouterService
    ) -> None:
        """Test searching prompts by description."""
        prompts = await service.search_prompts("generate")
        assert len(prompts) == 1
        assert prompts[0].name == "Story Generator"

    @pytest.mark.asyncio
    async def test_get_prompt_by_id(self, service: PromptRouterService) -> None:
        """Test getting a prompt by ID."""
        template = await service.get_prompt_by_id("test-1")
        assert template.name == "Test Prompt 1"
        assert len(template.variables) == 2

    @pytest.mark.asyncio
    async def test_get_prompt_by_id_not_found(
        self, service: PromptRouterService
    ) -> None:
        """Test getting a non-existent prompt raises error."""
        with pytest.raises(PromptNotFoundError):
            await service.get_prompt_by_id("nonexistent")

    @pytest.mark.asyncio
    async def test_get_prompt_by_name(self, service: PromptRouterService) -> None:
        """Test getting a prompt by name."""
        template = await service.get_prompt_by_name("Test Prompt 1")
        assert template.id == "test-1"

    @pytest.mark.asyncio
    async def test_save_prompt(
        self, service: PromptRouterService, mock_repo: MockPromptRepository
    ) -> None:
        """Test saving a prompt."""
        template = PromptTemplate.create(
            name="New Prompt",
            content="Test {{variable}}",
            tags=["test"],
        )
        template_id = await service.save_prompt(template)
        assert template_id == template.id
        assert await service.count_prompts() == 3

    @pytest.mark.asyncio
    async def test_delete_prompt(self, service: PromptRouterService) -> None:
        """Test deleting a prompt."""
        deleted = await service.delete_prompt("test-1")
        assert deleted is True
        assert await service.count_prompts() == 1

    @pytest.mark.asyncio
    async def test_delete_prompt_not_found(self, service: PromptRouterService) -> None:
        """Test deleting a non-existent prompt returns False."""
        deleted = await service.delete_prompt("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_count_prompts(self, service: PromptRouterService) -> None:
        """Test counting prompts."""
        count = await service.count_prompts()
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_version_history(
        self, service: PromptRouterService, mock_repo: MockPromptRepository
    ) -> None:
        """Test getting version history."""
        # Create a new version
        original = await service.get_prompt_by_id("test-1")
        new_version = original.create_new_version(content="Updated content")
        await service.save_prompt(new_version)

        history = await service.get_version_history("test-1")
        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2

    @pytest.mark.asyncio
    async def test_get_all_tags(self, service: PromptRouterService) -> None:
        """Test getting all tags."""
        tags = await service.get_all_tags()
        assert "test" in tags["all"]
        assert "greeting" in tags["all"]
        assert "creative" in tags["all"]
        assert "story" in tags["all"]
        assert "gpt-4" in tags["model"]

    @pytest.mark.asyncio
    async def test_render_prompt(self, service: PromptRouterService) -> None:
        """Test rendering a prompt."""
        result = await service.render_prompt(
            prompt_id="test-1",
            variables={"name": "Alice", "age": 25},
            strict=True,
        )
        assert "Alice" in result["rendered"]
        assert "25" in result["rendered"]
        assert result["template_name"] == "Test Prompt 1"
        assert result["token_count"] > 0
        assert "name" in result["variables_used"]
        assert "age" in result["variables_used"]

    @pytest.mark.asyncio
    async def test_render_prompt_missing_variable(
        self, service: PromptRouterService
    ) -> None:
        """Test rendering with missing required variable raises error."""
        with pytest.raises(ValueError):
            await service.render_prompt(
                prompt_id="test-1",
                variables={"name": "Alice"},  # missing 'age'
                strict=True,
            )

    @pytest.mark.asyncio
    async def test_render_prompt_strict_false(
        self, service: PromptRouterService
    ) -> None:
        """Test rendering with strict=False uses default values."""
        result = await service.render_prompt(
            prompt_id="test-1",
            variables={"name": "Alice"},
            strict=False,
        )
        # Should render without error
        assert "Alice" in result["rendered"]

    @pytest.mark.asyncio
    async def test_render_prompt_not_found(self, service: PromptRouterService) -> None:
        """Test rendering non-existent prompt raises error."""
        with pytest.raises(PromptNotFoundError):
            await service.render_prompt(
                prompt_id="nonexistent",
                variables={},
                strict=True,
            )

    def test_to_summary(self, service: PromptRouterService) -> None:
        """Test converting template to summary dict."""
        template = PromptTemplate.create(
            name="Test",
            content="Test content",
            tags=["test"],
        )
        summary = service.to_summary(template)
        assert summary["id"] == template.id
        assert summary["name"] == "Test"
        assert summary["variable_count"] == 0
        assert summary["tags"] == ["test"]
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_to_detail(self, service: PromptRouterService) -> None:
        """Test converting template to detail dict."""
        template = PromptTemplate.create(
            name="Test",
            content="Test {{variable}}",
            tags=["test"],
        )
        detail = service.to_detail(template)
        assert detail["id"] == template.id
        assert detail["name"] == "Test"
        assert detail["content"] == "Test {{variable}}"
        assert len(detail["variables"]) == 1
        assert detail["variables"][0]["name"] == "variable"
        assert detail["llm_config"]["provider"] == "openai"
        assert detail["llm_config"]["model_name"] == "gpt-4"


class TestPromptRouterServiceRollback:
    """Tests for prompt rollback functionality."""

    @pytest.fixture
    async def service_with_versions(
        self, service: PromptRouterService
    ) -> PromptRouterService:
        """Create a service with multiple prompt versions."""
        # Create initial version
        v1 = PromptTemplate.create(
            name="Test Prompt",
            content="Original content: {{input}}",
            description="Initial version",
        )
        await service.save_prompt(v1)

        # Create second version
        v2 = v1.create_new_version(
            content="Modified content: {{input}}",
            description="Second version",
        )
        await service.save_prompt(v2)

        # Create third version
        v3 = v2.create_new_version(
            content="Third version content: {{input}}",
            description="Third version",
        )
        await service.save_prompt(v3)

        return service

    @pytest.mark.asyncio
    async def test_rollback_to_previous_version(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test rollback from v3 to v2."""
        service = service_with_versions

        # Find v3 ID
        prompts = await service.list_prompts()
        v3 = next(p for p in prompts if p.version == 3)

        # Rollback from v3 to v2
        rolled_back = await service.rollback_to_version(
            prompt_id=v3.id,
            target_version=2,
        )

        # The rolled back version should have v2's content
        assert "Modified content:" in rolled_back.content
        # But should be a new version (v4)
        assert rolled_back.version == 4
        # Description should indicate rollback
        assert "rolled back" in rolled_back.description.lower()

    @pytest.mark.asyncio
    async def test_rollback_to_first_version(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test rollback from v3 to v1."""
        service = service_with_versions

        # Find v3 ID
        prompts = await service.list_prompts()
        v3 = next(p for p in prompts if p.version == 3)

        # Rollback to v1
        rolled_back = await service.rollback_to_version(
            prompt_id=v3.id,
            target_version=1,
        )

        # Should have v1's content
        assert "Original content:" in rolled_back.content
        assert rolled_back.version == 4

    @pytest.mark.asyncio
    async def test_rollback_same_version_raises_error(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test rollback to same version raises error."""
        service = service_with_versions

        prompts = await service.list_prompts()
        v3 = next(p for p in prompts if p.version == 3)

        with pytest.raises(ValueError, match="already at version"):
            await service.rollback_to_version(
                prompt_id=v3.id,
                target_version=3,
            )

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_version_raises_error(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test rollback to non-existent version raises error."""
        service = service_with_versions

        prompts = await service.list_prompts()
        v3 = next(p for p in prompts if p.version == 3)

        with pytest.raises(PromptNotFoundError, match="Version 99 not found"):
            await service.rollback_to_version(
                prompt_id=v3.id,
                target_version=99,
            )


class TestPromptRouterServiceCompare:
    """Tests for prompt version comparison functionality."""

    @pytest.fixture
    async def service_with_versions(
        self, service: PromptRouterService
    ) -> PromptRouterService:
        """Create a service with multiple prompt versions to compare."""
        # Create initial version
        v1 = PromptTemplate.create(
            name="Test Prompt",
            content="Original content: {{input}}",
            description="Initial version",
            tags=("v1",),
        )
        _v1_id = await service.save_prompt(v1)  # noqa: F841

        # Create second version with changes
        v2 = v1.create_new_version(
            content="Modified content: {{input}} with extra",
            description="Second version - modified",
            tags=("v2", "modified"),
        )
        await service.save_prompt(v2)

        return service

    @pytest.mark.asyncio
    async def test_compare_versions_content_diff(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test comparing two versions shows content diff."""
        service = service_with_versions

        prompts = await service.list_prompts()
        # Filter to find our test prompt (not the base fixture prompts)
        test_prompts = [p for p in prompts if p.name == "Test Prompt"]
        result = await service.compare_versions(
            prompt_id=test_prompts[0].id,
            version_a=1,
            version_b=2,
        )

        assert result["version_a"]["version"] == 1
        assert result["version_b"]["version"] == 2
        assert len(result["content_diff"]) > 0

    @pytest.mark.asyncio
    async def test_compare_versions_metadata_diff(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test comparing versions shows metadata changes."""
        service = service_with_versions

        prompts = await service.list_prompts()
        test_prompts = [p for p in prompts if p.name == "Test Prompt"]
        result = await service.compare_versions(
            prompt_id=test_prompts[0].id,
            version_a=1,
            version_b=2,
        )

        # Description changed
        assert "description" in result["metadata"]
        assert result["metadata"]["description"]["old"] == "Initial version"
        assert result["metadata"]["description"]["new"] == "Second version - modified"

        # Tags changed
        assert "tags" in result["metadata"]
        assert "v2" in result["metadata"]["tags"]["added"]
        assert "v1" in result["metadata"]["tags"]["removed"]

    @pytest.mark.asyncio
    async def test_compare_versions_nonexistent_raises_error(
        self, service_with_versions: PromptRouterService
    ) -> None:
        """Test comparing with non-existent version raises error."""
        service = service_with_versions

        prompts = await service.list_prompts()
        test_prompts = [p for p in prompts if p.name == "Test Prompt"]

        with pytest.raises(PromptNotFoundError, match="Version 99 not found"):
            await service.compare_versions(
                prompt_id=test_prompts[0].id,
                version_a=1,
                version_b=99,
            )

    @pytest.mark.asyncio
    async def test_compute_character_diff(self, service: PromptRouterService) -> None:
        """Test character diff computation."""
        text_a = "Line 1\nLine 2\nLine 3\n"
        text_b = "Line 1\nLine 2 modified\nLine 3\nLine 4\n"

        diffs = service._compute_character_diff(text_a, text_b)

        # Should have insert and replace operations
        assert len(diffs) > 0
        # Check that we have the modified line
        replace_ops = [d for d in diffs if d["type"] == "replace"]
        assert len(replace_ops) > 0

    @pytest.mark.asyncio
    async def test_compare_identical_versions_empty_diff(
        self, service: PromptRouterService
    ) -> None:
        """Test comparing identical versions returns empty diff."""
        # Create a prompt
        v1 = PromptTemplate.create(
            name="Test",
            content="Same content: {{input}}",
        )
        await service.save_prompt(v1)

        # Compare v1 to itself (same content)
        result = await service.compare_versions(
            prompt_id=v1.id,
            version_a=1,
            version_b=1,
        )

        # Should have no content diff
        assert len(result["content_diff"]) == 0
        assert result["version_a"]["version"] == 1
        assert result["version_b"]["version"] == 1
