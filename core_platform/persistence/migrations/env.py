"""
Alembic Environment Configuration for Novel Engine Platform
========================================================

Database migration environment with support for:
- Multiple database configurations
- Async and sync migration support
- Auto-generation from SQLAlchemy models
- Transaction safety and rollback capability
"""

import asyncio
import logging
from logging.config import fileConfig

from alembic import context

# Import configuration
from core_platform.config.settings import get_database_settings

# Import all models to ensure they're registered with SQLAlchemy metadata
from core_platform.persistence.models import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from configuration."""
    try:
        settings = get_database_settings()
        return settings["url"]
    except Exception as e:
        logger.warning(f"Failed to get database settings: {e}")
        # Fallback to Alembic config
        return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        # Custom rendering for PostgreSQL-specific types
        render_as_batch=False,
        # Transaction per migration for safety
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        # Custom rendering for PostgreSQL-specific types
        render_as_batch=False,
        # Transaction per migration for safety
        transaction_per_migration=True,
        # Include object filters if needed
        # include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override the sqlalchemy.url config option
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        # Create engine from configuration
        connectable = context.get_context().bind

        if connectable is None:
            from sqlalchemy import create_engine

            connectable = create_engine(
                get_database_url(),
                poolclass=pool.NullPool,
            )

    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.

    This is useful for applications that use async SQLAlchemy.
    """
    configuration = config.get_section(config.config_ini_section)

    # Convert sync URL to async URL
    database_url = get_database_url()
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

    configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to include in migrations.

    This function can be used to exclude certain tables, columns, etc.
    from auto-generation.
    """
    # Skip temporary or system tables
    if type_ == "table" and name.startswith("_temp"):
        return False

    # Skip certain schemas if needed
    if hasattr(object, "schema") and object.schema in [
        "information_schema",
        "pg_catalog",
    ]:
        return False

    return True


# Determine which migration mode to use
if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")

    # Check if we should run async migrations
    if context.config.attributes.get("async_mode", False):
        logger.info("Running async migrations")
        asyncio.run(run_async_migrations())
    else:
        run_migrations_online()
