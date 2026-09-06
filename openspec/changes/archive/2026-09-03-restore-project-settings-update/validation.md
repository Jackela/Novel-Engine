# Validation evidence

## Final integrated candidate evidence — 2026-09-05 (`13a4fed4`)

The merged main commit `13a4fed4d9252d33793e3806a2e9565ec7618c3e` (squash
merge of [PR #456](https://github.com/Jackela/Novel-Engine/pull/456);
tree-identical to review candidate `d532d261`, re-verified by empty
`git diff --stat`) is the final integrated candidate. Full evidence lives in
[the acceptance closeout](../../../docs/agents/acceptance-evidence-closeout-2026-09-05.md):

- Task 4.3 is closed on `13a4fed4`: server type-check, lint (432 files),
  architecture, size (via gates, 621 files), full tests (202 files / 1273
  tests), and gates all passed; frontend lint (215 files), format (214
  files), type-check, unit (84 files / 464 tests), and build passed; React
  diagnostics passed with `pnpm --dir frontend exec react-doctor --json`
  (score 100, 202 files, zero diagnostics); browser workflows passed — smoke
  3 tests including the Settings title/description/provider persistence
  flow, and full-audit 9 tests (the historical `4 passed / 2 failed / 3 not
  run` audit belonged to the pre-merge shell/body chain and is superseded);
  strict OpenSpec passed 19/19.
- Required CI on `13a4fed4`: `validate`, `container`, and
  `Analyze (javascript-typescript)` all green (run URLs in the closeout).
- Independent review accounting: the standards/security re-review at
  `cbe69543` is clean; the remaining range to `13a4fed4` is covered by the
  segment review chain in the closeout (bounded clean review of
  `b2019bae..b061e4df`, reviewed Lore repair, and a verified zero-product-code
  delta after `688acfe7`). No Settings-surface product code changed after
  `688acfe7`.
- Task 4.4 remains open: the canonical-spec merge/archive step is a separate
  deliberate decision gated on the change's own closed gates, including
  human acceptance. The 4.3 row in the earlier pointer below is superseded
  by this section; its 4.4 row remains current.

Human acceptance remains `not run`; use
[the acceptance packet](../../../docs/agents/refactor-human-acceptance-2026-09-05.md).

## Current closeout pointer — 2026-09-05

The failed browser audit and pending review descriptions below are historical
observations for their named phase candidates. The subsequent refactor handoff
recorded 9/9 browser flows on `67c33992`; the new Draft repair candidate
`b2019baec05485c9ae4aa930cdeb6e8dccba48ee` again passed all 9 flows, including
Settings title/description/provider persistence. See
[the exact-candidate evidence](../../../docs/agents/draft-selection-closeout-2026-09-05.md).

| Open task | Implementation / validation correspondence | Remaining closure condition |
| --- | --- | --- |
| 4.3 | Server Settings update/validation/OpenAPI/application suites; frontend `useProjectSettingsUpdate.test.tsx`, `StudioSettingsPanel.test.tsx`, and the TS main Studio persistence workflow. The new candidate passed frontend full checks, 463 unit tests, API drift, React diagnostics, gates, OpenSpec and 9 E2E flows. | Server full/type/lint/arch evidence below remains at `cbe69543`; await final-candidate CI and explicitly account for the complete independent security/UX review scope. |
| 4.4 | CI and canonical-spec/archive step, separately owned from shell work. | Remains open. No archive, merge, or release is authorized by local validation. |

Human acceptance remains `not run`; the
[acceptance packet](../../../docs/agents/refactor-human-acceptance-2026-09-05.md)
includes Settings persistence, errors, busy state, and keyboard focus.

## Candidate

- Fixed baseline: `eebfa7db0e078cf0c47fa89eded2a867aa8791ed`.
- Server implementation candidate: `cbe69543` (`d2926b22` plus independent
  review repairs).
- Frontend implementation candidate: `056e8ed7`.
- Scope: server tasks 1.1 through 2.5, frontend tasks 3.1 through 3.5 and 4.1
  through 4.2, the frozen OpenAPI baseline, and its generated frontend API type
  consumer.

## Targeted

- `pnpm --dir server exec vitest run tests/api/studio_project_settings_update.test.ts tests/api/studio_project_settings_validation.test.ts tests/api/studio_project_settings_openapi.test.ts tests/api/studio_route_composition.test.ts tests/contexts/project_settings_update.test.ts`
  passed: 5 files, 15 tests.
- The API tests exercised each optional scalar alone and together, complete
  settings replacement, omitted-field preservation, exact scalar response,
  original unknown keys, raw field types, bounds, normalized blank title,
  guard ordering, zero store calls on guard/validation failures, and identical
  missing/cross-Owner 404 bodies.
- The application/store tests exercised normalization before one command,
  omission as absent properties, one supplied time, one Owner-scoped SQL
  UPDATE, same/backwards-clock monotonicity, and full rollback from an
  after-update SQLite trigger, compile-time and runtime empty-command rejection,
  and database-free PATCH 503 composition.
- `pnpm --dir server openapi:snapshot` passed and deliberately refreshed
  `server/qa-baselines/openapi.current.json`.
- `pnpm --dir frontend gen:api-types` passed and deliberately refreshed
  `frontend/generated/api-types.ts`.

## Local full

- `pnpm --dir server test` passed on the final implementation candidate: 202
  files, 1,269 tests, duration 490.81 s.
- `pnpm --dir server type-check` passed.
- `pnpm --dir server lint` passed: 432 files checked.
- `pnpm --dir server arch` passed: 224 modules and 935 dependencies, no
  violations.
- `pnpm --dir server build` passed.
- `pnpm --dir server gates` passed: SSOT, repository hygiene, 608-file size
  gate, migration channel, llms.txt links, and frozen OpenAPI snapshot.
- `pnpm --dir frontend check:api-types` passed with no generated-type drift.
- `pnpm --dir frontend type-check` passed.
- `pnpm spec:validate` passed: 19 items, 0 failures.

## Frontend and browser candidate

- `pnpm --dir frontend test:unit` passed: 80 files, 446 tests.
- Focused Settings/API/UI verification passed: 5 files, 48 tests. It covers
  strict scalar parsing, exact omitted request serialization, mutable-only
  shell merge, immutable/structural preservation, reversed intent settlement,
  duplicate submission, unmount abort, wrong identity, 401/404 routing,
  recoverable operational failure, panel-local error semantics, and focus.
- `pnpm --dir frontend lint`, `format:check`, `type-check`, `build`, and
  `check:api-types` passed.
- `pnpm exec react-doctor --json` passed with score 100 and zero diagnostics.
- `pnpm --dir frontend test:e2e:smoke` passed: 3 tests. The first real
  TypeScript-backend workflow changed title, description, and provider through
  Settings, reloaded the deep link, and observed all three persisted values.
- `pnpm --dir frontend test:e2e:full-audit` was run but is not a full pass: 4
  passed, 2 failed, and 3 did not run after the serial failure. The failures are
  outside this Settings write set: content acceptance observed an empty saved
  chapter after proposal acceptance, and whole-book prose validation received
  an undefined body while those helpers/flows still assumed Project shell rows
  contained bodies. This candidate did not modify that document-body chain.
- `pnpm spec:validate` passed after the Settings implementation: 19 items, 0
  failures.

## Independent review and unfinished gates

- Independent fixed-SHA standards/security review first found one P2
  (internally empty update types) and one P3 evidence gap (forward-clock and
  database-free PATCH 503 branches). Both were repaired in `cbe69543`.
- Independent re-review of `cbe69543` was clean with no actionable findings;
  it reran 3 focused files / 11 tests plus server type-check, lint, architecture,
  and diff checks.
- Frontend behavior tasks 3.1 through 3.5 and the browser persistence workflow
  are implemented in `056e8ed7`.
- Task 4.3 remains open because the full browser audit is not green and the
  final fixed-SHA independent standards/security/UX review has not run.
- Required CI is not run locally and remains `not run`; the integrator must
  obtain green required contexts on the final candidate before archive.
- Human acceptance is `not run`; the Owner must exercise the Settings flow on
  the final candidate before release if required by the integrator.
