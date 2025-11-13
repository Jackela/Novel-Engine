# Design: streamline-experience-report-maintenance

## Report Retention
- After writing new `.md/.html/.json` files, list existing report files sorted by timestamp and remove older ones beyond a configurable limit (default 10).
- Implement entirely in the Node script so both local and CI runs behave the same.

## Stable Test Identification
- Use Playwright annotations or tags (e.g., `test('...', { tag: '@experience-cta' }`) or `test('Demo', async () => {}, { annotations: [...] })`).
- Reporter queries JSON for tests whose titles include the tag or whose annotations match; this avoids manual string matching when titles change.

## Documentation
- Document retention behavior and tagging requirement in README / TELEMETRY doc so contributors know that older reports auto-delete and how to mark future tests for inclusion.
