## 1. Specification and version authority

- [x] 1.1 Pin OpenSpec 1.4.1 and add strict CI validation
- [x] 1.2 Set `pyproject.toml` to 0.3.0 and derive all runtime versions
- [x] 1.3 Replace README with installation and OpenSpec navigation

## 2. SQLite authoring core

- [x] 2.1 Add the SQLAlchemy database, schema, migrations, backup, and FTS setup
- [x] 2.2 Implement project, document, immutable revision, link, and search services
- [x] 2.3 Implement snapshots, reviews, exports, jobs, usage events, and guest cleanup
- [x] 2.4 Implement idempotent read-only legacy import

## 3. Public API and operations

- [x] 3.1 Add owner setup/session APIs and 24-hour guest sessions
- [x] 3.2 Replace workspace routes with project/document/revision/search APIs
- [x] 3.3 Add AI proposal, review, snapshot, export, download, job retry, and import APIs
- [x] 3.4 Reduce CLI to serve, import, backup, and doctor

## 4. Novel Studio frontend

- [x] 4.1 Replace the landing page with setup and project library
- [x] 4.2 Implement the three-panel project shell and document navigation
- [x] 4.3 Add CodeMirror editing, autosave, conflict handling, history, and restore
- [x] 4.4 Add AI proposal, review, search, export, settings, and guest-expiry surfaces

## 5. Runtime and repository consolidation

- [x] 5.1 Serve the built SPA with deep-link fallback
- [x] 5.2 Add Dockerfile, Compose, persistent data volume, migration startup, and health checks
- [x] 5.3 Remove obsolete product modules, docs, generated frontend output, dependencies, and tests
- [x] 5.4 Add SSOT, OpenAPI, backend, frontend, browser, export, migration, and container gates
