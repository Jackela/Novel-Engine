# Tasks

Dependency graph: `T1` (server aggregation) blocks `T2` (route) and `T3`
(frontend hook + panel); `T2` blocks `T3` and `T4`; `T4` (tab wiring)
depends on `T3`'s component contract; `T5` is workflows and gates, blocked
by `T2`–`T4`. Write sets are disjoint: T1 owns
`server/src/contexts/studio/application/` statistics files; T2 owns the
new route file and the regenerated OpenAPI baseline; T3–T4 own
`frontend/src/features/studio/` stats files and the tab constants; T5 owns
`frontend/tests/e2e-ts/` and evidence docs.

## T1: Server aggregation service

- [ ] T1.1 Add the statistics aggregation service (studio application):
      word-count deltas per revision against its parent using the unified
      word-count definition, source attribution (`author`, `ai-accepted`,
      `restore`), first-revision full-count attribution, daily/weekly
      calendar bucketing (project-local dates), chapter count and
      started-chapters share, and the streak rule (consecutive
      `author`-revision days ending today or yesterday). Acceptance:
      `pnpm --dir server test -- writing_stats` green, including the
      five-day streak with an AI-only day, first-revision attribution,
      and weekly-sum-equals-days cases.
- [ ] T1.2 Compose the AI usage summary from the existing
      `aggregateProjectUsage` aggregation — no second accounting path.
      Acceptance: server tests assert the stats payload's usage figures
      equal the usage aggregation for the same seeded history.

## T2: HTTP surface

- [ ] T2.1 Add the owner-guarded read-only route
      (`/api/projects/:projectId/stats`, TypeBox response schema,
      thin-handler discipline) exposing the aggregation. Acceptance:
      `pnpm --dir server test -- stats` green including auth, owner data
      isolation (unknown identifiers are not found), and empty-project
      zero states.
- [ ] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`) and review additive-only
      diffs; regenerate frontend API types
      (`pnpm --dir frontend gen:api-types`). Acceptance:
      `pnpm --dir server gates` green.

## T3: Frontend hook and panel

- [ ] T3.1 Add the stats data hook: lazy load on first activation, busy
      and error states under the explicit asynchronous operation state
      discipline, retry on failure. Acceptance:
      `pnpm --dir frontend test:unit -- WritingStats` green (hook tests:
      lazy load, failure recovery, duplicate-submission guard).
- [ ] T3.2 Add the stats panel component: daily/weekly words split by
      source, chapters and started share, streak, AI usage summary, and
      defined zero states for an empty project — all under the 200-line
      component rule (split sections as needed). Acceptance:
      `pnpm --dir frontend test:unit -- WritingStats` green (component
      tests cover every zero state and the source split rendering).

## T4: Inspector tab wiring

- [ ] T4.1 Add the `stats` tab to the Inspector tab list (APG-compliant
      tabs contract, URL-backed activation, keyboard navigation) and mount
      the panel with lazy first-activation loading. Acceptance:
      `pnpm --dir frontend test:unit -- StudioInspector` green including
      tablist, activation, and panel wiring cases.

## T5: Workflows, gates, and evidence

- [ ] T5.1 Add a TypeScript-backend Playwright workflow: author saves and
      an accepted proposal on known days, then the stats tab shows the
      source split, the chapter share, and the streak; an empty project
      shows the zero states. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- writing_stats` green.
- [ ] T5.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
