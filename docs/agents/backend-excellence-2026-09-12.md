# Backend Excellence Loop campaign — 2026-09-12

Research-driven refinement + AI-friendliness hardening. NOT a refactor campaign.
Orchestrator: main session (dispatch/adjudicate/review/accept only). Implementation
layer: implementer subagents on `GLM-5.3-Flash`. Loop: audit → adjudicate → fix →
review/merge → retrospect, max 3 rounds or until convergence
(0 P1, P2 ≤ 2 edge-contested).

## Owner decisions

- Campaign scope locked at kickoff (see plan): refinement + AI-friendliness only;
  destructive architecture changes stop the campaign and produce an ADR draft.
- **2026-09-12, Owner AFK at decision point — two forks self-decided on
  recommendation, per established AFK precedent (same pattern as v0.7.0 release):**
  1. **JSDoc standard (A3-06)**: prose-style contract comments with explicit
     failure semantics are declared this repo's equivalent standard; no repo-wide
     `@param/@returns/@throws` tag retrofit. Global CODING_STANDARDS tag
     requirement is satisfied by the declared repo override.
  2. **`.env.local` cwd semantics (A6-F1, P1)**: fix direction A — anchor
     `envFile`/`workingDirectory` defaults to the workspace root (reusing the
     `workspace_manifest` resolution pattern), plus regression tests and
     `.gitignore` `server/data/` coverage.
  Both remain listed here for Owner review; reopen if overruled.

## Phase 0 — probe & baseline (2026-09-12)

- Flash probe: **PASS**. implementer dispatch returned `server/package.json`
  version `0.7.0` verbatim; subagent reported model
  `builtin:bigmodel-coding-plan/GLM-5.3-Flash`. Work tickets dispatched.
- Baseline: `git status` clean (only untracked `.zcode/` harness state); main @
  `863fea281c1b50abf5f72d9cedc247f2e248891d`
  (`863fea28 chore(deps): clear dependency-audit advisories (#493) (#516)`).
- `pnpm --dir server gates` — PASS (ssot 0.7.0 aligned, repo-hygiene clean,
  file-size clean 706 files / limit 300 / 0 legacy baselines, migration-channel
  clean, llms-txt clean 21 links, OpenAPI snapshot 1/1).
- `pnpm spec:validate` — PASS (`openspec validate --all --strict`: 1/1).

Premise correction at kickoff: the task brief claimed "llms-full.txt was formally
exempted"; A5 verified via `git log --all --full-history` + `git log -S` that it
**never existed** — no file, no content mention, no exemption registry. Removed
from campaign narrative.

## Wave A — Round 1 results (7 read-only Explore agents, 2026-09-12)

Raw findings: **68 (P1 × 6 / P2 × 25 / P3 × 37)**. Highlights:

- A1 architecture: **zero actual contract violations** in import reality;
  gaps are rule-coverage (depcruise regex misses `shared/application`, ai
  non-ports tree) and semantic ownership (studio jobs/usage tables live in
  shared kernel schema).
- A2 complexity: 4 P1 hotspots — `buildApp` (~180 lines, file margin 6),
  `toAppError` (134-line instanceof chain), `publishArtifact` (138 lines),
  `document_routes` (241-line plugin, margin 10); plus duplication families
  (cursor ×5, pageLimit ×5, failed-job literals ×4).
- A3 comments: exceptional discipline (ports 18/18 + ai 1/1 module contracts;
  10 high-risk comment-vs-code checks **zero drift**); real debt is method-level
  failure semantics on 5 key seams + systemic absence of `@throws` tags.
- A4 tests: assertion strength unusually high (CSRF dual codes, SSE error
  frames, retry idempotency matrix, usage UTC zero-fill, 4×capacity 422, FTS
  hostile input intact). Gaps: accept-proposal 409 not HTTP-locked/declared;
  token-bucket refill zero coverage.
- A5 docs: error-codes three-way sync 20/20; ci-gates/README/ADR 0001–0010 all
  verified accurate. Drift: quickstart setup-route location, workspace missing
  `tools/api-types`, llms.txt missing ADR-0006..0010, minor line/pagination
  drift.
- A6 AI-friendliness: llms.txt 21/21 links exist, 6/6 spot-checked publicly
  reachable, 0 description drift. **P1: README's documented cold-start silently
  ignores root `.env.local` under `pnpm --dir server cli serve` (envFile/working
  Directory default to cwd=server/); DB lands in git-unignored `server/data/`.**
- A7 dead code: zero orphan files, zero TODO markers; 1 P1 dead shim
  (`readWorkspaceVersion` documented in AGENTS.md CODE MAP but 0 references);
  ~26 dead type aliases/re-exports; ~143 needless exports; python-parity
  comments describe archived code as current authority.

## Wave B — Round 1 adjudication (main session, 2026-09-12)

Spot-verification: all 6 P1s **confirmed by direct code read**
(`readWorkspaceVersion` grep 0 refs; `server_config.ts` envFile `./.env.local` +
workingDirectory `process.cwd()` defaults; app.ts awk-measured 294 code lines;
toAppError/publishArtifact/document_routes line evidence; depcruise regex gap
read directly). Dedup merges: A2-F7≡A7-F09, A2-F8≡A7-F10, A5-02≡A6-F08,
A5-06≡A6-F03.

Disposition: **17 fix-now tickets (T1–T17), 6 deferred issues (D1–D6),
3 waivers.** Fix tickets are batched by file-disjointness:

- **Batch 1**: T1 arch-rules, T3 errormap-table, T4 publish-split, T6
  usage-agg-move, T8 jsdoc-failures, T10 accept-409, T11 tokenbucket-tests,
  T12 assertions.
- **Batch 2** (after batch 1 merges): T2 buildapp-split, T5 revision-routes,
  T9 comment-gaps, T13 docs-drift, T17 python-comments.
- **Batch 3**: T7 artifact-port (+method contracts), T14 dead-code, T16
  error-codes-gate.
- **Batch 4**: T15 env-cwd-anchor (needs T13/T17 landed first).

### Findings ledger (Round 1)

| Finding | Sev | Summary | Disposition |
|---|---|---|---|
| A1-F1 | P2 | depcruise `functional-core-isolation` misses `shared/application` target | fix → T1 |
| A1-F2 | P2 | depcruise ai rules leave `ai/domain`+root unconstrained | fix → T1 |
| A1-F3 | P2 | studio jobs/usage/jobEvents tables defined in shared kernel schema | defer → D1 (migration risk) |
| A1-F4 | P3 | `ExportArtifactGateway` port types live in 306-line service file | fix → T7 |
| A1-F5 | P3 | `ports/studio_store.ts` is a cross-capability type bazaar (175 lines) | defer → D2 |
| A1-F6 | P3 | cli main.ts guarded top-level await (import-time side effect, defended) | **waive**: dual argv/import.meta guard, no db/app at module scope |
| A1-F7 | P3 | two benign module-level singletons (dummy-hash memo, transport descriptors) | **waive**: documented, no state leakage |
| A1-F8 | P3 | depcruise apps exemption spans whole `src/apps/**` | defer → D2 |
| A2-F1 | P1 | `buildApp` ~180 lines / file margin 6 code lines | fix → T2 |
| A2-F2 | P1 | `toAppError` 134-line instanceof chain (13 same-shaped branches) | fix → T3 |
| A2-F3 | P1 | `publishArtifact` 138-line four-phase function | fix → T4 |
| A2-F4 | P1 | `documentRoutes` 241-line plugin, 8 routes, margin 10 | fix → T5 |
| A2-F5 | P2 | `job_store_part.ts` margin 5; inline usage SQL aggregation | fix → T6 |
| A2-F6 | P2 | export recovery chain: 4 multi-phase 60–94-line functions | defer → D3 |
| A2-F7≡A7-F09 | P2 | cursor encode/decode boilerplate ×5 | defer → D3 (wire-contract risk) |
| A2-F8≡A7-F10 | P2 | pageLimit brand+clamp boilerplate ×5 (+frontend 6th) | defer → D3 |
| A2-F9 | P2 | document seed write sequence ×3 copies | defer → D3 |
| A2-F10 | P2 | failed-job literal six-pack ×4 sites | defer → D3 |
| A2-F11 | P2 | proposal pipeline 3× same skeleton; retry preamble coupled | defer → D3 |
| A2-F12 | P3 | per-route error-response constant sets | defer → D3 |
| A2-F13 | P3 | proposal_landing mixes prompt vocab + code-point counter + landing | defer → D3 |
| A2-F14 | P3 | dashscope incremental extractor covers 3 transport modes | defer → D3 (adjacent to #502) |
| A2-F15 | P3 | export dual prefix; file↔class name mismatch; orchestration suffix variance | defer → D3 (freeze new increments) |
| A3-01..05 | P2 | failure semantics invisible on 5 key seams (generateStructured, advanceDocument, acquire, export service ×4, payload builders) | fix → T8 (+T7 for export service) |
| A3-06 | P2 | systemic `@param/@returns/@throws` absence vs global standard | **ruled**: prose+failure-semantics declared equivalent (see Owner decisions); declaration lands with T13 |
| A3-07..12 | P3 | comment gaps: version_route, cors policy, scaffold scanner, retry executor, review record, misc types | fix → T9 |
| A4-F1 | P2 | accept-proposal 409 REVISION_CONFLICT not HTTP-tested, not declared in OpenAPI | fix → T10 |
| A4-F2 | P2 | token-bucket refill/retryAfter/sweep zero coverage | fix → T11 |
| A4-F3 | P3 | stream CSRF test lacks error.code assertion | fix → T12 |
| A4-F4 | P3 | malformed-JSON test tolerates {400,422} + loose code assert | fix → T12 |
| A4-F5 | P3 | no coverage threshold | **waive**: current assertion discipline + qa gates sufficient; threshold adds flake/CI time |
| A5-01 | P2 | quickstart points GET /api/setup at studio http dir (actually shared auth_routes) | fix → T13 |
| A5-02≡A6-F8 | P2 | workspace declared as 2 packages; `tools/api-types` missing from AGENTS.md/openwiki | fix → T13 |
| A5-03 | P3 | CODE MAP `assembleResidentContext` line drifted to :136 | fix → T13 |
| A5-04 | P3 | STRUCTURE gates comment omits llms-txt | fix → T13 |
| A5-05 | P3 | CONTEXT.md lacks Search/FTS5 term | fix → T13 |
| A5-06≡A6-F3 | P3 | llms.txt lists only ADR-0001..0005 (repo has 10) + missing architecture pages | fix → T13 |
| A5-07 | P3 | studio-workspace says 72ch; editor.css is 75ch | fix → T13 |
| A5-08 | P3 | debounce/residentMatchCorpus symbol attribution drift | fix → T13 |
| A6-F1 | P1 | README cold-start silently ignores root `.env.local`; DB in unignored `server/data/` | fix → T15 (direction A, ruled above) |
| A6-F2 | P2 | error-codes.md over-promises NOT_FOUND message ids (4/20 sites) | fix doc now → T13; code convergence defer → D6 |
| A6-F4 | P3 | no .nvmrc / root engines for node 24 | fix → T13 |
| A6-F5 | P3 | pnpm acquisition not documented | fix → T13 |
| A6-F6 | P3 | error-codes lockstep unguarded (gate candidate) | fix → T16 (new guard) |
| A6-F7 | P3 | capacity messages lack resource/limit inline | defer → D6 |
| A7-F01 | P1 | `readWorkspaceVersion` dead shim documented in CODE MAP | fix → T14 (code+doc line) |
| A7-F02 | P2 | 15 dead `Static` type aliases in studio_request_schemas | fix → T14 |
| A7-F03 | P2 | 2 dead type exports (ProposalStreamError, ReviewIssuePayload) | fix → T14 |
| A7-F04 | P2 | 7 dead re-export entries across server+frontend | fix → T14 (respect SYSTEM_PROMPT test import) |
| A7-F05 | P2 | live alembic_version python-schema guard in startup chain | defer → D4 (Owner support-window decision; data-safety rail — do not touch before ruling) |
| A7-F06 | P3 | ~143 needless exports (used in-file only) | defer → D5 |
| A7-F07 | P3 | `isRecord` guard ×3 in frontend | defer → D3 |
| A7-F08 | P3 | generation/export retry capacity outcome twin files (~70% same) | defer → D3 |
| A7-F11 | P3 | python-parity comments present archived code as current authority (~15 files) | fix → T17 (workspace_manifest.ts part lands in T14) |
| A7-F12 | — | positive: zero TODO/FIXME debt, zero orphan files | no action |

### Waivers (with reasons)

1. **A1-F6** (cli top-level await): guarded by argv[1]+import.meta.url dual check;
   no db/app instances at module scope; tests import without triggering.
2. **A1-F7** (module-level singletons): bcrypt dummy-hash memo is a documented
   timing-attack constant; DashscopeTransport descriptors are pure data. No
   leaked runtime state.
3. **A4-F5** (coverage threshold): assertion discipline is demonstrably strong;
   a threshold gate adds CI flake/time without guarding a demonstrated failure
   mode.

## Wave C/D — Round 1 execution log

### Batch 1 (8 tickets, worktrees `/tmp/ne-517…524`, dispatched 2026-09-12)

| Ticket | PR | Implementer | Reviewer | Merge |
|---|---|---|---|---|
| #517 arch-rules | #540 | done `f6264962` (probe-verified blocking) | approve-with-comments (P3 naming note) | merged |
| #518 errormap-table | #541 | done `a7e2f587` (13-branch table, byte-equal) | approve, zero findings (full 13-branch equivalence audit) | merged |
| #519 publish-split | #547 | partial→done `d48e6099`+`3f932829` | approve, zero findings (full symbol-by-symbol diff) | merged |
| #520 usage-agg | #542 | done `2d3134b6` (295→258 lines) | approve, zero findings | merged |
| #521 jsdoc-failures | #543 | done `e3b77145` (+40/−0 comments) | approve (all 5 seam claims verified vs implementation) | merged |
| #522 accept-409 | #544 | done `fd8fbff2` (+`8ce5b69f`) | request-changes → **P1 caught**: api-types drift; fixed by gen:api-types in-session (generated artifact, mechanical) | merged |
| #523 tokenbucket-tests | #545 | done `b1a08322` (mutation-verified) | approve-with-comments (2 P3 comment precision) | merged |
| #524 assertions | #546 | done `aecd3d32` | approve-with-comments (P3 comment suggestion) | merged |

Orchestrator rulings during batch 1:
- #519 file-size conflict (347 > 300 after same-file split): ruled **no
  LEGACY_LIMITS entry** (zero-exception baseline is a repo invariant);
  authorized sibling-module extraction instead. Residual: stages file at 297/300
  (3-line margin) — fs-primitives extraction (`writeDurableFile` family)
  appended to the D3 complexity backlog.
- #520 258 vs ~255 approximate target: accepted (gate margin is the binding
  constraint).
- Reviewer P3 comment-precision notes (#545 ×2, #546 ×1): recorded, not applied
  (one-line comment tweaks below the PR-noise threshold) — added to ledger
  residuals.

### Batch 2 (5 tickets, worktrees `/tmp/ne-525…529`, based on origin/main@2b7b1c8d)

| Ticket | PR | Implementer | Reviewer | Merge |
|---|---|---|---|---|
| #525 buildapp-split | #548 | done `1cde701e` (app.ts 294→207; 4 blocks sunk) | approve-with-comments (2 P3: AppOptions field duplication, positional params → backlog notes) | merged |
| #526 revision-routes | #549 | done `61ca2408` (document_routes 290→210; snapshot zero-diff proven by before/after regen) | approve, zero findings | merged |
| #527 comment-gaps | #550 | done `14bee48e` (+52/−0) | **2× P2 comment inaccuracies caught** (CORS "exactly what routes use" false — 3/9 headers unconsumed; retry replay wording misses running-window 409) + 1 P3 → fix-up commit applied | merged after fix-up |
| #528 docs-drift | #551 | done `24b3ac30` (11/11 items; llms.txt 21→31 links) | approve with **P1 caught**: MarkdownEditor.tsx:66 runtime 72ch theme override likely beats editor.css 75ch — the original A5-07 finding was half-right | merged; code fix split to #553 |
| #529 python-comments | #529 | done `1a8b25c3` (22 sites self-contained, 9 kept as legitimately historical; zero code lines) | approve (P3: implementer count 23 vs 22 — reporting nit) | merged |

New findings spawned during batch 2 (self-learning loop producing tickets):
- **#553** (P2→bug): stale `maxWidth: "72ch"` runtime override in MarkdownEditor.tsx duplicates editor.css 75ch (SSOT of record); render reality follows the override. Found by #551's reviewer doing cascade analysis — docs gate can't catch UI-fact drift.
- **#554** (P2): `x-total-count` dead CORS exposure (no producer, no consumer; found by #527 implementer refusing to fabricate a rationale).
- Backlog notes appended to D3/D2: AppOptions↔module-interface field duplication (#548 P3), assembleStudioServices positional params (#548 P3), GUARD_RESPONSES per-file duplication (#549 note), DEFAULT_DATABASE_URL SQLAlchemy-style URL legacy (#529 note), openwiki Primary sources missing useDocumentDraftAutosave (#528 note).

### Batch 3 (4 tickets, based on origin/main@fb791440)

| Ticket | PR | Implementer | Reviewer | Merge |
|---|---|---|---|---|
| #530 artifact-port | #555 | done `85d22a40` (gateway+4 types → ports/artifact_gateway.ts; 293/54 lines; 4 method contracts verified against impl) | approve, zero findings (verbatim migration + contract-accuracy full check) | merged |
| #531 dead-code | #556 | done `a953cde9` (11 files −60; wordCount re-export kept — **audit false positive**: 5 test consumers) | approve (kept-exception ruling independently confirmed) | merged |
| #532 errcodes-gate | #557 | done `0de9f100` + fix-up `ff019721` | approve after fix: reviewer **tamper-verified a fail-open hole** (duplicate catalog row last-wins) → fix + 3 regression cases; test split into new file (file-size forced, per ssot_gate precedent) | merged |
| #553 editor-width (spawned) | #558 | done `ae87afd3` (72ch + redundant margin removed) | approve — **cascade truth corrected**: style-mod mounts CM styles at head TOP, editor.css was already winning; PR is pure SSOT dedup, no visual change (PR body + issue record corrected) | merged |

### Batch 4 (2 tickets + 1 spawned, based on origin/main@fb791440)

| Ticket | PR | Implementer | Reviewer | Merge |
|---|---|---|---|---|
| #533 env-cwd-anchor (P1, direction A) | #560 | done `bcd0d434` (lazy `locateWorkspaceRoot()` defaults; eager version caught by existing fs-mock tests and corrected; 4+1 regression tests; container reasoning verified) | approve-with-comments → P3 fix-up (spy-assert locator-not-called) | merged after fix-up |
| #554 x-total-count (spawned) | #559 | done `24647f9d` (one line; grep evidence in commit) | main-session review (one-line dead-constant removal; evidence chain personally verified twice — reviewer deviation recorded) | merged |
| — | #550 (batch 2 spillover) | fix-up `cdc718f3` (3 comment wording fixes) + orchestrator-resolved merge conflict with #548 | main-session verification of wording | merged |

#### Round 1 closeout state

19 issues filed (17 planned + 2 spawned #553/#554), 21 PRs (#540-#560), all
merged green. Deferred: #534-#539. Waived: 3 (see ledger).

## Round 2 — convergence audit (2026-09-12, revised prompts)

7 read-only agents on main@179a0e51. **Result: 0 P1 / 3 P2 / ~10 P3.**

- Regression checks passed across the board: all Round-1 splits stable
  (stages 297, document_routes 210, app 207 — no post-merge additions); all
  new tests still precisely lock behavior; both OpenAPI/api-types baselines
  in sync; A1 even source-verified the depcruise toolchain assumptions
  (swc tracks `import type`; .js-suffix resolution) — the gates truly watch.
- **P2s (all small, mechanical, 2 self-inflicted by Round 1):**
  A3-F1 rawText contract comment inaccurate vs deterministic provider
  (#521's own new comment); A7R2-01 `renderResidentContextSections` orphan
  (#556 deleted its only consumption path but not the body); A7R2-02 two
  missed Static aliases (ProjectUpdateBody/DocumentCreateBody).
- Notable P3s: stages file 3-line margin (tracked in D3); dead
  `REVIEW_SEVERITIES` island; dead `EXPORT_PUBLICATION_VERSION` re-export
  (#519-introduced); AGENTS.md gate-enumeration lines still missing
  error-codes (known closeout item); CODE MAP :136→:135 regressed again
  (line-number brittleness); error-codes.md accept-409 action guidance;
  `.env.example`/README variable coverage gap (7 read-but-undocumented vars
  — the example file itself is in the forbidden `.env*` zone, so the fix is
  README-side); CORS expose-headers list not locked by test; error-codes
  gate missing 4 fail-closed tamper directions.
- **Adjudication**: batch 5 (residual wave) fixes the mechanical set as 4
  disjoint tickets; frontend giant-hooks family (useDocumentDraft 280-line
  et al., all pre-campaign stock) and stream_json_unwrapper complexity
  (#497) defer to a new issue; isDescendant ×4 dedup appended to D3;
  OpenSpec subdirectory-launch scenario noted as future change decision.

### Batch 5 (residual wave, Round-2 fixes)

| Ticket | Scope | Reviewer |
|---|---|---|
| #562 r2a dead-code residuals (A7R2-01..05: 5 deletions) | code deletions | reviewer |
| #563 r2b comment accuracy (A3-F1/F2/F3 + error-codes.md accept action) | comments + doc line | reviewer |
| #564 r2c docs closeout bundle (AGENTS.md gate lines ×2 + :136→:135 + twins wording + WHERE-TO-LOOK row + CODE MAP symbol; openwiki overview gates line; README env vars; llms.txt gate mention) | docs | reviewer |
| #565 r2d test hardening (CORS expose-headers precise assert; error-codes gate +4 fail-closed tamper directions) | tests | reviewer |

Also deferred this round: #561 (frontend giant-hooks family, stock debt);
D3 comment appended (isDescendant ×4, stream_json_unwrapper, document_routes
residual).

### Batch 5 results (2026-09-12)

| Ticket | PR | Result |
|---|---|---|
| #562 dead-code residuals | #566 | 4/5 deleted; **item 4 refused with evidence — Round-2 audit false positive** (`EXPORT_PUBLICATION_VERSION` re-export has two live importers: manifest_evidence.ts:8, cleanup_journal.ts:11); reviewer independently confirmed the refusal |
| #563 comment accuracy | #567 | 4/4; reviewer P3 (deterministic review-step carve-out) applied as reviewer-prescribed one-line fix in-session |
| #564 docs closeout bundle | #568 | 8/8; reviewer P3 (gate enumeration order vs chain) applied in-session |
| #565 test hardening | #569 | 2/2; join(', ') canary judged intentional; two adjacent hardening candidates recorded |

## Convergence decision (campaign close)

- Audit rounds used: **2** (Round 1 full 68-finding wave + Round 2 revised-
  prompt wave returning 0 P1 / 3 P2 / ~10 P3), plus one residual fix wave
  (batch 5) — within the 3-round cap.
- After batch 5, every Round-2 finding is either fixed (mechanical residuals),
  deferred with a ticket (#561 frontend hooks family; D3/D2/D5/D6 appends), or
  waived with reason. Remaining open P2-class items are pre-campaign stock
  debt outside this backend campaign's scope, all tracked.
- A third full audit wave would re-surface only deferred-ticket items;
  campaign declares convergence. (A light post-batch-5 verification pass ran
  as part of CI on the merged tree: all 7 gates + spec green at the final
  merge.)

## Final ledger state (all waves)

**fixed via PR (22 issues closed):** #517 #518 #519 #520 #521 #522 #523 #524
#525 #526 #527 #528 #529 #530 #531 #532 #533 #553 #554 #562 #563 #564 #565 —
26 PRs merged green (#540-#560, #566-#569, plus this closeout).

**deferred (7 open issues):** #534 schema ownership · #535 architecture
polish (depcruise apps-exemption breadth, studio_store cohesion,
AppOptions duplication) · #536 complexity dedup backlog (+Round-2 appends) ·
#537 alembic guard lifecycle (Owner support-window decision) · #538
needless-export batch (~211 in-file-only exports per Round-2 count) · #539
error-message enrichment · #561 frontend giant-hooks family.

**waived (4, reasons on record):** A1-F6 (guarded cli top-level await),
A1-F7 (benign module singletons), A4-F5 (coverage threshold), A7R2-04
(EXPORT_PUBLICATION_VERSION "dead re-export" — audit false positive,
refused by implementer re-grep and confirmed by reviewer).

**Audit quality trail (self-learning evidence):** 3 audit false positives
across both rounds (wordCount token-corpus undercount; 72ch cascade
intuition vs source-level truth; re-export-as-SSOT-transit miscount) — every
one caught before merge by the implementer-re-grep or reviewer layer, zero
shipped. Round-2 prompt revisions (import-statement counting, source-level
verification of runtime claims, verification-method labels) are recorded
above and produced a materially cleaner wave (0 P1).

## Final report numbers

- Baseline main@863fea28 → campaign end: 26 merged PRs, ~3,000 added /
  ~1,100 removed lines across server/frontend/docs.
- Waves: A(7 audits R1) → B(adjudicate: 17 fix/6 defer/3 waive) → C/D in 4
  batches (21 PRs) → E retrospective → A(7 audits R2, revised prompts) →
  batch-5 residual wave (4 PRs) → closeout.
- Review layer: 26/26 PRs reviewed (24 subagent depth-1, 1 main-session
  one-liner (#559), 1 in-session re-review (#550 wording)); reviewer-caught
  issues: 1 P1 (api-types drift), 5 P2 (2 comment inaccuracies, cascade
  mis-narrative, gate fail-open hole, false-positive refusal), 6 P3.
- Rework rate: 5 fix-up commits across 26 PRs (19%); 2 merge conflicts
  (both orchestrator planning gaps, resolved deterministically); 0 CI
  failures shipped to main; 0 waivered regressions.
- New executable guard shipped: gate:error-codes (three-way lockstep,
  fail-closed on duplicates/unparsable, 12 tamper regression cases).
- AI-friendliness before → after: README cold-start silently ignoring root
  .env.local → workspace-root-anchored (source-verified chain); llms.txt 21
  → 31 links + lockstep mention; error-codes doc unguarded → gated; NOT_FOUND
  over-promise → honest + accept-409 action guidance; no .nvmrc/pnpm/env-var
  docs → present; python-parity comments as false authority → self-contained;
  CORS dead exposure → removed and test-locked.

## Wave E — Round 1 retrospective (self-learning)

### Audit quality review

**False positives found and corrected during execution (2.5):**
1. A7-F04 `wordCount` re-export declared dead — actually 5 test consumers
   (#531 implementer re-grep caught; reviewer independently confirmed). Audit
   corpus methodology under-counted test imports.
2. The 72ch "runtime override wins the cascade" claim (A6/#551 review chain) —
   source-level analysis (#558 reviewer: style-mod inserts at head top, before
   editor.css) proved editor.css already won. The doc-drift finding was real;
   the effectiveness claim was wrong. Lesson: cascade claims need source-level
   verification, not "injected later wins" intuition.
3. (minor) A4's brief premise said OPERATION_CAPACITY_EXCEEDED → 429; actual
   mapping is 503 (A4 itself corrected this in its report).

**Audit true-positive highlights:** all 6 P1s confirmed by direct read;
A5/A6 doc-drift items all real (11/11 fixed); llms.txt coverage gap real
(21→31 links).

**Prompt revisions for Round 2 (see Prompt revision history).**

### Review-layer value (why every PR gets a reviewer)

- #544: api-types drift after OpenAPI regen (P1, CI would have failed).
- #550: 2 comment↔implementation inaccuracies (P2×2).
- #557: fail-open hole in the new gate, tamper-verified (P2).
- #560: lazy-resolution property only behaviorally locked (P3 → hardened).
- #558: corrected a wrong cascade narrative before it fossilized.

### Process lessons (Round 1)

1. **Batch disjointness must be pairwise across ALL file scopes including
   destination files** — batch 2's #525 (CORS block sinking into
   cors_registration_policy.ts) overlapped #527 (comment additions to the same
   file); undetected at planning, surfaced as PR #550's merge conflict
   (resolved by hand: main's structure + fixed comment). Checklist item added.
2. Merge-ring economics: strict up-to-date protection ⇒ ~10 min per PR; 21 PRs
   ≈ 3.5 h of serial CI across the round. Budget batches accordingly; consider
   larger-per-PR batching when files allow.
3. Local git transport is flakier than gh API (URL-scoped proxy key bypass +
   10× retry loop is the working recipe); pushes from worktrees occasionally
   "succeed" without pushing — always verify remote ref before gh pr create.
4. The existing test suite caught an eager-locator regression (#533 first
   draft) before any human review — hermetic tests double as design review.
5. Full-suite flakes under parallel worktree load: rerun-with-full-logs
   discipline absorbed all of them (0 false regressions shipped).

### Pattern-learning candidates (guards proposed)

- **Dual-SSOT in CM theme vs editor.css** (#553/#558 adjacent finding):
  propose a contract-test assertion that editor.css is the sole declarer of
  editor content width/focus outline → ticket filed in Round-2 backlog if
  Round 2 confirms recurrence.
- **error-codes lockstep gate** (#532): shipped this round.
- TS-side duplicate-entry dedup in the error-codes gate parser (P3 note from
  #557 fix-up): folded into the guard's issue as a follow-up comment, not
  ticketed (code-side duplicates are review-caught).

### Merge-ring friction (recorded for the pattern library)

- Repo has **strict up-to-date branch protection**: every merge makes all other
  open PRs BEHIND → each PR needs `update-branch` + fresh CI (~9 min) before its
  own merge. N disjoint PRs = N sequential CI rounds; budget accordingly.
- `gh pr checks --watch` exits early when the post-update CI run is still
  registering jobs → merge retry window must poll `gh pr merge` directly at
  ≥25s intervals for ~10+ min per PR, not rely on watch.
- Parallel full vitest suites across worktrees can flake under CPU contention
  (observed 2×: single-test failures that vanish on full-log rerun). Mitigation
  applied: implementers must rerun failures once with untruncated logs before
  reporting; treat persistent-only failures as real.

## Prompt revision history (self-learning trail)

- Round 1 Wave A: baseline prompts as dispatched.
- Round 2 Wave A (revised 2026-09-12 after Round-1 retrospective):
  1. **A7 dead-code**: reference counting must analyze actual import
     statements (not token corpus) and categorize "src-dead but
     test-consumed" separately — Round 1's `wordCount` false positive came
     from a token corpus that under-counted test imports.
  2. **A6 AI-friendliness (+ any face making runtime/cascade claims)**:
     behavioral claims about CSS cascade, module side effects, or runtime
     ordering must be source-level verified (read the library code path) or
     explicitly labeled hypothesis — Round 1's "runtime 72ch wins" claim was
     intuitively plausible and wrong (style-mod inserts at head top).
  3. **All faces**: findings must state the verification method used
     (grep/read/executed) so Wave B can weigh confidence.
  4. **A2 complexity**: also check destination-file overlap when proposing
     moves/splits (a split target can collide with other in-flight work) —
     feeding the batch planner.

## Lessons

1. **Ticket scope must pre-check file-size headroom for "same-file split"
   instructions** (#519): a split that adds named functions + state interfaces
   to a 289/300 file cannot fit; prescribe sibling-module extraction from the
   start when margin < ~60 lines.
2. **Snapshot-touching tickets must include `pnpm --dir frontend gen:api-types`
   in the acceptance command list** (#522): OpenAPI regen without generated
   types drift will fail CI; reviewer caught it, but the ticket should have
   mandated it. Applied to the dispatch template for any snapshot-regen ticket.
3. **Merge ring**: see "Merge-ring friction" above — patient polling loop,
   sequential per-PR update+CI+merge, expect ~10 min per PR wall clock.
4. **Test-suite parallelism**: concurrent multi-worktree full-suite runs can
   flake; rerun-with-full-logs discipline absorbed into dispatch template.

## Skips and residuals

- None yet beyond deferred tickets D1–D6.
