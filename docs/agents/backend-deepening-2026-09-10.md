# Backend architecture deepening — 2026-09-10

Campaign evidence for the backend architecture-deepening pass (candidates 1+2
of the architecture review; skills chain: `improve-codebase-architecture` →
`codebase-design` vocabulary; implementation by general-purpose subagents,
main agent orchestrated, reviewed, and accepted). Scan report (subagent,
hot-spot-scoped to `contexts/studio`): 5 candidates, 2 Strong selected;
protected list (Export publication cluster per ADR-0007, thin-router pattern,
resident_context/lorebook assemblers) untouched.

## B1 — Narrow the StudioStore aggregate (`7189957e`)

- Deleted: `infrastructure/drizzle_studio_store.ts` (310-line forwarding
  shell) and the `StudioStore` aggregate + 4 barrel re-export groups in
  `ports/studio_store.ts` (328→175 lines).
- Every application service now declares only the part ports it uses; new
  composition-root factory `apps/studio_persistence.ts` instantiates and
  distributes the 8 parts; `buildApp` injection semantics unchanged.
- 13 service constructors narrowed; new focused ports `document_store.ts`,
  `project_store.ts`; `renumberDocuments` ownership aligned to
  `volume_store.ts` per ADR-0005.
- Tests: 31 files mechanically retargeted (spy prototypes → parts, fake
  types → narrow ports, facade calls → part prefixes); assertions untouched
  (independent code-reviewer verified 12 representative files line-by-line).
- Verification: type-check/lint/arch/test (212 files, 1324 tests)/gates all
  green; OpenAPI snapshot byte-identical (not regenerated); reviewer
  findings: one [P3] duplicate import — fixed by main agent (biome
  organize-imports, lint clean).
- Net: 74 files, +1044/−1030; locality: "how a Job lands" is one hop; part
  ports are fakeable test surfaces for the first time.

## B2 — Consolidate the proposal pipeline (`f5e6f71e`)

- Diff-mapping first (per ticket): the three sequences (sync draft, SSE
  stream, job retry) share every load-bearing step; differences are only
  transport, landing target, permit ownership, and usage provenance — no
  substantive divergence, unification safe.
- New `application/proposal_pipeline.ts` (`ProposalGenerationPipeline`,
  constructed once, owns all prompt/landing config incl.
  `loreBudgetCharacters`) + `application/proposal_admission.ts` (pure
  admission half, consumed by pipeline and review retry — has independent
  reason to exist).
- Entrypoints slimmed: `proposal_service.ts` 205→118 physical lines,
  `proposal_streaming.ts` 188→77, retry's proposal sequence is a one-line
  pipeline delegation. `job_retry_executor.ts`'s hand-written landing JSON
  replaced by `proposal_landing.completedProposalLanding()` — retry/draft
  landing shape now equal by construction.
- Config threading: 7 files / 5 constructor layers → `app.ts` →
  `createStudioServices` → pipeline.
- Verification: full suite green (212 files / 1324 tests), gates 6/6,
  `spec:validate` 2/2, OpenAPI byte-identical, SSE tests unchanged and
  passing; ADR-0004 untouched (resident_context/lorebook not in diff).
- Reviewer findings: one [P3] — the retry chain's clock split into two
  injection points after the refactor (pipeline `now` vs executor `now`).
  Fixed by main agent: `ProposalRetryRequest` now carries an explicit `now`
  sourced from the executor's single injection point
  (`proposal_admission.ts`, `proposal_pipeline.ts:236,268`,
  `job_retry_executor.ts`); full validation re-run green.

## Skips and residuals

- Candidates 3 (capacity replay recognition into the Job payload exit) and
  4 (provider payload logic out of the dashscope namespace) remain
  unimplemented — Worth exploring, queued as follow-ups.
- Candidate 5 (payloads.ts utility relocation) Speculative — not planned.
- `proposal_pipeline.ts` sits at 289/300 code lines; further sequence
  growth must continue the split.
- Commits local on `main`, not pushed (PR #494 covers the frontend batch
  only; these two commits will need a second PR when the owner asks).
- Process notes: one lint pipe-masking incident during B1 commit (ELIFECYCLE
  exit hidden by `tail`); caught and amended same-commit. flash implementer
  probe still pending a new session — both tickets ran on general-purpose.
