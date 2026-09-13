## MODIFIED Requirements

### Requirement: Health and version surface

The API MUST expose a database-aware health check, liveness and readiness
probes (`/health/ready` failing with 503 when not ready), and a version
endpoint reporting the product version, the runtime identifier and version,
the environment, and the build SHA. When application persistence exists, the
default readiness probe MUST execute a read-only check through the same live
SQLite handle used by requests. An injected probe MAY replace it explicitly.
The database-free walking skeleton MAY remain ready with no components, and
liveness MUST remain independent of dependency state.

#### Scenario: Readiness reflects the database

- **GIVEN** the SQLite database is unreachable
- **WHEN** `/health/ready` is requested
- **THEN** the response is 503

#### Scenario: Version reports the runtime

- **GIVEN** the server runs on Node
- **WHEN** `/version` is requested
- **THEN** the payload reports the product version and a `runtime` field with the Node version

#### Scenario: Default readiness uses the live SQLite handle

- **GIVEN** the application opened its configured SQLite database and no probe
  override was injected
- **WHEN** `/health/ready` is requested
- **THEN** the default probe performs a read-only check through that same handle
- **AND** the response is 200 only while the check is healthy

#### Scenario: Closed database is not ready but remains live

- **GIVEN** the process remains alive but its SQLite handle is closed or unusable
- **WHEN** liveness and readiness are requested
- **THEN** `/health/ready` responds 503 with a stable database failure
- **AND** `/health/live` remains 200

### Requirement: Environment configuration surface

Configuration MUST be read from the `.env.local` file (not `.env`) plus the
process environment, using the single prefix family `APP_`, `DB_`, `API_`,
`SECURITY_`, `LLM_`, `LOG_`, `MONITORING_`, and `HEALTH_`. CORS origins MUST
be configured through `SECURITY_CORS_ORIGINS` alone; legacy alias names are
retired and MUST be ignored. Defaults without configuration: the SQLite
store at `data/novel-engine.sqlite3`, host `0.0.0.0:8000`, and the
authentication rate limit of five per minute.

The fully resolved `DB_URL` path, including its basename, MUST be the one
database-file authority for API startup, import, backup, doctor, schema checks,
migration, reconciliation, and serving. Every downstream layer MUST preserve
that basename and MUST NOT replace it with a default. If `DB_URL` uses a
non-default basename and the default-name sibling exists in the same directory,
whether or not the configured file also exists, every API or maintenance start
MUST fail before backup, migration, reconciliation, import, or traffic; the
system MUST NOT choose, move, merge, or silently fall back to either file.

#### Scenario: Retired CORS alias names have no effect

- **GIVEN** `CORS_ORIGINS` or `CORS_ALLOWED_ORIGINS` is set in the environment
- **WHEN** settings load
- **THEN** the value is ignored
- **AND** `SECURITY_CORS_ORIGINS` remains the only recognized name

#### Scenario: Defaults apply without configuration

- **GIVEN** no environment configuration is provided
- **WHEN** the server starts
- **THEN** the database resolves to `data/novel-engine.sqlite3` on SQLite
- **AND** the server binds `0.0.0.0:8000` with the five-per-minute authentication limit

#### Scenario: The environment file is `.env.local`

- **GIVEN** `.env.local` declares a setting such as the application environment
- **WHEN** the server starts from the workspace root
- **THEN** the declared value applies without shell exports

#### Scenario: Custom SQLite basename remains one authority

- **GIVEN** `DB_URL` names `data/author.sqlite3`
- **WHEN** serve, import, doctor, and backup operate on the installation
- **THEN** every operation addresses `data/author.sqlite3`
- **AND** `data/novel-engine.sqlite3` is not created or inspected as a substitute

#### Scenario: Legacy split-brain fails before mutation

- **GIVEN** `DB_URL` uses a non-default basename and the default-name sibling
  exists in the same directory, whether or not the configured file also exists
- **WHEN** an API or maintenance command starts
- **THEN** startup fails before backup, migration, reconciliation, import, or traffic
- **AND** the failure identifies both the configured path and default sibling
- **AND** no database is selected, moved, merged, or repaired implicitly

### Requirement: CLI operational surface

The CLI MUST provide four commands. Every command MUST establish the configured
database authority and pass the legacy-sibling ambiguity gate before database
backup, migration, reconciliation, import, or inspection. After that gate
passes, `serve` MUST back up the SQLite store before applying pending
migrations, then start the API. `import` MUST take an explicit source path and
owner, run as the owner principal without HTTP authentication, and print the
imported project. `backup` MUST write a backup and print its path. `doctor` MUST
report the version, database path, integrity check, journal mode, foreign-key
enforcement, and owner status, exiting non-zero unless the integrity check
passes and foreign keys are enabled.

#### Scenario: Serve backs up before migrating

- **GIVEN** the database authority and ambiguity gate passes for a database with
  pending migrations
- **WHEN** `serve` runs
- **THEN** a backup is written beneath the backups directory before migrations apply

#### Scenario: CLI import binds to an owner

- **GIVEN** a legacy workspace directory
- **WHEN** `import` runs with the explicit source path and owner name
- **THEN** the project is imported scoped to that owner without HTTP authentication
- **AND** the imported project is printed

#### Scenario: Doctor fails on corruption

- **GIVEN** a corrupted database
- **WHEN** `doctor` runs
- **THEN** the integrity check reports the corruption
- **AND** the exit code is non-zero
