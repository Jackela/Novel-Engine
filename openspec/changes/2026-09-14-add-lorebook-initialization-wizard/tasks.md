# Tasks

Dependency graph: `T1` (server extraction pipeline) blocks `T2` (route) and
`T3` (frontend wizard); `T2` blocks `T3`; `T4` (frontend entry points)
depends only on `T3`'s component contracts; `T5` (workflows and gates) is
blocked by all of `T2`–`T4`. Server and frontend write sets are disjoint:
T1 owns `server/src/contexts/studio/application/` extraction files and its
ports wiring; T2 owns the new route file plus regenerated OpenAPI baseline;
T3–T4 own `frontend/src/features/studio/` wizard files; T5 owns
`frontend/tests/e2e-ts/` and evidence docs.

## T1: Server extraction pipeline

- [ ] T1.1 Add the extraction application service (studio context, behind
      a port to the ai context's structured text generation): input
      segments, per-segment Unicode code-point cap, assembled-prompt UTF-8
      byte check under the shared 8,388,608 authority, fail-closed stable
      capacity error before provider construction, and deterministic
      (kind, title) candidate merge with union-of-aliases. Acceptance:
      `pnpm --dir server test -- lorebook_init` green, including
      over-budget boundary tests (exact limit passes, limit + 1 rejects)
      and merge-order determinism.
- [ ] T1.2 Register the `lore-extract` Job type under the synchronous job
      execution model: events for every transition, keyed retry with
      stored outcomes, and exactly one usage event per completed provider
      request under the existing usage accounting rules. Acceptance:
      `pnpm --dir server test -- job` green with new cases for replay
      idempotency and usage singularity on the extraction job.
- [ ] T1.3 Wire the mock (trial) provider path: deterministic placeholder
      candidates for any valid input. Acceptance: `pnpm --dir server test`
      cases proving mock extraction returns the fixed placeholder set and
      real-provider failures stay inside the provider diagnostics boundary
      (no body exposure).
- [ ] T1.4 Confirm the FTS red line: any retrieval added for wizard
      document selection goes through `buildFtsMatchQuery` and
      parameterized MATCH; add malicious-input coverage if a search path
      exists in this change. Acceptance: `pnpm --dir server test -- fts`
      green; review confirms zero new SQL string concatenation.

## T2: HTTP surface

- [ ] T2.1 Add the extraction route (owner-guarded, TypeBox schemas,
      thin-handler discipline) for submitting input segments and reading
      the extraction Job result, reusing the existing job result surface
      where it already fits. Acceptance: `pnpm --dir server test -- <route
      file>` green including auth, validation, and error-envelope cases.
- [ ] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`) and review the diff for
      additive-only changes. Acceptance: `pnpm --dir server gates` green
      including the OpenAPI snapshot gate.

## T3: Frontend wizard flow

- [ ] T3.1 Add the wizard data hook: build input segments (paste box +
      existing-document picker reading current content), submit
      extraction, load candidates, expose per-candidate selection state
      and busy/error states under the explicit asynchronous operation
      state discipline. Acceptance: `pnpm --dir frontend test:unit --
      LorebookWizard` green (hook tests: submit, failure recovery,
      duplicate-submission guard).
- [ ] T3.2 Add the wizard component flow: input step, extraction pending,
      candidate list (kind, title, editable aliases, summary preview),
      confirm step, and per-candidate creation results where a failed
      creation names its candidate and remains retryable. Components stay
      under the 200-line rule; confirmation issues one creation command
      per selected candidate through the existing document creation API.
      Acceptance: `pnpm --dir frontend test:unit -- LorebookWizard` green
      (component tests: candidate toggle, confirm, partial failure,
      abandon leaves nothing).
- [ ] T3.3 Render the trial-mode label on the wizard session when the
      project's provider is the trial provider, using the #615
      trial-mode wording family. Acceptance: component tests assert the
      label appears only for the trial provider.

## T4: Inspector entry points

- [ ] T4.1 Add the empty-lorebook guidance entry (the onboarding moment:
      a project with no `character`/`world` documents surfaces the wizard
      entry prominently in the Lore area) and the persistent entry for
      projects that already have entries. Acceptance:
      `pnpm --dir frontend test:unit -- StudioInspector` green with empty
      and populated lorebook cases.
- [ ] T4.2 Wire route-backed activation for the wizard surface following
      the existing Inspector URL contract. Acceptance:
      `pnpm --dir frontend test:unit -- studioRouteState` green.

## T5: Workflows, gates, and evidence

- [ ] T5.1 Add a TypeScript-backend Playwright workflow: paste a draft,
      run extraction (deterministic stub), toggle candidates, confirm,
      see `draft` entries appear with per-candidate results; abandon a
      second run and verify the lorebook is unchanged. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- lorebook_wizard` green.
- [ ] T5.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
