# Design: exact database authority and live readiness

## Exact path ownership

`ServerConfig.databasePath` is the only operational database-file identity.
`buildApp`, persistence startup, reconciled startup, doctor, import, and backup
pass that exact path without replacing its basename. The deepest database
startup boundary derives `dirname(databasePath)` once for the ownership lock,
export root, and backup directory. `DATABASE_FILENAME` remains a default and
test-fixture value, not a runtime reconstruction rule.

The API composition option becomes an exact `databasePath`. Callers that need a
database provide the file rather than a directory. The database-free walking
skeleton remains explicit by omitting it.

## Legacy ambiguity gate

Older builds may have ignored a custom basename and written live data to the
default sibling. When the configured basename is non-default, the directory is
locked and inspected before backup, schema checks, migration, reconciliation,
import, or listening. If the default sibling exists—whether alone or beside the
configured file—startup fails with both paths named. The system never guesses,
moves bytes, or falls back; a human must establish one authority.

Backup performs the same ambiguity check while holding directory ownership so
maintenance cannot certify a different file from serve, doctor, or import.

## Live SQLite readiness

A small infrastructure adapter implements the existing `HealthProbe` port over
the current `StudioDatabase.raw` handle. It checks the handle's open state and
executes one static read-only query. A closed handle or known SQLite failure
returns one stable unhealthy database component without exposing paths.
Unexpected programming errors remain visible to the existing fail-closed health
collector.

`buildApp` keeps an explicit injected probe highest precedence. Otherwise it
uses the live SQLite probe when persistence exists and the empty probe only for
the intentional database-free skeleton. Liveness never touches SQLite.
