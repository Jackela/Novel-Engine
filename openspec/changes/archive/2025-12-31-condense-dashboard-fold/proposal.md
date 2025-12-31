# Proposal: Condense First-Fold Dashboard Layout

## Why
- Fresh MCP capture (`tmp/mcp/ui-audit.png`, 2025-11-14) shows >50% of the first fold is empty because only the control cluster and world map render above the fold; Streams/Signals tiles violate the `dashboard-layout` spec scenarios that require multiple zones per fold.
- Quick Actions tile remains visually detached from KPI cards and duplicates the STANDBY label, making the cockpit feel like two separate surfaces rather than one control strip.
- World State Map monopolizes the first content row despite showing little motion, while Activity/Performance/Pipeline telemetry is buried off-screen. Users cannot see real-time signals without scrolling.

## What Changes
1. **Control Band Compression** – Merge Quick Actions into the Summary strip grid so KPIs + controls share a single `control-cluster` container with no vertical stacking, targeting ≤180px height on desktop/tablet.
2. **First Fold Rebalance** – Promote Activity Stream and Pipeline tiles into the first content row (just below the control band) and cap World Map height (≤420px) so Character Networks can share the row.
3. **Semantic Hooks & Styling** – Update `data-role` markers to reflect the new ordering (`data-role="stream-feed"` next to pipeline), tighten padding/spacing tokens, and ensure Playwright selectors remain deterministic.
4. **Telemetry Density** – Add optional condensed view for Activity Stream entries (two-column list) when viewport ≥1200px so more events are visible before scrolling.

## Impact
- Requires edits to `frontend/src/components/dashboard/{Dashboard,SummaryStrip,QuickActions,RealTimeActivity,TurnPipelineStatus,WorldStateMapV2}.tsx` plus shared layout (`BentoGrid`, `MobileTabbedDashboard`).
- Playwright page object + specs need minor selector updates but should remain compatible with existing `data-role` attributes.
- Docs/README should include a new MCP screenshot once the condensed layout ships. Regression suite (lint, type-check, vitest, targeted Playwright) must rerun.
