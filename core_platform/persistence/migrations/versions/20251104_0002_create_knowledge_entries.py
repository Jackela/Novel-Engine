"""Create knowledge_entries table

Revision ID: 0002
Revises: 0001
Create Date: 2025-11-04 00:00:00.000000

Feature: 001-dynamic-agent-knowledge
Purpose: Create knowledge_entries table with indexes for Knowledge Management bounded context
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alembic_revision_ids() -> tuple[
    str,
    Union[str, None],
    Union[str, Sequence[str], None],
    Union[str, Sequence[str], None],
]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    """Upgrade database schema - Create knowledge_entries table."""

    # Create knowledge_entries table
    op.create_table(
        "knowledge_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "knowledge_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "owning_character_id",
            sa.String(length=255),
            nullable=True,  # Nullable for world knowledge
        ),
        sa.Column(
            "access_level",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "allowed_roles",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "allowed_character_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # Content validation constraint
        sa.CheckConstraint(
            "LENGTH(TRIM(content)) > 0",
            name="ck_knowledge_entries_content_not_empty",
        ),
        # Knowledge type enum constraint
        sa.CheckConstraint(
            "knowledge_type IN ('profile', 'objective', 'memory', 'lore', 'rules')",
            name="ck_knowledge_entries_valid_type",
        ),
        # Access level enum constraint
        sa.CheckConstraint(
            "access_level IN ('public', 'role_based', 'character_specific')",
            name="ck_knowledge_entries_valid_access_level",
        ),
        # Timestamp validation constraint
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_knowledge_entries_valid_timestamps",
        ),
        # Role-based access requires roles constraint
        sa.CheckConstraint(
            "access_level != 'role_based' OR (allowed_roles IS NOT NULL AND array_length(allowed_roles, 1) > 0)",
            name="ck_knowledge_entries_role_based_requires_roles",
        ),
        # Character-specific access requires character IDs constraint
        sa.CheckConstraint(
            "access_level != 'character_specific' OR (allowed_character_ids IS NOT NULL AND array_length(allowed_character_ids, 1) > 0)",
            name="ck_knowledge_entries_character_specific_requires_ids",
        ),
    )

    # Create indexes for performance (SC-002: <500ms retrieval for ≤100 entries)
    op.create_index(
        "ix_knowledge_entries_owning_character_id",
        "knowledge_entries",
        ["owning_character_id"],
    )
    op.create_index(
        "ix_knowledge_entries_access_level",
        "knowledge_entries",
        ["access_level"],
    )
    op.create_index(
        "ix_knowledge_entries_knowledge_type",
        "knowledge_entries",
        ["knowledge_type"],
    )
    op.create_index(
        "ix_knowledge_entries_created_at",
        "knowledge_entries",
        ["created_at"],
    )
    op.create_index(
        "ix_knowledge_entries_updated_at",
        "knowledge_entries",
        ["updated_at"],
    )

    # GIN indexes for array searches (role and character ID filtering)
    op.create_index(
        "ix_knowledge_entries_allowed_roles",
        "knowledge_entries",
        ["allowed_roles"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_knowledge_entries_allowed_character_ids",
        "knowledge_entries",
        ["allowed_character_ids"],
        postgresql_using="gin",
    )

    # Create trigger for automatic updated_at timestamp
    # (Reuses update_updated_at_column() function from migration 0001)
    op.execute(
        """
        CREATE TRIGGER trigger_knowledge_entries_updated_at
        BEFORE UPDATE ON knowledge_entries
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Downgrade database schema - Remove knowledge_entries table."""

    # Drop trigger
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_knowledge_entries_updated_at ON knowledge_entries"
    )

    # Drop indexes (will be dropped automatically with table, but explicit for clarity)
    op.drop_index(
        "ix_knowledge_entries_allowed_character_ids", table_name="knowledge_entries"
    )
    op.drop_index("ix_knowledge_entries_allowed_roles", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_updated_at", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_created_at", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_knowledge_type", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_access_level", table_name="knowledge_entries")
    op.drop_index(
        "ix_knowledge_entries_owning_character_id", table_name="knowledge_entries"
    )

    # Drop table
    op.drop_table("knowledge_entries")
