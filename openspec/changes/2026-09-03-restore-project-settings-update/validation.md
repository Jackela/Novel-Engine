# Validation evidence

## Candidate

- Fixed baseline: `eebfa7db0e078cf0c47fa89eded2a867aa8791ed`.
- Server implementation candidate: `cbe69543` (`d2926b22` plus independent
  review repairs).
- Scope: server tasks 1.1 through 2.5, the frozen OpenAPI baseline, and its
  generated frontend API type consumer.

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

## Independent review and unfinished gates

- Independent fixed-SHA standards/security review first found one P2
  (internally empty update types) and one P3 evidence gap (forward-clock and
  database-free PATCH 503 branches). Both were repaired in `cbe69543`.
- Independent re-review of `cbe69543` was clean with no actionable findings;
  it reran 3 focused files / 11 tests plus server type-check, lint, architecture,
  and diff checks.
- Frontend behavior tasks 3.1 through 3.5 and the browser persistence workflow
  remain owned by their later wave; no frontend behavioral completion is
  claimed by this server candidate.
- Required CI is not run locally and remains `not run`; the integrator must
  obtain green required contexts on the final candidate before archive.
- Human acceptance is `not run`; the Owner must exercise the Settings flow on
  the final candidate before release if required by the integrator.
