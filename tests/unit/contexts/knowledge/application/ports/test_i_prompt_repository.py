"""
Unit Tests for IPromptRepository Port Interface

Warzone 4: AI Brain - BRAIN-014A
Tests for IPromptRepository port and related exceptions.
"""

import pytest

from src.contexts.knowledge.application.ports.i_prompt_repository import (
    IPromptRepository,
    PromptNotFoundError,
    PromptRepositoryError,
    PromptValidationError,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)


class MockPromptRepository(IPromptRepository):
    """Mock implementation of IPromptRepository for testing."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    async def save(self, template: PromptTemplate) -> str:
        self._templates[template.id] = template
        return template.id

    async def get_by_id(self, template_id: str) -> PromptTemplate | None:
        return self._templates.get(template_id)

    async def get_by_name(
        self, name: str, version: int | None = None
    ) -> PromptTemplate | None:
        for template in self._templates.values():
            if template.name == name:
                if version is None or template.version == version:
                    return template
        return None

    async def list_all(
        self,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptTemplate]:
        results = list(self._templates.values())
        if tags:
            results = [t for t in results if all(tag in t.tags for tag in tags)]
        return results[offset : offset + limit]

    async def delete(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    async def get_version_history(self, template_id: str) -> list[PromptTemplate]:
        template = self._templates.get(template_id)
        if not template:
            return []
        # Return template and its descendants
        results = [template]
        for t in self._templates.values():
            if t.parent_version_id == template_id:
                results.append(t)
        return sorted(results, key=lambda t: t.version)

    async def get_by_tag(self, tag: str, limit: int = 50) -> list[PromptTemplate]:
        results = [t for t in self._templates.values() if tag in t.tags]
        return results[:limit]

    async def count(self) -> int:
        return len(self._templates)

    async def search(self, query: str, limit: int = 20) -> list[PromptTemplate]:
        query_lower = query.lower()
        results = [
            t
            for t in self._templates.values()
            if query_lower in t.name.lower() or query_lower in t.description.lower()
        ]
        return results[:limit]


class TestPromptRepositoryExceptions:
    """Tests for prompt repository exceptions."""

    def test_prompt_not_found_error(self) -> None:
        """Should create error with template ID."""
        error = PromptNotFoundError("test-id")
        assert error.prompt_id == "test-id"
        assert "test-id" in str(error)

    def test_prompt_validation_error(self) -> None:
        """Should create error with message."""
        error = PromptValidationError("Invalid template")
        assert error.message == "Invalid template"
        assert "Invalid template" in str(error)


class TestIPromptRepository:
    """Tests for IPromptRepository interface using mock."""

    @pytest.fixture
    def repository(self) -> MockPromptRepository:
        """Create a mock repository for testing."""
        return MockPromptRepository()

    @pytest.fixture
    def sample_template(self) -> PromptTemplate:
        """Create a sample prompt template."""
        return PromptTemplate(
            id="test-1",
            name="Test Template",
            content="Hello {{name}}!",
            variables=(
                VariableDefinition(name="name", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

    @pytest.mark.asyncio
    async def test_save_and_get_by_id(
        self, repository: MockPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Should save and retrieve template by ID."""
        template_id = await repository.save(sample_template)
        assert template_id == "test-1"

        retrieved = await repository.get_by_id("test-1")
        assert retrieved is not None
        assert retrieved.id == "test-1"
        assert retrieved.name == "Test Template"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: MockPromptRepository) -> None:
        """Should return None for non-existent ID."""
        result = await repository.get_by_id("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_get_by_name(
        self, repository: MockPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Should retrieve template by name."""
        await repository.save(sample_template)

        retrieved = await repository.get_by_name("Test Template")
        assert retrieved is not None
        assert retrieved.name == "Test Template"

    @pytest.mark.asyncio
    async def test_list_all(
        self, repository: MockPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Should list all templates."""
        await repository.save(sample_template)

        templates = await repository.list_all()
        assert len(templates) == 1
        assert templates[0].id == "test-1"

    @pytest.mark.asyncio
    async def test_list_all_with_tags(
        self, repository: MockPromptRepository
    ) -> None:
        """Should filter templates by tags."""
        template1 = PromptTemplate(
            id="test-1",
            name="Template 1",
            content="Content 1",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            tags=("tag1",),
        )
        template2 = PromptTemplate(
            id="test-2",
            name="Template 2",
            content="Content 2",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            tags=("tag1", "tag2"),
        )

        await repository.save(template1)
        await repository.save(template2)

        # Filter by tag1
        results = await repository.list_all(tags=["tag1"])
        assert len(results) == 2

        # Filter by tag1 and tag2
        results = await repository.list_all(tags=["tag1", "tag2"])
        assert len(results) == 1
        assert results[0].id == "test-2"

    @pytest.mark.asyncio
    async def test_list_all_with_limit_and_offset(
        self, repository: MockPromptRepository
    ) -> None:
        """Should support pagination."""
        for i in range(5):
            template = PromptTemplate(
                id=f"test-{i}",
                name=f"Template {i}",
                content="Content",
                variables=(),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            )
            await repository.save(template)

        results = await repository.list_all(limit=2, offset=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete(
        self, repository: MockPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Should delete template."""
        await repository.save(sample_template)
        assert await repository.delete("test-1") is True
        assert await repository.get_by_id("test-1") is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository: MockPromptRepository) -> None:
        """Should return False when deleting non-existent template."""
        assert await repository.delete("non-existent") is False

    @pytest.mark.asyncio
    async def test_get_version_history(self, repository: MockPromptRepository) -> None:
        """Should retrieve version history."""
        v1 = PromptTemplate(
            id="v1",
            name="Template",
            content="Version 1",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            version=1,
        )
        v2 = v1.create_new_version(content="Version 2")

        await repository.save(v1)
        await repository.save(v2)

        history = await repository.get_version_history("v1")
        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2

    @pytest.mark.asyncio
    async def test_get_by_tag(self, repository: MockPromptRepository) -> None:
        """Should retrieve templates by tag."""
        template1 = PromptTemplate(
            id="test-1",
            name="Template 1",
            content="Content 1",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            tags=("character",),
        )
        template2 = PromptTemplate(
            id="test-2",
            name="Template 2",
            content="Content 2",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            tags=("scene",),
        )

        await repository.save(template1)
        await repository.save(template2)

        results = await repository.get_by_tag("character")
        assert len(results) == 1
        assert results[0].id == "test-1"

    @pytest.mark.asyncio
    async def test_count(
        self, repository: MockPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Should count templates."""
        assert await repository.count() == 0
        await repository.save(sample_template)
        assert await repository.count() == 1

    @pytest.mark.asyncio
    async def test_search(
        self, repository: MockPromptRepository
    ) -> None:
        """Should search templates by name or description."""
        template1 = PromptTemplate(
            id="test-1",
            name="Character Generator",
            content="Content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            description="Generates character profiles",
        )
        template2 = PromptTemplate(
            id="test-2",
            name="Scene Builder",
            content="Content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            description="Builds narrative scenes",
        )

        await repository.save(template1)
        await repository.save(template2)

        # Search by name
        results = await repository.search("character")
        assert len(results) == 1
        assert results[0].id == "test-1"

        # Search by description
        results = await repository.search("narrative")
        assert len(results) == 1
        assert results[0].id == "test-2"
