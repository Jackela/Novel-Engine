# Proposal: enhance-experience-reporting

## Why
- Stakeholders requested a “端到端体验报告” that captures CTA → dashboard → offline cues each run; today’s Playwright output is raw logs, so they lack a concise, shareable summary.
- The new offline indicator emits UI state changes but no structured logs/metrics, limiting observability for support teams.
- Playwright CI takes ~4 minutes for every run; smoke vs. full splits would speed PR validation without losing coverage.
- Onboarding docs do not explain how to run the demo CTA flow, offline simulation, or the new `PLAYWRIGHT_VERIFY_*` env vars.

## What
1. Generate a human-readable “Experience Report” (Markdown/HTML) after Playwright runs, highlighting CTA success, guest banner state, offline indicator behaviour, and attaching key screenshots.
2. Emit lightweight console/metrics events whenever the connection indicator flips (ONLINE/LIVE/OFFLINE) so future telemetry can track incident frequency.
3. Introduce a smoke Playwright command (subset via `--grep` or dedicated spec) that runs <1 min for PRs, while keeping the full suite for nightly/merge builds.
4. Update README/onboarding docs with instructions for the demo CTA journey, offline simulation flags, `PLAYWRIGHT_VERIFY_ATTEMPTS`, and how to interpret the new Experience Report.

## Success Criteria
- Specs updated for frontend-quality/devtools-audit/docs-alignment to reflect the reporting, observability, and documentation expectations; process-management covers the CI split requirements.
- `tasks.md` enumerates the implementation steps, including scripts, Playwright config, logging hooks, and documentation.
- `openspec validate enhance-experience-reporting --strict` passes.
