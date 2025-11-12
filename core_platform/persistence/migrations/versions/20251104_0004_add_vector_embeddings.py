"""Add vector embeddings column for semantic search

Revision ID: 20251104_0004
Revises: 20251104_0003
Create Date: 2025-01-04

Constitution Compliance:
- Article IV (SSOT): PostgreSQL with pgvector extension as single source of truth
- US4: Semantic knowledge retrieval with vector embeddings
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = "20251104_0004"
down_revision = "20251104_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add vector embedding column to knowledge_entries table.
    
    Enables semantic search using PostgreSQL pgvector extension.
    Embedding dimension: 1536 (OpenAI ada-002 standard)
    """
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Add embedding column (1536 dimensions for OpenAI ada-002)
    op.add_column(
        "knowledge_entries",
        sa.Column(
            "embedding",
            sa.types.UserDefinedType("vector(1536)"),
            nullable=True,  # Nullable to support gradual migration
            comment="Vector embedding for semantic search (1536 dimensions)",
        ),
    )
    
    # Create index for vector similarity search using HNSW (Hierarchical Navigable Small World)
    # HNSW is faster than IVFFlat for most use cases
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_embedding_hnsw
        ON knowledge_entries
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    
    # Note: m=16 and ef_construction=64 are balanced defaults
    # - m: max connections per layer (higher = better recall, more memory)
    # - ef_construction: search candidates during index build (higher = better index quality)


def downgrade() -> None:
    """
    Remove vector embedding column and index.
    
    Supports rollback to non-semantic retrieval mode.
    """
    # Drop index first
    op.execute("DROP INDEX IF EXISTS idx_knowledge_entries_embedding_hnsw")
    
    # Drop embedding column
    op.drop_column("knowledge_entries", "embedding")
    
    # Note: We don't drop the vector extension to avoid breaking other potential uses
    # Extension can be manually dropped if needed: DROP EXTENSION vector CASCADE
