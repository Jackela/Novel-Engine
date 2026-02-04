"""
Tests for YAMLPromptMigrator

Warzone 4: AI Brain - BRAIN-014B
Tests for migrating YAML prompts to PromptTemplate entities.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)
from src.contexts.knowledge.infrastructure.migrations.migrate_yaml_prompts import (
    YAMLPromptMigrator,
    PromptSource,
    MigrationResult,
    PromptMigrationError,
    _INCLUDE_PATTERN,
    _VARIABLE_PATTERN,
)


class TestIncludePattern:
    """Tests for the include pattern regex."""

    def test_include_pattern_matches_basic(self) -> None:
        """Test that {{> prompt_name}} is matched correctly."""
        content = "Some text {{> base_prompt}} more text"
        matches = list(_INCLUDE_PATTERN.finditer(content))
        assert len(matches) == 1
        assert matches[0].group(1) == "base_prompt"

    def test_include_pattern_matches_with_spaces(self) -> None:
        """Test that {{>  prompt_name  }} with spaces is matched."""
        content = "{{>  base_prompt  }}"
        matches = list(_INCLUDE_PATTERN.finditer(content))
        assert len(matches) == 1
        assert matches[0].group(1) == "base_prompt"

    def test_include_pattern_matches_multiple(self) -> None:
        """Test that multiple includes are all matched."""
        content = "{{> first }} and {{> second }}"
        matches = list(_INCLUDE_PATTERN.finditer(content))
        assert len(matches) == 2
        assert matches[0].group(1) == "first"
        assert matches[1].group(1) == "second"


class TestVariablePattern:
    """Tests for the variable pattern regex."""

    def test_variable_pattern_matches_basic(self) -> None:
        """Test that {{variable}} is matched correctly."""
        content = "Hello {{name}}, welcome to {{place}}"
        matches = _VARIABLE_PATTERN.findall(content)
        assert set(matches) == {"name", "place"}

    def test_variable_pattern_requires_valid_name(self) -> None:
        """Test that only valid variable names are matched."""
        content = "{{valid}} {{1invalid}} {{-notvalid}}"
        matches = _VARIABLE_PATTERN.findall(content)
        assert matches == ["valid"]

    def test_variable_pattern_underscores_allowed(self) -> None:
        """Test that underscores are allowed in variable names."""
        content = "{{first_name}} {{user_id}}"
        matches = _VARIABLE_PATTERN.findall(content)
        assert set(matches) == {"first_name", "user_id"}


class TestPromptSource:
    """Tests for PromptSource value object."""

    def test_prompt_source_creation(self) -> None:
        """Test creating a PromptSource."""
        source = PromptSource(
            file_path=Path("/test/character_gen.yaml"),
            name="character_gen",
            context="character",
            raw_content={"system_prompt": "You are a character generator."},
        )
        assert source.name == "character_gen"
        assert source.context == "character"
        assert source.raw_content["system_prompt"] == "You are a character generator."


class TestMigrationResult:
    """Tests for MigrationResult value object."""

    def test_migration_result_defaults(self) -> None:
        """Test MigrationResult default values."""
        result = MigrationResult()
        assert result.total_found == 0
        assert result.migrated == 0
        assert result.skipped == 0
        assert result.errors == []
        assert result.prompts == []

    def test_migration_result_with_values(self) -> None:
        """Test MigrationResult with values."""
        template = Mock(spec=PromptTemplate)
        result = MigrationResult(
            total_found=5,
            migrated=3,
            skipped=2,
            errors=["Error 1", "Error 2"],
            prompts=[template],
        )
        assert result.total_found == 5
        assert result.migrated == 3
        assert result.skipped == 2
        assert len(result.errors) == 2
        assert len(result.prompts) == 1


@pytest.fixture
def temp_project_dir() -> tempfile.TemporaryDirectory:
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.TemporaryDirectory()
    base_path = Path(temp_dir.name)

    # Create directory structure
    contexts = base_path / "src" / "contexts"
    contexts.mkdir(parents=True)

    # Create prompt directories
    (contexts / "world" / "infrastructure" / "prompts").mkdir(parents=True)
    (contexts / "character" / "infrastructure" / "prompts").mkdir(parents=True)
    (contexts / "story" / "infrastructure" / "prompts").mkdir(parents=True)

    yield temp_dir

    temp_dir.cleanup()


@pytest.fixture
def sample_yaml_content() -> dict[str, str]:
    """Sample YAML content for testing."""
    return {
        "system_prompt": """You are a creative writing assistant.

Generate content based on the {{input_type}} provided.

Follow these guidelines:
- Be creative
- Stay in character
- Use {{tone}} consistently

Output must be valid JSON."""
    }


@pytest.fixture
def migrator(temp_project_dir: tempfile.TemporaryDirectory) -> YAMLPromptMigrator:
    """Create a migrator instance for testing."""
    repository = InMemoryPromptRepository()
    project_root = Path(temp_project_dir.name)
    return YAMLPromptMigrator(repository, project_root=project_root)


class TestYAMLPromptMigratorDiscover:
    """Tests for YAMLPromptMigrator.discover_prompts()."""

    @pytest.mark.asyncio
    async def test_discover_prompts_finds_yaml_files(
        self, migrator: YAMLPromptMigrator, temp_project_dir: tempfile.TemporaryDirectory
    ) -> None:
        """Test that discover_prompts finds all YAML files."""
        base_path = Path(temp_project_dir.name)

        # Create test YAML files
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        (world_prompts / "world_gen.yaml").write_text(
            yaml.dump({"system_prompt": "Generate a world"}), encoding="utf-8"
        )
        (world_prompts / "dialogue_gen.yaml").write_text(
            yaml.dump({"system_prompt": "Generate dialogue"}), encoding="utf-8"
        )

        char_prompts = base_path / "src" / "contexts" / "character" / "infrastructure" / "prompts"
        (char_prompts / "character_gen.yaml").write_text(
            yaml.dump({"system_prompt": "Generate a character"}), encoding="utf-8"
        )

        # Discover prompts
        sources = migrator.discover_prompts()

        assert len(sources) == 3
        source_names = {s.name for s in sources}
        assert source_names == {"world_gen", "dialogue_gen", "character_gen"}

    @pytest.mark.asyncio
    async def test_discover_prompts_handles_invalid_yaml(
        self, migrator: YAMLPromptMigrator, temp_project_dir: tempfile.TemporaryDirectory
    ) -> None:
        """Test that discover_prompts handles invalid YAML gracefully."""
        base_path = Path(temp_project_dir.name)

        # Create valid and invalid YAML files
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        (world_prompts / "valid.yaml").write_text(
            yaml.dump({"system_prompt": "Valid prompt"}), encoding="utf-8"
        )
        (world_prompts / "invalid.yaml").write_text("{ invalid yaml content", encoding="utf-8")

        # Should not raise, just skip invalid
        sources = migrator.discover_prompts()
        assert len(sources) == 1
        assert sources[0].name == "valid"


class TestYAMLPromptMigratorResolveIncludes:
    """Tests for YAMLPromptMigrator.resolve_includes()."""

    @pytest.mark.asyncio
    async def test_resolve_includes_basic(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test basic include resolution."""
        sources = [
            PromptSource(
                file_path=Path("/base.yaml"),
                name="base_prompt",
                context="world",
                raw_content={"system_prompt": "Base content here"},
            )
        ]

        content = "Before {{> base_prompt}} after"
        resolved = migrator.resolve_includes(content, sources)

        assert "Base content here" in resolved
        assert "{{> base_prompt}}" not in resolved

    @pytest.mark.asyncio
    async def test_resolve_includes_nested(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test nested include resolution."""
        sources = [
            PromptSource(
                file_path=Path("/base.yaml"),
                name="base_prompt",
                context="world",
                raw_content={"system_prompt": "Base with {{> common}}"},
            ),
            PromptSource(
                file_path=Path("/common.yaml"),
                name="common",
                context="world",
                raw_content={"system_prompt": "Common content"},
            ),
        ]

        content = "{{> base_prompt }}"
        resolved = migrator.resolve_includes(content, sources)

        assert "Base with" in resolved
        assert "Common content" in resolved
        assert "{{>" not in resolved  # All includes resolved

    @pytest.mark.asyncio
    async def test_resolve_includes_circular_detection(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that circular references are detected."""
        sources = [
            PromptSource(
                file_path=Path("/a.yaml"),
                name="prompt_a",
                context="world",
                raw_content={"system_prompt": "{{> prompt_b}}"},
            ),
            PromptSource(
                file_path=Path("/b.yaml"),
                name="prompt_b",
                context="world",
                raw_content={"system_prompt": "{{> prompt_a}}"},
            ),
        ]

        content = "{{> prompt_a }}"

        with pytest.raises(PromptMigrationError) as exc_info:
            migrator.resolve_includes(content, sources)

        assert "Circular reference" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_includes_missing_reference(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that missing references are detected."""
        sources = [
            PromptSource(
                file_path=Path("/a.yaml"),
                name="prompt_a",
                context="world",
                raw_content={"system_prompt": "Content A"},
            ),
        ]

        content = "{{> missing_prompt }}"

        with pytest.raises(PromptMigrationError) as exc_info:
            migrator.resolve_includes(content, sources)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_includes_empty_content(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test handling of include with empty content."""
        sources = [
            PromptSource(
                file_path=Path("/empty.yaml"),
                name="empty_prompt",
                context="world",
                raw_content={"system_prompt": ""},
            ),
        ]

        content = "{{> empty_prompt }}"

        with pytest.raises(PromptMigrationError) as exc_info:
            migrator.resolve_includes(content, sources)

        assert "no system_prompt content" in str(exc_info.value)


class TestYAMLPromptMigratorExtractVariables:
    """Tests for YAMLPromptMigrator.extract_variables()."""

    def test_extract_variables_basic(self, migrator: YAMLPromptMigrator) -> None:
        """Test extracting variables from content."""
        content = "Hello {{name}}, your {{role}} is ready."
        variables = migrator.extract_variables(content)

        assert len(variables) == 2
        var_names = {v.name for v in variables}
        assert var_names == {"name", "role"}

    def test_extract_variables_all_string_type(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that all extracted variables are STRING type by default."""
        content = "{{var1}} and {{var2}}"
        variables = migrator.extract_variables(content)

        assert all(v.type == VariableType.STRING for v in variables)

    def test_extract_variables_deduplicates(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that duplicate variables are deduplicated."""
        content = "{{name}} said {{name}} again"
        variables = migrator.extract_variables(content)

        assert len(variables) == 1
        assert variables[0].name == "name"

    def test_extract_variables_none(self, migrator: YAMLPromptMigrator) -> None:
        """Test content with no variables."""
        content = "Plain text with no placeholders"
        variables = migrator.extract_variables(content)

        assert len(variables) == 0


class TestYAMLPromptMigratorSourceToTemplate:
    """Tests for YAMLPromptMigrator.source_to_template()."""

    @pytest.mark.asyncio
    async def test_source_to_template_basic(
        self, migrator: YAMLPromptMigrator, sample_yaml_content: dict[str, str]
    ) -> None:
        """Test converting a source to template."""
        source = PromptSource(
            file_path=Path("/test.yaml"),
            name="test_prompt",
            context="world",
            raw_content=sample_yaml_content,
        )

        template = migrator.source_to_template(source, [source])

        assert template.name == "test_prompt"
        assert template.content == sample_yaml_content["system_prompt"]
        assert len(template.variables) == 2  # input_type, tone
        assert "world" in template.tags

    @pytest.mark.asyncio
    async def test_source_to_template_with_includes(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test converting source with include directives."""
        sources = [
            PromptSource(
                file_path=Path("/main.yaml"),
                name="main_prompt",
                context="world",
                raw_content={"system_prompt": "Main {{> base_prompt }} content"},
            ),
            PromptSource(
                file_path=Path("/base.yaml"),
                name="base_prompt",
                context="world",
                raw_content={"system_prompt": "BASE"},
            ),
        ]

        template = migrator.source_to_template(sources[0], sources)

        assert "BASE" in template.content
        assert "{{>" not in template.content  # Includes resolved

    @pytest.mark.asyncio
    async def test_source_to_template_missing_system_prompt(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test error when system_prompt is missing."""
        source = PromptSource(
            file_path=Path("/test.yaml"),
            name="test_prompt",
            context="world",
            raw_content={},  # No system_prompt
        )

        with pytest.raises(PromptMigrationError) as exc_info:
            migrator.source_to_template(source, [source])

        assert "no system_prompt" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_source_to_template_model_config_adjustment(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that model config is adjusted based on prompt type."""
        test_cases = [
            ("dialogue_gen", "world", 0.8, 500),
            ("world_gen", "world", 0.7, 4000),
            ("beat_suggester", "world", 0.7, 1000),
            ("character_gen", "character", 0.7, 800),
        ]

        for name, context, expected_temp, expected_tokens in test_cases:
            source = PromptSource(
                file_path=Path(f"/{name}.yaml"),
                name=name,
                context=context,
                raw_content={"system_prompt": "Test content"},
            )

            template = migrator.source_to_template(source, [source])

            assert (
                template.model_config.temperature == expected_temp
            ), f"Temperature mismatch for {name}"
            assert (
                template.model_config.max_tokens == expected_tokens
            ), f"Max tokens mismatch for {name}"

    @pytest.mark.asyncio
    async def test_source_to_template_tag_generation(
        self, migrator: YAMLPromptMigrator
    ) -> None:
        """Test that tags are generated correctly."""
        test_cases = [
            ("dialogue_gen", "world", ["world", "generation", "dialogue"]),
            ("world_gen", "world", ["world", "generation"]),
            ("scene_gen", "story", ["story", "generation", "scene"]),
        ]

        for name, context, expected_tags in test_cases:
            source = PromptSource(
                file_path=Path(f"/{name}.yaml"),
                name=name,
                context=context,
                raw_content={"system_prompt": "Test content"},
            )

            template = migrator.source_to_template(source, [source])

            for tag in expected_tags:
                assert tag in template.tags, f"Tag '{tag}' missing for {name}"


class TestYAMLPromptMigratorMigrate:
    """Tests for YAMLPromptMigrator.migrate()."""

    @pytest.mark.asyncio
    async def test_migrate_success(
        self,
        migrator: YAMLPromptMigrator,
        temp_project_dir: tempfile.TemporaryDirectory,
    ) -> None:
        """Test successful migration."""
        base_path = Path(temp_project_dir.name)

        # Create test files
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        world_prompts.mkdir(parents=True, exist_ok=True)
        (world_prompts / "test_prompt.yaml").write_text(
            yaml.dump({"system_prompt": "Generate {{type}} content"}), encoding="utf-8"
        )

        result = await migrator.migrate(dry_run=False)

        assert result.total_found == 1
        assert result.migrated == 1
        assert result.skipped == 0
        assert len(result.prompts) == 1
        assert result.prompts[0].name == "test_prompt"

    @pytest.mark.asyncio
    async def test_migrate_skips_existing(
        self,
        migrator: YAMLPromptMigrator,
        temp_project_dir: tempfile.TemporaryDirectory,
    ) -> None:
        """Test that existing prompts are skipped."""
        base_path = Path(temp_project_dir.name)

        # Create test file
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        world_prompts.mkdir(parents=True, exist_ok=True)
        (world_prompts / "test_prompt.yaml").write_text(
            yaml.dump({"system_prompt": "Content"}), encoding="utf-8"
        )

        # First migration
        result1 = await migrator.migrate(dry_run=False)
        assert result1.migrated == 1

        # Second migration should skip
        result2 = await migrator.migrate(dry_run=False)
        assert result2.migrated == 0
        assert result2.skipped == 1

    @pytest.mark.asyncio
    async def test_migrate_dry_run(
        self,
        migrator: YAMLPromptMigrator,
        temp_project_dir: tempfile.TemporaryDirectory,
    ) -> None:
        """Test dry run mode."""
        base_path = Path(temp_project_dir.name)

        # Create test file
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        world_prompts.mkdir(parents=True, exist_ok=True)
        (world_prompts / "test_prompt.yaml").write_text(
            yaml.dump({"system_prompt": "Content"}), encoding="utf-8"
        )

        # Dry run should not save
        result = await migrator.migrate(dry_run=True)
        assert result.migrated == 1

        # Verify not actually in repository
        exists = await migrator.repository.get_by_name("test_prompt")
        assert exists is None

    @pytest.mark.asyncio
    async def test_migrate_with_errors(
        self,
        migrator: YAMLPromptMigrator,
        temp_project_dir: tempfile.TemporaryDirectory,
    ) -> None:
        """Test migration with some files having errors."""
        base_path = Path(temp_project_dir.name)

        # Create valid and invalid files
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        world_prompts.mkdir(parents=True, exist_ok=True)
        (world_prompts / "valid.yaml").write_text(
            yaml.dump({"system_prompt": "Valid content"}), encoding="utf-8"
        )
        (world_prompts / "invalid.yaml").write_text(
            yaml.dump({"no_system_prompt": "Missing key"}), encoding="utf-8"
        )

        result = await migrator.migrate(dry_run=False)

        assert result.total_found == 2
        assert result.migrated == 1
        assert result.skipped == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_migrate_full_workflow(
        self,
        temp_project_dir: tempfile.TemporaryDirectory,
    ) -> None:
        """Test complete migration workflow with actual project structure."""
        base_path = Path(temp_project_dir.name)

        # Set up actual prompt files like in the real project
        world_prompts = base_path / "src" / "contexts" / "world" / "infrastructure" / "prompts"
        world_prompts.mkdir(parents=True, exist_ok=True)

        # Create a base prompt to be included
        (world_prompts / "base_prompt.yaml").write_text(
            yaml.dump({"system_prompt": "You are a creative assistant."}), encoding="utf-8"
        )

        # Create a prompt that includes the base
        (world_prompts / "dialogue_gen.yaml").write_text(
            yaml.dump({
                "system_prompt": """{{> base_prompt }}

Generate dialogue for {{character_name}} with {{mood}} tone."""
            }), encoding="utf-8"
        )

        # Run migration
        repository = InMemoryPromptRepository()
        migrator = YAMLPromptMigrator(repository, project_root=base_path)
        result = await migrator.migrate(dry_run=False)

        # Verify results
        assert result.migrated == 2
        assert len(result.errors) == 0

        # Check dialogue_gen template includes base content
        dialogue_template = await repository.get_by_name("dialogue_gen")
        assert dialogue_template is not None
        assert "You are a creative assistant" in dialogue_template.content

        # Check variables were extracted
        var_names = {v.name for v in dialogue_template.variables}
        assert "character_name" in var_names
        assert "mood" in var_names
