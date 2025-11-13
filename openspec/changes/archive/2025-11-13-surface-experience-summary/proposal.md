# Proposal: surface-experience-summary

## Why
- The Experience Report currently lives only as downloadable artifacts. Stakeholders must hunt through CI logs to know if Demo CTA/Offline checks passed, which slows reviews.
- GitHub supports job summaries, but our workflows never publish the report snippet there.
- Documentation doesn't mention the report summary location, so onboarding engineers still ask where to find the results.

## What
1. Generate a concise summary (Markdown/HTML snippet) after Playwright runs and publish it to the GitHub job summary so reviewers can see pass/fail badges without downloading artifacts.
2. Keep storing the full `.md/.html` reports as artifacts, but link to them from the summary.
3. Update docs to explain that CI job summary now contains the Experience Report highlights and how to expand it.

## Success Criteria
- Specs (process-management + docs-alignment) capture the requirement that CI output includes a job summary referencing the experience report.
- Tasks list the script/workflow updates plus documentation steps.
- `openspec validate surface-experience-summary --strict` passes.
