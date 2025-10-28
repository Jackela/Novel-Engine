"""
Database Migration Utilities
===========================

Utilities and helpers for database migrations, schema management,
and migration operations for Novel Engine platform.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from ..config.settings import get_database_settings

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    High-level migration management for Novel Engine platform.

    Features:
    - Migration generation and execution
    - Schema validation and health checks
    - Migration history and status tracking
    - Rollback and recovery operations
    - Multi-environment support
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize migration manager with Alembic configuration."""
        if config_path is None:
            # Default to alembic.ini in persistence directory
            config_path = Path(__file__).parent / "alembic.ini"

        self.config_path = str(config_path)
        self.alembic_config = Config(self.config_path)

        # Set up paths
        script_location = self.alembic_config.get_main_option("script_location")
        if not os.path.isabs(script_location):
            # Make relative paths absolute from config file location
            config_dir = os.path.dirname(self.config_path)
            script_location = os.path.join(config_dir, script_location)
            self.alembic_config.set_main_option("script_location", script_location)

    def initialize_migration_repository(self) -> None:
        """Initialize the migration repository if it doesn't exist."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            if not os.path.exists(script_dir.dir):
                logger.info("Initializing migration repository...")
                command.init(self.alembic_config, script_dir.dir)
                logger.info("Migration repository initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize migration repository: {e}")
            raise

    def generate_migration(self, message: str, auto_generate: bool = True) -> str:
        """
        Generate a new migration script.

        Args:
            message: Description of the migration
            auto_generate: Whether to auto-generate from model changes

        Returns:
            Revision ID of the generated migration
        """
        try:
            logger.info(f"Generating migration: {message}")

            if auto_generate:
                # Auto-generate migration from model changes
                revision = command.revision(
                    self.alembic_config, message=message, autogenerate=True
                )
            else:
                # Create empty migration template
                revision = command.revision(self.alembic_config, message=message)

            logger.info(f"Generated migration with revision ID: {revision.revision}")
            return revision.revision

        except Exception as e:
            logger.error(f"Failed to generate migration: {e}")
            raise

    def run_migrations(self, target_revision: Optional[str] = None) -> None:
        """
        Run pending migrations.

        Args:
            target_revision: Specific revision to migrate to (None for latest)
        """
        try:
            logger.info("Running database migrations...")

            if target_revision:
                command.upgrade(self.alembic_config, target_revision)
                logger.info(f"Migrated to revision: {target_revision}")
            else:
                command.upgrade(self.alembic_config, "head")
                logger.info("Migrated to latest revision")

        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise

    def rollback_migration(self, target_revision: str = "-1") -> None:
        """
        Rollback migrations.

        Args:
            target_revision: Revision to rollback to ("-1" for previous)
        """
        try:
            logger.info(f"Rolling back migration to: {target_revision}")
            command.downgrade(self.alembic_config, target_revision)
            logger.info("Migration rollback completed")

        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            raise

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get the migration history."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            revisions = []

            for revision in script_dir.walk_revisions():
                revisions.append(
                    {
                        "revision": revision.revision,
                        "down_revision": revision.down_revision,
                        "branch_labels": revision.branch_labels,
                        "message": revision.doc,
                        "path": revision.path,
                    }
                )

            return revisions

        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            raise

    def get_current_revision(self) -> Optional[str]:
        """Get the current database revision."""
        try:
            settings = get_database_settings()
            engine = create_engine(settings["url"])

            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()

            return current_rev

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migration revisions."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            current_revision = self.get_current_revision()

            if current_revision is None:
                # No migrations applied yet, return all revisions
                return [rev.revision for rev in script_dir.walk_revisions()]

            # Get revisions between current and head
            revisions = []
            for revision in script_dir.walk_revisions("head", current_revision):
                if revision.revision != current_revision:
                    revisions.append(revision.revision)

            return revisions

        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            raise

    def validate_schema(self) -> Dict[str, Any]:
        """Validate that the database schema matches the models."""
        try:
            from alembic.autogenerate import compare_metadata

            from ..persistence.models import Base

            settings = get_database_settings()
            engine = create_engine(settings["url"])

            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                diff = compare_metadata(context, Base.metadata)

                validation_result = {
                    "is_valid": len(diff) == 0,
                    "differences": len(diff),
                    "details": [],
                }

                for change in diff:
                    validation_result["details"].append(str(change))

                return validation_result

        except Exception as e:
            logger.error(f"Failed to validate schema: {e}")
            raise

    def create_database_if_not_exists(self) -> None:
        """Create the database if it doesn't exist."""
        try:
            settings = get_database_settings()
            database_url = settings["url"]

            # Parse database URL to get database name
            from urllib.parse import urlparse

            parsed = urlparse(database_url)
            database_name = parsed.path.lstrip("/")

            # Create connection to postgres database (without specific database)
            admin_url = database_url.replace(f"/{database_name}", "/postgres")
            engine = create_engine(admin_url)

            with engine.connect() as connection:
                # Use autocommit mode for database creation
                connection = connection.execution_options(autocommit=True)

                # Check if database exists
                result = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": database_name},
                )

                if not result.fetchone():
                    logger.info(f"Creating database: {database_name}")
                    connection.execute(text(f'CREATE DATABASE "{database_name}"'))
                    logger.info("Database created successfully")
                else:
                    logger.info(f"Database {database_name} already exists")

        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise

    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        try:
            current_revision = self.get_current_revision()
            pending_migrations = self.get_pending_migrations()
            migration_history = self.get_migration_history()
            schema_validation = self.validate_schema()

            return {
                "current_revision": current_revision,
                "pending_migrations": pending_migrations,
                "pending_count": len(pending_migrations),
                "total_migrations": len(migration_history),
                "schema_valid": schema_validation["is_valid"],
                "schema_differences": schema_validation["differences"],
                "is_up_to_date": len(pending_migrations) == 0,
            }

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            raise


# Convenience functions
_migration_manager = None


def get_migration_manager() -> MigrationManager:
    """Get the global migration manager instance."""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager


def init_database() -> None:
    """Initialize database and run all migrations."""
    manager = get_migration_manager()
    manager.create_database_if_not_exists()
    manager.run_migrations()


def create_migration(message: str, auto_generate: bool = True) -> str:
    """Create a new migration."""
    manager = get_migration_manager()
    return manager.generate_migration(message, auto_generate)


def migrate() -> None:
    """Run all pending migrations."""
    manager = get_migration_manager()
    manager.run_migrations()


def rollback(target: str = "-1") -> None:
    """Rollback migrations."""
    manager = get_migration_manager()
    manager.rollback_migration(target)


def migration_status() -> Dict[str, Any]:
    """Get current migration status."""
    manager = get_migration_manager()
    return manager.get_migration_status()
