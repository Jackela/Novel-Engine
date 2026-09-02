# Use the configured database as the single authority

## Why

Configuration resolves the full `DB_URL` path, but API startup, doctor, and
import discard its basename and reopen `novel-engine.sqlite3`; backup alone
uses the configured file. A custom basename can therefore split runtime and
maintenance work across two databases. In addition, a persistence-backed app
defaults to an empty health probe, so readiness can remain 200 after its live
SQLite handle is closed.

## What changes

- Pass the exact configured database path through every API and CLI persistence
  composition boundary; derive the data directory only from that path.
- Fail before mutation when a custom path conflicts with a legacy default-name
  sibling instead of selecting, moving, or merging either file implicitly.
- Bind the default readiness probe to the same live SQLite handle used by the
  application while preserving liveness and database-free skeleton behavior.

## Non-goals

- No automatic database migration, rename, merge, or recovery decision.
- No change to SQLite schema, data format, backup retention, or HTTP shapes.
- No removal of injected health probes used by tests or integrations.

## Validation

- Exact-path startup and CLI integration tests with a custom basename.
- Legacy sibling ambiguity tests proving failure precedes backup or migration.
- Open/closed SQLite health-probe unit and app-level readiness tests.
- Full server gates, OpenSpec, browser workflows, and fixed-SHA evidence.
