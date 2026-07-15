"""Domain exceptions for Novel Studio."""

from __future__ import annotations


class RevisionConflict(RuntimeError):
    """Raised when a client saves against a stale revision."""

    def __init__(self, current_revision_id: str | None) -> None:
        super().__init__("Document changed since the requested base revision.")
        self.current_revision_id = current_revision_id


class SnapshotConflict(RuntimeError):
    """Raised when an immutable snapshot still references a document."""

    def __init__(self) -> None:
        super().__init__("Document is referenced by an immutable snapshot.")


class NotFound(RuntimeError):
    """Raised when a resource is not visible to the active principal."""


class InvalidOperation(RuntimeError):
    """Raised when a valid resource cannot perform an operation."""
