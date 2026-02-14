"""Access control value object for knowledge entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, assert_never

from .access_level import AccessLevel
from .agent_identity import AgentIdentity


def _normalize(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(v.strip().lower() for v in values if v))


@dataclass(frozen=True, slots=True)
class AccessControlRule:
    access_level: AccessLevel
    allowed_roles: Tuple[str, ...] = ()
    allowed_character_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_roles", _normalize(self.allowed_roles))
        object.__setattr__(
            self,
            "allowed_character_ids",
            tuple(v.strip() for v in self.allowed_character_ids if v),
        )
        if self.access_level == AccessLevel.ROLE_BASED and not self.allowed_roles:
            raise ValueError("ROLE_BASED access requires at least one allowed role")
        if (
            self.access_level == AccessLevel.CHARACTER_SPECIFIC
            and not self.allowed_character_ids
        ):
            raise ValueError(
                "CHARACTER_SPECIFIC access requires at least one allowed character ID"
            )

    def permits(self, agent: AgentIdentity) -> bool:
        if self.access_level == AccessLevel.PUBLIC:
            return True
        if self.access_level == AccessLevel.ROLE_BASED:
            return any(agent.has_role(role) for role in self.allowed_roles)
        if self.access_level == AccessLevel.CHARACTER_SPECIFIC:
            return agent.character_id in self.allowed_character_ids
        assert_never(self.access_level)
