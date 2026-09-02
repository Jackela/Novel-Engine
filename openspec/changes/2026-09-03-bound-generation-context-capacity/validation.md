# Validation evidence

## Fixed points

- Comparison SHA: `fdfecac9078b8d30f34b879ba18b8485265c9188`
- Change proposal SHA: `4ee4989ae8473730afd73670697dec92f368762d`
- Final local candidate SHA: `65956ade42fee3d5d171c6d2cfad1b3377bdfd7c`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0, Vitest 4.1.11

## Targeted and review evidence

The targeted capacity set passed 10 files and 52 tests on the candidate's
immediate predecessor; the final SSOT-only follow-up passed its two owning
files and 10 tests, then the complete server suite covered the integrated
candidate. Exact and plus-one fixtures cover the 8,388,608-byte aggregate
prompt boundary, UTF-8 accounting, 60-word and 512-code-point digests,
pre-Provider sync/SSE admission, structured keyed-retry replay, and whole-book
stop/resume behavior. Lore tests use deterministic counters for one summary
and one full representation per match and one final render pass; resident and
Lore consumers stop producing later lines after capacity refusal.

The first two-axis review found one P1 and four P2 findings: resident/Lore
sections were materialized before incremental admission, Lore instrumentation
measured source getters rather than representations, whole-book resumption was
not directly proven, persisted limits were not closed to the fixed policy,
and generic 422 schemas lived in the export module. Repair commits introduced
lazy iterators, direct representation counters, the resume fixture, a domain
capacity policy, and a neutral unprocessable-entity schema. A second review
found one remaining P2 bare error-code duplication; `65956ade` moved the full
catalog to shared domain and left HTTP as a compatibility re-export. The final
narrow review reported no P0-P2 findings. Agent review supports but does not
replace the fixed-SHA commands below.

## Local fixed-SHA evidence

All commands below ran from a clean tracked tree at
`65956ade42fee3d5d171c6d2cfad1b3377bdfd7c`.

| Validation surface | Command | Result |
|---|---|---|
| Full server tests | `pnpm --dir server test` | Passed: 183 files, 1,206 tests in 295.91 seconds. |
| Server policy gates | `pnpm --dir server gates` | Passed: SSOT, hygiene, 552-file size budget, migration channel, llms-txt, and OpenAPI snapshot. |
| Server types and lint | `pnpm --dir server type-check` and `pnpm --dir server lint` | Passed; Biome checked 399 files. |
| Server architecture | `pnpm --dir server arch` | Passed: 211 modules and 876 dependencies, zero violations. |
| Server build | `pnpm --dir server build` | Passed with the production TypeScript build. |
| Full frontend unit tests | `pnpm --dir frontend test:unit` | Passed: 67 files and 371 tests in 23.34 seconds. |
| Frontend static/build | lint, format check, type check, and production build | Passed: 1,913 modules; Novel Engine 0.6.0 identity verified in HTML and 7 JavaScript bundles. |
| React static diagnostics | `pnpm --dir frontend exec react-doctor --json` plus CI summary assertion | Passed: score 100, zero diagnostics. |
| API-types drift | `pnpm --dir frontend check:api-types` | Passed; generated types match the OpenAPI snapshot. |
| TypeScript-backend Playwright | `pnpm --dir frontend test:e2e:ts` | Passed: 8 of 8 in 24.3 seconds. |
| Strict OpenSpec | `pnpm spec:validate --strict` | Passed: 15 of 15 active changes/specification items. |

## Named later changes

This change does not claim one coherent read transaction for target revision,
outline, volumes, prior chapters, beat, and Lore. It also preserves the
existing retry rule that records the original request base revision while
generation resolves the current revision. Coherent proposal-context reads and
retry base-revision semantics require separate product decisions and tests.

Project detail, revision history, review history, project/export catalogs, and
their frontend caches remain separate pagination/resource changes. They are
not silently treated as covered by the aggregate Provider-prompt limit.

## External and release gates

This change remains active and unarchived. Required GitHub checks were not run
because no push or pull request was authorized. The production dependency
audit, Linux execution, and container persistence/restart job therefore remain
`not run`; owner is the repository maintainer and closure requires every live
required context to pass on the exact integration SHA. No visual or interaction
acceptance is required because production UI behavior and copy did not change;
release authorization remains owner-required and is not implied by local or
agent evidence.
