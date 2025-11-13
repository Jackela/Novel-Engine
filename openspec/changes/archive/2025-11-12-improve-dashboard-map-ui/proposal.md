# Change: Improve dashboard map interaction clarity

## Why
The world map tile advertises selectable entity markers and a "Live" status, yet activating a marker never reveals new information and the timestamp label never refreshes outside incidental renders. Quick actions are also duplicated in the header and a separate tile, which dilutes their semantic weight for keyboard and assistive-technology users.

## What Changes
- Add an entity details panel beside the world map that announces metadata for the currently selected character and exposes a clear "nothing selected" state.
- Refresh the map's timestamp on a timer (≤30s cadence) with an aria-live label so the "Live" badge reflects real telemetry even when the rest of the dashboard is idle.
- Rework the duplicate quick-action tile into a run-state summary that surfaces the same controls once, alongside contextual status, to reduce focus churn.
- Back the new behavior with a targeted component test to prevent regressions.

## Impact
- Affected specs: dashboard-interactions
- Affected code: frontend/src/components/EmergentDashboardSimple.tsx, frontend/src/components/EmergentDashboard.css (and related unit tests)
