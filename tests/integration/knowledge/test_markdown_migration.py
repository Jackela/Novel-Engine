"""
Integration Tests for Markdown Migration

Tests migration of Markdown files to knowledge base with backup and rollback.

Constitution Compliance:
- Article III (TDD): Tests written FIRST, confirmed failing
- Article IV (SSOT): PostgreSQL as target for migrated knowledge
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from contexts.knowledge.domain.models.agent_identity import AgentIdentity
from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from contexts.knowledge.domain.models.access_level import AccessLevel
from contexts.knowledge.infrastructure.adapters.markdown_migration_adapter import (
    MarkdownMigrationAdapter,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestMarkdownMigration:
    """Integration tests for Markdown to knowledge base migration."""
    
    @pytest.fixture
    def temp_markdown_dir(self):
        """Create temporary directory with sample Markdown files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create sample agent Markdown files
        agent_dir = Path(temp_dir) / "agents"
        agent_dir.mkdir()
        
        # Agent 1: Explorer character
        explorer_file = agent_dir / "explorer-001.md"
        explorer_file.write_text("""
# Explorer Agent Knowledge

## Background
The explorer has visited 15 star systems and documented 42 alien species.

## Current Mission
Investigating mysterious signals from the Andromeda sector.

## Equipment
- Quantum scanner
- Universal translator
- Emergency beacon
""")
        
        # Agent 2: Scientist character
        scientist_file = agent_dir / "scientist-001.md"
        scientist_file.write_text("""
# Scientist Agent Knowledge

## Research Focus
Xenobiology and quantum mechanics.

## Recent Discoveries
- New element: Quantium-7
- Faster-than-light communication possible via quantum entanglement

## Lab Equipment
- Quantum analyzer
- DNA sequencer
""")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def migration_adapter(self):
        """Create migration adapter instance."""
        # Mock repository
        repository = AsyncMock()
        
        # Will fail until MarkdownMigrationAdapter is implemented
        adapter = MarkdownMigrationAdapter(repository=repository)
        
        return adapter
    
    @pytest.mark.asyncio
    async def test_migrate_all_agents_converts_markdown_files_to_knowledge_entries(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that migrate_all_agents converts all Markdown files to knowledge entries.
        
        Workflow:
        1. Scan agent directory for .md files
        2. Parse each Markdown file into sections
        3. Create KnowledgeEntry for each section
        4. Save entries to PostgreSQL
        5. Return migration report
        
        This validates FR-016: Manual migration from Markdown to knowledge base
        """
        # Mock repository to track saved entries
        saved_entries = []
        
        async def mock_save(entry):
            saved_entries.append(entry)
        
        migration_adapter._repository.save = mock_save
        
        # Execute migration
        report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
        )
        
        # Verify migration report
        assert report is not None
        assert report["total_files"] == 2  # explorer-001.md, scientist-001.md
        assert report["total_entries"] >= 2  # At least one entry per file
        assert report["status"] == "success"
        
        # Verify entries were saved
        assert len(saved_entries) >= 2
        
        # Verify entry structure
        first_entry = saved_entries[0]
        assert first_entry.content is not None
        assert len(first_entry.content) > 0
        assert first_entry.knowledge_type in [
            KnowledgeType.LORE,
            KnowledgeType.RULES,
            KnowledgeType.PROFILE,
        ]
        assert first_entry.access_control.access_level == AccessLevel.PUBLIC
    
    @pytest.mark.asyncio
    async def test_migrate_all_agents_handles_empty_directory(
        self, migration_adapter
    ):
        """
        Test that migration handles empty directories gracefully.
        
        Expected: Return report with zero files processed
        """
        # Create empty temp directory
        with tempfile.TemporaryDirectory() as empty_dir:
            report = await migration_adapter.migrate_all_agents(
                markdown_directory=empty_dir,
            )
            
            assert report["total_files"] == 0
            assert report["total_entries"] == 0
            assert report["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_migrate_all_agents_skips_non_markdown_files(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that migration skips non-.md files.
        
        Create .txt, .json files alongside .md files, verify only .md processed.
        """
        # Add non-markdown files
        agent_dir = Path(temp_markdown_dir) / "agents"
        (agent_dir / "notes.txt").write_text("Some notes")
        (agent_dir / "config.json").write_text('{"key": "value"}')
        
        report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
        )
        
        # Should only process .md files (2 files)
        assert report["total_files"] == 2
    
    @pytest.mark.asyncio
    async def test_migrate_all_agents_preserves_character_ownership(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that migrated entries are assigned to correct owning character.
        
        File: explorer-001.md → owning_character_id = "explorer-001"
        """
        saved_entries = []
        
        async def mock_save(entry):
            saved_entries.append(entry)
        
        migration_adapter._repository.save = mock_save
        
        await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
        )
        
        # Verify character ownership
        explorer_entries = [
            e for e in saved_entries if e.owning_character_id == "explorer-001"
        ]
        scientist_entries = [
            e for e in saved_entries if e.owning_character_id == "scientist-001"
        ]
        
        assert len(explorer_entries) > 0
        assert len(scientist_entries) > 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestMarkdownMigrationBackup:
    """Integration tests for backup creation during migration (FR-017)."""
    
    @pytest.fixture
    def temp_markdown_dir(self):
        """Create temporary directory with sample Markdown files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create sample agent Markdown files
        agent_dir = Path(temp_dir) / "agents"
        agent_dir.mkdir()
        
        agent_file = agent_dir / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nTest content")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def migration_adapter(self):
        """Create migration adapter instance."""
        repository = AsyncMock()
        adapter = MarkdownMigrationAdapter(repository=repository)
        return adapter
    
    @pytest.mark.asyncio
    async def test_migration_creates_timestamped_backup_directory(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that migration creates timestamped backup before modifying files.
        
        Backup directory format: backups/migration-YYYYMMDD-HHMMSS/
        
        This validates FR-017: Timestamped backup creation
        """
        # Execute migration with backup
        report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
            create_backup=True,
        )
        
        # Verify backup was created
        assert "backup_path" in report
        backup_path = Path(report["backup_path"])
        
        assert backup_path.exists()
        assert backup_path.is_dir()
        assert "migration-" in backup_path.name
        
        # Verify backup contains original files
        backed_up_files = list(backup_path.rglob("*.md"))
        assert len(backed_up_files) >= 1
    
    @pytest.mark.asyncio
    async def test_backup_preserves_directory_structure(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that backup preserves original directory structure.
        
        Original: agents/explorer-001.md
        Backup: backups/migration-*/agents/explorer-001.md
        """
        # Create nested structure
        agent_dir = Path(temp_markdown_dir) / "agents" / "explorers"
        agent_dir.mkdir(parents=True)
        (agent_dir / "nested-agent.md").write_text("# Nested")
        
        report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
            create_backup=True,
        )
        
        backup_path = Path(report["backup_path"])
        
        # Verify nested structure preserved
        nested_backup = backup_path / "agents" / "explorers" / "nested-agent.md"
        assert nested_backup.exists()
    
    @pytest.mark.asyncio
    async def test_migration_without_backup_flag_skips_backup(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that migration can skip backup when create_backup=False.
        
        Use case: Testing or when backup already exists
        """
        report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
            create_backup=False,
        )
        
        # Backup path should not be in report
        assert "backup_path" not in report or report["backup_path"] is None


@pytest.mark.integration
@pytest.mark.asyncio
class TestMarkdownMigrationRollback:
    """Integration tests for rollback capability (FR-018)."""
    
    @pytest.fixture
    def temp_markdown_dir(self):
        """Create temporary directory with sample Markdown files."""
        temp_dir = tempfile.mkdtemp()
        
        agent_dir = Path(temp_dir) / "agents"
        agent_dir.mkdir()
        
        agent_file = agent_dir / "test-agent.md"
        agent_file.write_text("# Original Content\n\nOriginal knowledge")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def migration_adapter(self):
        """Create migration adapter instance."""
        repository = AsyncMock()
        adapter = MarkdownMigrationAdapter(repository=repository)
        return adapter
    
    @pytest.mark.asyncio
    async def test_rollback_deletes_migrated_knowledge_entries(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that rollback deletes all knowledge entries created during migration.
        
        Workflow:
        1. Run migration → Creates knowledge entries
        2. Run rollback → Deletes all migrated entries from PostgreSQL
        3. Verify entries deleted
        
        This validates FR-018: Rollback capability to restore Markdown-based operation
        """
        # Track saved and deleted entries
        saved_entry_ids = []
        deleted_entry_ids = []
        
        async def mock_save(entry):
            saved_entry_ids.append(entry.id)
        
        async def mock_delete(entry_id):
            deleted_entry_ids.append(entry_id)
        
        migration_adapter._repository.save = mock_save
        migration_adapter._repository.delete = mock_delete
        
        # Execute migration
        migration_report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
            create_backup=True,
        )
        
        # Execute rollback
        rollback_report = await migration_adapter.rollback_migration(
            backup_path=migration_report["backup_path"],
        )
        
        # Verify all entries were deleted
        assert rollback_report["status"] == "success"
        assert rollback_report["entries_deleted"] == len(saved_entry_ids)
        assert set(deleted_entry_ids) == set(saved_entry_ids)
    
    @pytest.mark.asyncio
    async def test_rollback_restores_original_markdown_files(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that rollback restores Markdown files from backup.
        
        Workflow:
        1. Backup created during migration
        2. Rollback copies files from backup back to original location
        3. Original Markdown files restored
        """
        # Execute migration with backup
        migration_report = await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
            create_backup=True,
        )
        
        # Modify original file (simulate corruption)
        agent_file = Path(temp_markdown_dir) / "agents" / "test-agent.md"
        agent_file.write_text("# Modified Content")
        
        # Execute rollback
        await migration_adapter.rollback_migration(
            backup_path=migration_report["backup_path"],
        )
        
        # Verify original content restored
        restored_content = agent_file.read_text()
        assert "Original Content" in restored_content
        assert "Modified Content" not in restored_content
    
    @pytest.mark.asyncio
    async def test_rollback_without_backup_path_raises_error(
        self, migration_adapter
    ):
        """
        Test that rollback requires valid backup path.
        
        Expected: Raise ValueError if backup_path is None or invalid
        """
        with pytest.raises(ValueError, match="backup_path"):
            await migration_adapter.rollback_migration(backup_path=None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestMarkdownMigrationVerification:
    """Integration tests for verification mode (FR-019)."""
    
    @pytest.fixture
    def temp_markdown_dir(self):
        """Create temporary directory with sample Markdown files."""
        temp_dir = tempfile.mkdtemp()
        
        agent_dir = Path(temp_dir) / "agents"
        agent_dir.mkdir()
        
        agent_file = agent_dir / "test-agent.md"
        agent_file.write_text("""
# Test Agent

## Section 1
Content for section 1

## Section 2
Content for section 2
""")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def migration_adapter(self):
        """Create migration adapter instance."""
        repository = AsyncMock()
        adapter = MarkdownMigrationAdapter(repository=repository)
        return adapter
    
    @pytest.mark.asyncio
    async def test_verify_migration_compares_markdown_vs_knowledge_base(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that verification mode compares Markdown content vs PostgreSQL.
        
        Workflow:
        1. Run migration
        2. Run verification
        3. Verify report shows content matches
        
        This validates FR-019: Verification mode for comparing sources
        """
        # Mock repository to return matching entries
        saved_entries = []
        
        async def mock_save(entry):
            saved_entries.append(entry)
        
        async def mock_retrieve(agent, **kwargs):
            return saved_entries
        
        migration_adapter._repository.save = mock_save
        migration_adapter._repository.retrieve_for_agent = mock_retrieve
        
        # Execute migration
        await migration_adapter.migrate_all_agents(
            markdown_directory=temp_markdown_dir,
        )
        
        # Execute verification
        verification_report = await migration_adapter.verify_migration(
            markdown_directory=temp_markdown_dir,
        )
        
        # Verify report structure
        assert verification_report["status"] == "success"
        assert "files_checked" in verification_report
        assert "entries_matched" in verification_report
        assert verification_report["files_checked"] >= 1
    
    @pytest.mark.asyncio
    async def test_verify_migration_detects_content_mismatch(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that verification detects when content doesn't match.
        
        Scenario: Markdown file modified after migration
        Expected: Verification report shows mismatch
        """
        # Mock repository with mismatched content
        async def mock_retrieve(agent, **kwargs):
            from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
            from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
            from datetime import datetime, timezone
            
            now = datetime.now(timezone.utc)
            
            return [
                KnowledgeEntry(
                    id="entry-001",
                    content="Different content than Markdown",  # Mismatch
                    knowledge_type=KnowledgeType.LORE,
                    owning_character_id="test-agent",
                    access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                    created_at=now,
                    updated_at=now,
                    created_by="migration",
                )
            ]
        
        migration_adapter._repository.retrieve_for_agent = mock_retrieve
        
        # Execute verification
        verification_report = await migration_adapter.verify_migration(
            markdown_directory=temp_markdown_dir,
        )
        
        # Verify mismatch detected
        assert verification_report["status"] == "mismatch"
        assert "mismatches" in verification_report
        assert len(verification_report["mismatches"]) > 0
    
    @pytest.mark.asyncio
    async def test_verify_migration_detects_missing_entries(
        self, migration_adapter, temp_markdown_dir
    ):
        """
        Test that verification detects when knowledge entries are missing.
        
        Scenario: Markdown file exists but no corresponding knowledge entry
        Expected: Verification report shows missing entries
        """
        # Mock repository with no entries
        async def mock_retrieve(agent, **kwargs):
            return []
        
        migration_adapter._repository.retrieve_for_agent = mock_retrieve
        
        # Execute verification
        verification_report = await migration_adapter.verify_migration(
            markdown_directory=temp_markdown_dir,
        )
        
        # Verify missing entries detected
        assert verification_report["status"] == "missing_entries"
        assert "missing_files" in verification_report
        assert len(verification_report["missing_files"]) > 0
