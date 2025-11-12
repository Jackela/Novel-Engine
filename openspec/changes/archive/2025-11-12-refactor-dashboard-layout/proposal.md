## Why
- Manual MCP audit (`tmp/mcp/dashboard-plan.json`) shows the dashboard hero crams status text, four quick-action buttons, and secondary controls into a single row; there is no distinct quick-actions tile, so the UI lacks hierarchy and Playwright specs cannot find `data-testid="quick-actions"`.
- Every widget (map, networks, timeline, activity, metrics, pipeline, backlog) renders simultaneously with uniform heights, creating a visually dense experience and overwhelming mobile users (critical feedback from stakeholders: "dashboard feels very crowded").
- Quick-action buttons do not synchronize with TurnPipelineStatus/RealTimeActivity state, so pressing Play/Pause fails to show obvious live indicators, and the e2e test for "quick actions toggle pipeline state" still fails.

## What Changes
- Introduce a summary strip + dedicated Quick Actions tile (with `data-testid="quick-actions"`) that own the start/pause/stop/refresh controls, emit shared `pipelineStatus`/`isLive` state, and surface KPI badges (health, queue depth, last update).
- Reorganize the Bento grid into zones (Summary, Spatial Context, Streams, Backlog) with breakpoint-specific layouts (tabs/accordions on mobile) so primary telemetry stays above the fold while secondary lists collapse gracefully.
- Update TurnPipelineStatus, RealTimeActivity, and related tiles to respond to the new shared status (show active class/live indicator when quick actions play) and ensure responsive heights/scroll affordances.
- Document the new layout requirements under `dashboard-layout` spec and provide implementation plan/design doc covering React structure, CSS grid tokens, and test regimen (lint + type-check + vitest + targeted Playwright + `act` CI runs + MCP manual audit snapshot).

## Impact
- UX: Users (and automated UAT) get a clear, spacious summary, discoverable quick actions, and visual feedback when orchestrations start/stop.
- QA: Playwright spec `dashboard-interactions` can target the new quick-actions tile; regression suite will cover the refactor via lint/type-check/vitest/Playwright/act.
- DevEx: `scripts/dev_env_daemon.sh` + MCP workflow already validated page capture; post-change we will rerun manual audit to ensure layout matches the new spec across breakpoints.
