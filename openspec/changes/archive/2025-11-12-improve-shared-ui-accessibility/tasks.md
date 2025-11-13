## Task List

1. **Upgrade shared form controls**
   - [x] Refactor `frontend/src/components/ui/Button.tsx`, `Input.tsx`, and `ErrorBanner.tsx` to use deterministic IDs, `type="button"` defaults, loading/disabled props, focus-visible styles, and tokenized classnames.
   - [x] Ensure error/helper text uses `aria-live` / `role` semantics and add documentation comments for future contributors.
2. **Dashboard loading & error states**
   - [x] Replace literal `"..."` placeholders in `frontend/src/components/Dashboard.tsx` with skeleton components tied to query loading flags and add `aria-live="polite"` messaging + retry affordances.
3. **Regression validation**
   - [x] Run `npm run lint`, `npm run type-check`, `npm test -- --run`, and `npm run test:e2e -- quick-e2e.spec.js` from `frontend/`.
   - [x] Run `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test`, `act --pull=false -W .github/workflows/ci.yml -j tests`, and `act --pull=false -W .github/workflows/deploy-production.yml -j tests` to confirm GitHub workflows stay green. Logs: `act-frontend-ci.log`, `act-ci.log`, `act-deploy.log`.
