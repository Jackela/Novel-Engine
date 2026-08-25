## ADDED Requirements

### Requirement: One product and version authority
The system MUST define Novel Engine as the only authoring product, MUST read
the product version from the single workspace package manifest, and MUST
define product behavior in the `novel-engine` capability specification.

#### Scenario: Derived surfaces report the release version
- **GIVEN** the workspace manifest declares version `0.4.0`
- **WHEN** the API, Studio, logs, monitoring metadata, and OpenAPI are produced
- **THEN** each surface reports `0.4.0`
- **AND** none requires an independent version override

### Requirement: Unified error envelope
Every API error response MUST use a single error envelope with a stable
`code`, a human-readable `message`, and an optional `details` object. The
legacy `{"detail": ...}` shape MUST NOT appear. A document save conflict
(HTTP 409) MUST identify the conflicting revision inside `details`.

#### Scenario: Validation failure
- **GIVEN** a request body violates a schema constraint
- **WHEN** the API responds
- **THEN** the status is 422 and the body is `{"error": {"code": "VALIDATION_ERROR", "message": ..., "details": ...}}`
- **AND** each invalid field is listed with its message and error type

#### Scenario: Conflict error carries the current revision
- **GIVEN** a client saves a document based on revision A while the document points to revision B
- **WHEN** the API responds
- **THEN** the status is 409 with error code `REVISION_CONFLICT`
- **AND** `details.current_revision_id` equals revision B's identifier

#### Scenario: Internal failure is opaque but traceable
- **GIVEN** an unhandled failure occurs while serving a request
- **WHEN** the API responds
- **THEN** the status is 500 with error code `INTERNAL_ERROR` and an `error_id`
- **AND** the response leaks no stack trace or internal detail

### Requirement: Session cookie contract
The session cookie MUST be named `novel_engine_session` and the CSRF cookie
`novel_engine_csrf`. The session cookie MUST be HttpOnly, SameSite=Lax,
scoped to the application path, and marked Secure in production and staging.
Owner sessions MUST last 30 days and guest sessions 24 hours.

#### Scenario: Owner login sets the session cookie
- **GIVEN** the owner authenticates successfully
- **WHEN** the response is delivered
- **THEN** `novel_engine_session` is set with the adjudicated attributes
- **AND** the guest equivalent expires within 24 hours

#### Scenario: Production cookies are Secure
- **GIVEN** the environment is production or staging
- **WHEN** any session cookie is set
- **THEN** it carries the Secure attribute

### Requirement: CSRF double-submit protection
Every state-changing API request MUST present an `X-CSRF-Token` header that
matches the `novel_engine_csrf` cookie under constant-time comparison,
except the setup, login, and guest endpoints, which are exempt. Mismatched
or missing tokens MUST be rejected with 403.

#### Scenario: Write without a valid token is rejected
- **GIVEN** an authenticated session
- **WHEN** a POST/PUT/PATCH/DELETE request omits or mismatches the CSRF token
- **THEN** the API responds 403 and performs no state change

#### Scenario: Exempt endpoints accept first contact
- **GIVEN** no session exists
- **WHEN** setup, login, or guest creation is requested
- **THEN** the request proceeds without CSRF validation

### Requirement: Session and provider surface
The API MUST expose owner setup (`GET`/`POST /setup`), authentication
(`POST /session/login`, `POST /session/guest`, `GET /session`,
`DELETE /session`), and provider discovery (`GET /providers` returning, for
each provider, whether it is configured, its model, and whether it is the
default).

#### Scenario: Provider discovery
- **GIVEN** no provider API key is configured
- **WHEN** `GET /providers` is called by the owner
- **THEN** each provider reports `configured: false`
- **AND** the response includes the mock provider as configured

### Requirement: Health and version surface
The API MUST expose a database-aware health check, liveness and readiness
probes (`/health/ready` failing with 503 when not ready), and a version
endpoint reporting the product version, the runtime identifier and version,
the environment, and the build SHA.

#### Scenario: Readiness reflects the database
- **GIVEN** the SQLite database is unreachable
- **WHEN** `/health/ready` is requested
- **THEN** the response is 503

#### Scenario: Version reports the runtime
- **GIVEN** the server runs on Node
- **WHEN** `/version` is requested
- **THEN** the payload reports the product version and a `runtime` field with the Node version

### Requirement: Request validation constraints
The API MUST enforce the adjudicated request constraints: titles 1–240
characters, AI instructions at most 10000 characters, AI operations limited
to `continue`/`rewrite`/`generate`, providers limited to
`mock`/`dashscope`/`openai_compatible`, import sources 1–240 characters
without path separators, and reorder requests naming every document of the
project exactly once.

#### Scenario: Overlong title is rejected
- **GIVEN** a project create request with a 241-character title
- **WHEN** the API responds
- **THEN** the status is 422 under the unified error envelope

#### Scenario: Partial reorder is rejected
- **GIVEN** a project has three documents
- **WHEN** a reorder request lists only two identifiers
- **THEN** the status is 422 and document order is unchanged
