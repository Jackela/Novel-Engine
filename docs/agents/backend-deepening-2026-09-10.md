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

## B3 — Capacity replay recognition into a single exit (`930b07fe`, 2026-09-11)

- Safety valve triggered honestly: placing recognition inside `jobPayload`
  itself would flip GET `/jobs/:jobId` from 200 to 422 on capacity rows,
  violating the spec's "complete Job detail" requirement. The exit is
  therefore the dedicated `replayedJobPayload` (`job_replay_payload.ts`),
  consumed by the three replay surfaces; the audit GET keeps plain
  `jobPayload` with the split documented in JSDoc (reviewer verified
  against spec.md L2757-2812 and L4910-4960).
- Writer/recognizer now share `as const` key lists locked by `satisfies`
  at compile time (reviewer verified TS2353/TS2741 on key drift); new
  contract test `tests/contexts/job_replay_payload.test.ts` round-trips
  real writer output through the exit (3 cases).
- Equivalence proven per call site (reviewer: recognizer gates on
  `status === "failed"`, rows are immutable post-failure, `claimJobRetry`
  determinism via unique constraint); existing API tests unchanged,
  including the byte-level `expect(replay.body).toBe(first.body)`.
- Reviewer findings: two [P3] (fixture detail-shape mirror, retained
  vendor-flavored naming) — both fixed by main agent before commit.

## B4 — Shared provider payload parsing out of the dashscope namespace (`450712dd`)

- Discovery: `dashscope_payload.ts` + `dashscope_json.ts` contained no
  DashScope-specific logic at all — both deleted (git records
  `provider_payload.ts` as a 56% rename); true vendor protocol remains in
  `dashscope_protocol.ts`, untouched.
- Neutral `provider_payload.ts` (188 code lines) now serves both adapters;
  the inverted dependency (neutral `provider_json` importing vendor
  modules) is gone — reviewer verified 134/134 normalized-line equality
  with the deleted files and zero `dashscope_*` imports in neutral modules.
- Reviewer [P3] (function name `parseDashscopeJsonObject` retained in a
  neutral module) fixed pre-commit: renamed `parseProviderJsonObject`
  (error message unchanged, preserving pure-move semantics; tests pin
  only `/not a JSON object/`).
- Validation on the final tree (both tickets + P3 fixes): type-check,
  lint (0 errors), arch, 213 files / 1327 tests, gates exit 0, spec 2/2,
  OpenAPI snapshot byte-identical.

## Skips and residuals

- Candidates 3 and 4 delivered as B3/B4 above.
- Candidate 5 (payloads.ts utility relocation) Speculative — not planned.
- `proposal_pipeline.ts` sits at 289/300 code lines; further sequence
  growth must continue the split.
- Optional follow-ups surfaced by B3/B4: a dependency-cruiser rule locking
  "neutral providers must not import vendor modules" (config write-set
  exceeded the ticket); literal "recognize-by-default" exit form would
  require an OpenSpec change plus a 422 declaration on the Job-detail
  route.
- Commits local on `main`, not pushed (PR #494 covers the frontend batch
  only; the five backend commits B1–B4 + evidence await a second PR).
- Process notes: one lint pipe-masking incident during B1 commit (ELIFECYCLE
  exit hidden by `tail`); caught and amended same-commit. flash implementer
  probe still pending a new session — both tickets ran on general-purpose.
