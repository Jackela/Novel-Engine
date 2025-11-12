# Update dashboard responsive layout

## Background
The emergent dashboard (`frontend/src/components/EmergentDashboardSimple.tsx`) is the primary authenticated surface. Its tiles render with `.bento-tile tile-{size}` classes and are wrapped in a bare `<div class="bento-grid">`. The design system already defines a responsive 12/8/1 column grid, yet the dashboard bypasses the shared `<BentoGrid />` layout component (`frontend/src/components/layout/BentoGrid.tsx`).

## Problem
- `.tile-large|medium|small` have no grid-column rules anywhere in the codebase, so every tile collapses to a one-column stack even on desktop widths. The temporary selectors in `frontend/src/components/EmergentDashboard.css:586-634` look for inline `style="grid-column: span N"`, but the component never sets inline styles, so the overrides never apply.
- The header action bar (`.dashboard-header__actions`) stays `display:flex` without wrapping, so on tablets and phones the five action buttons overflow horizontally and become unreachable.
- Several tiles hard-code heights (e.g., `.world-map-canvas { height: 240px; }`) without using responsive constraints. On short or narrow screens these rigid values either crop the content or push the tiles beyond the viewport.

Collectively, the current page is not responsive and violates the UX requirement called out by the user.

## Goals
1. Restore a true responsive grid layout (12 columns ≥1200px, 8 columns on tablets, single column on mobile) using class-based spans for large/medium/small tiles.
2. Ensure header actions and status blocks reflow cleanly below 900px without horizontal scroll.
3. Make the high-visibility tiles (map, timelines, metrics) honor flexible heights so they scale down gracefully on phones.

## Non-goals
- Rewriting the dashboard content, data sources, or React Query logic.
- Introducing new visual themes beyond the existing design system tokens.

## Proposed Changes
1. Replace the raw `.bento-grid` div with the shared `<BentoGrid>` layout wrapper so we inherit the centralized breakpoint rules and padding.
2. Add explicit CSS rules for `.tile-large`, `.tile-medium`, and `.tile-small` spanning 6/4/3 columns on desktop, 8/4 columns on tablet, and 1 column on mobile. Remove the broken `[style*="span"]` selectors, and make the tile base class flex so dynamic heights work.
3. Update `.dashboard-header` structure + CSS so the status chips and button group stack/wrap under 900px (e.g., `flex-wrap: wrap`, `gap`, `width:100%`, two-column button grid on phones) while preserving existing semantics.
4. Relax hard-coded heights by switching to `min()` / `clamp()` expressions (e.g., `height: min(32vh, 340px)` for the map) and ensure scrollable sections use `max-height: clamp(…)` instead of fixed `height` values.

## Impact / Risks
- Primarily CSS/structural change to a single React component; risk is low and limited to dashboard layout.
- Need to re-run existing visual/Playwright smoke tests for `/dashboard` to confirm selectors still exist.
