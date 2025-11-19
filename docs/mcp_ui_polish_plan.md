# MCP UI Polish & MCP-Audit Execution Plan

This plan drives the next polish cycle using Chrome DevTools MCP as the primary inspection tool. It assumes the canonical backend endpoint is **/api/characters** (single version; no `/v1`+), and uses TDD: write/extend tests first, then fix, then verify via MCP.

## 1) Scope & Goals
- Validate Landing and Dashboard UIs against design specs (`docs/design/DESIGN_FRONTEND_UX.md`, `openspec/specs/dashboard-layout/spec.md`).
- Ensure dashboard data comes from `/api/characters` (and `/api/characters/{id}`) with correct UI signaling (“API feed”, connection ONLINE/LIVE).
- Eliminate console warnings (React act, DOM nesting, tooltip/disabled) and reduce aborted fetch noise.
- Strengthen automated coverage so MCP findings regress into tests (a11y, data-source chips, connection text, tooltips, unread badges, pipeline focusability).

## 2) Environment & Preflight
1. Start services (logs go to `tmp/dev_env/*.log`):
   ```bash
   npm run dev:daemon
   ```
2. Launch Chrome for MCP:
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/mcp-chrome --no-first-run --no-default-browser-check about:blank
   ```
3. Note `browserWSEndpoint` from `http://127.0.0.1:9222/json/version` and use it for all `chrome-devtools/*` calls.
4. Verify API health:
   ```bash
   curl -fsS http://127.0.0.1:8000/health
   curl -fsS http://127.0.0.1:8000/api/characters
   ```

## 3) Automated Test Gates (run before/after fixes)
- `npm run lint`
- `npm run type-check`
- `npx vitest run src/components/dashboard/__tests__/dashboard-accessibility.test.tsx`
- `npx vitest run src/__tests__/AppRouterWarnings.test.tsx`
- Full suite when time permits: `npx vitest run`

## 4) MCP Audit Loops (step-by-step)
Perform each loop with Chrome DevTools MCP, capture screenshots to `docs/assets/audit/YYYYMMDD_<section>.png`, and log findings (ID, severity, evidence, fix).

### Loop A: Landing (`/`)
1. Navigate via MCP new_page to `http://127.0.0.1:3000/`.
2. Keyboard path: `Tab` → Skip link focus, `Enter` → jump to main.
3. Validate CTA block (`View Demo`, `mailto:ops@novel-engine.ai`), hero copy, feature bullets; capture `landing_hero.png`.
4. Trigger “View Demo” → confirm sessionStorage guest key and redirect to `/dashboard`; verify via MCP console.

### Loop B: Dashboard Fold
1. Navigate to `/dashboard`; confirm `role="main"` on `[data-testid="dashboard-layout"]`.
2. Capture first-fold screenshot (`dashboard_fold.png`); note connection indicator text and data chips (“API feed”).
3. Tab order across header → skip link → SummaryStrip → QuickActions → Stream → Map; note any missing `:focus-visible`.

### Loop C: Control Cluster (SummaryStrip + QuickActions)
1. Exercise `play/pause/stop/refresh/save/settings/fullscreen/export`; record Snackbar text and `[data-testid="connection-status"]` content (expect ONLINE; consider LIVE when streaming).
2. Confirm tooltips do not wrap disabled buttons; if warnings appear, add tests and fixes.
3. Toggle offline via DevTools Network → observe chip states.

### Loop D: Streams & Pipeline
1. RealTimeActivity (`data-role="stream-feed"`): ensure density=condensed, badge counts capped, unread init correct; scroll for virtualization issues; capture `stream_activity.png`.
2. TurnPipeline (`data-role="pipeline"`): Play through phases; check `data-status` and focusability with `aria-label`; capture `pipeline_live.png`.
3. Narrative Timeline: verify keyboard reach and current-turn indicator.

### Loop E: Spatial Zones
1. World Map (`data-role="hero-map"`): click markers, expand character lists; chips for totals/active match API data; capture `world_state_map.png`.
2. Character Networks (`data-role="network-visuals"`): chips show counts; hover/focus cards; trust bars render; capture `character_networks.png`.

### Loop F: System Signals & Performance
1. Performance tile: should read “Demo” unless API error; metrics neutral; no warning unless error present.
2. Connection indicator should prefer LIVE when API feed returning events; otherwise ONLINE.
3. Validate analytics/event cascade sections for overflow; capture `system_signals.png`.

### Loop G: Accessibility Sweep
1. Tab through entire dashboard; log components lacking focus styles.
2. Check `aria-live` regions (`[data-testid="live-indicator"]`) fire when connection flips.
3. Ensure no console warnings (validateDOMNesting, act, tooltip-disabled).

## 5) TDD Fix Cycle
For each issue from MCP:
1. **Reproduce** via MCP evidence (console log, DOM snippet, screenshot).
2. **Test-first**: add/extend Vitest (RTL + jest-axe where a11y) to lock expected behavior.
3. **Implement fix** (prefer minimal touch): e.g., connection label LIVE/ONLINE logic, tooltip wrappers, abort-handling in `useDashboardCharactersDataset`, map/network chip sync.
4. **Verify**: re-run targeted tests, then full gates; re-run MCP step where found.
5. **Document**: append finding/resolution to `docs/testing/uat/UAT_REAL_TESTING_RESULTS.md` and update audit images list here.

## 6) Targeted Known Risks to Re-check
- Connection indicator wording (LIVE vs ONLINE) when API data is present but idle.
- Aborted fetch noise during retries; ensure no user-facing errors.
- Any lingering `/v1` callers; proxy and hooks must stick to `/api`.
- Timeline/TurnPipeline DOM nesting (no nested `<p>`), tooltip+disabled warnings, React act warnings.

## 7) Output & Handoff
- Keep this plan updated after each loop (date + short note).
- Store newest screenshots and reference them here (replace the prior `20251115_dashboard_api_feed_polish_v4.png` if superseded).
- Summarize resolved vs open items before shipping the next PR/commit.
