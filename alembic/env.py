"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import all models to ensure they're registered with SQLAlchemy
from src.contexts.knowledge.infrastructure.persistence.models import (
    Base as KnowledgeBase,
)
from src.contexts.narrative.infrastructure.persistence.models import (
    Base as NarrativeBase,
)
from src.contexts.world.infrastructure.persistence.models import Base as WorldBase
from src.shared.infrastructure.config.settings import get_settings

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database.url)

# Combine all model metadata
target_metadata = [
    KnowledgeBase.metadata,
    NarrativeBase.metadata,
    WorldBase.metadata,
]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
