## ADDED Requirements

### Requirement: Constant-time owner authentication
Login MUST perform the full password-hash verification whether or not the
username exists, and MUST NOT reveal username existence through response
timing or payload. Every failed login MUST return the same status, error
code, and message regardless of which factor failed.

#### Scenario: Unknown username behaves like a wrong password
- **GIVEN** an owner exists
- **WHEN** login is attempted with a username that does not exist
- **THEN** the API runs the password-hash comparison against a dummy hash before responding
- **AND** responds 422 under the unified error envelope with the same generic invalid-credentials error as a wrong password for the real username
- **AND** the response time is comparable to an existing-username attempt

### Requirement: Owner setup policy and single-owner invariant
Owner setup MUST accept a stripped, non-empty username and a password of
10–72 UTF-8 bytes; violations MUST be rejected with 422 and MUST NOT create
an owner. The store MUST hold at most one owner: setup after an owner exists
MUST fail with 422, and concurrent first-run setups MUST produce exactly one
owner.

#### Scenario: Weak credentials are rejected
- **GIVEN** no owner is configured
- **WHEN** setup submits a nine-character password or a whitespace-only username
- **THEN** the status is 422 under the unified error envelope
- **AND** no owner is created

#### Scenario: Duplicate setup is rejected
- **GIVEN** an owner is already configured
- **WHEN** setup is submitted again with any credentials
- **THEN** the status is 422
- **AND** the existing owner is unchanged

#### Scenario: Concurrent setup yields exactly one owner
- **GIVEN** no owner is configured
- **WHEN** two setup requests race on a fresh store
- **THEN** exactly one request succeeds with 201
- **AND** the other fails with 422
- **AND** the store contains a single owner afterwards

### Requirement: Lazy session expiry
Session expiry MUST be enforced at validation time. A presented session past
its expiry MUST be invalidated server-side and treated as unauthenticated,
and each successful validation MUST refresh the session's last-seen
timestamp.

#### Scenario: Expired session is rejected on next use
- **GIVEN** a guest session whose 24-hour expiry has passed
- **WHEN** a request presents its token
- **THEN** the API responds 401 on authenticated surfaces
- **AND** the session record is deleted so the token cannot authenticate again

#### Scenario: Valid use refreshes the session
- **GIVEN** an active owner session last seen at time T
- **WHEN** it authenticates a request at time T+10 minutes
- **THEN** the request succeeds
- **AND** the session's last-seen advances to T+10 minutes

### Requirement: Logout terminates the session
Logout MUST delete the server-side session record and clear both the session
and CSRF cookies in the same response, returning 204 with no body.

#### Scenario: Logout clears session state
- **GIVEN** an authenticated session
- **WHEN** the session is deleted with a valid CSRF token
- **THEN** the session record is removed from the store
- **AND** both `novel_engine_session` and `novel_engine_csrf` cookies are cleared
- **AND** the response status is 204

### Requirement: Setup same-origin validation
The setup endpoint MUST validate browser origin metadata: `Origin` and
`Referer`, when present, MUST match the request's own origin or the
configured CORS origins. Origins that are the literal `null`, carry
userinfo, use a non-HTTP(S) scheme, carry a path, query, or fragment in
`Origin`, or declare an out-of-range port MUST be rejected with 403.
Localhost wildcard entries expand to the local development ports. Requests
without origin metadata, such as CLI and bootstrap clients, MUST remain
allowed.

#### Scenario: Foreign origin is rejected
- **GIVEN** first-run setup with default CORS origins
- **WHEN** the setup request arrives with `Origin: https://evil.example`
- **THEN** the status is 403
- **AND** no owner is created

#### Scenario: Null and userinfo origins are rejected
- **GIVEN** first-run setup
- **WHEN** the setup request arrives with `Origin: null` or an origin carrying a username or password component
- **THEN** the status is 403

#### Scenario: Local development origin is allowed
- **GIVEN** first-run setup with default CORS origins
- **WHEN** the setup request arrives from `http://localhost:5173`
- **THEN** the request proceeds

#### Scenario: Origin-less bootstrap client is allowed
- **GIVEN** first-run setup
- **WHEN** a local bootstrap client submits setup with neither `Origin` nor `Referer`
- **THEN** the request proceeds

### Requirement: Authentication endpoint rate limiting
The setup, login, and guest endpoints MUST be rate limited per client IP
with a token bucket defaulting to five requests per minute. Excess requests
MUST receive 429 with a `Retry-After` header in seconds under the unified
error envelope, and MUST NOT trigger authentication side effects. Client
identity MUST use the first `X-Forwarded-For` entry only when the immediate
peer is a configured trusted proxy (IP, CIDR network, or host); otherwise
the peer address itself. Preflight `OPTIONS` requests are exempt.

#### Scenario: Burst exhausted
- **GIVEN** the default five-per-minute limit
- **WHEN** a sixth setup, login, or guest request arrives from the same client IP within the window
- **THEN** the status is 429 with a `Retry-After` of at least one second
- **AND** no session or owner state changes

#### Scenario: Untrusted proxy cannot shuffle identity
- **GIVEN** no trusted proxies are configured
- **WHEN** requests from one peer address present differing `X-Forwarded-For` values
- **THEN** they share a single bucket keyed by the peer address

### Requirement: Production configuration guards
Production and staging MUST refuse to start when the session secret is
missing or the default value. Production MUST additionally require the
SQLite store and MUST reject CORS origins containing a wildcard or a
localhost address. Outside production, an unset secret MUST be replaced by a
fresh random value on every start — deliberately invalidating all existing
sessions at each restart.

#### Scenario: Default secret refuses production startup
- **GIVEN** the environment is production or staging and `SECURITY_SECRET_KEY` is unset or the default
- **WHEN** the server starts
- **THEN** startup fails with a configuration error rather than serving requests

#### Scenario: Production store and CORS restrictions
- **GIVEN** the environment is production
- **WHEN** the configuration names a non-SQLite database URL or CORS origins containing `*` or `localhost`
- **THEN** startup fails

#### Scenario: Non-production restart invalidates sessions
- **GIVEN** development with no secret configured
- **WHEN** the server restarts
- **THEN** all previously issued sessions fail authentication
- **AND** this logout-on-restart behavior is intended

### Requirement: CORS origin contract
The default allowed CORS origins MUST be the local development set
(`http://localhost:5173`, `http://localhost:4173`, `http://localhost:8000`),
credential-bearing requests MUST be allowed, and the `X-CSRF-Token` header
MUST be an allowed request header. Configured localhost wildcard entries
expand to exactly those development ports.

#### Scenario: Development origins carry credentials and CSRF
- **GIVEN** default settings
- **WHEN** a browser at `http://localhost:5173` calls the API with credentials and an `X-CSRF-Token` header
- **THEN** the cross-origin request is accepted

#### Scenario: Localhost wildcard expands to the development ports
- **GIVEN** `SECURITY_CORS_ORIGINS` contains `http://localhost:*`
- **WHEN** origins at ports 5173, 4173, and 8000 issue requests
- **THEN** each origin is allowed
- **AND** an origin at any other port is not

### Requirement: Environment configuration surface
Configuration MUST be read from the `.env.local` file (not `.env`) plus the
process environment, using the single prefix family `APP_`, `DB_`, `API_`,
`SECURITY_`, `LLM_`, `LOG_`, `MONITORING_`, and `HEALTH_`. CORS origins MUST
be configured through `SECURITY_CORS_ORIGINS` alone; legacy alias names are
retired and MUST be ignored. Defaults without configuration: the SQLite
store at `data/novel-engine.sqlite3`, host `0.0.0.0:8000`, and the
authentication rate limit of five per minute.

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

### Requirement: Principal-scoped data isolation
Every project-scoped query MUST be bound to the requesting principal: owner
data by `owner_id`, guest data by the guest `session_id`. A principal MUST
NOT observe or mutate another principal's data, and cross-principal
lookups MUST return not-found. Guests receive 24-hour sandboxes whose
projects, jobs, reviews, and exports MUST be deleted by the startup and
hourly cleanup once expired.

#### Scenario: Cross-principal access is not found
- **GIVEN** a project owned by the owner
- **WHEN** a guest requests it by identifier
- **THEN** the status is 404
- **AND** no data is disclosed

#### Scenario: Guest data is scoped by session
- **GIVEN** two guest sessions each hold a project
- **WHEN** one guest lists projects
- **THEN** only its own project appears

#### Scenario: Expired guest sandbox is cleaned up
- **GIVEN** a guest session older than 24 hours
- **WHEN** cleanup runs at startup or on the hourly schedule
- **THEN** its projects, jobs, reviews, and exports are deleted

### Requirement: CLI operational surface
The CLI MUST provide four commands. `serve` MUST back up the SQLite store
before applying pending migrations, then start the API. `import` MUST take
an explicit source path and owner, run as the owner principal without HTTP
authentication, and print the imported project. `backup` MUST write a backup
and print its path. `doctor` MUST report the version, database path,
integrity check, journal mode, foreign-key enforcement, and owner status,
exiting non-zero unless the integrity check passes and foreign keys are
enabled.

#### Scenario: Serve backs up before migrating
- **GIVEN** a database with pending migrations
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

### Requirement: Entry flow session probe
The Studio entry MUST probe the session on mount and take one of three
paths: a valid session replaces navigation into the project library; an
unconfigured owner renders a unified setup and login form whose single
submit creates the owner and establishes the session; a configured owner
renders the login form. The guest entry MUST remain available in every
state. The form prefills the username `author`, enforces the ten-character
password minimum, and switches autocomplete between new-password and
current-password according to setup status.

#### Scenario: Valid session skips to the library
- **GIVEN** a valid session exists
- **WHEN** the entry page mounts
- **THEN** navigation replaces into the project library without rendering the form

#### Scenario: First-run single submit sets up and logs in
- **GIVEN** no owner is configured
- **WHEN** the author submits the unified form once with valid credentials
- **THEN** the owner is created and the session established in one flow
- **AND** navigation proceeds to the project library

#### Scenario: Guest entry remains available
- **GIVEN** an owner is configured
- **WHEN** the entry page renders
- **THEN** the guest entry is still offered

### Requirement: In-memory document drafts
Document drafts — content, title, and save state — MUST live only in
component memory and MUST NOT persist per-document across navigation or
reloads. Switching documents or refreshing the page discards unsaved
keystrokes, with the loss window bounded above by the 1.5-second autosave
debounce. This discard is explicit, intended behavior.

#### Scenario: Switching documents discards the draft
- **GIVEN** unsaved edits younger than the debounce window
- **WHEN** the author switches to another document
- **THEN** the unsaved keystrokes are discarded and no revision is created

#### Scenario: No client-side draft persistence
- **GIVEN** unsaved edits
- **WHEN** the page reloads
- **THEN** the editor loads the last saved revision with no draft recovery

### Requirement: Terminal-state job list without polling
The Studio MUST NOT poll for job updates — no intervals, server-sent
events, or WebSockets. Job list freshness equals its last explicit trigger:
loading when the jobs tab becomes active and refreshing after actions that
create or mutate jobs. This contract presupposes the synchronous execution
model in which workflow responses already carry terminal state; if execution
becomes asynchronous, this Requirement and the API client timeout MUST be
reopened with it.

#### Scenario: Job list refreshes only on explicit triggers
- **GIVEN** a workflow response carried a terminal job state
- **WHEN** the author activates the jobs tab later
- **THEN** the list is fetched at that moment
- **AND** no background refresh occurs while the tab remains open

### Requirement: Frontend API client timeout
The frontend API client MUST default its timeout to 300000 milliseconds,
shared by regular requests and file downloads, overridable through
`VITE_API_TIMEOUT`. The default exists because workflow requests execute
provider calls synchronously and may legitimately run for minutes.

#### Scenario: Long workflow request is awaited
- **GIVEN** no `VITE_API_TIMEOUT` override
- **WHEN** a workflow request runs for 240 seconds
- **THEN** the client still awaits its response
- **AND** a request exceeding the timeout aborts with the timeout message

### Requirement: Section-filtered document views
The manuscript section MUST show every document; the outline, characters,
and world sections MUST show only documents of their kind. When the active
document does not match the section's kind, the section MUST fall back to
its first document of that kind.

#### Scenario: Outline section filters by kind
- **GIVEN** a project holds chapter, outline, character, and world documents and the active document is a chapter
- **WHEN** the author opens the outline section
- **THEN** only outline documents are listed
- **AND** the first outline document becomes active

### Requirement: Generated document naming
New documents MUST receive generated names: `Chapter N` for chapters and
`{Label} N` for other kinds, where N counts that kind's existing documents
plus one. Chapters prefill their content with the `# Chapter N` heading;
other kinds start empty. A generated name that collides with an existing
title after user renames MUST be rejected by the server's unique-identity
rule and surfaced through the normal error path.

#### Scenario: Chapter creation generates the next name
- **GIVEN** two chapters exist
- **WHEN** the author creates a new chapter
- **THEN** it is titled `Chapter 3` and prefilled with `# Chapter 3`

#### Scenario: Rename collision follows the normal error path
- **GIVEN** a user rename produced an existing `Chapter 3` title
- **WHEN** creation would generate the same name
- **THEN** the server rejects with 422
- **AND** the Studio surfaces the error through the normal path without silent retry

### Requirement: Client-derived export download
A successful export MUST trigger a browser download whose filename is
derived client-side from the project title and format, with markdown
mapping to the `md` extension; the server's `Content-Disposition` MUST NOT
be relied upon. The download is two-phase: create the export, whose
response embeds the download URL, then fetch the blob and hand it to the
browser, revoking the object URL afterwards.

#### Scenario: Export saves with the derived filename
- **GIVEN** a project titled `Draft` and a successful markdown export
- **WHEN** the download completes
- **THEN** the browser saves `Draft.md`
- **AND** the filename was derived client-side rather than from a response header

### Requirement: Silent project entry fallback
The Studio MUST silently navigate back to the entry route when any of the
initial project-load requests — session, project, reviews, or exports —
fails for any reason, including authentication, not-found, server, network,
or timeout failures; no error is surfaced.

#### Scenario: Initial load failure returns to entry
- **GIVEN** a studio route whose initial load requests fail
- **WHEN** the failure occurs for any reason
- **THEN** navigation replaces to the entry route
- **AND** no error banner or message is displayed
