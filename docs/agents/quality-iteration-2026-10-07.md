# Quality iteration — 2026-10-07

Campaign: document sync, frontend race fixes and component splits, backend
config/app/application dedupe, service tests, spec reconciliation, and the
file-size plus coverage gates. The integrator owns this record. Subagent
splits were re-checked on the shared working tree before these commands.

## Baseline

- Fixed comparison SHA: `a39e38d5b7e9a3bfc37a533611fe6b061a54e74a` (`main`).
- The commands below ran on that SHA plus the uncommitted campaign diff,
  before these commits existed. The evidence commit adds only this file.
- Local environment: macOS, Node `v24.19.0`, pnpm `11.6.0`.
- OpenAPI baseline `server/qa-baselines/openapi.current.json` is byte-identical
  to `a39e38d5` (`git diff a39e38d5 --` that path is empty). No route change.
- Not in any commit: `.commandcode/`, `.zcode/`, `dist/`, `coverage/`, `.env*`,
  `data/`, `server/drizzle/meta/*`, `AUDIT_REPORT_Linus.md`, `Makefile`,
  `justfile`.

## Targeted

| Surface | Command | Result |
|---|---|---|
| File-size gate, before the component cap | `node server/scripts/qa/check_file_sizes.mjs` | PASS, 1022 files, limit 300 |
| Server types, before the coverage edit | `pnpm --dir server type-check` | PASS |
| Frontend unit suite after the component split | `pnpm --dir frontend test:unit` | PASS, 156 files / 860 tests |
| Frontend types, lint, format, type-aware lint after the split | `pnpm --dir frontend type-check && lint && format:check && lint:types` | PASS |
| Size and hygiene gates after the 200-line component cap | `pnpm --dir server gate:sizes && pnpm --dir server gate:hygiene` | PASS, 1021 files, component limit 200, hygiene clean |
| Server coverage measurement (no thresholds yet) | `pnpm --dir server test:coverage` | PASS, 276 files / 1657 tests. Statements 92.39, branches 83.8, functions 96.29, lines 93.98 |
| Frontend coverage measurement | `pnpm --dir frontend test:coverage` | PASS, 156 files / 860 tests. Statements 91.26, branches 84.76, functions 90.91, lines 93.9 |

Frozen floors (向下取整, not raised): server 92 / 83 / 96 / 93, frontend 91 / 84 / 90 / 93.

## Local full

| Surface | Command | Result |
|---|---|---|
| Server types, lint, type-aware lint, architecture | `pnpm --dir server type-check && lint && lint:types && arch` | PASS. depcruise: 307 modules, 1393 dependencies, 0 violations |
| OpenSpec | `pnpm spec:validate` | PASS, `spec/novel-engine` |
| Frontend lint, type-aware lint, format, types | `pnpm --dir frontend lint && lint:types && format:check && type-check` | PASS |
| Frontend coverage with frozen floors | `pnpm --dir frontend test:coverage` | PASS, 156 files / 860 tests, same percentages as the measurement |
| Frontend production build | `pnpm --dir frontend build` | PASS. Identity check: Novel Engine 0.8.0 |
| Server coverage with frozen floors | `pnpm --dir server test:coverage` | PASS, 276 files / 1657 tests. Duration 349.77s |
| Server gates | `pnpm --dir server gates` | PASS. ssot 0.8.0, hygiene, compose-passthrough (18 provider variables), sizes (1021 files), migrations, llms-txt (53 links), error-codes (22), openapi snapshot |
| Server production build | `pnpm --dir server build` | PASS |
| Studio browser workflows | `pnpm --dir frontend test:e2e:ts` | PASS, 35 tests, Chromium, 1.1m |

`pnpm --dir server test` was not started as its own process. `test:coverage` is
`vitest run --coverage` over the same `tests/**/*.test.ts` include set, and
that run passed. Residual risk: none for assertion failures. A separate plain
`test` invocation is not required to close this record.

## Skips

| Check | Status | Reason | Residual risk | Closure |
|---|---|---|---|---|
| CI on the candidate SHA | not run | Local record, written before push | Branch protection is unverified until GitHub reports the `validate` job | Green required checks on the pushed SHA |
| Human acceptance | not run | No owner exercised the UI in this session | Visual or keyboard judgment is not claimed | Owner review of the PR |
| Plain `pnpm --dir server test` | not run | Covered by `test:coverage` on the same include set | None for test failures | Re-run the script name only if a reviewer asks |

## What landed

- Docs and `llms.txt` match the current CLI and doctor behavior. `.env.example` was not edited.
- `CHANGELOG.md` has a top `## Unreleased` section. `gate:ssot` allows it only at the top.
- Frontend races: revision preview is keyed by revision id, the jobs panel keeps the last click, provider failures go through `reportUnexpectedError`, beat candidates stay on the active project.
- Shared `useScopedProjectResource`, `InspectorResourcePanel`, and `StatTotalCard`.
- Ten studio components are at or under 180 code lines. New files stay under 200. DOM, class names, i18n keys, and ARIA from the parents were kept. `StudioHistoryPanel.preview.test.tsx` assertions were not rewritten by the split.
- Server config, `buildApp` registration, failure classification, and in-flight permits are split. Six service suites were added.
- Draft-rescue behavior is in the archived OpenSpec change and `openspec/specs/novel-engine/spec.md`.
- `frontend/src/**/*.tsx` except `*.test.tsx` has a 200-code-line cap with no exemption. Retired Python allow-rules and the python-freeze comments in the size gate and `common.mjs` are gone.
- Coverage floors are in both Vitest configs. The `validate` job runs `test:coverage`. The separate `server` job still runs `pnpm --dir server test`.
