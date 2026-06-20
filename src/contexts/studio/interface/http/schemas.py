from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.contexts.studio.domain.types import DocumentKind, ExportFormat


class OwnerSetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=10_000)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=10_000)
    settings: dict[str, Any] | None = None


class DocumentCreateRequest(BaseModel):
    kind: DocumentKind
    title: str = Field(min_length=1, max_length=240)
    content_markdown: str = ""
    position: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSaveRequest(BaseModel):
    content_markdown: str
    base_revision_id: str | None
    title: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRestoreRequest(BaseModel):
    base_revision_id: str | None


class ReorderRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1)


class AIProposalRequest(BaseModel):
    operation: Literal["continue", "rewrite", "generate"]
    instruction: str = Field(default="", max_length=10_000)
    provider: Literal["mock", "dashscope", "openai_compatible"] = "mock"


class ExportRequest(BaseModel):
    format: ExportFormat


class LegacyPathRequest(BaseModel):
    source: str = Field(
        min_length=1,
        max_length=240,
        description="Workspace directory name under data/imports.",
    )


class SnapshotRequest(BaseModel):
    reason: str = Field(default="manual", min_length=1, max_length=48)
