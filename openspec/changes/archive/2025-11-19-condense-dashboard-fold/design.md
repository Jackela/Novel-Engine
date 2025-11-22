# Design: Condensed Dashboard First Fold

## Goals
- Keep the cockpit (summary KPIs + quick actions) on a single visual surface that fits ≤180px height on desktop/tablet.
- Ensure real-time telemetry (Activity Stream + Turn Pipeline) is visible without scrolling.
- Maintain semantic hooks/Playwright stability while reordering the grid.

## Layout Sketch
1. **Control Cluster** – Use a wrapper component (could live inside `Dashboard.tsx`) that renders `SummaryStrip` and `QuickActions` as a CSS grid with `grid-template-columns: repeat(auto-fit, minmax(160px, 1fr))`. Buttons snap to the right using flex alignment. The entire band has `data-role="control-cluster"`.
2. **First Content Row** – Render a `FlowRow` containing `RealTimeActivity` (`data-role="stream-feed"`) and `TurnPipelineStatus` (`data-role="pipeline"`). Use `grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))`. Add `data-density` attribute triggered when viewport ≥1200px (the Activity component can read via media query hook or prop).
3. **Spatial Row** – Place `WorldStateMapV2` and `CharacterNetworks` side-by-side. Clamp the map height using `clamp(320px, 45vh, 420px)` and allow the networks tile to auto-fill remaining space. CharacterNetworks keeps the new semantic data attributes.

## Component Notes
- `QuickActions`: drop the standalone tile heading; embed controls directly into the control cluster. Keep `data-testid` for each button.
- `SummaryStrip`: accept an optional `inlineActions` slot for QuickActions so markup stays semantic.
- `RealTimeActivity`: add `condensed` prop to switch from stacked list to two-column layout; when active set `data-density="condensed"`.
- `WorldStateMapV2`: add `maxHeight` prop or use CSS clamp within the component wrapper.

## Testing Strategy
- Update Playwright POM to look for `data-role="control-cluster"` containing both summary + quick actions; verify `data-density="condensed"` on desktop.
- Rerun Chromium desktop specs (core + extended), login flow, interactions, accessibility.
- Lint/type-check/vitest standard suite.
- Regenerate MCP screenshot after layout updates.
