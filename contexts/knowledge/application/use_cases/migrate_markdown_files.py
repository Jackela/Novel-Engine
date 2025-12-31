"""
MigrateMarkdownFilesUseCase

Application use case for migrating Markdown files to knowledge base.

Constitution Compliance:
- Article I (DDD): Orchestrates domain operations
- Article II (Hexagonal): Depends on ports, not concrete adapters
- Article V (SOLID): Single Responsibility - migration orchestration
"""

from typing import Dict, Any


class MigrateMarkdownFilesUseCase:
    """
    Use case for migrating Markdown files to knowledge base.

    Coordinates migration workflow including backup creation,
    file parsing, knowledge entry creation, and verification.

    Constitution Compliance:
        - Article I (DDD): Orchestrates migration without business logic
        - Article II (Hexagonal): Depends on migration adapter abstraction
        - Article V (SOLID): SRP - migration orchestration only

    Functional Requirements:
        - FR-016: Manual migration from Markdown to knowledge base
        - FR-017: Timestamped backup creation
        - FR-018: Rollback capability
        - FR-019: Verification mode
    """

    def __init__(self, migration_adapter):
        """
        Initialize use case with migration adapter.

        Args:
            migration_adapter: Adapter implementing migration operations
        """
        self._migration_adapter = migration_adapter

    async def execute(
        self,
        markdown_directory: str,
        create_backup: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute Markdown to knowledge base migration.

        Workflow:
        1. Create timestamped backup (if requested)
        2. Parse Markdown files into knowledge entries
        3. Persist entries to PostgreSQL
        4. Return migration report

        Args:
            markdown_directory: Root directory containing agent .md files
            create_backup: Whether to create backup before migration (default: True)

        Returns:
            Migration report with statistics and backup path

        Example:
            >>> use_case = MigrateMarkdownFilesUseCase(migration_adapter)
            >>> report = await use_case.execute(
            ...     markdown_directory="/path/to/agents",
            ...     create_backup=True,
            ... )
            >>> print(report["total_entries"])
            42

        Constitution Compliance:
            - Article II (Hexagonal): Delegates to adapter
            - FR-016: Manual migration capability
        """
        # Delegate to migration adapter
        report = await self._migration_adapter.migrate_all_agents(
            markdown_directory=markdown_directory,
            create_backup=create_backup,
        )

        return report

    async def rollback(
        self,
        backup_path: str,
    ) -> Dict[str, Any]:
        """
        Rollback migration by restoring from backup.

        Workflow:
        1. Delete migrated knowledge entries from PostgreSQL
        2. Restore original Markdown files from backup
        3. Return rollback report

        Args:
            backup_path: Path to backup directory

        Returns:
            Rollback report with statistics

        Constitution Compliance:
            - FR-018: Rollback capability
        """
        # Delegate to migration adapter
        report = await self._migration_adapter.rollback_migration(
            backup_path=backup_path,
        )

        return report

    async def verify(
        self,
        markdown_directory: str,
    ) -> Dict[str, Any]:
        """
        Verify migration by comparing Markdown vs knowledge base.

        Workflow:
        1. Read Markdown files
        2. Query knowledge entries from PostgreSQL
        3. Compare content for mismatches
        4. Return verification report

        Args:
            markdown_directory: Root directory containing agent .md files

        Returns:
            Verification report with comparison results

        Constitution Compliance:
            - FR-019: Verification mode
        """
        # Delegate to migration adapter
        report = await self._migration_adapter.verify_migration(
            markdown_directory=markdown_directory,
        )

        return report
