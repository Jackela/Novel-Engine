# Proposal: streamline-experience-report-maintenance

## Why
- The `frontend/reports/` folder accumulates every Playwright run, eventually producing dozens of `experience-report-*.{md,html,json}` files that clutter local environments and risk accidental commits.
- The experience-report script relies on partial title matches (e.g., "Landing CTA launches...") to locate tests; renaming specs breaks the report unless we manually adjust the script.
- Keeping the repo tidy and making reporting resilient to title changes improves developer experience and reduces noise.

## What
1. Introduce an automated retention mechanism (e.g., keep latest N reports, clean up older ones) when generating Experience Reports.
2. Standardize Playwright tests used in the report by enforcing explicit tags/IDs so the reporter can look up results reliably, regardless of title wording.
3. Document the cleanup behavior and tagging convention so contributors know what to expect.

## Success Criteria
- Specs updated (frontend-quality/process-management) to capture report retention + tagging expectations.
- Tasks enumerate cleanup script, Playwright tag updates, docs.
- `openspec validate streamline-experience-report-maintenance --strict` passes.
