## MODIFIED Requirements

### Requirement: Environment configuration surface

Configuration MUST be read from the `.env.local` file (not `.env`) plus the
process environment, using the single prefix family `APP_`, `DB_`, `API_`,
`SECURITY_`, `LLM_`, `LOG_`, `MONITORING_`, and `HEALTH_`. CORS origins MUST
be configured through `SECURITY_CORS_ORIGINS` alone; legacy alias names are
retired and MUST be ignored. Defaults without configuration: the SQLite
store at `data/novel-engine.sqlite3`, host `0.0.0.0:8000`, and the
authentication rate limit of five per minute.

An absent `.env.local` file (`ENOENT`) MUST be treated as no file
configuration. Every other file-read failure MUST be rethrown unchanged, and
configuration loading MUST stop. A parser exception MUST likewise be rethrown
unchanged, and configuration loading MUST stop. Process variables MUST NOT turn
either failure into the absent-file case.

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

#### Scenario: Missing environment file is optional

- **GIVEN** the selected `.env.local` path does not exist
- **WHEN** configuration loads
- **THEN** defaults and process variables are resolved without a file

#### Scenario: Unreadable environment file fails loudly

- **GIVEN** the selected `.env.local` path fails to read for any reason other
  than `ENOENT`
- **WHEN** configuration loads, even with process variables present
- **THEN** the same read failure is rethrown unchanged
- **AND** configuration defaults and process overrides are not returned

#### Scenario: Environment parser failure stays visible

- **GIVEN** the selected `.env.local` file is read but the environment parser raises
- **WHEN** configuration loads, even with process variables present
- **THEN** the same parser exception is rethrown unchanged
- **AND** the failure is not treated as an absent environment file

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
