## Task List

1. **Specs**
   - [x] Update `frontend-quality` spec to require report retention (keep latest N files) and tag-stable Playwright coverage for CTA/offline scenarios.
   - [x] Update `process-management` spec to mention the cleanup step within CI/local workflows.
2. **Implementation**
   - [x] Enhance `scripts/generate-experience-report.mjs` (or a helper) to delete older report files, keeping only the most recent configurable count.
   - [x] Add explicit tags/annotations (`@experience-cta`, `@experience-offline`) to the relevant Playwright tests and have the reporter key off tags instead of fragile title substrings.
   - [x] Update docs (README/TELEMETRY) to describe retention + tagging behavior.
3. **Validation**
   - [x] Run `npm run test:e2e:smoke` locally to confirm reports generate, old files prune, and summary still renders.
