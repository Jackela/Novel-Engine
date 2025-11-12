## Task List

1. **Layout Orchestrator**
   - [x] Implement `DashboardZones` (or equivalent) that maps zone config to adaptive flow layout with semantic `data-role` markers.
   - [x] Update `Dashboard.tsx` to use the orchestrator, define zone weights, and remove legacy tile sequencing.
2. **Control Cluster**
   - [x] Merge Quick Actions + Run State into a composite card; update `QuickActions.tsx` to accept run-summary props and flexible layout rules.
   - [x] Remove the standalone `RunState` tile and update pipeline component props accordingly.
3. **Composite Stream Panels**
   - [x] Build `NarrativeActivityPanel` that renders timeline + activity feed side-by-side on desktop, tabs/accordion on smaller breakpoints, with scroll/virtualization guards.
   - [x] Build `SystemSignalsPanel` combining Performance metrics + Event Cascade with tabs and overflow handling.
4. **Pipeline Panel Enhancements**
   - [x] Expand `TurnPipelineStatus.tsx` to include run-state summary, new layout classes, and responsive height/scroll behavior.
   - [x] Ensure pipeline panel spans full width on desktop while collapsing responsibly on tablet/mobile.
5. **Styles & Responsive Behavior**
   - [x] Update layout CSS (BentoGrid, new zone containers) to use `auto-fit`/`minmax`, larger gaps, and container queries; drop `.tile-large/.tile-medium` assumptions.
   - [x] Adjust `MobileTabbedDashboard` ordering + presentation to align with new zones.
6. **Testing & Validation**
   - [x] Update Playwright specs (`dashboard-interactions`, `login-flow`, `quick-e2e`) to point to new zone/test IDs.
   - [x] Run `npm run lint`, `npm run type-check`, `npm test -- --run`, the three Playwright suites, and act parity jobs (`frontend-ci`, `ci`, `deploy-production`).
