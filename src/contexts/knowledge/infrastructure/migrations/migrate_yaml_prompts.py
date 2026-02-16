"""
YAML Prompt Migration Script

Warzone 4: AI Brain - BRAIN-014B
Migrates hardcoded YAML prompts to PromptTemplate entities.

Features:
- Scans for YAML prompt files in infrastructure/prompts directories
- Converts YAML prompts to PromptTemplate entities
- Supports {{> other_prompt}} include syntax for nested prompts
- Preserves original content and metadata

Usage:
    python -m src.contexts.knowledge.infrastructure.migrations.migrate_yaml_prompts
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ...application.ports.i_prompt_repository import IPromptRepository
from ...domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)

# Pattern for {{> other_prompt}} include syntax
_INCLUDE_PATTERN = re.compile(r"\{\{>\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

# Pattern for {{variable}} placeholders in templates
_VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


@dataclass(frozen=True, slots=True)
class PromptSource:
    """
    Represents a source YAML prompt file.

    Attributes:
        file_path: Path to the YAML file
        name: Extracted prompt name (derived from filename)
        context: The context name (character, story, world, etc.)
        raw_content: Raw YAML content as dictionary
    """

    file_path: Path
    name: str
    context: str
    raw_content: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationResult:
    """
    Result of a prompt migration operation.

    Attributes:
        total_found: Total number of YAML prompt files found
        migrated: Number of prompts successfully migrated
        skipped: Number of prompts skipped (already exist, errors, etc.)
        errors: List of error messages
        prompts: List of migrated PromptTemplate entities
    """

    total_found: int = 0
    migrated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    prompts: list[PromptTemplate] = field(default_factory=list)


class PromptMigrationError(Exception):
    """Base exception for prompt migration errors."""


class YAMLPromptMigrator:
    """
    Migrates YAML prompt files to PromptTemplate entities.

    Why separate class:
        Encapsulates migration logic for reusability and testing.
        Can be extended to support different source formats.

    Attributes:
        repository: Prompt repository for storing migrated templates
        project_root: Root directory of the project for scanning
    """

    def __init__(
        self, repository: IPromptRepository, project_root: Path | None = None
    ) -> None:
        """
        Initialize the migrator.

        Args:
            repository: Prompt repository for storing templates
            project_root: Project root directory (defaults to current directory)
        """
        self.repository = repository
        self.project_root = project_root or Path.cwd()

        # Cache for resolving includes during migration
        self._source_cache: dict[str, PromptSource] = {}

    def discover_prompts(self) -> list[PromptSource]:
        """
        Discover all YAML prompt files in the codebase.

        Returns:
            List of PromptSource objects representing found prompt files
        """
        sources: list[PromptSource] = []

        # Scan contexts directory for prompt files
        contexts_dir = self.project_root / "src" / "contexts"
        if not contexts_dir.exists():
            return sources

        # Find all infrastructure/prompts subdirectories
        for prompt_dir in contexts_dir.rglob("infrastructure/prompts"):
            if not prompt_dir.is_dir():
                continue

            # Extract context name from path
            # e.g., src/contexts/world/infrastructure/prompts -> world
            relative = prompt_dir.relative_to(contexts_dir)
            context = relative.parts[0] if relative.parts else "unknown"

            # Find all YAML files
            for yaml_file in prompt_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        content = yaml.safe_load(f) or {}

                    # Derive prompt name from filename
                    name = yaml_file.stem  # filename without extension

                    sources.append(
                        PromptSource(
                            file_path=yaml_file,
                            name=name,
                            context=context,
                            raw_content=content,
                        )
                    )
                except Exception as e:
                    # Log but don't fail for individual file errors
                    self._log_error(f"Failed to read {yaml_file}: {e}")

        return sources

    def resolve_includes(
        self, content: str, sources: list[PromptSource], visited: set[str] | None = None
    ) -> str:
        """
        Resolve {{> other_prompt}} include directives in template content.

        Args:
            content: Template content with potential includes
            sources: All available prompt sources for resolving references
            visited: Set of already visited prompt names (for circular reference detection)

        Returns:
            Content with includes resolved

        Raises:
            PromptMigrationError: If circular reference detected or referenced prompt not found
        """
        if visited is None:
            visited = set()

        result = content

        # Find all {{> prompt_name}} includes
        for match in _INCLUDE_PATTERN.finditer(content):
            ref_name = match.group(1)
            include_marker = match.group(0)

            # Check for circular references
            if ref_name in visited:
                raise PromptMigrationError(
                    f"Circular reference detected: {' -> '.join(sorted(visited))} -> {ref_name}"
                )

            # Find the referenced prompt source
            ref_source = next((s for s in sources if s.name == ref_name), None)
            if not ref_source:
                raise PromptMigrationError(
                    f"Referenced prompt '{ref_name}' not found in available sources"
                )

            # Get the content of the referenced prompt
            ref_content = str(ref_source.raw_content.get("system_prompt", ""))
            if not ref_content:
                raise PromptMigrationError(
                    f"Referenced prompt '{ref_name}' has no system_prompt content"
                )

            # Recursively resolve nested includes
            new_visited = visited | {ref_name}
            resolved_ref = self.resolve_includes(ref_content, sources, new_visited)

            # Replace the include marker with resolved content
            result = result.replace(include_marker, resolved_ref)

        return result

    def extract_variables(self, content: str) -> list[VariableDefinition]:
        """
        Extract variables from template content and create definitions.

        Args:
            content: Template content with {{variable}} placeholders

        Returns:
            List of VariableDefinition objects for found variables
        """
        var_names = set(_VARIABLE_PATTERN.findall(content))

        variables: list[VariableDefinition] = []
        for var_name in sorted(var_names):
            # Create variable definition with inferred type
            # Most prompt variables are strings, but we can detect some patterns
            var_def = VariableDefinition(
                name=var_name,
                type=VariableType.STRING,
                description=f"Variable: {var_name}",
                required=True,
                default_value=None,
            )
            variables.append(var_def)

        return variables

    def source_to_template(
        self, source: PromptSource, all_sources: list[PromptSource]
    ) -> PromptTemplate:
        """
        Convert a PromptSource to a PromptTemplate entity.

        Args:
            source: The prompt source to convert
            all_sources: All available sources for resolving includes

        Returns:
            PromptTemplate entity

        Raises:
            PromptMigrationError: If conversion fails
        """
        # Extract system prompt content
        raw_content = source.raw_content.get("system_prompt", "")
        if not raw_content:
            raise PromptMigrationError(
                f"Prompt '{source.name}' has no system_prompt field"
            )

        content = str(raw_content).strip()

        # Resolve {{> includes}} if present
        if _INCLUDE_PATTERN.search(content):
            content = self.resolve_includes(content, all_sources, {source.name})

        # Extract variables from content
        variables = self.extract_variables(content)

        # Build tags from context and filename
        tags: list[str] = [source.context]
        if "gen" in source.name:
            tags.append("generation")
        if "dialogue" in source.name:
            tags.append("dialogue")
        if "scene" in source.name:
            tags.append("scene")
        if "world" in source.name:
            tags.append("world")

        # Determine model config based on context
        # These are sensible defaults that can be updated post-migration
        provider = "gemini"  # Default to Gemini for most generation tasks
        model_name = "gemini-1.5-flash"
        temperature = 0.7
        max_tokens = 2000

        # Adjust for specific prompt types
        if source.context == "world":
            if "dialogue" in source.name:
                temperature = 0.8  # Higher temperature for creative dialogue
                max_tokens = 500
            elif "beat" in source.name:
                temperature = 0.7
                max_tokens = 1000
            elif "world" in source.name:
                max_tokens = 4000  # World gen needs more tokens
        elif source.context == "story":
            max_tokens = 1500
        elif source.context == "character":
            max_tokens = 800

        model_config = ModelConfig(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Create description from context and name
        description = (
            f"{source.context.title()} prompt for {source.name.replace('_', ' ')}"
        )

        # Create the PromptTemplate
        # Note: PromptTemplate.create() doesn't accept model_config directly,
        # so we use the PromptTemplate constructor with the config
        from uuid import uuid4

        template = PromptTemplate(
            id=str(uuid4()),
            name=source.name,
            content=content,
            variables=tuple(variables),
            model_config=model_config,
            tags=tuple(tags),
            description=description,
        )

        return template

    def _log_error(self, message: str) -> None:
        """Log an error message (can be overridden for logging integration)."""
        print(f"[ERROR] {message}")

    async def migrate(self, dry_run: bool = False) -> MigrationResult:
        """
        Run the migration process.

        Args:
            dry_run: If True, don't actually save to repository

        Returns:
            MigrationResult with statistics and migrated templates
        """
        result = MigrationResult()

        # Discover all prompt sources
        sources = self.discover_prompts()
        result.total_found = len(sources)

        # Cache sources for include resolution
        self._source_cache = {s.name: s for s in sources}

        for source in sources:
            try:
                # Check if template already exists
                existing = await self.repository.get_by_name(source.name)
                if existing is not None:
                    result.skipped += 1
                    continue

                # Convert source to template
                template = self.source_to_template(source, sources)

                # Save to repository (unless dry run)
                if not dry_run:
                    await self.repository.save(template)

                result.prompts.append(template)
                result.migrated += 1

            except PromptMigrationError as e:
                result.errors.append(f"{source.name}: {e}")
                result.skipped += 1
            except Exception as e:
                result.errors.append(f"{source.name}: Unexpected error: {e}")
                result.skipped += 1

        return result


async def main() -> None:
    """
    Main entry point for running the migration.

    This function can be called directly or imported and used programmatically.
    """
    from ..adapters.in_memory_prompt_repository import (
        InMemoryPromptRepository,
    )

    # Create repository and migrator
    repository = InMemoryPromptRepository()
    migrator = YAMLPromptMigrator(repository)

    print("Starting YAML prompt migration...")
    print("=" * 60)

    # Run migration
    result = await migrator.migrate(dry_run=False)

    # Print results
    print("\nMigration Results:")
    print(f"  Total prompts found: {result.total_found}")
    print(f"  Successfully migrated: {result.migrated}")
    print(f"  Skipped: {result.skipped}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")

    if result.prompts:
        print("\nMigrated Prompts:")
        for template in result.prompts:
            print(
                f"  - {template.name} (v{template.version}, {len(template.variables)} vars, "
                f"tags: {', '.join(template.tags)})"
            )

    print("=" * 60)
    print("Migration complete!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())


__all__ = [
    "YAMLPromptMigrator",
    "PromptSource",
    "MigrationResult",
    "PromptMigrationError",
    "main",
]
