"""Create the Novel Studio 0.3 authoritative schema."""

from __future__ import annotations

from alembic import op

from src.contexts.studio.infrastructure.models import Base

revision = "0001_novel_studio_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    bind.exec_driver_sql(
        "CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5("
        "document_id UNINDEXED, project_id UNINDEXED, title, content)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS document_search")
    Base.metadata.drop_all(bind)
