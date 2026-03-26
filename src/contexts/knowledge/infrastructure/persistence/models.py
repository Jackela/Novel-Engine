"""SQLAlchemy models for knowledge context persistence.

This module defines the database schema for knowledge base and document storage.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class KnowledgeBaseModel(Base):  # type: ignore[misc,valid-type]
    """SQLAlchemy model for knowledge_base table.

    Represents a knowledge base aggregate that manages document collections
    and provides vector search capabilities.
    """

    __tablename__ = "knowledge_bases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    owner_id = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    project_id = Column(String(255), nullable=True, index=True)
    embedding_model = Column(
        String(100), nullable=False, default="text-embedding-3-small"
    )
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationship to documents
    documents = relationship(
        "DocumentModel",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBaseModel(id={self.id}, name={self.name})>"


class DocumentModel(Base):  # type: ignore[misc,valid-type]
    """SQLAlchemy model for document table.

    Represents a document entity within a knowledge base.
    Documents can be chunked for better retrieval and support
    multiple content types.
    """

    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    knowledge_base_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default="text")
    source = Column(String(1000), nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    chunks = Column(JSON, nullable=False, default=list)
    embedding = Column(JSON, nullable=True)
    is_indexed = Column(Boolean, nullable=False, default=False)
    indexed_at = Column(DateTime, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationship to knowledge base
    knowledge_base = relationship("KnowledgeBaseModel", back_populates="documents")

    def __repr__(self) -> str:
        return f"<DocumentModel(id={self.id}, title={self.title})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": str(self.id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "source": self.source,
            "tags": self.tags,
            "chunks": self.chunks,
            "is_indexed": self.is_indexed,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "chunk_count": self.chunk_count,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.meta_data,
        }
