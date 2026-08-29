# Changelog

## 0.5.0

Studio deepening epic (#309–#328, ADR-0004/0005) plus a tech-debt and
LLM-friendliness polish pass. BREAKING: the guest principal was removed
end-to-end (#311) — authenticate a real principal before calling the API.

### Added

- Volume hierarchy: organize chapters into ordered volumes, with
  order-aware exports (#312).
- Keyword-triggered lorebook entries extracted from character and world
  documents (#315).
- Resident context assembly feeding every proposal generation (ADR-0004,
  #314).
- LLM editorial review over a closed dimension set (#316).
- Project usage surface aggregating the AI token ledger
  (`/api/projects/:projectId/usage`, #317).
- Whole-book generation loop: stoppable, resumable auto-accept across the
  full manuscript (#318).
- SSE streaming proposal generation (#308).
- `llms.txt` for LLM-oriented repository orientation and a
  `CONTRIBUTING.md` (#350, #360).

### Changed

- The two epic OpenSpec changes are archived into the canonical
  `novel-engine` spec (#352); `AGENTS.md` and openwiki documentation were
  recalibrated to the post-epic codebase (#353–#355).
- The repository facade now points contributors at GitHub issues and the
  TS-stack architecture overview (#354, #355).

### Fixed

- Streaming generation now enforces timeouts so stalled provider streams
  cannot hang a request (#361).
- DashScope Responses-mode stream extraction aligned with the actual
  provider payload (#364).
- Biome diagnostics swept to zero warnings (#362, #363, #359).

### Removed

- Python-era tool-configuration corpses left over from the cutover
  (#358).

### Security / Policy

- Mimosa false-positive waivers are registered in version control
  (#356).
- The file-size gate policy is documented for agents and reviewers
  (#357).

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
