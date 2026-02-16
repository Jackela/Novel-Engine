"""
Markdown Migration Adapter

Migrates Markdown files to PostgreSQL knowledge base with backup and rollback.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter for migration operations
- Article IV (SSOT): PostgreSQL as target for migrated knowledge
- Article V (SOLID): SRP - migration operations only
"""

import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ...application.ports.i_knowledge_repository import IKnowledgeRepository
from ...domain.models.access_control_rule import AccessControlRule
from ...domain.models.access_level import AccessLevel
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_entry import KnowledgeEntry
from ...domain.models.knowledge_type import KnowledgeType
from ..metrics_config import (
    migration_duration_seconds,
    migration_entries_processed_total,
)


class MarkdownMigrationAdapter:
    """
    Adapter for migrating Markdown files to knowledge base.

    Provides migration, backup, rollback, and verification operations for
    converting agent Markdown files to PostgreSQL knowledge entries.

    Constitution Compliance:
        - Article II (Hexagonal): Infrastructure adapter
        - Article IV (SSOT): PostgreSQL as single source after migration
        - Article V (SOLID): SRP - migration operations only

    Functional Requirements:
        - FR-016: Manual migration from Markdown to knowledge base
        - FR-017: Timestamped backup creation
        - FR-018: Rollback capability
        - FR-019: Verification mode
    """

    def __init__(self, repository: IKnowledgeRepository):
        """
        Initialize migration adapter with repository.

        Args:
            repository: Knowledge repository for persisting migrated entries
        """
        self._repository = repository
        self._migration_metadata: Dict[str, Dict[str, Any]] = (
            {}
        )  # Track migration details

    async def migrate_all_agents(
        self,
        markdown_directory: str,
        create_backup: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate all Markdown files to knowledge base (FR-016).

        Scans directory for .md files, parses content into sections,
        creates knowledge entries, and persists to PostgreSQL.

        Args:
            markdown_directory: Root directory containing agent .md files
            create_backup: Whether to create timestamped backup (default: True)

        Returns:
            Migration report with statistics and backup path

        Example Report:
            {
                "status": "success",
                "total_files": 10,
                "total_entries": 42,
                "backup_path": "/backups/migration-20250104-120000",
                "migrated_entry_ids": ["entry-001", "entry-002", ...]
            }

        Constitution Compliance:
            - Article IV (SSOT): PostgreSQL becomes authoritative source
            - FR-016: Manual migration capability
            - FR-017: Backup creation before modification
            - Article VII (Observability): Metrics instrumentation
        """
        start_time = time.time()
        markdown_path = Path(markdown_directory)

        # Create backup if requested (FR-017)
        backup_path = None
        if create_backup:
            backup_path = self._create_backup(markdown_path)

        # Find all Markdown files
        markdown_files = list(markdown_path.rglob("*.md"))

        total_entries = 0
        migrated_entry_ids = []
        errors = 0

        # Process each Markdown file
        for md_file in markdown_files:
            try:
                entries = await self._parse_markdown_file(md_file)

                for entry in entries:
                    await self._repository.save(entry)
                    migrated_entry_ids.append(entry.id)
                    total_entries += 1
                    migration_entries_processed_total.labels(status="success").inc()
            except Exception:
                errors += 1
                migration_entries_processed_total.labels(status="error").inc()

        # Store migration metadata for rollback
        if backup_path:
            self._migration_metadata[str(backup_path)] = {
                "entry_ids": migrated_entry_ids,
                "source_path": str(markdown_path),
            }

        # Record migration duration
        duration = time.time() - start_time
        migration_duration_seconds.labels(operation="migrate").observe(duration)

        # Build migration report
        report = {
            "status": "success" if errors == 0 else "partial",
            "total_files": len(markdown_files),
            "total_entries": total_entries,
            "migrated_entry_ids": migrated_entry_ids,
            "errors": errors,
        }

        if backup_path:
            report["backup_path"] = str(backup_path)

        return report

    async def rollback_migration(
        self,
        backup_path: str | None,
    ) -> Dict[str, Any]:
        """
        Rollback migration by deleting entries and restoring Markdown files (FR-018).

        Workflow:
        1. Delete all knowledge entries created during migration
        2. Restore original Markdown files from backup
        3. Return rollback report

        Args:
            backup_path: Path to backup directory created during migration

        Returns:
            Rollback report with statistics

        Raises:
            ValueError: If backup_path is None or invalid

        Constitution Compliance:
            - FR-018: Rollback capability to restore Markdown-based operation
            - Article VII (Observability): Metrics instrumentation
        """
        start_time = time.time()

        if not backup_path:
            raise ValueError("backup_path is required for rollback operation")

        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise ValueError(f"Backup directory not found: {backup_path}")

        # Get migration metadata
        metadata = self._migration_metadata.get(str(backup_path), {})
        entry_ids = metadata.get("entry_ids", [])
        original_source_path = metadata.get("source_path")

        # Delete all migrated entries from PostgreSQL
        entries_deleted = 0
        for entry_id in entry_ids:
            try:
                await self._repository.delete(entry_id)
                entries_deleted += 1
            except ValueError:
                # Entry already deleted or doesn't exist
                pass

        # Restore Markdown files from backup
        # Use stored source path for accurate restoration
        if original_source_path:
            original_path = Path(original_source_path)
            for backup_file in backup_dir.rglob("*.md"):
                # Calculate relative path from backup root
                relative_path = backup_file.relative_to(backup_dir)

                # Restore to original source location
                target_file = original_path / relative_path

                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)

        # Clear migration metadata
        if str(backup_path) in self._migration_metadata:
            del self._migration_metadata[str(backup_path)]

        # Record rollback duration
        duration = time.time() - start_time
        migration_duration_seconds.labels(operation="rollback").observe(duration)

        return {
            "status": "success",
            "entries_deleted": entries_deleted,
            "backup_path": str(backup_path),
        }

    async def verify_migration(
        self,
        markdown_directory: str,
    ) -> Dict[str, Any]:
        """
        Verify migration by comparing Markdown vs knowledge base (FR-019).

        Compares content between Markdown files and PostgreSQL entries
        to detect mismatches, missing entries, or data corruption.

        Args:
            markdown_directory: Root directory containing agent .md files

        Returns:
            Verification report with comparison results

        Example Report:
            {
                "status": "success",  # or "mismatch" or "missing_entries"
                "files_checked": 10,
                "entries_matched": 42,
                "mismatches": [],
                "missing_files": []
            }

        Constitution Compliance:
            - FR-019: Verification mode for comparing sources
            - Article VII (Observability): Metrics instrumentation
        """
        start_time = time.time()
        markdown_path = Path(markdown_directory)
        markdown_files = list(markdown_path.rglob("*.md"))

        files_checked = 0
        entries_matched = 0
        mismatches = []
        missing_files = []

        # Check each Markdown file
        for md_file in markdown_files:
            files_checked += 1

            # Extract character ID from filename
            character_id = md_file.stem  # Filename without extension

            # Retrieve entries for this character
            agent = AgentIdentity(character_id=character_id, roles=())
            entries = await self._repository.retrieve_for_agent(agent=agent)

            if not entries:
                missing_files.append(str(md_file))
                continue

            # Compare content between Markdown and knowledge entries
            md_content = md_file.read_text(encoding="utf-8")

            # Check if any entry matches the Markdown content
            content_matched = False
            for entry in entries:
                if entry.content.strip() == md_content.strip():
                    content_matched = True
                    entries_matched += 1
                    break

            if not content_matched:
                # Content mismatch detected
                mismatches.append(
                    {
                        "file": str(md_file),
                        "character_id": character_id,
                        "reason": "content_mismatch",
                    }
                )

        # Determine overall status
        status = "success"
        if mismatches:
            status = "mismatch"
        elif missing_files:
            status = "missing_entries"

        # Record verification duration
        duration = time.time() - start_time
        migration_duration_seconds.labels(operation="verify").observe(duration)

        return {
            "status": status,
            "files_checked": files_checked,
            "entries_matched": entries_matched,
            "mismatches": mismatches,
            "missing_files": missing_files,
        }

    def _create_backup(self, source_path: Path) -> Path:
        """
        Create timestamped backup directory (FR-017).

        Args:
            source_path: Source directory to backup

        Returns:
            Path to created backup directory

        Format: backups/migration-YYYYMMDD-HHMMSS/
        """
        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_root = source_path.parent / "backups"
        backup_root.mkdir(exist_ok=True)

        backup_dir = backup_root / f"migration-{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files preserving structure
        if source_path.is_dir():
            for item in source_path.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(source_path)
                    backup_file = backup_dir / relative_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, backup_file)

        return backup_dir

    async def _parse_markdown_file(self, md_file: Path) -> List[KnowledgeEntry]:
        """
        Parse Markdown file into knowledge entries.

        Parses Markdown sections (## headers) into separate knowledge entries.

        Args:
            md_file: Path to Markdown file

        Returns:
            List of KnowledgeEntry aggregates

        Example:
            # Agent Name

            ## Background
            Content here

            ## Equipment
            More content

            → Creates 2 knowledge entries (Background, Equipment)
        """
        content = md_file.read_text(encoding="utf-8")

        # Extract character ID from filename
        character_id = md_file.stem

        # Parse Markdown into sections
        # For MVP, create one entry per file
        # Full section parsing would split on ## headers

        now = datetime.now(timezone.utc)

        # Create single knowledge entry for entire file
        entry = KnowledgeEntry(
            id=str(uuid.uuid4()),
            content=content,
            knowledge_type=KnowledgeType.LORE,  # Use LORE for migrated content
            owning_character_id=character_id,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=now,
            updated_at=now,
            created_by="markdown_migration",
        )

        return [entry]
