# Tasks

Dependency graph: `T1` (server aggregation) blocks `T2` (route) and `T3`
(frontend hook + panel); `T2` blocks `T3` and `T4`; `T4` (tab wiring)
depends on `T3`'s component contract; `T5` is workflows and gates, blocked
by `T2`–`T4`.

Coordination: server files (T1) and stats frontend files (T3) are
file-disjoint within this change, but three frontend families are shared
with the lorebook-wizard change and are serialized with it — this change
lands first: the Inspector tab union (`studioConstants.ts` INSPECTOR_TABS /
`InspectorTab`), route state (`studioRouteState.ts`), and the Inspector
panels (`StudioInspectorPanels.tsx` / `studioInspectorTypes.ts`). The
OpenAPI baseline is a shared regenerate-once surface across route-adding
changes in the same window; regenerate serially, last writer reviews the
additive-only diff.

## T1: Server aggregation service

- [x] T1.1 Add the statistics aggregation service (studio application):
      word-count deltas per revision against its parent using the unified
      word-count definition, source attribution (`author`, `ai-accepted`,
      `restore`), first-revision full-count attribution, UTC calendar
      bucketing for daily rows and weekly rollups (the same UTC-day anchor
      as the usage aggregation's daily buckets), chapter count and
      started-chapters share, and the streak rule (consecutive
      `author`-revision UTC days ending on the current UTC day or the one
      before). Acceptance: `pnpm --dir server test -- writing_stats` green,
      including the five-day streak with an AI-only day, first-revision
      attribution, weekly-sum-equals-days, and a UTC-midnight bucket
      boundary case, plus an assertion that stats day rows and usage
      daily buckets agree on the same revision history.
- [x] T1.2 Compose the AI usage summary from the existing
      `aggregateProjectUsage` aggregation — no second accounting path.
      Acceptance: server tests assert the stats payload's usage figures
      equal the usage aggregation for the same seeded history.

## T2: HTTP surface

- [x] T2.1 Add the owner-guarded read-only route
      (`/api/projects/:projectId/stats`, TypeBox response schema,
      thin-handler discipline) exposing the aggregation. Acceptance:
      `pnpm --dir server test -- stats` green including auth, owner data
      isolation (unknown identifiers are not found), and empty-project
      zero states.
- [x] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`) and review additive-only
      diffs; regenerate frontend API types
      (`pnpm --dir frontend gen:api-types`). Acceptance:
      `pnpm --dir server gates` green.

## T3: Frontend hook and panel

- [x] T3.1 Add the stats data hook: lazy load on first activation, busy
      and error states under the explicit asynchronous operation state
      discipline, retry on failure. Acceptance:
      `pnpm --dir frontend test:unit -- WritingStats` green (hook tests:
      lazy load, failure recovery, duplicate-submission guard).
- [x] T3.2 Add the stats panel component: daily/weekly words split by
      source, chapters and started share, streak, AI usage summary, and
      defined zero states for an empty project — all under the 200-line
      component rule (split sections as needed). Acceptance:
      `pnpm --dir frontend test:unit -- WritingStats` green (component
      tests cover every zero state and the source split rendering).

## T4: Inspector tab wiring

- [x] T4.1 Add the `stats` tab to the Inspector tab union
      (`INSPECTOR_TABS` / `InspectorTab` in `studioConstants.ts`), wire
      URL-backed activation in `studioRouteState.ts`, and mount the panel
      through `StudioInspectorPanels.tsx` / `studioInspectorTypes.ts`
      (APG-compliant tabs contract, keyboard navigation, lazy
      first-activation loading) — these are the shared files the
      lorebook-wizard change's `lore` tab lands on after this change;
      leave both-tab coexistence verifiable. Acceptance:
      `pnpm --dir frontend test:unit -- StudioInspector studioRouteState`
      green including tablist, activation, and panel wiring cases.

## T5: Workflows, gates, and evidence

- [x] T5.1 Add a TypeScript-backend Playwright workflow: author saves and
      an accepted proposal on known days, then the stats tab shows the
      source split, the chapter share, and the streak; an empty project
      shows the zero states. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- writing_stats` green.
- [x] T5.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
