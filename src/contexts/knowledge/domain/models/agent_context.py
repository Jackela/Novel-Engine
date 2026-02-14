"""AgentContext aggregate used when assembling knowledge for agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Tuple

from .agent_identity import AgentIdentity
from .knowledge_entry import KnowledgeEntry
from .knowledge_type import KnowledgeType


@dataclass(frozen=True, slots=True)
class AgentContext:
    agent: AgentIdentity
    knowledge_entries: Tuple[KnowledgeEntry, ...] = field(default_factory=tuple)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_number: int = 0

    def __post_init__(self) -> None:
        if self.turn_number < 0:
            raise ValueError("turn_number cannot be negative")
        normalized_entries = tuple(self.knowledge_entries or ())
        object.__setattr__(self, "knowledge_entries", normalized_entries)
        object.__setattr__(self, "retrieved_at", self._normalize_ts(self.retrieved_at))

    @staticmethod
    def _normalize_ts(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def to_llm_prompt_text(self) -> str:
        header = ["# Knowledge Context", f"Agent: {self.agent.character_id}"]
        roles = ", ".join(self.agent.roles) if self.agent.roles else "None"
        header.append(f"Roles: {roles}")
        header.append(f"Turn: {self.turn_number}")

        if not self.knowledge_entries:
            header.append("No knowledge available")
            return "\n".join(header)

        sections: dict[KnowledgeType, list[str]] = {kt: [] for kt in KnowledgeType}
        for entry in self.knowledge_entries:
            sections[entry.knowledge_type].append(entry.content)

        order = [
            KnowledgeType.PROFILE,
            KnowledgeType.OBJECTIVE,
            KnowledgeType.MEMORY,
            KnowledgeType.LORE,
            KnowledgeType.RULES,
        ]
        labels = {
            KnowledgeType.PROFILE: "## Profile",
            KnowledgeType.OBJECTIVE: "## Objective",
            KnowledgeType.MEMORY: "## Memory",
            KnowledgeType.LORE: "## Lore",
            KnowledgeType.RULES: "## Rules",
        }

        body: list[str] = []
        for kind in order:
            entries = sections.get(kind)
            if entries:
                body.append(labels[kind])
                body.append("\n".join(entries))
                body.append("")

        return "\n".join([*header, "", *body]).strip()
