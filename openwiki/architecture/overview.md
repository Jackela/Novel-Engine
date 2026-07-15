# Architecture overview

Novel Studio is a FastAPI application with a React frontend; its persistence layer uses synchronous SQLAlchemy sessions. The Studio domain is organized into domain, application, infrastructure, and HTTP-interface layers; import-linter makes those boundaries executable rather than conventional (`.importlinter`).

## Runtime composition and lifecycle

`create_application()` builds a `NovelStudioApplication`, resolves settings, creates (or accepts) a `StudioRuntime`, and attaches both the runtime and its `StudioStore` to that specific FastAPI application's state (`src/apps/api/main.py`, `src/apps/api/runtime.py`, `src/contexts/studio/interface/http/dependencies.py`). Request dependencies retrieve the store from `request.app`; there is no module-global runtime.

`StudioRuntime` owns:

- a `StudioStore`, composed with `SqlAlchemyStudioRepository`, the configured data directory, the injected `SECURITY_SECRET_KEY`, an AI-provider factory, and the registered export writers; and
- a `StudioDatabase`, which owns the SQLAlchemy engine and session factory (`src/apps/api/runtime.py`, `src/contexts/studio/infrastructure/database.py`).

The FastAPI lifespan initializes the database without creating a backup or schema, recovers interrupted jobs through database initialization, removes expired guest sessions once at startup, then starts an hourly guest-cleanup loop. Shutdown cancels that task group and disposes the runtime database in `finally` (`src/apps/api/runtime.py`). Blocking database and cleanup work is dispatched from the lifespan through AnyIO worker threads; the persistence implementation itself uses synchronous SQLAlchemy sessions.

The CLI deliberately has a separate, short-lived `CliRuntime`. Each command creates it through `_configured_runtime()` and disposes its database on context exit. Commands that need an operational store run database backup/migrations before their work; `serve` releases this CLI runtime before Uvicorn calls the FastAPI application factory (`src/apps/cli/novel_engine.py`).

First-owner setup is the unauthenticated bootstrap write before a session exists. The HTTP boundary compares every supplied `Origin` and `Referer` with the serving origin or an explicit configured non-wildcard CORS origin (or a supported localhost/127.0.0.1 port wildcard), while requests without browser origin metadata remain available to local bootstrap clients. On SQLite, owner creation starts `BEGIN IMMEDIATE`, rechecks the Owner count inside that transaction, and raises the existing domain `InvalidOperation` when another request won the race; the HTTP decorator exposes that loser as a controlled `422` (`src/contexts/studio/interface/http/session_router.py`, `src/contexts/studio/infrastructure/repository/auth.py`, `src/contexts/studio/interface/http/errors.py`, `src/apps/api/middleware/cors.py`). Login and guest cookies are `Secure` in production and staging; local HTTP development intentionally leaves that attribute off. Session token lookup hashes are HMAC-SHA256 values keyed by `SECURITY_SECRET_KEY`; the registry injects this secret into `AuthService`, and rotating it deliberately invalidates all existing sessions without changing cookie, API, or CSRF shapes (`src/contexts/studio/domain/utils.py`, `src/contexts/studio/application/services/auth_service.py`, `src/contexts/studio/application/services/facade_base.py`).

## Enforced dependency direction

The import contracts forbid domain modules from importing application or infrastructure code, application modules from importing infrastructure, contexts from importing apps, shared code from importing contexts, and interface modules from importing infrastructure (`.importlinter`). Infrastructure is therefore supplied at composition points—such as the API runtime or CLI runtime—rather than selected by application services.

The application depends on the `StudioRepository` protocol and its DTO/core-port sections, not the SQLAlchemy repository. The port covers ownership and sessions, projects/documents/revisions, snapshots, reviews, exports, jobs, and usage events (`src/contexts/studio/application/ports/studio_repository.py`, `src/contexts/studio/application/ports/studio_repository_sections.py`). `SqlAlchemyStudioRepository` is the runtime-provided implementation (`src/apps/api/runtime.py`, `src/apps/cli/novel_engine.py`).

## Documents, revisions, and snapshots

Documents retain a `current_revision_id`; revision rows carry a parent revision ID, monotonically unique revision number per document, Markdown content, metadata, source, and creation time (`src/contexts/studio/infrastructure/models.py`). Saving a document delegates to the repository with a caller-supplied base revision ID; an out-of-date base is surfaced as a `RevisionConflict` by `DocumentService` (`src/contexts/studio/application/services/document_service.py`).

History is append-only in use: revision lookup/listing reads `DocumentRevision` rows, while a restore reads the selected historical revision and calls the normal save path with `source="restore"` and `restored_from` metadata. Restore therefore creates a new current revision rather than overwriting the historical revision (`src/contexts/studio/application/services/revision_service.py`, `src/contexts/studio/infrastructure/repository/document_revisions.py`).

A project snapshot records the exact revision ID currently selected for each document that has one, together with its position. Snapshot reads join those stored IDs back to documents and revisions, so later edits do not alter snapshot content (`src/contexts/studio/infrastructure/repository/snapshot.py`, `src/contexts/studio/infrastructure/models.py`).

The `SnapshotDocument.revision_id` foreign key uses `ON DELETE RESTRICT`, preserving every revision referenced by an export or review snapshot. Before deleting a document, the repository checks for any snapshot reference and raises the domain `SnapshotConflict`; the HTTP error decorator maps that expected conflict to `409` while leaving the database restriction intact. A rejected delete leaves the document, snapshots, and revisions untouched (`src/contexts/studio/infrastructure/models.py`, `src/contexts/studio/infrastructure/repository/document.py`, `src/contexts/studio/domain/exceptions.py`, `src/contexts/studio/interface/http/errors.py`).

Reviews are snapshot-bound as well as exports: review creation writes a `ProjectSnapshot(reason="review")`, stores its revision IDs on `SnapshotDocument`, associates the snapshot with the review, and evaluates issues from that frozen set. Later document edits therefore do not rewrite historical review findings (`src/contexts/studio/infrastructure/repository/review.py`, `openspec/specs/novel-studio/spec.md`).

The route-level Studio keeps these concerns separate: `/history` exposes revision listing and restore only, while `/export` exposes format selection, export pending/failure state, and recent export links. The top bar no longer duplicates Review, Export, or Settings actions; `StudioInspector` selects the surface from the route and uses the same API client and store contracts as the other panels (`frontend/src/features/studio/StudioPage.tsx`, `StudioTopbar.tsx`, `StudioInspector.tsx`).

## Export flow

`ExportService` compares the current `{document_id: current_revision_id}` mapping with the newest export snapshot. It reuses that snapshot only when the mappings match; otherwise it creates a new `reason="export"` snapshot. It exports only snapshot documents whose kind is `chapter`, and rejects an export with no chapters—exports are not an all-document dump (`src/contexts/studio/application/services/export_service.py`).

Markdown, DOCX, and EPUB output is written through a temporary file in the destination directory and atomically replaced into place. DOCX and EPUB writers receive prepared chapter titles and plain text; the service records the resulting file's relative path, size, checksum, format, and snapshot ID in the repository (`src/contexts/studio/application/services/export_service.py`, `src/contexts/studio/infrastructure/exporters/docx_exporter.py`, `src/contexts/studio/infrastructure/exporters/epub_exporter.py`).

AI generation keeps the author instruction in explicit begin/end markers and sanitizes known control phrases before sending it to the provider. Manuscript text is serialized as `{"content_markdown": ...}` inside `[BEGIN UNTRUSTED MANUSCRIPT JSON]` / `[END UNTRUSTED MANUSCRIPT JSON]`; bracket characters are escaped in the serialized payload so author text cannot manufacture a second delimiter. The system prompt explicitly says that this block is data and never an instruction. Instruction sanitization and output Markdown sanitization remain separate defenses, and the public request/response payload is unchanged (`src/contexts/studio/application/service_common.py`, `src/contexts/studio/application/services/ai_service.py`).

Validation handlers keep response details compatible while logging only the request path, HTTP method, field, error type, and human-readable message. They pass `format_validation_errors(...)` to the logger instead of raw Pydantic `errors()`, so password, token, API-key, and other input values are not written to telemetry (`src/apps/api/middleware/error_handler.py`).

## Quality gates

The CI `validate` job installs locked Python and pnpm dependencies, checks AI regression differences for pull requests, validates SSOT/OpenSpec and repository hygiene, then runs backend formatting, linting, security, type, import-boundary, test/coverage, and OpenAPI checks. It also runs frontend lint/format/type/unit/build checks, requires a clean React Doctor report, and executes the Studio smoke workflow in Playwright. A dependent container job verifies a fresh install, persistence across restart, deep-link serving, authenticated session persistence, SQLite integrity, and the expected migration (`.github/workflows/ci.yml`).

CodeQL separately analyzes both Python and JavaScript/TypeScript on pushes and pull requests to `main`/`develop`, plus a scheduled weekly run; it initializes the repository CodeQL configuration and performs autobuild before analysis (`.github/workflows/codeql.yml`).

The pre-remediation audit and each focused remediation batch use the same
replayable backend, frontend, OpenSpec, OpenAPI, security, and Studio smoke
checks. Focused tests cover route surfaces and APG keyboard behavior, pending
and duplicate-submission guards, conflict recovery, snapshot-protected delete,
AI prompt boundaries, validation-log redaction, and HMAC key rotation. After
source changes, rerun the release-equivalent commands in
`openwiki/quickstart.md` and wait for hosted `validate`, container, and CodeQL
jobs before merge.

## Change guidance

- Change runtime ownership or request access through `src/apps/api/runtime.py`, `src/apps/api/main.py`, and `src/contexts/studio/interface/http/dependencies.py` together; preserve app-owned state and lifespan disposal.
- Add application behavior behind an application port and service before changing repository infrastructure; `uv run lint-imports` in CI verifies the layer rules.
- Preserve revision IDs in snapshots and the restore-as-new-revision behavior when modifying history or export paths.
- For export changes, keep snapshot comparison chapter-only selection and atomic output replacement intact; run the focused service tests plus the CI-equivalent backend/frontend checks as applicable.
