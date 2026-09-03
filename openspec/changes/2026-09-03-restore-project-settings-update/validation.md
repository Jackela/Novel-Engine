# Validation evidence

## Candidate

- Fixed baseline: `eebfa7db0e078cf0c47fa89eded2a867aa8791ed`.
- Server implementation candidate: `d2926b22`.
- Scope: server tasks 1.1 through 2.5, the frozen OpenAPI baseline, and its
  generated frontend API type consumer.

## Targeted

- `pnpm --dir server exec vitest run tests/api/studio_project_settings_update.test.ts tests/api/studio_project_settings_validation.test.ts tests/api/studio_project_settings_openapi.test.ts tests/contexts/project_settings_update.test.ts`
  passed: 4 files, 13 tests.
- The API tests exercised each optional scalar alone and together, complete
  settings replacement, omitted-field preservation, exact scalar response,
  original unknown keys, raw field types, bounds, normalized blank title,
  guard ordering, zero store calls on guard/validation failures, and identical
  missing/cross-Owner 404 bodies.
- The application/store tests exercised normalization before one command,
  omission as absent properties, one supplied time, one Owner-scoped SQL
  UPDATE, same/backwards-clock monotonicity, and full rollback from an
  after-update SQLite trigger.
- `pnpm --dir server openapi:snapshot` passed and deliberately refreshed
  `server/qa-baselines/openapi.current.json`.
- `pnpm --dir frontend gen:api-types` passed and deliberately refreshed
  `frontend/generated/api-types.ts`.

## Local full

- `pnpm --dir server test` passed: 202 files, 1,268 tests, duration 313.18 s.
- `pnpm --dir server type-check` passed.
- `pnpm --dir server lint` passed: 432 files checked.
- `pnpm --dir server arch` passed: 224 modules and 935 dependencies, no
  violations.
- `pnpm --dir server build` passed.
- `pnpm --dir server gates` passed: SSOT, repository hygiene, 608-file size
  gate, migration channel, llms.txt links, and frozen OpenAPI snapshot.
- `pnpm --dir frontend check:api-types` passed with no generated-type drift.
- `pnpm --dir frontend type-check` passed.
- `pnpm spec:validate` is recorded after this evidence file and task state are
  committed.

## Independent review and unfinished gates

- Independent fixed-SHA server standards/security review of `d2926b22` is in
  progress; its result is not yet claimed here.
- Frontend behavior tasks 3.1 through 3.5 and the browser persistence workflow
  remain owned by their later wave; no frontend behavioral completion is
  claimed by this server candidate.
- Required CI is not run locally and remains `not run`; the integrator must
  obtain green required contexts on the final candidate before archive.
- Human acceptance is `not run`; the Owner must exercise the Settings flow on
  the final candidate before release if required by the integrator.
