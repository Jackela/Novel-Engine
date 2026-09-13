# Refactor acceptance evidence closeout — 2026-09-05

Integrator evidence for [GitHub issue #457](https://github.com/Jackela/Novel-Engine/issues/457)
("Close remaining refactor acceptance evidence"), recorded under the rules in
[change-evidence.md](change-evidence.md). This pass is reconciliation and
evidence recording only: no product code, dependency, lockfile, test, or
workflow file changed. This document closes #457 items 1, 2, and 6, records
item 3 as findings with follow-up tickets, and leaves items 4 (human
acceptance) and 5 (archive) open.

## Fixed points

- Historical comparison baseline: `2a1d959fc0afb644de0bfbde9f6fa840ace58da4`.
- Final integrated candidate: `13a4fed4d9252d33793e3806a2e9565ec7618c3e`
  (main, squash merge of [PR #456](https://github.com/Jackela/Novel-Engine/pull/456)).
- Tree identity re-verified this session: `git diff d532d261 13a4fed4 --stat`
  is empty, so the PR #456 review candidate and the merged main commit have
  identical file trees.
- Evidence candidate (this docs-only change): its product-code tree is
  identical to `13a4fed4`; its own required-CI result is recorded on its pull
  request, not here.
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0. All pnpm commands
  ran serially from the repository root.
- Local supporting logs: `/tmp/novel-engine-457-evidence-20260905/`
  (`server-fast.log`, `server-full-test.log`, `frontend-fast.log`,
  `browser-and-spec.log`). They are local artifacts, not portable CI URLs.

## Local full — rerun on `13a4fed4`

Every command below ran on the merged main commit during this session
(UTC timestamps from the logs). No listed surface was skipped.

| Surface | Exact command | Result |
| --- | --- | --- |
| Server gates | `pnpm --dir server gates` | Passed: SSOT clean; repo hygiene clean; size gate 621 files; migration channel clean; llms-txt 19 targets; OpenAPI snapshot 1 test. |
| Server type-check | `pnpm --dir server type-check` | Passed. |
| Server lint | `pnpm --dir server lint` | Passed: 432 files checked. |
| Server architecture | `pnpm --dir server arch` | Passed, no violations. |
| Server full tests | `pnpm --dir server test` | Passed: 202 files, 1273 tests, 123.90 s (10:13:38–10:15:44Z). This is the first full-suite pass recorded on a final integrated SHA; the earlier interrupted run is not relabeled. |
| Frontend lint | `pnpm --dir frontend lint` | Passed: 215 files checked. |
| Frontend format | `pnpm --dir frontend format:check` | Passed: 214 files checked. |
| Frontend type-check | `pnpm --dir frontend type-check` | Passed. |
| Frontend unit | `pnpm --dir frontend test:unit` | Passed: 84 files, 464 tests, 8.50 s. |
| Frontend build | `pnpm --dir frontend build` | Passed: 1929 modules transformed, identity check included. |
| Generated API drift | `pnpm --dir frontend check:api-types` | Passed, no drift. |
| React diagnostics | `pnpm --dir frontend exec react-doctor --json` | Passed: score 100, 202 files analyzed, zero diagnostics. |
| Browser smoke | `pnpm --dir frontend test:e2e:smoke` | Passed: 3 tests, 12.1 s — includes the Settings title/description/provider persistence workflow and the bounded History keyboard-retry workflow. |
| Browser full audit | `pnpm --dir frontend test:e2e:full-audit` | Passed: 9 tests, 18.4 s. The previously recorded `4 passed / 2 failed / 3 not run` audit is historical: both failures (empty saved chapter after proposal acceptance; whole-book undefined body) belonged to the shell/body split chain that PR #456 completed, and the audit is green on the integrated candidate. |
| Strict OpenSpec | `pnpm spec:validate` | Passed: 19 items, 0 failures. |

## Required CI — `13a4fed4` on main

Required contexts were resolved live via
`gh api repos/Jackela/Novel-Engine/branches/main/protection` (2026-09-05):
`Analyze (javascript-typescript)`, `validate`, `container`, with
`strict = true`. Check runs on the merged commit:

| Context | Conclusion | Run / job |
| --- | --- | --- |
| `validate` | success (2026-09-05T02:43:40Z) | [run 33939564179, job 101234185287](https://github.com/Jackela/Novel-Engine/actions/runs/33939564179/job/101234185287) |
| `container` | success (2026-09-05T02:44:35Z) | [run 33939564179, job 101235101859](https://github.com/Jackela/Novel-Engine/actions/runs/33939564179/job/101235101859) |
| `Analyze (javascript-typescript)` | success (2026-09-05T02:38:58Z) | [run 33939564176, job 101234185333](https://github.com/Jackela/Novel-Engine/actions/runs/33939564176/job/101234185333) |

## Independent review chain — `2a1d959f..13a4fed4`

Every segment of the integrated range is now covered by an independent
fixed-SHA review or verified to contain no product code:

| Segment | Content | Review disposition |
| --- | --- | --- |
| `2a1d959f..67c33992` | Full refactor series (160 commits) | Independent review: no P0/P1/P2 (refactor-handoff record). |
| `67c33992..52741fbf` | Docs only | Verified this session: one file, 88 insertions (`refactor-handoff-2026-09-05.md`). |
| `52741fbf..b2019bae` | Draft selection repair | Independent Standards + Spec reviews clean (draft-selection-closeout record). |
| `b2019bae..b061e4df` | SemVer prerelease/ReDoS fix, export test identity, fast-uri lockfile, docs | Bounded independent review performed this session: no P0-P2. Two optional P3 notes below. |
| `b061e4df..688acfe7` | Lore savedStatus repair | Independent Standards + Spec reviews clean (repository-maintenance record). |
| `688acfe7..13a4fed4` | Issue templates, CONTRIBUTING, evidence docs, openspec validation note, browserslist lockfile patch | Verified this session: zero product code (`git diff 688acfe7 13a4fed4 --stat`). |

Earlier per-surface reviews remain as recorded in each change's
`validation.md` (two clean fixed-SHA reviews for revision pagination; a clean
standards/security re-review at `cbe69543` for Settings).

P3 notes from the `b2019bae..b061e4df` review (optional follow-ups, not
blockers): the SemVer pattern exists as two lockstep-maintained copies
(`server/src/shared/infrastructure/workspace_manifest.ts:8` and
`server/scripts/qa/check_ssot.mjs:21`) with no structural sync guarantee; and
`server/tests/infrastructure/workspace_manifest.test.ts:115` places an import
after the describe block. The review verified the SemVer fix is
semantics-preserving and closes the exponential-backtracking vector, and that
the export test-identity change is backed by the product's
`quarantineOwnedFile` inode mechanism rather than test self-deception.

## CodeQL configuration comparison reconciliation (#457 item 6)

- Current analysis is workflow-only:
  [`.github/workflows/codeql.yml`](../../.github/workflows/codeql.yml) runs a
  `javascript-typescript` matrix with
  [`.github/codeql/codeql-config.yml`](../../.github/codeql/codeql-config.yml)
  (paths `server/src`, `server/scripts`, `frontend/src`; generated/dependency
  trees ignored). Default setup state is `not-configured`
  (`gh api repos/Jackela/Novel-Engine/code-scanning/default-setup`).
- Analysis history (read via the code-scanning analyses API) contains two
  categories: `language:python` (73 analyses, latest
  `2026-08-25T07:09:48Z` at commit `3d148cc`, PR #299 merge) and
  `language:javascript-typescript` (continuous since, latest on `13a4fed4` at
  `2026-09-05T02:38:28Z`).
- Conclusion: the configuration-comparison warning in the code-scanning UI is
  the expected consequence of pre-cutover analyses (python + TypeScript
  matrix, before the Python stack retired at tag `python-final`) coexisting
  with current TypeScript-only analyses. The historical analyses are retained
  deliberately as security evidence of the Python era. No analysis was
  deleted and no configuration was changed to silence the warning; the
  required `Analyze (javascript-typescript)` gate is live and green on main.

## OpenSpec task reconciliation

### `2026-09-03-paginate-revision-history` — tasks 5.1 and 5.2 closed

- 5.1: every listed regression category maps to named passing coverage on
  `13a4fed4` — revision create/save/restore (`server/tests/api/studio_revisions.test.ts`),
  import (`studio_imports.test.ts`, word-count seed assertions), proposal
  accept (`studio_proposals.test.ts`, `proposal_acceptance_transactions.test.ts`),
  word-count invariants (`revision_word_count.test.ts`), migration/startup
  (`revision_word_count_reconciliation.test.ts`, `startup_pipeline.test.ts`,
  `qa_gate_regressions.test.ts`), authorization
  (`studio_revision_pagination_contract.test.ts`,
  `studio_revision_cursor_contract.test.ts`), OpenAPI/type drift
  (`openapi_snapshot.test.ts` + `check:api-types`), query-plan
  (`revision_store_pagination.test.ts` EXPLAIN coverage), frontend
  contract/cache (`apiContract.test.ts`, `api.pagination.test.ts`,
  `useRevisionCache.*`), autosave (`useDocumentDraft.*`), History
  (`StudioHistoryPanel.*` + the smoke History workflow), stale/abort
  (`useRevisionCache.*`, `useStudioActions.lifecycle.test.tsx`,
  `api.test.ts`). No category is uncovered.
- 5.2: every listed surface reran green on `13a4fed4` (table above). The
  server "size" surface is `gate:sizes` inside `pnpm --dir server gates`
  (no standalone size script exists). The Playwright History workflow ran in
  both smoke and full-audit. The independent fixed-SHA review requirement is
  satisfied by the review chain above (segment reviews plus the two clean
  change-scoped reviews already recorded).
- 5.3 remains open: the canonical-spec merge/archive step is deliberately not
  performed in this pass.

### `2026-09-03-restore-project-settings-update` — task 4.3 closed

- Every listed surface reran green on `13a4fed4`: server type-check, lint,
  architecture, size (via gates), full tests, gates; frontend lint, format,
  type-check, unit, build; React diagnostics (`react-doctor` score 100);
  browser workflows (smoke 3 passed — including the Settings persistence
  flow — and full-audit 9 passed); strict OpenSpec 19/19.
- The independent fixed-SHA standards/security review is recorded clean at
  `cbe69543`; the remaining range to the integrated candidate is covered by
  the review chain above with zero Settings-surface product changes after
  `688acfe7`.
- 4.4 remains open: archive step, separately owned.

### `2026-09-03-split-project-shell-document-body` — task 3.6 closed; findings recorded

- 3.6 closes per its own stated condition ("until each churn/removal/error
  scenario is explicitly attributed"). Attribution on `13a4fed4`:
  unexpected revision → `useCurrentDocument.test.tsx` "refreshes the shell
  once and accepts a raced body only when its pointer matches"; project
  vanished → "classifies authentication and project absence globally" plus
  the shell-404 library navigation in `useStudioProject.test.tsx`;
  Document vanished → "refreshes structural authority after a scoped 404
  without inventing a body" plus the `useActiveDocument.test.tsx` fallback
  trio; second churn mismatch → "bounds revision churn to one shell refresh
  and one replacement body read"; shared-cycle and unexpected failures →
  `useCurrentDocument.ownership/unexpected.test.tsx`. All inside the
  464-test frontend full suite.
- Remaining gaps stay open and are ticketed (see below): 1.5 dedicated
  no-sibling-body resume assertion; 3.2 page-level request-ledger assertion;
  3.4 Lore field-intent epoch, beat-command frontend wiring, and the
  reverse/older-revision matrix; 4.1–4.4 browser matrices; 5.1/5.2 missing
  TS-browser workflows (project-switch, reorder, Review run, Export
  failure/retry, cross-resource isolation); 5.3 four-domain single-SHA
  review loop; 5.4 archive.

## Outstanding gates

| Gate | State | Owner / closure condition |
| --- | --- | --- |
| Human acceptance | `not run` | Jackela, via [the acceptance packet](refactor-human-acceptance-2026-09-05.md). Fixtures verified present this session at `/tmp/novel-engine-draft-closeout-20260905/human-fixtures.json` and `human-data/` (temporary; may be reclaimed by the OS). No acceptance server was started this session. |
| OpenSpec archive | `not performed` | Only a change whose own product/spec/validation gates have closed may archive; human acceptance is pending per the standing rule. Merge does not bulk-close tasks. |
| Release authorization | `not granted` | Separate owner decision. |
| Evidence-PR required CI | pending at write time | The docs-only candidate must record green `validate`, `container`, and `Analyze (javascript-typescript)` on its own head SHA (recorded on the pull request). |

## Follow-up tickets

Opened against #457 item 3 (linked from the #457 progress comment):

1. Whole-book resume no-sibling-body proof (shell task 1.5).
2. Page-level bootstrap request-ledger assertion (shell task 3.2).
3. Narrow Lore/beat causal-authority matrix (shell task 3.4: field-intent
   epoch, beat command wiring, reverse/older-revision coverage).
4. Missing TypeScript-backend browser workflows (shell tasks 4.1–4.4 and
   5.1/5.2: project-switch, reorder, Review run, Export failure/retry,
   cross-resource isolation matrix).
