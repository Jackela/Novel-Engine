# Design: Refactor Dashboard Layout & Quick Actions

## Current Pain Points (Chrome DevTools audit)
- Header crams title, status pill, and four action buttons without grouping; no `quick-actions` container exists, breaking Playwright.
- Bento grid renders every tile with equal weight; summary vs. detail are indistinguishable.
- Quick actions do not drive shared state, so pipeline/activity tiles stay static after Play/Pause.
- Mobile view stacks all tiles vertically, resulting in very long scroll.

## Target Architecture
### 1. Shared State + Context
- `Dashboard.tsx` maintains `pipelineStatus: 'idle'|'running'|'paused'` and `isLiveMode`.
- Pass `status` props to `QuickActions`, `TurnPipelineStatus`, `RealTimeActivity`.
- Snackbar uses new helper to avoid duplicate messages.

### 2. Summary Strip & Quick Actions Tile
- New `DashboardSummary` component renders KPI cards (health, active turn, queue, last refresh).
- `QuickActions` tile receives props `{status, isLive, onAction}` and renders grouped buttons plus microcopy.
- Header keeps only title + breadcrumb; quick actions move into tile (with `data-testid="quick-actions"`).

### 3. Layout Zoning
- Update `DashboardLayout` and/or `BentoGrid` to support column templates per breakpoint:
  - Desktop: summary row spans width; below, two/three columns (spatial vs. stream vs. backlog).
  - Tablet: two columns with reorder (summary left, controls right).
  - Mobile: summary cards + tabs for map/activity/metrics, backlog collapsed.
- Use CSS variables or theme spacing to enforce vertical rhythm.

### 4. Responsive UX
- Add `MobileDashboardTabs` (if needed) to show map/activity/metrics as swipeable tabs.
- Quick actions tile becomes horizontal scroll on mobile with min 44px contact targets.
- Collapse "Recent Projects" and "Characters" into accordions on small screens.

### 5. Visual Feedback
- `TurnPipelineStatus` receives `status` prop to toggle `.active` class; `RealTimeActivity` shows `Live` badge whenever `isLiveMode` true.
- Summary strip shows `status-pill` derived from health query or fallback state.

## Testing & Validation Strategy
1. `npm run lint`, `npm run type-check`, `npm test -- --run`.
2. Playwright:
   - `quick-e2e.spec.js`
   - `login-flow.spec.ts` (chromium desktop)
   - `dashboard-interactions.spec.ts` (chromium desktop) to confirm quick actions now toggle pipeline.
3. `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test` and `act --pull=false -W .github/workflows/ci.yml -j tests`.
4. Manual MCP audit via `scripts/dev_env_daemon.sh start` + `python scripts/mcp_chrome_runner.py --isolated` to capture updated layout snapshot.
5. Screenshot review (optional) for summary strip spacing.
