## Why

The Owner has a configured Grok CLI and needs it to perform Novel Engine's four
AI tasks, including supporting-file tools and permissions. The current HTTP
providers cannot connect to ACP or present permission requests. Real Review
requests also omit manuscript text and cannot ground their editorial findings.

## What Changes

- Add an Owner-operated ACP WebSocket proxy and stdio connecting CLI command.
- Let authenticated trusted clients supply an agent launch command without a
  shell interpreter; keep Novel Engine's launch and model server-owned.
- Add the ACP Provider for chapter draft/revision, editorial review, and lore
  extraction, with typed progress, cancellation, and permission decisions.
- Preserve manuscript authority and disclose completed or uncertain tool effects.
- Supply captured chapter text and revision identity to Review under the shared
  prompt budget.

## Impact

Adds CLI commands, provider discovery/configuration, execution interaction APIs,
and bilingual Studio controls. Requires ACP SDK and WebSocket dependencies plus
deliberate OpenAPI/API-types regeneration. No database migration, release version
bump, production deployment change, or automatic issue closure is included.

Full-project acceptance, historical remediation, and release readiness are
recorded separately. Real-author interviews and retention validation are skipped
by the Owner for this request; the existing release gate is not rewritten.
