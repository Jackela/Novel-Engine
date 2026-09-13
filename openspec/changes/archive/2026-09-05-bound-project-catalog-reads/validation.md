# Validation evidence

## Fixed points

- Comparison SHA (baseline): `1dd8c85f` (worktree `codex/458-bound-project-catalog-reads`)
- Candidate SHA: recorded at PR creation from this branch's tip
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Measured baseline (on `1dd8c85f`)

Temporary hermetic vitest probe (since deleted; replay: seed 250 projects via
`POST /api/projects`, grow one row's settings via `PATCH`, read
`GET /api/projects`):

| Metric | Value |
| --- | --- |
| Rows returned (unbounded) | 250 |
| Response size | 79,582 bytes |
| Heaviest row (≈8 KB settings) | 8,320 bytes |
| Typical row | ~286 bytes |
| SQL statements for the list | 1 (`SELECT *` scoped by owner, no `LIMIT`) |

## Red → green record

- Red: `tests/api/studio_project_catalog_pagination.test.ts` failed at import
  (`project_catalog_cursor.js`, `project_page_queries.js` did not exist) before
  implementation — `pnpm --dir server vitest run` exited 1 with "Test Files 1
  failed / Tests no tests".
- Green: after implementation, the split suites pass —
  `studio_project_catalog_pagination.test.ts` (8 tests) plus
  `studio_project_catalog_cursor_contract.test.ts` (2 tests); 10/10 green.
- One implementation-time regression was caught and fixed before commit: the
  library hook initially cleared the bootstrap `error` at reload start, which
  unmounted the Retry control during in-flight retries and moved restored
  focus to the heading (`ProjectLibraryPage.lifecycle.test.tsx`). The fix
  preserves `error` during the in-flight phase, restoring the baseline
  focus contract.

## Local full evidence (worktree candidate)

| Surface | Command | Result |
| --- | --- | --- |
| Server full suite | `pnpm --dir server test` | 203 files / 1283 tests passed |
| Server gates | `pnpm --dir server gates` | SSOT, hygiene, file-size (629 files), migration-channel, llms-txt, OpenAPI snapshot all clean |
| Server type-check | `pnpm --dir server type-check` | Passed |
| Server lint | `pnpm --dir server lint` | 437 files, clean |
| Server architecture | `pnpm --dir server arch` | 227 modules / 954 dependencies, no violations |
| Frontend unit | `pnpm --dir frontend test:unit` | 85 files / 471 tests passed |
| Frontend type-check | `pnpm --dir frontend type-check` | Passed |
| Frontend lint / format | `pnpm --dir frontend lint` / `format:check` | 218 / 217 files, clean |
| Frontend build | `pnpm --dir frontend build` | Built; build identity verified (Novel Engine 0.6.0) |
| API-types drift | `pnpm --dir frontend check:api-types` | Clean |
| OpenSpec strict | `pnpm spec:validate` | 20 / 20 passed |

## Deliberate artifact refresh

- `server/qa-baselines/openapi.current.json` regenerated via
  `pnpm --dir server openapi:snapshot` (route query/response contract change).
- `frontend/generated/api-types.ts` regenerated via
  `pnpm --dir frontend gen:api-types`; drift check clean.
- Migration `0020_paginate-project-catalog.sql` generated only through
  `pnpm --dir server db:generate --name paginate-project-catalog`; SQL and
  metadata reviewed without hand edits; migration-channel gate clean.

## Skips

| Check | Status | Reason / owner / closure |
| --- | --- | --- |
| Browser Playwright workflows | not run (local) | Port policy: CI owns browser workflows. Owner: repository CI. Closes when required CI is green on the PR SHA. |
| Human acceptance | not run | Product-flow judgment (owner: Jackela) remains open per the acceptance packet convention. |
| Required CI | pending | PR must record check URLs on the final candidate SHA (task 4.3). |
