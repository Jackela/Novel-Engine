# Design

## Product Boundary

Novel Studio is a self-hosted, single-owner novel writing IDE. A temporary
guest sandbox is available for evaluation and expires after 24 hours. Real-time
collaboration, cloud sync, community publishing, and PDF layout are out of
scope.

## Authority Model

- `pyproject.toml` owns the product version.
- `openspec/specs/novel-studio/spec.md` owns product behavior.
- SQLite owns all current authoring content and immutable revision history.
- Markdown is the canonical document syntax, not the persistence authority.
- OpenAPI, UI version labels, logs, monitoring metadata, README, and release
  artifacts are derived surfaces.

## Persistence

Use SQLAlchemy 2 and Alembic against `data/novel-engine.sqlite3`. Enable foreign
keys and WAL. Core tables are owners, sessions, projects, documents,
document_revisions, document_links, project_snapshots, snapshot_documents,
jobs, job_events, reviews, review_issues, exports, and usage_events.

Every document save inserts a revision and atomically advances
`documents.current_revision_id`. The caller supplies `base_revision_id`; a
stale base returns HTTP 409. Restoring a historical revision creates a new
revision instead of mutating history.

FTS5 indexes current document title and Markdown content. Reviews and exports
first capture a project snapshot containing exact document revision IDs.

## Runtime

The FastAPI process serves the API and built SPA. A persistent SQLite job queue
stores status and events. On startup, queued work remains retryable and
lease-less running work becomes interrupted. The single-node deployment may
execute jobs in-process, but job state must not be process-local.

The owner account is created during first-run setup. Guest sessions and their
projects receive `expires_at`; cleanup runs at startup and hourly.

## Studio

The app opens at setup or project library. Project routes expose Manuscript,
Outline, Characters, World, Review, History, Export, and Settings. CodeMirror 6
edits Markdown and autosaves after 1.5 seconds. The shell follows the visual
reference in `docs/design/novel-studio-0.3-concept.png`.

AI operations create proposals containing a replacement Markdown payload and
diff metadata. Accepting a proposal performs the normal conflict-checked save.
Review never mutates author content. Batch generation is capped at three
chapters.

## Legacy Import

The importer previews `story.yaml`, manuscript chapters, sidecars, reviews, and
run evidence. An import hash makes repeated imports idempotent. Source
directories are never modified.

## Deployment

A single image builds the Vite app and Python service. Compose mounts `/app/data`.
Startup backs up an existing database before migrations, applies migrations,
then starts the API. Operational CLI commands are `serve`, `import`, `backup`,
and `doctor`.
