## Overview
The current “flow-based” dashboard still behaves like a three-column pillar layout because every zone is rendered as an auto-fit card with arbitrary spans. The Quick Actions tile stacks vertically, the pipeline tile renders twice, and the summary strip isn’t pinned. This design document captures the adjustments needed to translate the spec into an actual flow layout and aligns the automation tooling (MCP) with the new structure.

## Layout Strategy
1. **Control Cluster Band**
   - Replace the ad-hoc `zoneConfigs` entries for Summary + Quick Actions with a dedicated wrapper that spans the full width (`grid-column: 1 / -1`) on desktop/tablet.
   - Desktop: use CSS grid or flex inside the band to position the summary cards next to a horizontal quick-action toolbar so the entire zone is ≤ 220 px tall.
   - Tablet/Mobile: allow the band to stack (Summary above Quick Actions). The Quick Actions component must support both horizontal and two-row modes.

2. **Adaptive Flow for Remaining Zones**
   - Streams, Signals, Pipeline, World Map, etc., should use auto-fit columns with a consistent min width (e.g., 320 px). We can keep `BentoGrid` but introduce explicit span tokens (e.g., `grid-column: span 2` only when ≥1600 px).
   - Remove the second `<TurnPipelineStatus />`; the pipeline zone should be a single tile that can grow vertically to show all steps.

3. **Mobile Tabs**
   - Instead of hard-clamping each tab’s content to `maxHeight: 200px`, allow `control` and `pipeline` panels to grow while providing “View more” accordions for verbose feeds (narrative timeline, analytics). This reduces scroll fatigue while keeping touch targets ≥ 44 px.

## Quick Actions Component
- Desktop: convert the action buttons into a two-row flex layout, grouping Control/System/View actions but keeping the connection indicator inline with the title.
- Mobile: maintain the horizontal scrolling option but also support a two-row wrap when the viewport is narrow, so the carousel isn’t clipped inside tab containers.
- Ensure the connection indicator/Chip combo remains visible and uses the new spacing tokens; telemetry hooks remain untouched.

## MCP Automation
- The new `scripts/mcp_chrome_runner.js` launches headless Chrome, auto-clicks the “View Demo” CTA, waits for `data-role` markers, captures a screenshot, and saves metadata. This script becomes the canonical way to refresh README/UX evidence.
- After the layout refactor, update the script selectors if necessary (e.g., new `data-role` names for the control band). Documentation must mention the command and where outputs live.

## Validation Plan
1. Unit/Integration: ESLint, tsc, Vitest.
2. E2E: all Playwright specs (core UAT, extended, cross-browser, accessibility) driven via `npm run dev:daemon`.
3. Backend focus pytest suites to ensure nothing regresses during the flow layout work.
4. CI parity: `scripts/validate_ci_locally.sh`, `act` workflows, Lighthouse CI.
5. Evidence: rerun the MCP runner and stick the PNG/JSON in `docs/assets/dashboard/`, referencing them in README/docs.
