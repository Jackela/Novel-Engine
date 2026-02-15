"""
Tests for InMemoryPromptRepository

Warzone 4: AI Brain - BRAIN-014B
Tests for the in-memory prompt repository implementation.
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.ports.i_prompt_repository import (
    PromptValidationError,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_template() -> PromptTemplate:
    """Create a sample prompt template for testing."""
    return PromptTemplate.create(
        name="test_prompt",
        content="Generate {{type}} content with {{tone}} tone.",
        variables=[
            VariableDefinition(
                name="type",
                type=VariableType.STRING,
                description="Type of content",
            ),
            VariableDefinition(
                name="tone",
                type=VariableType.STRING,
                description="Tone of content",
            ),
        ],
        description="A test prompt template",
        tags=["test", "sample"],
    )


@pytest.fixture
def repository() -> InMemoryPromptRepository:
    """Create a fresh repository for each test."""
    return InMemoryPromptRepository()


class TestInMemoryPromptRepositorySave:
    """Tests for InMemoryPromptRepository.save()."""

    @pytest.mark.asyncio
    async def test_save_new_template(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test saving a new template."""
        template_id = await repository.save(sample_template)

        assert template_id == sample_template.id

        # Verify it was saved
        retrieved = await repository.get_by_id(template_id)
        assert retrieved is not None
        assert retrieved.name == "test_prompt"

    @pytest.mark.asyncio
    async def test_save_update_existing(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test updating an existing template."""
        # Save original
        original_id = await repository.save(sample_template)

        # Create new version
        new_version = sample_template.create_new_version(
            content="Updated content for {{type}}"
        )

        # Save the new version
        new_id = await repository.save(new_version)

        # Both should exist
        original = await repository.get_by_id(original_id)
        updated = await repository.get_by_id(new_id)

        assert original is not None
        assert updated is not None
        assert updated.content == "Updated content for {{type}}"

    @pytest.mark.asyncio
    async def test_save_validates_template(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that invalid templates are rejected."""
        # Create a template with syntax errors
        with pytest.raises(PromptValidationError) as exc_info:
            template = PromptTemplate.create(
                name="invalid_prompt",
                content="Template with {single} braces",
            )
            await repository.save(template)

        assert "validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_save_updates_name_index(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that saving updates the name index for get_by_name."""
        template = PromptTemplate.create(
            name="indexed_prompt",
            content="Content",
        )

        await repository.save(template)

        # Should be retrievable by name
        retrieved = await repository.get_by_name("indexed_prompt")
        assert retrieved is not None
        assert retrieved.id == template.id


class TestInMemoryPromptRepositoryGetById:
    """Tests for InMemoryPromptRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test retrieving an existing template by ID."""
        await repository.save(sample_template)

        retrieved = await repository.get_by_id(sample_template.id)

        assert retrieved is not None
        assert retrieved.id == sample_template.id
        assert retrieved.name == sample_template.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test retrieving a non-existent template."""
        retrieved = await repository.get_by_id("non-existent-id")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_id_deleted(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test that deleted templates are not returned."""
        await repository.save(sample_template)
        await repository.delete(sample_template.id)

        retrieved = await repository.get_by_id(sample_template.id)

        assert retrieved is None


class TestInMemoryPromptRepositoryGetByName:
    """Tests for InMemoryPromptRepository.get_by_name()."""

    @pytest.mark.asyncio
    async def test_get_by_name_found(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test retrieving an existing template by name."""
        await repository.save(sample_template)

        retrieved = await repository.get_by_name("test_prompt")

        assert retrieved is not None
        assert retrieved.name == "test_prompt"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test retrieving a non-existent template by name."""
        retrieved = await repository.get_by_name("non-existent")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_name_returns_latest_version(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that get_by_name returns the latest version."""
        v1 = PromptTemplate.create(name="versioned", content="Version 1", id="id-v1")
        v2 = v1.create_new_version(content="Version 2")
        v3 = v2.create_new_version(content="Version 3")

        await repository.save(v1)
        await repository.save(v2)
        await repository.save(v3)

        retrieved = await repository.get_by_name("versioned")

        assert retrieved is not None
        assert retrieved.version == 3
        assert retrieved.content == "Version 3"

    @pytest.mark.asyncio
    async def test_get_by_name_with_version(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test retrieving a specific version."""
        v1 = PromptTemplate.create(name="versioned", content="Version 1", id="id-v1")
        v2 = v1.create_new_version(content="Version 2")

        await repository.save(v1)
        await repository.save(v2)

        v1_retrieved = await repository.get_by_name("versioned", version=1)
        v2_retrieved = await repository.get_by_name("versioned", version=2)

        assert v1_retrieved.version == 1
        assert v2_retrieved.version == 2


class TestInMemoryPromptRepositoryListAll:
    """Tests for InMemoryPromptRepository.list_all()."""

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repository: InMemoryPromptRepository) -> None:
        """Test listing when repository is empty."""
        results = await repository.list_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_list_all_returns_all(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test listing returns all non-deleted templates."""
        t1 = PromptTemplate.create(name="template_1", content="Content 1")
        t2 = PromptTemplate.create(name="template_2", content="Content 2")
        t3 = PromptTemplate.create(name="template_3", content="Content 3")

        await repository.save(t1)
        await repository.save(t2)
        await repository.save(t3)

        results = await repository.list_all()

        assert len(results) == 3
        names = {t.name for t in results}
        assert names == {"template_1", "template_2", "template_3"}

    @pytest.mark.asyncio
    async def test_list_all_excludes_deleted(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that deleted templates are excluded."""
        t1 = PromptTemplate.create(name="template_1", content="Content 1")
        t2 = PromptTemplate.create(name="template_2", content="Content 2")

        await repository.save(t1)
        await repository.save(t2)
        await repository.delete(t1.id)

        results = await repository.list_all()

        assert len(results) == 1
        assert results[0].name == "template_2"

    @pytest.mark.asyncio
    async def test_list_all_with_tags(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test filtering by tags."""
        t1 = PromptTemplate.create(
            name="t1", content="C1", tags=["world", "generation"]
        )
        t2 = PromptTemplate.create(
            name="t2", content="C2", tags=["dialogue", "generation"]
        )
        t3 = PromptTemplate.create(name="t3", content="C3", tags=["world"])

        await repository.save(t1)
        await repository.save(t2)
        await repository.save(t3)

        # Filter by single tag
        world_only = await repository.list_all(tags=["world"])
        assert len(world_only) == 2
        assert {t.name for t in world_only} == {"t1", "t3"}

        # Filter by multiple tags (AND logic)
        both = await repository.list_all(tags=["world", "generation"])
        assert len(both) == 1
        assert both[0].name == "t1"

    @pytest.mark.asyncio
    async def test_list_all_pagination(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test limit and offset parameters."""
        for i in range(5):
            template = PromptTemplate.create(name=f"template_{i}", content=f"C{i}")
            await repository.save(template)

        # Limit
        page1 = await repository.list_all(limit=2)
        assert len(page1) == 2

        # Offset
        page2 = await repository.list_all(limit=2, offset=2)
        assert len(page2) == 2
        assert page2[0].name == "template_2"


class TestInMemoryPromptRepositoryDelete:
    """Tests for InMemoryPromptRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_existing(
        self, repository: InMemoryPromptRepository, sample_template: PromptTemplate
    ) -> None:
        """Test deleting an existing template."""
        await repository.save(sample_template)

        result = await repository.delete(sample_template.id)

        assert result is True

        # Verify it's deleted
        retrieved = await repository.get_by_id(sample_template.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_non_existent(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test deleting a non-existent template."""
        result = await repository.delete("non-existent-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_removes_from_name_index(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that deletion updates the name index."""
        template = PromptTemplate.create(name="to_delete", content="Content")
        await repository.save(template)

        await repository.delete(template.id)

        # Should not be findable by name
        retrieved = await repository.get_by_name("to_delete")
        assert retrieved is None


class TestInMemoryPromptRepositoryGetVersionHistory:
    """Tests for InMemoryPromptRepository.get_version_history()."""

    @pytest.mark.asyncio
    async def test_get_version_history(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test retrieving version history."""
        v1 = PromptTemplate.create(name="versioned", content="V1", id="id-v1")
        v2 = v1.create_new_version(content="V2")
        v3 = v2.create_new_version(content="V3")

        await repository.save(v1)
        await repository.save(v2)
        await repository.save(v3)

        history = await repository.get_version_history(v3.id)

        assert len(history) == 3
        versions = [t.version for t in history]
        assert versions == [1, 2, 3]  # Should be ordered ascending

    @pytest.mark.asyncio
    async def test_get_version_history_non_existent(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test version history for non-existent template."""
        history = await repository.get_version_history("non-existent")

        assert history == []


class TestInMemoryPromptRepositoryGetByTag:
    """Tests for InMemoryPromptRepository.get_by_tag()."""

    @pytest.mark.asyncio
    async def test_get_by_tag_found(self, repository: InMemoryPromptRepository) -> None:
        """Test retrieving templates by tag."""
        t1 = PromptTemplate.create(
            name="t1", content="C1", tags=["world", "generation"]
        )
        t2 = PromptTemplate.create(name="t2", content="C2", tags=["dialogue"])
        t3 = PromptTemplate.create(name="t3", content="C3", tags=["world"])

        await repository.save(t1)
        await repository.save(t2)
        await repository.save(t3)

        results = await repository.get_by_tag("world")

        assert len(results) == 2
        names = {t.name for t in results}
        assert names == {"t1", "t3"}

    @pytest.mark.asyncio
    async def test_get_by_tag_not_found(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test retrieving with non-existent tag."""
        results = await repository.get_by_tag("nonexistent")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_tag_limit(self, repository: InMemoryPromptRepository) -> None:
        """Test limit parameter for get_by_tag."""
        for i in range(5):
            template = PromptTemplate.create(
                name=f"t{i}", content=f"C{i}", tags=["common"]
            )
            await repository.save(template)

        results = await repository.get_by_tag("common", limit=3)

        assert len(results) == 3


class TestInMemoryPromptRepositoryCount:
    """Tests for InMemoryPromptRepository.count()."""

    @pytest.mark.asyncio
    async def test_count_empty(self, repository: InMemoryPromptRepository) -> None:
        """Test count when repository is empty."""
        count = await repository.count()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_after_saves(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test count increases with saves."""
        assert await repository.count() == 0

        await repository.save(PromptTemplate.create(name="t1", content="C1"))
        assert await repository.count() == 1

        await repository.save(PromptTemplate.create(name="t2", content="C2"))
        assert await repository.count() == 2

    @pytest.mark.asyncio
    async def test_count_excludes_deleted(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that deleted templates are not counted."""
        t1 = PromptTemplate.create(name="t1", content="C1")
        t2 = PromptTemplate.create(name="t2", content="C2")

        await repository.save(t1)
        await repository.save(t2)

        assert await repository.count() == 2

        await repository.delete(t1.id)

        assert await repository.count() == 1


class TestInMemoryPromptRepositorySearch:
    """Tests for InMemoryPromptRepository.search()."""

    @pytest.mark.asyncio
    async def test_search_by_name(self, repository: InMemoryPromptRepository) -> None:
        """Test searching by name."""
        t1 = PromptTemplate.create(
            name="character_generator", content="C1", description="Generate characters"
        )
        t2 = PromptTemplate.create(
            name="dialogue_gen", content="C2", description="Generate dialogue"
        )
        t3 = PromptTemplate.create(
            name="world_builder", content="C3", description="Build worlds"
        )

        await repository.save(t1)
        await repository.save(t2)
        await repository.save(t3)

        # Search for "gen"
        results = await repository.search("gen")

        assert len(results) == 2
        names = {t.name for t in results}
        assert names == {"character_generator", "dialogue_gen"}

    @pytest.mark.asyncio
    async def test_search_by_description(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test searching by description."""
        t1 = PromptTemplate.create(
            name="t1", content="C1", description="For creating character profiles"
        )
        t2 = PromptTemplate.create(
            name="t2", content="C2", description="For generating scenes"
        )

        await repository.save(t1)
        await repository.save(t2)

        results = await repository.search("character")

        assert len(results) == 1
        assert results[0].name == "t1"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self, repository: InMemoryPromptRepository
    ) -> None:
        """Test that search is case insensitive."""
        template = PromptTemplate.create(
            name="Character_Generator", content="C1", description="Generate characters"
        )
        await repository.save(template)

        results = await repository.search("character")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_limit(self, repository: InMemoryPromptRepository) -> None:
        """Test search limit parameter."""
        for i in range(5):
            template = PromptTemplate.create(name=f"prompt_{i}", content=f"C{i}")
            await repository.save(template)

        results = await repository.search("prompt", limit=3)

        assert len(results) == 3
