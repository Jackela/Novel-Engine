"""Create knowledge_audit_log table

Revision ID: 0003
Revises: 0002
Create Date: 2025-11-04 00:01:00.000000

Feature: 001-dynamic-agent-knowledge
Purpose: Create knowledge_audit_log table for audit trail (FR-011)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - Create knowledge_audit_log table."""

    # Create knowledge_audit_log table
    op.create_table(
        "knowledge_audit_log",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            autoincrement=True,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "snapshot",
            postgresql.JSONB(),
            nullable=True,  # Snapshot of entry state for deleted entries
        ),
        sa.PrimaryKeyConstraint("id"),
        # Foreign key to knowledge_entries (with ON DELETE CASCADE)
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["knowledge_entries.id"],
            name="fk_knowledge_audit_log_entry_id",
            ondelete="CASCADE",
        ),
        # Change type enum constraint
        sa.CheckConstraint(
            "change_type IN ('created', 'updated', 'deleted')",
            name="ck_knowledge_audit_log_valid_change_type",
        ),
    )

    # Create indexes for audit queries
    op.create_index(
        "ix_knowledge_audit_log_entry_id",
        "knowledge_audit_log",
        ["entry_id"],
    )
    op.create_index(
        "ix_knowledge_audit_log_timestamp",
        "knowledge_audit_log",
        ["timestamp"],
    )
    op.create_index(
        "ix_knowledge_audit_log_user_id",
        "knowledge_audit_log",
        ["user_id"],
    )
    op.create_index(
        "ix_knowledge_audit_log_change_type",
        "knowledge_audit_log",
        ["change_type"],
    )


def downgrade() -> None:
    """Downgrade database schema - Remove knowledge_audit_log table."""

    # Drop indexes
    op.drop_index("ix_knowledge_audit_log_change_type", table_name="knowledge_audit_log")
    op.drop_index("ix_knowledge_audit_log_user_id", table_name="knowledge_audit_log")
    op.drop_index("ix_knowledge_audit_log_timestamp", table_name="knowledge_audit_log")
    op.drop_index("ix_knowledge_audit_log_entry_id", table_name="knowledge_audit_log")

    # Drop table (foreign key constraint will be dropped automatically)
    op.drop_table("knowledge_audit_log")
