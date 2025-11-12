# Update dashboard visuals and responsiveness

## Why
After repairing the CI regressions we still render the dashboard inside a single `BentoGrid` owned by `EmergentDashboardSimple`. While that keeps tiles readable, the visual system remains coarse:
- Only three breakpoints exist (≥1200, 900–1199, <900). On 1024/768 ranges the layout feels cramped and the header still consumes excessive vertical space.
- Tiles snap directly from 6/4/3 spans to full width; we have no medium+ offsets or two-column stacks, so content like “World Map + Timeline” can’t sit side-by-side on tablets.
- We’re missing consistent elevation/animation: hover/focus states are subtle, but no entry transitions or density adjustments exist for high-density dashboards.
- Mobile spacing/padding is still inconsistent because `BentoGrid` pads 0 and `MainContainer` sets static padding. We need a unified spacing scale that matches the design tokens.

## What changes
1. Expand the responsive grid to cover four tiers (≥1440, 1200–1439, 900–1199, 600–899, <600) with class-based spans + row gaps so we can keep two-column layouts on tablets while still stacking on phones.
2. Introduce utility classes for tile elevation, hover/focus scale, and optional entrance animations so cards feel less “flat”.
3. Add spacing tokens for the dashboard shell (header, main container, tile gutters) that shrink progressively; ensure quick actions wrap into a 2x2 grid between 600–899px.
4. Document these expectations in the existing `dashboard-layout` spec so future tiles/layout components follow the richer breakpoint map and visual polish.

## Impact
- Touches shared layout CSS (`frontend/src/components/EmergentDashboard.css`, design tokens) plus `BentoGrid`/`DashboardLayout` for spacing props.
- No API/backend work. Purely frontend layout + animation.
- Requires re-running lint + quick Playwright smoke to ensure no regressions.
