"""Add a CSRF token column to studio sessions."""

from __future__ import annotations

import secrets

import sqlalchemy as sa
from alembic import op

revision = "0003_add_csrf_token_to_sessions"
down_revision = "0002_stable_revision_numbers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("sessions")}
    if "csrf_token" in columns:
        return

    op.add_column(
        "sessions",
        sa.Column("csrf_token", sa.String(length=64), nullable=True),
    )

    rows = bind.execute(
        sa.text("SELECT id FROM sessions WHERE csrf_token IS NULL")
    ).mappings()
    for row in rows:
        bind.execute(
            sa.text("UPDATE sessions SET csrf_token = :token WHERE id = :id"),
            {"token": secrets.token_urlsafe(32), "id": row["id"]},
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("sessions")}
    if "csrf_token" not in columns:
        return
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("csrf_token")
