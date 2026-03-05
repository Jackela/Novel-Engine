"""
Chat Session Repository (PREP-013)

Repository for persisting and retrieving chat sessions and messages.
Provides an abstraction layer over the SQLAlchemy models.
"""

import structlog
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.chat_session import (
    ChatMessageORM,
    ChatSessionORM,
    get_db_session,
)

logger = structlog.get_logger(__name__)


@dataclass
class ChatMessage:
    """Domain object for a chat message."""

    role: str  # 'user' or 'assistant'
    content: str
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ChatSession:
    """Domain object for a chat session."""

    session_id: str
    messages: List[ChatMessage]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatSessionRepository:
    """
    Repository for chat session persistence.

    Provides methods for CRUD operations on chat sessions and messages.
    Uses SQLite for persistence via SQLAlchemy.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initialize the repository.

        Args:
            session: Optional SQLAlchemy session. If not provided, a new session
                    will be created for each operation.
        """
        self._session = session
        self.logger = logger.getChild(self.__class__.__name__)

    def _get_session(self) -> Session:
        """Get a database session."""
        if self._session:
            return self._session
        return get_db_session()

    def get_session(self, session_id: str) -> List[ChatMessage]:
        """
        Get all messages for a chat session.

        Args:
            session_id: The unique identifier for the session

        Returns:
            List of ChatMessage objects in chronological order
        """
        try:
            with self._get_session() as session:
                messages = (
                    session.query(ChatMessageORM)
                    .filter(ChatMessageORM.session_id == session_id)
                    .order_by(ChatMessageORM.created_at)
                    .all()
                )
                return [
                    ChatMessage(
                        role=msg.role,  # type: ignore[arg-type]
                        content=msg.content,  # type: ignore[arg-type]
                        created_at=msg.created_at,  # type: ignore[arg-type]
                    )
                    for msg in messages
                ]
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting session {session_id}: {e}")
            return []

    def get_session_detail(self, session_id: str) -> Optional[ChatSession]:
        """
        Get session details including metadata.

        Args:
            session_id: The unique identifier for the session

        Returns:
            ChatSession object or None if not found
        """
        try:
            with self._get_session() as session:
                session_orm = (
                    session.query(ChatSessionORM)
                    .filter(ChatSessionORM.session_id == session_id)
                    .first()
                )
                if not session_orm:
                    return None

                messages = [
                    ChatMessage(
                        role=str(msg.role),
                        content=str(msg.content),
                        created_at=msg.created_at,
                    )
                    for msg in session_orm.messages
                ]

                return ChatSession(
                    session_id=str(session_orm.session_id),
                    messages=messages,
                    created_at=session_orm.created_at,  # type: ignore[arg-type]
                    updated_at=session_orm.updated_at,  # type: ignore[arg-type]
                )
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting session detail {session_id}: {e}")
            return None

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """
        Add a message to a session.

        Creates the session if it doesn't exist.

        Args:
            session_id: The unique identifier for the session
            message: The message to add
        """
        try:
            with self._get_session() as session:
                # Ensure session exists
                session_orm = (
                    session.query(ChatSessionORM)
                    .filter(ChatSessionORM.session_id == session_id)
                    .first()
                )

                if not session_orm:
                    session_orm = ChatSessionORM(session_id=session_id)
                    session.add(session_orm)

                # Add message
                message_orm = ChatMessageORM(
                    session_id=session_id,
                    role=message.role,
                    content=message.content,
                )
                session.add(message_orm)
                session.commit()

        except SQLAlchemyError as e:
            self.logger.error(f"Error adding message to session {session_id}: {e}")
            if session:
                session.rollback()

    def clear_session(self, session_id: str) -> None:
        """
        Clear all messages for a session.

        Args:
            session_id: The unique identifier for the session
        """
        try:
            with self._get_session() as session:
                session.query(ChatMessageORM).filter(
                    ChatMessageORM.session_id == session_id
                ).delete()
                session.query(ChatSessionORM).filter(
                    ChatSessionORM.session_id == session_id
                ).delete()
                session.commit()

        except SQLAlchemyError as e:
            self.logger.error(f"Error clearing session {session_id}: {e}")
            if session:
                session.rollback()

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[ChatSession]:
        """
        List all chat sessions.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of ChatSession objects (without messages)
        """
        try:
            with self._get_session() as session:
                sessions = (
                    session.query(ChatSessionORM)
                    .order_by(ChatSessionORM.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )

                return [
                    ChatSession(
                        session_id=s.session_id,  # type: ignore[arg-type]
                        messages=[],  # Don't load messages for list view
                        created_at=s.created_at,  # type: ignore[arg-type]
                        updated_at=s.updated_at,  # type: ignore[arg-type]
                    )
                    for s in sessions
                ]
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing sessions: {e}")
            return []

    def get_session_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessage]:
        """
        Get messages for a session with pagination.

        Args:
            session_id: The unique identifier for the session
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of ChatMessage objects in chronological order
        """
        try:
            with self._get_session() as session:
                messages = (
                    session.query(ChatMessageORM)
                    .filter(ChatMessageORM.session_id == session_id)
                    .order_by(ChatMessageORM.created_at)
                    .limit(limit)
                    .offset(offset)
                    .all()
                )

                return [
                    ChatMessage(
                        role=msg.role,  # type: ignore[arg-type]
                        content=msg.content,  # type: ignore[arg-type]
                        created_at=msg.created_at,  # type: ignore[arg-type]
                    )
                    for msg in messages
                ]
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
