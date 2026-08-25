# Novel Engine

Novel Engine is a self-hosted, single-author novel writing studio. SQLite is
the content authority and Markdown is the document syntax.

## Language

### Product and architecture

**Novel Engine**:
The product and the repository. One name across code, tooling, CLI, and
user-facing surfaces.
_Avoid_: Novel Studio (removed; see openspec change 2026-08-17-rename-novel-engine)

**Context**:
A bounded context owning one capability area — `studio` (authoring) or `ai`
(text generation). In architecture discussion, "context" means this and
nothing else.

### Authoring core

**Project**:
A novel workspace holding documents, owned by the Owner.

**Document**:
A Markdown unit inside a project — chapter, character, world, or similar.

**Draft**:
The in-editor, not-yet-saved state of a document in the UI.
_Avoid_: calling an unsaved draft a "revision"

**Revision**:
The immutable accepted state of a document. A conflict-checked save creates a
new revision atomically.
_Avoid_: version, history entry

**Snapshot**:
An immutable, complete revision set of a project. Review and export read
snapshots, never live documents.
_Avoid_: backup, checkpoint

**Proposal**:
An AI-suggested change to a document. Applied only when the author explicitly
accepts it.
_Avoid_: suggestion, AI edit

**Review**:
The author's accept/reject pass over proposals, bound to a snapshot.

**Job**:
A durable operation with explicit state, executed synchronously inside the
request and recorded with its events, retryable.

**Export**:
A deterministic Markdown, DOCX, or EPUB artifact written from a snapshot.

**Import**:
The one-time, read-only ingestion of a legacy file workspace.

### Actors and access

**Owner**:
The single local author account; owns every project.

**Guest**:
A temporary (24-hour) principal, isolated from Owner data.

**Principal**:
The authenticated actor of a request — Owner or Guest.

**Session**:
An authenticated Owner or Guest session, identified by an HMAC-derived token.
