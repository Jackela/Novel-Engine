## Task List

1. **Spec deltas**
   - [x] Update `frontend-quality` spec with a requirement for the `/` → CTA → dashboard Playwright flow, including guest banner assertions.
   - [x] Update `dashboard-interactions` spec with a requirement for the connection/offline indicator state machine and accessibility.
2. **Playwright coverage**
   - [x] Add or extend a spec (e.g., login-flow or dedicated demo-entry test) that starts at `/`, uses the CTA, and validates guest banner + summary strip without `SKIP_DASHBOARD_VERIFY`.
   - [x] Add an offline simulation test that toggles `page.context().setOffline(true/false)` and asserts the indicator/ARIA states.
3. **Infrastructure cleanup**
   - [x] Remove the hard dependency on `SKIP_DASHBOARD_VERIFY` by making the global setup robust (auto-start stack or retry logic) so Chrome runs the real flow by default.
4. **Validation**
   - [x] Run `npm run lint`, `npm run type-check`, vitest, and the updated Playwright suite to document success.
