## Why
- After the flow-based layout refactor, MCP snapshots still show some zones (Streams, Signals) crammed with text when activity/event counts spike. Buttons and chip typography remain fixed, so visual density varies wildly based on data volume.
- We need semantic density controls (e.g., `data-density="relaxed|compact"`) so AI-generated or long-form content can trigger tighter typography, extra scroll affordances, or collapsed sections automatically.
- Stakeholders want the dashboard to remain "AI-friendly"—i.e., capable of expanding for rich context yet shrinking gracefully when streams overflow—without manual CSS tweaks per panel.

## What Changes
- Introduce density heuristics per zone (e.g., live feed length, queue depth, active events) that toggle relaxed/compact tokens for padding, typography, and chip/button sizing.
- Add semantic attributes (`data-density`, `data-volume`) on zone containers so automation/tests can assert the state and future AI routines can override density.
- Ensure overflow handling respects density (e.g., when compact, show summary badges, limit visible rows, add virtualization hooks).
- Update dashboard layout spec to encode density behavior and semantic metadata.

## Impact
- **Frontend**: DashboardZones, QuickActions, TurnPipelineStatus, NarrativeActivityPanel, SystemSignalsPanel, CSS tokens, maybe design-system typography utilities.
- **Testing**: Unit tests for density heuristics, Playwright assertions verifying data-role/data-density, existing suites rerun.
- **Docs/Spec**: `dashboard-layout` spec gains density requirements.
