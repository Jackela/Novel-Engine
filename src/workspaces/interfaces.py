from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Workspace:
    id: str
    root: Path


class WorkspaceStore(ABC):
    @abstractmethod
    def create(self) -> Workspace:
        raise NotImplementedError

    @abstractmethod
    def get_or_create(self, workspace_id: str) -> Workspace:
        raise NotImplementedError

    @abstractmethod
    def export_zip(self, workspace_id: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def import_zip(self, zip_bytes: bytes) -> Workspace:
        raise NotImplementedError


class CharacterStore(ABC):
    @abstractmethod
    def list_ids(self, workspace_id: str) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get(self, workspace_id: str, character_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, workspace_id: str, character_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(
        self, workspace_id: str, character_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, workspace_id: str, character_id: str) -> None:
        raise NotImplementedError


class RunStore(ABC):
    @abstractmethod
    def list_ids(self, workspace_id: str) -> List[str]:
        raise NotImplementedError
