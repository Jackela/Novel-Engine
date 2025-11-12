# Design: Dashboard Density Controls

## Goals
1. Provide consistent visual rhythm even when streams/events explode with text by letting zones switch between relaxed and compact modes.
2. Surface semantic signals for automation/AI (e.g., `data-density="compact"`) so future routines can orchestrate layout without hacking CSS.
3. Avoid large rewrites: reuse existing flow zones, layering density heuristics atop them.

## Approach
### 1. Density heuristics
- Define a shared helper (`useZoneDensity` or utils) that accepts `contentLength` + thresholds and returns `relaxed | compact`.
- Control cluster: use pipeline queue length + snackbar backlog to flip density.
- Streams: base on activity feed length (>6 entries) or timeline events.
- Signals: base on event cascade nodes / performance alerts.

### 2. Semantic attributes
- Each zone `<section>` already has `data-role`; add `data-density`, `data-volume`, `data-overflow`. Example: `<section data-role="stream-feed" data-density="compact" data-volume="high">`.
- Child components surface the same attributes for sub-panels when helpful.

### 3. Styling tokens
- Extend `Dashboard.css` with `.density-compact` class toggled via `className` or attribute selectors to tighten padding, type scale, chip sizes.
- Use CSS variables (e.g., `--zone-gap`, `--zone-font-scale`) to avoid deep overrides.

### 4. Overflow handling
- Streams/Signals: when compact, limit visible rows and show “View more” affordance (deferred for now) or enable virtualization placeholder.
- QuickActions: in compact mode reduce chip spacing, show condensed run summary, keep actions accessible.

### 5. Testing
- Unit tests around heuristic helpers (jest/vitest).
- Update Playwright page object to assert `data-density` toggles when seeding long activity lists.

## Risks / Open Questions
- Need to ensure density heuristics don’t flicker when data updates rapidly → add debounce.
- Playwright fixtures may need deterministic data seeds to trigger compact mode.
