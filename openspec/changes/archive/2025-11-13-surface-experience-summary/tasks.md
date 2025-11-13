## Task List

1. **Specs**
   - [x] Update `process-management` spec with a requirement to publish Playwright experience summaries to the CI job summary (with links to artifacts).
   - [x] Update `docs-alignment` spec so onboarding docs mention the job summary location.
2. **Implementation**
   - [x] Extend the experience-report generator (or a small wrapper) to emit a short Markdown block (status badges + links) suitable for GitHub job summary.
   - [x] Update GitHub workflow to call the summary script and append it to `$GITHUB_STEP_SUMMARY`, including links to the full `.md`/`.html` artifacts.
   - [x] Ensure the summary also prints locally (e.g., console output) for developers running Playwright by hand.
   - [x] Update README/docs to note that CI job summary now surfaces the report.
3. **Validation**
   - [x] Run the Playwright smoke workflow locally (or via `npm run test:e2e:smoke`) and confirm the summary markdown renders; capture artifacts to prove it works.
