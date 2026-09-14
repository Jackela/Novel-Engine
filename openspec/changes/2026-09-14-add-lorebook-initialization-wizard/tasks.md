# Tasks

Dependency graph: `T1` (server extraction pipeline) blocks `T2` (route) and
`T3` (frontend wizard); `T2` blocks `T3`; `T4` (Inspector tab) depends only
on `T3`'s component contracts; `T5` (workflows and gates) is blocked by all
of `T2`–`T4`.

Coordination: server files (T1, T2) and wizard frontend files (T3) are
file-disjoint, but three frontend families are shared with the
writing-stats change and are serialized with it — this change lands after
stats: the Inspector tab union (`studioConstants.ts` INSPECTOR_TABS /
`InspectorTab`), route state (`studioRouteState.ts`), and the Inspector
panels (`StudioInspectorPanels.tsx` / `studioInspectorTypes.ts`). The
OpenAPI baseline is also a shared regenerate-once surface across
route-adding changes in the same window; regenerate serially, last writer
reviews the additive-only diff.

## T1: Server extraction pipeline

- [ ] T1.1 Add the extraction application service (studio context, behind
      a port to the ai context's structured text generation): one input
      segment per call — a 100,000 Unicode code-point cap checked before
      provider construction, and the segment's assembled extraction prompt
      checked against the shared 8,388,608 UTF-8 byte authority — failing
      closed with 422 `GENERATION_CAPACITY_EXCEEDED`, details
      `resource: lore_extract_segment`, `limit: 100000`, `observed`
      bounded to limit + 1 (the generation-capacity inline shape).
      Acceptance: `pnpm --dir server test -- lorebook_init` green,
      including boundary tests (99,999 passes, 100,000 passes, 100,001
      rejects with the exact envelope) and prompt-byte boundary tests for
      the assembled segment prompt.
- [ ] T1.2 Register the `lore-extract` Job type, one Job per segment, under
      the synchronous job execution model: events for every transition,
      keyed retry with stored outcomes, and exactly one usage event per
      completed provider request. Extend the Job enum SSOT —
      `JOB_SUMMARY_KINDS` gains `lore-extract` and
      `JOB_SUMMARY_OPERATIONS` gains `extract` in
      `server/src/contexts/studio/application/payload_schemas/job.ts`,
      with the guards in `payloads.ts` following the constants — and the
      summary/detail serializers must round-trip the new kind. Acceptance:
      `pnpm --dir server test -- job` green with new cases for replay
      idempotency, usage singularity, and summary/detail round-trip of
      `lore-extract` jobs.
- [ ] T1.3 Wire the mock (trial) provider path: deterministic placeholder
      candidates for any valid segment. Acceptance: `pnpm --dir server
      test` cases proving mock extraction returns the fixed placeholder
      set and real-provider failures stay inside the provider diagnostics
      boundary (no body exposure).
- [ ] T1.4 Confirm the retrieval contract: the wizard's document selection
      reads through existing read services and adds no search surface of
      its own; if any retrieval is introduced, its observable behavior
      must follow the full-text search requirement (operator-laden input
      safely reduced to strict tokens, irreducible input returning no
      results, parameterized execution), with malicious-input coverage
      extended accordingly. Acceptance: `pnpm --dir server test -- fts`
      green; review confirms no new free-form match expression anywhere.

## T2: HTTP surface

- [ ] T2.1 Add the extraction route (owner-guarded, TypeBox schemas,
      thin-handler discipline) submitting one segment and returning its
      terminal `lore-extract` Job, reusing the existing job result and
      retry surfaces where they already fit. Acceptance:
      `pnpm --dir server test -- <route file>` green including auth,
      validation, capacity-envelope, and error-envelope cases.
- [ ] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`) and review the diff for
      additive-only changes, serially with any other route-adding change
      in the window. Extend the frontend job types to match the new enums:
      `StudioJobKind` / `StudioJobSummaryKind` gain `lore-extract` and
      `StudioJobSummaryOperation` gains `extract` in
      `frontend/src/app/types/studio.ts`, regenerating API types
      (`pnpm --dir frontend gen:api-types`). Acceptance:
      `pnpm --dir server gates` green including the OpenAPI snapshot gate;
      `pnpm --dir frontend type-check` green.

## T3: Frontend wizard flow

- [ ] T3.1 Add the wizard data hook: build input segments (paste box +
      existing-document picker reading current content), submit each
      segment as its own extraction Job, retain per-segment busy/error
      state under the explicit asynchronous operation state discipline,
      and fold completed segment Jobs into one merged candidate list —
      (kind, title) collapse with union-of-aliases, deterministic order,
      recomputed from completed results only; candidates live in the
      session and vanish on abandon. Acceptance:
      `pnpm --dir frontend test:unit -- LorebookWizard` green (hook tests:
      per-segment submit, merge determinism, failure recovery,
      duplicate-submission guard).
- [ ] T3.2 Add the wizard component flow: input step, per-segment pending,
      merged candidate list (kind, title, editable aliases, summary
      preview), confirm step, and per-candidate results with the three
      outcome states — created, created-with-failed-aliases (aliases kept
      for retry, never silently dropped), and failed — where confirmation
      issues the existing document creation call followed by the existing
      alias write per selected candidate. Components stay under the
      200-line rule. Acceptance: `pnpm --dir frontend test:unit --
      LorebookWizard` green (component tests: candidate toggle, confirm,
      alias-write failure partial success, abandon leaves nothing).
- [ ] T3.3 Render the trial-mode label on the wizard session when the
      project's provider is the trial provider, using the #615
      trial-mode wording family. Acceptance: component tests assert the
      label appears only for the trial provider.

## T4: Inspector `lore` tab

- [ ] T4.1 Add the `lore` tab to the Inspector tab union
      (`INSPECTOR_TABS` / `InspectorTab` in `studioConstants.ts`), wire
      URL-backed activation in `studioRouteState.ts`, and mount the panel
      through `StudioInspectorPanels.tsx` / `studioInspectorTypes.ts` —
      all shared files, landed after the writing-stats change's `stats`
      tab with a rebase check for both tabs coexisting. Acceptance:
      `pnpm --dir frontend test:unit -- StudioInspector studioRouteState`
      green with both-tab cases, APG tablist contract intact.
- [ ] T4.2 Inside the tab, surface the empty-lorebook guidance entry (a
      project with no `character`/`world` documents shows the wizard as
      the primary action) and the persistent entry for projects that
      already have entries. Acceptance: `pnpm --dir frontend test:unit --
      LorebookWizard StudioInspector` green with empty and populated
      lorebook cases.

## T5: Workflows, gates, and evidence

- [ ] T5.1 Add a TypeScript-backend Playwright workflow: paste a draft,
      run extraction (deterministic stub), toggle candidates, confirm,
      see `draft` entries appear with per-candidate results including a
      routed alias-write failure reporting created-with-failed-aliases
      with retry; abandon a second run and verify the lorebook is
      unchanged. Acceptance: `pnpm --dir frontend test:e2e-ts --
      lorebook_wizard` green.
- [ ] T5.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
