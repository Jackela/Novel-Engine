"""Value object capturing the identity of an agent requesting knowledge."""

from __future__ import annotations

from dataclasses import dataclass


def _normalize_roles(roles: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(r.strip().lower() for r in roles if r))


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    character_id: str
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.character_id:
            raise ValueError("character_id is required for AgentIdentity")
        normalized = _normalize_roles(self.roles)
        object.__setattr__(self, "roles", normalized)

    def has_role(self, role: str) -> bool:
        if not role:
            return False
        return role.strip().lower() in self.roles
