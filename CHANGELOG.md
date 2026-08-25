# Changelog

## 0.4.0

TypeScript rewrite cutover (#277, ADR-0002): the Fastify + TypeBox server
under `server/` is the single backend and serves the Studio SPA from one
Node.js process.

- One-way data door: 0.4.0 opens a fresh SQLite schema and does not migrate
  Python-era databases. Back up the old `data/` directory, start with a
  fresh data directory, and re-import legacy workspaces through the
  read-only idempotent `import` CLI. Rolling back the cutover commit
  restores the Python stack, but data written after the cutover does not
  survive the rollback. The final Python state is preserved by the
  protected git tag `python-final`.
- Removed the Python tree (`src/`, `alembic/`, Python tests and QA scripts,
  `pyproject.toml`) and the Python CI jobs; the Node QA gates under
  `server/scripts/qa/` are the operative twins.
- Release version authority moved to `server/package.json`.
- OpenAPI baseline regenerated from the TS server; frontend codegen derives
  from it and the Python-compat parsing branches (dual CSRF cookie, legacy
  `{detail}` errors) were removed — the unified error envelope and
  `novel_engine_*` cookies are the only contract.
- Product specification consolidated under the `novel-engine` OpenSpec
  capability; `novel-studio` retired (#240 closed as superseded).

## 0.3.1

- Remediated Linus-style audit findings across security, architecture,
  documentation, and dead code.
- Added AI guardrails, local safety checks, and stronger CI/pre-commit mypy
  coverage for tests.
- Hardened AI proposal acceptance, app-owned API runtime settings, token bucket
  cleanup, and frontend API response contract parsing.

## 0.3.0

- Added the self-hosted Novel Studio API and React writing workspace.
- Added SQLite-backed projects, documents, revisions, snapshots, reviews,
  exports, durable jobs, sessions, CSRF protection, and rate limiting.
- Added provider adapters for mock, DashScope, and OpenAI-compatible text
  generation.
- Hardened FTS5 search query construction, startup factories, LLM defaults,
  delete endpoints, and documentation consistency.
