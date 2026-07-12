from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ProjectDto,
    RevisionDto,
)


@dataclass
class FakeSearchIndexEntry:
    document_id: str
    project_id: str
    title: str
    content: str


class FakeStudioRepositorySearchMixin:
    _search_index: list[FakeSearchIndexEntry]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        raise NotImplementedError

    def search_documents(
        self,
        project_id: str,
        query: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[dict[str, Any]]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        tokens = [token.strip('"') for token in query.split('" "') if token.strip('"')]
        return [
            self._match_entry(entry, tokens)
            for entry in self._search_index
            if self._entry_matches(entry, project_id, tokens)
        ]

    def _index_document(self, document: DocumentDto, revision: RevisionDto) -> None:
        self._delete_search_document_records(document.id)
        self._search_index.append(
            FakeSearchIndexEntry(
                document_id=document.id,
                project_id=document.project_id,
                title=document.title,
                content=revision.content_markdown,
            )
        )

    def _delete_search_document_records(self, document_id: str) -> None:
        self._search_index = [
            entry for entry in self._search_index if entry.document_id != document_id
        ]

    def _entry_matches(
        self,
        entry: FakeSearchIndexEntry,
        project_id: str,
        tokens: list[str],
    ) -> bool:
        if entry.project_id != project_id or not tokens:
            return False
        title_lower = entry.title.casefold()
        content_lower = entry.content.casefold()
        return all(
            token.casefold() in title_lower or token.casefold() in content_lower
            for token in tokens
        )

    def _match_entry(
        self,
        entry: FakeSearchIndexEntry,
        _tokens: list[str],
    ) -> dict[str, Any]:
        excerpt = entry.content[:100]
        return {
            "document_id": entry.document_id,
            "title": entry.title,
            "excerpt": excerpt,
        }
