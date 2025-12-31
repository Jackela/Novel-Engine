## Why
- Fresh MCP capture (`docs/assets/dashboard/dashboard-flow-2025-11-14.png`) shows the dashboard still renders as three crowded towers: the Quick Actions/connection indicator stack consumes an entire column, the pipeline tile renders twice in the same zone, and the summary strip floats mid-page instead of anchoring the hero controls.
- The mobile/tabs layout clamps every panel to ~200 px, so the quick-action carousel and pipeline feed are cropped on phones; this violates the “flow-based adaptive zones” spec and makes the UI unusable in the exact scenario it was meant to improve.
- Automated MCP audits frequently failed because the landing page button must be clicked before `/dashboard` renders; without a deterministic runner the docs/tests drift from reality.

## What Changes
1. Rework the desktop/tablet grid so Summary + Quick Actions render inside a dedicated control cluster row that spans the width, streams/signals/pipeline share an adaptive two-column flow, and the pipeline tile mounts exactly once.
2. Update QuickActions to support a compact horizontal mode on large screens (no more 400 px column) and ensure mobile controls break into two rows instead of a clipped scroll box.
3. Soften the mobile tabbed dashboard by letting critical panels expand to fit their content (Quick Actions, pipeline, events) and push lower-priority feeds behind accordions.
4. Ship a documented MCP chrome runner script that automatically clicks the CTA, waits for the new `data-role` hooks, and emits screenshot + metadata for README/docs.

## Success Criteria
- Desktop/Tablet MCP captures show Summary + Quick Actions fused into a control band at the top, with streams/signals/pipeline occupying balanced tiles underneath; no duplicate pipeline component is present.
- Mobile tabs no longer clamp Quick Actions or pipeline to 200 px; Playwright/mobile screenshots show full controls with ≥44 px touch targets.
- `scripts/mcp_chrome_runner.js` consistently produces `docs/assets/dashboard/dashboard-flow-YYYY-MM-DD.(png|json)` without manual intervention, and documentation references the command.
