# Design: reinforce-demo-entry-validation

## Overview
The change focuses on codifying two UX flows (demo entry and offline indicator) so they are consistently enforced via specs and Playwright tests while keeping the runtime implementation minimal.

## Key Decisions
1. **Spec-driven coverage** – Instead of ad-hoc tests, we document the CTA journey and offline indicator as explicit requirements inside `frontend-quality` and `dashboard-interactions`. This ensures future changes must reconcile with the spec.
2. **Single-browser validation** – We keep the default Playwright matrix on Chromium but require the real landing flow to run (no `SKIP_DASHBOARD_VERIFY`). Additional browsers remain opt-in to avoid destabilizing CI.
3. **Deterministic selectors** – To support the new tests, we rely on existing `data-testid` hooks (`cta-demo`, `guest-mode-banner`, `connection-status`) rather than introducing complex instrumentation.

## Open Questions
- Should the demo CTA test live alongside login coverage or as a dedicated spec? (Default plan: extend `login-flow.spec.ts` so CI keeps one entry point.)
- Do we need to capture analytics for offline state transitions? Currently out-of-scope unless stakeholders request it.
