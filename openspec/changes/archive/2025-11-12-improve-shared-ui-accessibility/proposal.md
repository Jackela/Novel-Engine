## Why
- Shared form controls (Button, Input, ErrorBanner) rely on inline styles with weak focus cues, non-deterministic IDs, and missing semantic states, causing accessibility regressions and accidental form submissions.
- Dashboard overview tiles flash placeholder ellipses with no skeleton/loading state or aria-live messaging, which confuses both visual and assistive users when data fetches take >1s.
- QA asked for stronger regression coverage (lint, type, unit, smoke e2e, act) before merging UI tweaks, so we need a scoped plan that improves both UX and local CI fidelity.

## What Changes
- Upgrade the design system primitives (buttons, inputs, banners) to expose deterministic IDs, loading/disabled props, focus-visible styles, and aria attributes aligned with WCAG 2.1 AA.
- Add dashboard loading skeletons + live status messaging so metrics cards and activity lists never present empty/"..." states while data resolves; add retry affordance on fetch errors.
- Document and validate the workflow by re-running the agreed regression stack (lint, type-check, vitest, targeted Playwright smoke, act frontend + deploy tests).

## Impact
- Improves keyboard navigation, screen-reader support, and click safety across every screen that uses the shared controls.
- Raises perceived performance on the dashboard and sets a baseline pattern for other data-heavy surfaces.
- Keeps CI green through local validation, reducing risk before opening a PR.
