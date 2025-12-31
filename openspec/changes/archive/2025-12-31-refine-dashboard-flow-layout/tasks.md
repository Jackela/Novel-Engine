## Implementation Tasks
1. Layout restructuring
   - [x] Refactor `frontend/src/components/dashboard/Dashboard.tsx` so the summary strip + quick actions live inside a single `control-cluster` wrapper that spans the full width on desktop/tablet.
   - [x] Remove the duplicate `<TurnPipelineStatus />` tile and rebalance the zone spans so Streams, Signals, and Pipeline each occupy predictable widths (auto-fit min 320 px).
   - [x] Update `BentoGrid`/layout styles if needed to support explicit CSS areas for the control band versus flow zones.
2. Quick Actions & Summary polish
   - [x] Rebuild `QuickActions.tsx` so desktop mode lays out actions horizontally (two rows max) and mobile mode stacks into two rows without overflow; preserve existing `data-testid`s.
   - [x] Ensure SummaryStrip consumes the entire control band on all breakpoints and updates its spacing/tokens to match the new layout.
3. Mobile experience
   - [x] Relax the hardcoded `maxHeight` clamps inside `MobileTabbedDashboard.tsx`; introduce per-panel sizing rules so Quick Actions, pipeline, and streams can expand to show full content while low-priority cards stay collapsed.
4. Tooling & documentation
   - [x] Finalize `scripts/mcp_chrome_runner.js` (CTA click, selector waits, metadata) and document the workflow in README/docs/assets README.
   - [x] Capture a fresh MCP screenshot + JSON after the layout changes and update any references (README, UX docs).
5. Validation
   - [x] Frontend: `npm run lint`, `npm run type-check`, `npx vitest run --reporter=dot`, Playwright suites (core UAT, extended, accessibility, cross-browser, interactions, login).
   - [x] Backend focus pytest suites already in scope (`tests/test_security_framework.py`, `tests/test_quality_framework.py`).
   - [x] CI parity: `scripts/validate_ci_locally.sh`, `act -W .github/workflows/frontend-ci.yml -j build-and-test`, `act -W .github/workflows/ci.yml -j tests`, `npx @lhci/cli@0.14.0 autorun`.
   - [x] Run `node scripts/mcp_chrome_runner.js ...` to confirm the automation still succeeds post-change.
