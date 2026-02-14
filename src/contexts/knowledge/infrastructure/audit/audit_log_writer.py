"""
AuditLogWriter

Infrastructure service for writing knowledge entry audit logs.

Constitution Compliance:
- Article VII (Observability): Audit trail for all knowledge mutations
- Article IV (SSOT): PostgreSQL knowledge_audit_log as authoritative audit source
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.types.shared_types import KnowledgeEntryId, UserId

from ...domain.models.knowledge_entry import KnowledgeEntry


class AuditLogWriter:
    """
    Service for writing knowledge entry audit logs.

    Writes audit records to PostgreSQL knowledge_audit_log table for:
    - FR-011: Audit trail requirement
    - Article VII: Observability and compliance

    Audit log includes:
    - Timestamp of change
    - User ID who performed the action
    - Entry ID affected
    - Change type (created, updated, deleted)
    - Snapshot of entry state (for deleted entries)

    Constitution Compliance:
    - Article VII (Observability): Complete audit trail for compliance
    - Article IV (SSOT): PostgreSQL as authoritative audit source
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize audit log writer with database session.

        Args:
            session: AsyncSession from DatabaseManager

        Constitution Compliance:
        - Article V (SOLID): DIP - Depend on AsyncSession abstraction
        """
        self._session = session

    async def log_created(
        self,
        entry: KnowledgeEntry,
        user_id: UserId,
    ) -> None:
        """
        Log knowledge entry creation event.

        Args:
            entry: KnowledgeEntry that was created
            user_id: User ID who created the entry

        Raises:
            AuditLogError: If audit log write fails

        Constitution Compliance:
        - Article VII (Observability): Record creation event
        """
        await self._write_audit_record(
            user_id=user_id,
            entry_id=entry.id,
            change_type="created",
            snapshot=None,  # No snapshot needed for creation
        )

    async def log_updated(
        self,
        entry: KnowledgeEntry,
        user_id: UserId,
    ) -> None:
        """
        Log knowledge entry update event.

        Args:
            entry: KnowledgeEntry that was updated
            user_id: User ID who updated the entry

        Raises:
            AuditLogError: If audit log write fails

        Constitution Compliance:
        - Article VII (Observability): Record update event
        """
        await self._write_audit_record(
            user_id=user_id,
            entry_id=entry.id,
            change_type="updated",
            snapshot=None,  # No snapshot needed for update (entry still exists)
        )

    async def log_deleted(
        self,
        entry: KnowledgeEntry,
        user_id: UserId,
    ) -> None:
        """
        Log knowledge entry deletion event with snapshot.

        Captures full entry state before deletion for audit trail.

        Args:
            entry: KnowledgeEntry that is being deleted
            user_id: User ID who deleted the entry

        Raises:
            AuditLogError: If audit log write fails

        Constitution Compliance:
        - Article VII (Observability): Record deletion event with snapshot
        """
        # Create snapshot of entry state before deletion
        snapshot = {
            "id": entry.id,
            "content": entry.content,
            "knowledge_type": entry.knowledge_type.value,
            "owning_character_id": entry.owning_character_id,
            "access_level": entry.access_control.access_level.value,
            "allowed_roles": list(entry.access_control.allowed_roles),
            "allowed_character_ids": list(entry.access_control.allowed_character_ids),
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "created_by": entry.created_by,
        }

        await self._write_audit_record(
            user_id=user_id,
            entry_id=entry.id,
            change_type="deleted",
            snapshot=snapshot,
        )

    async def _write_audit_record(
        self,
        user_id: UserId,
        entry_id: KnowledgeEntryId,
        change_type: str,
        snapshot: Dict[str, Any] | None,
    ) -> None:
        """
        Write audit record to knowledge_audit_log table.

        Args:
            user_id: User ID who performed the action
            entry_id: Knowledge entry ID affected
            change_type: Type of change (created, updated, deleted)
            snapshot: Optional snapshot of entry state (for deleted entries)

        Raises:
            AuditLogError: If audit log write fails

        Constitution Compliance:
        - Article IV (SSOT): PostgreSQL audit log as authoritative source
        - Article VII (Observability): Complete audit trail
        """
        from uuid import UUID

        from sqlalchemy import text

        # INSERT audit record
        insert_sql = text("""
            INSERT INTO knowledge_audit_log (
                timestamp, user_id, entry_id, change_type, snapshot
            ) VALUES (
                :timestamp, :user_id, :entry_id, :change_type, :snapshot
            )
        """)

        # Execute insert
        await self._session.execute(
            insert_sql,
            {
                "timestamp": datetime.now(timezone.utc),
                "user_id": user_id,
                "entry_id": UUID(entry_id),
                "change_type": change_type,
                "snapshot": json.dumps(snapshot) if snapshot else None,
            },
        )

        # Commit handled by session context manager
