## Task List

1. **Establish shared layout + state**
   - [x] Update `Dashboard.tsx` to manage `pipelineStatus`/`isLiveMode`, add `DashboardSummary`, and wire snackbar helpers.
   - [x] Move quick-action rendering into the grid (remove header buttons) and pass status props to impacted tiles.
2. **Quick Actions tile + summary UI**
   - [x] Refactor `frontend/src/components/dashboard/QuickActions.tsx` to expose grouped controls, `data-testid="quick-actions"`, and responsive layout (desktop stacks, mobile horizontal scrolling).
   - [x] Mirror the same tile in `EmergentDashboardSimple.tsx` so landing/demo routes stay in sync and Playwright selectors exist.
3. **Responsive layout zoning**
   - [x] Update `DashboardLayout`/`BentoGrid` CSS to define summary, spatial, streaming, and backlog zones with breakpoint-specific column templates; collapse backlog into accordion/tabs on mobile.
   - [x] Adjust `TurnPipelineStatus`, `RealTimeActivity`, and related tiles to react to the new status props (active class, live indicator) and enforce min heights.
4. **Documentation & specs**
   - [x] Author spec delta for `dashboard-layout` describing summary strip, quick-actions tile, and responsive priorities.
5. **Validation**
   - [x] Run `npm run lint`, `npm run type-check`, `npm test -- --run`.
   - [x] Execute Playwright suite: `npm run test:e2e -- quick-e2e.spec.js`, `npx playwright test tests/e2e/login-flow.spec.ts --project=chromium-desktop`, `npx playwright test tests/e2e/dashboard-interactions.spec.ts --project=chromium-desktop`.
   - [x] Run CI parity: `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test` and `act --pull=false -W .github/workflows/ci.yml -j tests` (plus deploy workflow if required).
   - [x] Perform manual MCP audit (`scripts/dev_env_daemon.sh start` + `python scripts/mcp_chrome_runner.py --isolated`) to capture the updated layout snapshot for review.
