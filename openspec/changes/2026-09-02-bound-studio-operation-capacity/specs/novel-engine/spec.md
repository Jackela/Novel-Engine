## ADDED Requirements

### Requirement: App-local expensive-workflow capacity admission

Each API app instance MUST bound admitted synchronous proposal, streaming
proposal, editorial review, export, and proposal/review/export retry executions
by both an application-wide limit and a per-project limit. Defaults MUST be four
application-wide and two per project. Project deletion, proposal acceptance,
reads/downloads, CRUD, authentication, legacy import execution, backup,
migration, startup recovery, and artifact reconciliation MUST NOT consume this
capacity.

After authentication, CSRF, and request-schema validation, admission MUST apply
this order atomically: an existing project-deletion owner, an identical target,
per-project capacity, then application capacity. The first two MUST retain 409
`OPERATION_IN_FLIGHT`; capacity refusal MUST return 503
`OPERATION_CAPACITY_EXCEEDED` with message `Studio operation capacity is
exhausted.`, `Retry-After: 5`, and details containing `scope` (`project` or
`application`), the numeric `limit`, current `in_flight`, requesting
`project_id`, and `retry_after_seconds: 5`. If both limits are exhausted, the
project scope MUST win. The retry hint MUST NOT trigger automatic retry.
`in_flight` MUST report the count for the named scope, and CORS responses MUST
expose `Retry-After` to an allowed browser origin.

The OpenAPI contract for every affected workflow route MUST document the 503
capacity envelope and an optional integer-seconds `Retry-After` response header
while continuing to permit persistence-unavailable 503 responses without that
header. Generated frontend API types MUST remain synchronized with that
contract.

Every successful admission MUST return an opaque permit bound to that exact
ownership generation. Release MUST be idempotent and an old permit MUST NOT
release a later operation for the same target. A workflow MUST hold its permit
through terminal landing and all workflow-owned Provider, generator, artifact,
acknowledgement, rollback, and reporting cleanup. A streamed proposal MUST also
hold it through response drain/disconnect handling and generator disposal. A
non-streaming workflow MAY release after its service-owned cleanup finishes,
before Fastify serializes its terminal payload.

Capacity refusal MUST occur before Provider construction and MUST create no
job, job event, usage event, snapshot, snapshot document, review, review issue,
export row, staged or final artifact, manifest, cleanup intent, or running retry
job. A streaming refusal MUST remain a normal pre-stream JSON error and MUST NOT
hijack the response.

#### Scenario: Per-project capacity is exhausted

- **GIVEN** two distinct admitted workflows are active for one project under
  the default limits
- **WHEN** another distinct workflow for that project requests admission
- **THEN** it receives 503 `OPERATION_CAPACITY_EXCEEDED` with project scope,
  limit 2, in-flight 2, and `Retry-After: 5`
- **AND** another project can still use remaining application capacity

#### Scenario: Application capacity is exhausted

- **GIVEN** four admitted workflows across projects fill the default app limit
- **WHEN** a workflow for a project below its own limit requests admission
- **THEN** it receives 503 `OPERATION_CAPACITY_EXCEEDED` with application scope,
  limit 4, in-flight 4, and `Retry-After: 5`

#### Scenario: Existing conflicts win over capacity

- **GIVEN** capacity is exhausted and either an identical target or project
  deletion already owns the requesting project
- **WHEN** that project receives the conflicting workflow
- **THEN** the request receives the established 409 `OPERATION_IN_FLIGHT`
- **AND** the failed admission does not change capacity counts

#### Scenario: Idle-project deletion ignores capacity elsewhere

- **GIVEN** other projects fill application workflow capacity
- **AND** the target project has no active workflow or deletion
- **WHEN** that target project is deleted
- **THEN** deletion may acquire project-exclusive ownership without a capacity
  permit

#### Scenario: Streaming refusal stays pre-stream

- **GIVEN** capacity is exhausted
- **WHEN** a streamed proposal requests admission
- **THEN** it receives the normal JSON 503 envelope before response hijacking
- **AND** no Provider stream, job, event, or usage evidence is created

#### Scenario: Retry refusal creates no running job

- **GIVEN** a retryable terminal job and exhausted capacity
- **WHEN** the author requests its retry
- **THEN** the request receives the capacity error
- **AND** no retry job or first retry event is created

#### Scenario: Cleanup owns the permit

- **GIVEN** an admitted workflow has landed an outcome but still owns Provider,
  generator, response, artifact, acknowledgement, rollback, or reporting cleanup
- **WHEN** another request would exceed a configured limit
- **THEN** it remains capacity-refused until the first workflow's outer cleanup
  releases its permit
- **AND** success, failure, disconnect, or cleanup failure releases that permit
  exactly once when ownership actually ends

#### Scenario: A stale permit cannot release a later owner

- **GIVEN** one permit released and a later workflow acquired the same target
- **WHEN** cleanup invokes the old permit's release again
- **THEN** the later workflow remains admitted and counted

#### Scenario: Invalid capacity configuration fails before persistence

- **GIVEN** either capacity value is outside 1 through 1024 or the per-project
  value exceeds the application value
- **WHEN** API configuration loads
- **THEN** startup fails before database open, backup, migration,
  reconciliation, Provider construction, or traffic

## MODIFIED Requirements

### Requirement: Environment configuration surface

Configuration MUST be read from the `.env.local` file (not `.env`) plus the
process environment, using the single prefix family `APP_`, `DB_`, `API_`,
`SECURITY_`, `LLM_`, `LOG_`, `MONITORING_`, and `HEALTH_`. CORS origins MUST
be configured through `SECURITY_CORS_ORIGINS` alone; legacy alias names are
retired and MUST be ignored. Defaults without configuration: the SQLite
store at `data/novel-engine.sqlite3`, host `0.0.0.0:8000`, the authentication
rate limit of five per minute, four active expensive workflows per app, and
two per project. `API_MAX_ACTIVE_WORKFLOWS` and
`API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT` MUST accept integers from 1 through
1024, and the per-project value MUST NOT exceed the app value.

An absent `.env.local` file (`ENOENT`) MUST be treated as no file
configuration. The selected path MUST resolve to a regular file; a directory or
other non-regular target MUST stop loading with a stable configuration error.
Every actual metadata or file-read failure other than `ENOENT` MUST be rethrown
unchanged, and configuration loading MUST stop. A parser exception MUST
likewise be rethrown unchanged, and configuration loading MUST stop. Process
variables MUST NOT turn any of these failures into the absent-file case.

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
- **AND** one app admits at most four expensive workflows and two per project

#### Scenario: The environment file is `.env.local`

- **GIVEN** `.env.local` declares a setting such as the application environment
- **WHEN** the server starts from the workspace root
- **THEN** the declared value applies without shell exports

#### Scenario: Missing environment file is optional

- **GIVEN** the selected `.env.local` path does not exist
- **WHEN** configuration loads
- **THEN** defaults and process variables are resolved without a file

#### Scenario: Unreadable environment file fails loudly

- **GIVEN** metadata lookup or reading the selected `.env.local` path fails for
  any reason other than `ENOENT`
- **WHEN** configuration loads, even with process variables present
- **THEN** the same metadata or read failure is rethrown unchanged
- **AND** configuration defaults and process overrides are not returned

#### Scenario: Non-regular environment target fails consistently

- **GIVEN** the selected `.env.local` path resolves to a directory or another
  non-regular target
- **WHEN** configuration loads on any supported platform
- **THEN** loading stops with a stable configuration error that identifies the path
- **AND** process variables do not turn the target into an absent-file case

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

#### Scenario: Invalid workflow capacity fails before mutation

- **GIVEN** a configured workflow capacity is outside 1 through 1024 or the
  per-project value exceeds the app value
- **WHEN** API or maintenance configuration loads
- **THEN** startup fails before backup, migration, reconciliation, import, or traffic
