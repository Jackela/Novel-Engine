"""Add stable per-document revision numbers."""

from __future__ import annotations

from collections import defaultdict

import sqlalchemy as sa
from alembic import op

revision = "0002_stable_revision_numbers"
down_revision = "0001_novel_studio_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("document_revisions")
    }
    if "revision_number" in columns:
        return

    op.add_column(
        "document_revisions",
        sa.Column(
            "revision_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    rows = bind.execute(
        sa.text(
            "SELECT id, document_id, parent_revision_id "
            "FROM document_revisions"
        )
    ).mappings()
    by_document: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    for row in rows:
        by_document[str(row["document_id"])].append(dict(row))

    for document_rows in by_document.values():
        children = {
            row["parent_revision_id"]: row["id"]
            for row in document_rows
            if row["parent_revision_id"] is not None
        }
        current = next(
            row["id"]
            for row in document_rows
            if row["parent_revision_id"] is None
        )
        number = 1
        while current is not None:
            bind.execute(
                sa.text(
                    "UPDATE document_revisions "
                    "SET revision_number = :number WHERE id = :revision_id"
                ),
                {"number": number, "revision_id": current},
            )
            current = children.get(current)
            number += 1

    op.create_index(
        "uq_document_revision_number",
        "document_revisions",
        ["document_id", "revision_number"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("document_revisions")
    }
    if "revision_number" not in columns:
        return
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("document_revisions")
    }
    if "uq_document_revision_number" in indexes:
        op.drop_index(
            "uq_document_revision_number",
            table_name="document_revisions",
        )
    with op.batch_alter_table("document_revisions") as batch_op:
        batch_op.drop_column("revision_number")
