## Why
- Manual MCP audit (tmp/mcp/dashboard-crowded.png) shows the refreshed dashboard still renders as evenly spaced vertical pillars; high-priority controls (Quick Actions + Run State) compete for the same narrow columns as text-heavy feeds.
- Current spec (Responsive Bento Grid + Zone-based layout) assumes fixed tile classes (`tile-large`, `tile-medium`, `tile-small`). That rigidity blocks AI-generated or long-form content: Activity feed entries wrap awkwardly, pipeline + run-state duplicate information across two cards, and there is no semantic metadata for future automation to rearrange cards.
- Stakeholder request: "flow-based adaptive layout" that reacts to content density, keeps Activity Stream/Event Cascade readable, and exposes semantic hooks for AI-assistive modules.

## What Changes
- Replace the fixed class-based grid with a flow layout manager that groups tiles by semantic zones (Control Cluster, Streams, Signals, Pipeline) and uses adaptive `minmax()` spans plus weights to let cards expand/contract with content.
- Merge related widgets into composite panels (Quick Actions + Run State, Narrative + Activity, Performance + Event Cascade) with internal flex/tabs so each zone occupies fewer but richer cards; add semantic attributes (`data-role`) for future AI routines.
- Introduce virtualization/overflow handling for high-volume feeds so long AI activity lists do not stretch the page, while ensuring desktop/tablet/mobile breakpoints remain accessible.
- Update dashboard spec to codify flow-based adaptive behavior and semantic roles beyond the legacy "tile size" rules.

## Impact
- **Frontend**: `Dashboard.tsx`, layout/CSS, QuickActions, TurnPipelineStatus, NarrativeTimeline, RealTimeActivity, PerformanceMetrics, EventCascadeFlow, RunState (removed/repurposed), MobileTabbedDashboard.
- **Testing**: Playwright selectors (`dashboard-interactions`, `login-flow`, `quick-e2e`), unit tests for composite panels, lint/type-check/vitest.
- **Docs/Spec**: `openspec/specs/dashboard-layout/spec.md` gains new requirements for adaptive zones + semantic hooks.
- **Risk**: Medium—layout churn affects multiple components, but scope is limited to dashboard route; comprehensive Playwright + act runs will mitigate regressions.
