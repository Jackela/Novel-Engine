# Design: surface-experience-summary

## Approach
- Reuse the data extracted for the dual-format Experience Reports. After Playwright finishes, generate a condensed Markdown snippet such as:
  ```
  | Scenario | Status | Duration |
  | --- | --- | --- |
  | Demo CTA | ✅ | 2.3s |
  | Offline Recovery | ✅ | 2.1s |
  [Download full report](artifact-link)
  ```
- When running in GitHub Actions we append the snippet to `$GITHUB_STEP_SUMMARY`. Locally we print the same snippet to stdout so developers see it.
- Provide helper env var `EXPERIENCE_REPORT_SUMMARY_PATH` or detect `GITHUB_STEP_SUMMARY` automatically.
- Documentation: README + docs/TELEMETRY mention “CI job summary includes the Experience Report table with download links.”
