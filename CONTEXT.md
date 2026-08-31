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

**Review dimension**:
A closed category of editorial finding the LLM review may report, such as
pacing or continuity, so the Studio can render findings stably.

**Beat**:
The outline unit a chapter is generated against; each chapter links to the
beat it fulfills.
_Avoid_: scene, plot point

**Volume**:
A container that groups chapters in reading order — the level between the
project and its chapters.
_Avoid_: part, arc, act

**Lore entry**:
A keyword-triggered context unit derived from a character or world document;
injected into generation prompts when its keys appear in recent manuscript
text.
_Avoid_: world info, memory, wiki

**Lifecycle status**:
The lore-entry gate — `draft`, `stable`, or `deprecated`. New lore entries
start at `draft`; only `stable` entries participate in keyword-triggered
injection, so half-written or retired documents never reach a prompt.
_Avoid_: publish state, quality flag

**Canon**:
The author-approved lore a project generates against: the `stable` lore
entries. Pre-gate lore entries were admitted as canon by migration; `draft`
is not-yet-canon and `deprecated` is retired canon.
_Avoid_: truth, official setting

**Resident context**:
The context layer always injected into generation prompts: the outline
position, a rolling summary of prior chapters, and the tail of the most
recent chapter.
_Avoid_: system context, background

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

**Principal**:
The authenticated actor of a request — the Owner.

**Session**:
An authenticated Owner session, identified by an HMAC-derived token.
