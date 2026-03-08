"""
Chat Session SQLAlchemy Model (PREP-013)

Provides persistence for chat sessions and messages using SQLite.
This allows chat history to persist across server restarts.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    """Base class for chat session models."""

    pass


class ChatSessionORM(Base):
    """
    SQLAlchemy model for chat sessions.

    A session represents a conversation between a user and the AI.
    """

    __tablename__ = "chat_sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    session_metadata = Column(JSON, nullable=True)  # Optional session metadata

    # Relationship to messages
    messages = relationship(
        "ChatMessageORM", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatSessionORM(id={self.session_id}, messages={len(self.messages)})>"


class ChatMessageORM(Base):
    """
    SQLAlchemy model for chat messages.

    Each message belongs to a session and has a role (user/assistant).
    """

    __tablename__ = "chat_messages"

    message_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36), ForeignKey("chat_sessions.session_id"), nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to session
    session = relationship("ChatSessionORM", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessageORM(id={self.message_id}, role={self.role})>"


def get_chat_db_path() -> str:
    """Get the path to the chat database file."""
    import os

    # Use data directory for persistence
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "chat_sessions.db")


# Create engine and session factory
_engine = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Any:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        db_path = get_chat_db_path()
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


def get_db_session() -> Session:
    """Get a database session."""
    session: Session = get_session_factory()()
    return session
