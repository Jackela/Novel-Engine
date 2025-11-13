"""KnowledgeEntry aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from contexts.knowledge.domain.events.knowledge_entry_updated import (
    KnowledgeEntryUpdated,
)

from .access_control_rule import AccessControlRule
from .agent_identity import AgentIdentity
from .knowledge_type import KnowledgeType


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_content(content: str) -> str:
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")
    return content


@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    id: str
    content: str
    knowledge_type: KnowledgeType
    owning_character_id: Optional[str]
    access_control: AccessControlRule
    created_at: datetime
    updated_at: datetime
    created_by: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("KnowledgeEntry.id is required")
        _validate_content(self.content)
        if not isinstance(self.knowledge_type, KnowledgeType):
            raise ValueError("knowledge_type must be a KnowledgeType enum value")
        if not self.created_by:
            raise ValueError("created_by is required")
        created_at = _normalize_timestamp(self.created_at)
        updated_at = _normalize_timestamp(self.updated_at)
        if updated_at < created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "content", self.content.strip())

    def update_content(self, new_content: str, updated_by: str) -> KnowledgeEntryUpdated:
        _validate_content(new_content)
        if not updated_by:
            raise ValueError("updated_by is required")
        timestamp = datetime.now(timezone.utc)
        object.__setattr__(self, "content", new_content)
        object.__setattr__(self, "updated_at", timestamp)
        return KnowledgeEntryUpdated(
            entry_id=self.id,
            updated_by=updated_by,
            timestamp=timestamp,
        )

    def is_accessible_by(self, agent: AgentIdentity) -> bool:
        return self.access_control.permits(agent)
