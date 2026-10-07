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
| CI on `6a7c198f` | failed | `validate` exited in React Doctor; `server` and `Analyze (javascript-typescript)` passed; `container` was skipped | The branch was not mergeable | The follow-up in this file |
| CI on `3f55e599` | passed | Required jobs below are success on that SHA | None for those four jobs | Already closed on `3f55e599` |
| CI on the documentation commit that records `3f55e599` | not run | This paragraph is that commit, written after the green run | The product tree is unchanged, but this SHA is a new candidate | Green required jobs on this documentation SHA before merge |
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

## CI on `6a7c198f`

Branch `quality-iteration-2026-10-07`, pull request
[#681](https://github.com/Jackela/Novel-Engine/pull/681). Run
[37625413884](https://github.com/Jackela/Novel-Engine/actions/runs/37625413884)
is the CI workflow. Run
[37625413872](https://github.com/Jackela/Novel-Engine/actions/runs/37625413872)
is CodeQL.

| Check | Result |
|---|---|
| `validate` (job 112805794628) | FAIL, 10m7s. Step "Validate React static diagnostics" exited 1. The log does not print the diagnostic JSON, because `react-doctor` itself exits 1 under `bash -e` before the printer runs. |
| `server` (job 112805794302) | PASS, 6m40s |
| `Analyze (javascript-typescript)` (job 112805794350) | PASS, 1m41s |
| `container` (job 112810224691) | skipped, because `validate` failed |
| `CodeQL` | NEUTRAL. Not a failure and not a required success. |

Local reproduction on that tree, `pnpm --dir frontend exec react-doctor --json`
(react-doctor 0.9.12), reported `totalDiagnosticCount` 3, score 83:

- error `no-ref-current-in-render` at `useRevisionPreview.ts` line 87 (`scopeEpochRef.current += 1` during render);
- warning `no-many-boolean-props` at `StudioHistoryLoadOlder.tsx` line 29;
- warning `rerender-memo-with-default-value` at `StudioWholeBookControl.tsx` line 33 (`occupiedChapters = []`).

## React Doctor follow-up

The follow-up drops the render-time scope epoch. A settled preview read
publishes only while its row is still `loading` for the same request
sequence, so a document switch that clears the cache cannot accept the
abandoned response. The history footer's five flags are one
`HistoryLoadOlderStatus` object. The empty occupied-chapter list is the
module constant `EMPTY_OCCUPIED_CHAPTERS`. DOM, class names, i18n keys, and
ARIA are unchanged. Existing test assertions were not edited.

These commands ran on that uncommitted diff (macOS, Node `v24.19.0`, pnpm
`11.6.0`), before the follow-up commit existed.

| Surface | Command | Result |
|---|---|---|
| React Doctor | `pnpm --dir frontend exec react-doctor --json` | PASS, exit 0, `totalDiagnosticCount` 0, score 100 |
| Affected unit tests | `pnpm --dir frontend exec vitest run` on `useRevisionPreview.test.tsx`, `StudioHistoryPanel.test.tsx`, `StudioHistoryPanel.preview.test.tsx`, `StudioWholeBookControl.confirm.test.tsx`, `StudioWholeBookControl.i18n.test.tsx` | PASS, 5 files / 23 tests |
| Frontend static | `pnpm --dir frontend type-check && lint && lint:types && format:check` | PASS |
| File size | `node server/scripts/qa/check_file_sizes.mjs` | PASS, 1021 files, component limit 200 |
| Frontend coverage | `pnpm --dir frontend test:coverage` | PASS, 156 files / 860 tests. Statements 91.26, branches 84.75, functions 90.9, lines 93.9. Floors 91 / 84 / 90 / 93 still hold. |

`act(...)` stderr in the coverage run is the same pre-existing noise as the
earlier local full run.

### CI-required on `3f55e599`

Product fix `b7aa1983`, evidence tip `3f55e599f263675b187bd712a9ef9910c5df0ef0`.
Pull request [#681](https://github.com/Jackela/Novel-Engine/pull/681). CI run
[37631910485](https://github.com/Jackela/Novel-Engine/actions/runs/37631910485).
CodeQL run
[37631910660](https://github.com/Jackela/Novel-Engine/actions/runs/37631910660).
Both `headSha` values are `3f55e599`.

| Check | Result |
|---|---|
| `validate` (job 112828079769) | PASS, 12m18s |
| `server` (job 112828079323) | PASS, 6m34s |
| `container` (job 112834038610) | PASS, 44s |
| `Analyze (javascript-typescript)` (job 112828080254) | PASS, 1m28s |
| `CodeQL` | NEUTRAL. Not a failure and not one of the four required successes. |

Human acceptance is still not run. The commit that adds this table changes
only this file. It does not reuse the `3f55e599` result as its own CI pass.
