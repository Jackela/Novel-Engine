"""SQLAlchemy models for narrative context persistence.

This module defines the database schema for stories, chapters, and scenes.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
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


class StoryModel(Base):  # type: ignore[misc,valid-type]
    """SQLAlchemy model for stories table.

    Represents a story aggregate that manages chapters
    and provides narrative structure.
    """

    __tablename__ = "stories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(200), nullable=False, index=True)
    genre = Column(String(50), nullable=False)
    author_id = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft")
    current_chapter_id = Column(String(36), nullable=True)
    target_audience = Column(String(100), nullable=True)
    themes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationship to chapters
    chapters = relationship(
        "ChapterModel",
        back_populates="story",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChapterModel.chapter_number",
    )

    def __repr__(self) -> str:
        return f"<StoryModel(id={self.id}, title={self.title})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": str(self.id),
            "title": self.title,
            "genre": self.genre,
            "author_id": self.author_id,
            "status": self.status,
            "current_chapter_id": self.current_chapter_id,
            "target_audience": self.target_audience,
            "themes": self.themes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.meta_data,
        }


class ChapterModel(Base):  # type: ignore[misc,valid-type]
    """SQLAlchemy model for chapters table.

    Represents a chapter entity within a story.
    Chapters organize the narrative into major sections.
    """

    __tablename__ = "chapters"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    story_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationship to story
    story = relationship("StoryModel", back_populates="chapters")

    # Relationship to scenes
    scenes = relationship(
        "SceneModel",
        back_populates="chapter",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SceneModel.scene_number",
    )

    def __repr__(self) -> str:
        return (
            f"<ChapterModel(id={self.id}, "
            f"chapter_number={self.chapter_number}, title={self.title})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": str(self.id),
            "story_id": str(self.story_id),
            "chapter_number": self.chapter_number,
            "title": self.title,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.meta_data,
        }


class SceneModel(Base):  # type: ignore[misc,valid-type]
    """SQLAlchemy model for scenes table.

    Represents a scene entity within a chapter.
    Scenes are the core narrative units that contain content.
    """

    __tablename__ = "scenes"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    chapter_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    scene_type = Column(String(50), nullable=False, default="narrative")
    choices = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column("metadata", JSON, nullable=False, default=dict)

    # Relationship to chapter
    chapter = relationship("ChapterModel", back_populates="scenes")

    def __repr__(self) -> str:
        return (
            f"<SceneModel(id={self.id}, "
            f"scene_number={self.scene_number}, title={self.title})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": str(self.id),
            "chapter_id": str(self.chapter_id),
            "scene_number": self.scene_number,
            "title": self.title,
            "content": self.content,
            "scene_type": self.scene_type,
            "choices": self.choices,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.meta_data,
        }
