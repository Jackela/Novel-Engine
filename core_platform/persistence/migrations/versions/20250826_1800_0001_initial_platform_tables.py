"""Initial platform tables

Revision ID: 0001
Revises:
Create Date: 2025-08-26 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - Create initial platform tables."""

    # Create outbox_events table for outbox pattern
    op.create_table(
        "outbox_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
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
        # Event identification
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("event_version", sa.String(length=20), nullable=False, default="1.0.0"),
        # Event data
        sa.Column("event_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        # Event metadata
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Processing status
        sa.Column("processed", sa.Boolean(), nullable=False, default=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Publishing details
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("partition_key", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )

    # Create indexes for outbox_events
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_processed", "outbox_events", ["processed"])
    op.create_index("ix_outbox_events_correlation_id", "outbox_events", ["correlation_id"])
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"])
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])

    # Create event_store table for event sourcing
    op.create_table(
        "event_store",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
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
        # Stream identification
        sa.Column("stream_id", sa.String(length=200), nullable=False),
        sa.Column("stream_type", sa.String(length=100), nullable=False),
        # Event identification
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("event_version", sa.String(length=20), nullable=False),
        # Event sequencing
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("global_sequence", sa.BigInteger(), nullable=False),
        # Event data
        sa.Column("event_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("event_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        # Event context
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("global_sequence"),
    )

    # Create indexes for event_store
    op.create_index("ix_event_store_stream_id", "event_store", ["stream_id"])
    op.create_index(
        "ix_event_store_stream_id_sequence",
        "event_store",
        ["stream_id", "sequence_number"],
    )
    op.create_index("ix_event_store_correlation_id", "event_store", ["correlation_id"])
    op.create_index("ix_event_store_event_type", "event_store", ["event_type"])
    op.create_index("ix_event_store_global_sequence", "event_store", ["global_sequence"])
    op.create_index("ix_event_store_created_at", "event_store", ["created_at"])

    # Create sequence for global event ordering
    op.execute("CREATE SEQUENCE IF NOT EXISTS event_store_global_sequence_seq")

    # Create function to auto-set global sequence
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_event_store_global_sequence()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.global_sequence IS NULL THEN
                NEW.global_sequence := nextval('event_store_global_sequence_seq');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger for auto-setting global sequence
    op.execute(
        """
        CREATE TRIGGER trigger_set_event_store_global_sequence
        BEFORE INSERT ON event_store
        FOR EACH ROW
        EXECUTE FUNCTION set_event_store_global_sequence();
    """
    )

    # Create updated_at trigger function for automatic timestamp updates
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create updated_at triggers for both tables
    op.execute(
        """
        CREATE TRIGGER trigger_outbox_events_updated_at
        BEFORE UPDATE ON outbox_events
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    )

    op.execute(
        """
        CREATE TRIGGER trigger_event_store_updated_at
        BEFORE UPDATE ON event_store
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    )


def downgrade() -> None:
    """Downgrade database schema - Remove initial platform tables."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_event_store_updated_at ON event_store")
    op.execute("DROP TRIGGER IF EXISTS trigger_outbox_events_updated_at ON outbox_events")
    op.execute("DROP TRIGGER IF EXISTS trigger_set_event_store_global_sequence ON event_store")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP FUNCTION IF EXISTS set_event_store_global_sequence()")

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS event_store_global_sequence_seq")

    # Drop indexes (will be dropped automatically with tables, but explicit for clarity)
    op.drop_index("ix_event_store_created_at", table_name="event_store")
    op.drop_index("ix_event_store_global_sequence", table_name="event_store")
    op.drop_index("ix_event_store_event_type", table_name="event_store")
    op.drop_index("ix_event_store_correlation_id", table_name="event_store")
    op.drop_index("ix_event_store_stream_id_sequence", table_name="event_store")
    op.drop_index("ix_event_store_stream_id", table_name="event_store")

    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_correlation_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_processed", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")

    # Drop tables
    op.drop_table("event_store")
    op.drop_table("outbox_events")
