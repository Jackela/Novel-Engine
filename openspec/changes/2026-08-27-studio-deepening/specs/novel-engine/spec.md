## MODIFIED Requirements

### Requirement: Session cookie contract
The session cookie MUST be named `novel_engine_session` and the CSRF cookie
`novel_engine_csrf`. The session cookie MUST be HttpOnly, SameSite=Lax,
scoped to the application path, and marked Secure in production and staging.
Owner sessions MUST last 30 days.

#### Scenario: Owner login sets the session cookie
- **GIVEN** the owner authenticates successfully
- **WHEN** the response is delivered
- **THEN** `novel_engine_session` is set with the adjudicated attributes

#### Scenario: Production cookies are Secure
- **GIVEN** the environment is production or staging
- **WHEN** any session cookie is set
- **THEN** it carries the Secure attribute

### Requirement: CSRF double-submit protection
Every state-changing API request MUST present an `X-CSRF-Token` header that
matches the `novel_engine_csrf` cookie under constant-time comparison,
except the setup and login endpoints, which are exempt. Mismatched or
missing tokens MUST be rejected with 403.

#### Scenario: Write without a valid token is rejected
- **GIVEN** an authenticated session
- **WHEN** a POST/PUT/PATCH/DELETE request omits or mismatches the CSRF token
- **THEN** the API responds 403 and performs no state change

#### Scenario: Exempt endpoints accept first contact
- **GIVEN** no session exists
- **WHEN** setup or login is requested
- **THEN** the request proceeds without CSRF validation

### Requirement: Session and provider surface
The API MUST expose owner setup (`GET`/`POST /setup`), authentication
(`POST /session/login`, `GET /session`, `DELETE /session`), and provider
discovery (`GET /providers` returning, for each provider, whether it is
configured, its model, and whether it is the default). A guest session
surface MUST NOT exist.

#### Scenario: Provider discovery
- **GIVEN** no provider API key is configured
- **WHEN** `GET /providers` is called by the owner
- **THEN** each provider reports `configured: false`
- **AND** the response includes the mock provider as configured

#### Scenario: Guest surface is gone
- **GIVEN** any session state
- **WHEN** `POST /session/guest` is requested
- **THEN** the response is 404 under the unified error envelope

### Requirement: Read-only idempotent legacy import
Import MUST never modify the source directory. A legacy workspace MUST
contain `story.yaml`; chapters come from `manuscript/chapters/chapter-*.md`
sorted by filename, and each becomes a chapter document titled `Chapter N`
by position, with no additional seeded document. Import MUST be idempotent
per owner scope: re-importing the same source hash within the owner scope
returns the existing project without duplication. Web imports MUST be
owner-only and confined to `data/imports`: path separators, traversal,
absolute paths, and symbolic links MUST be rejected, and the resolved source
MUST stay inside `data/imports`.

#### Scenario: Repeated import is idempotent
- **GIVEN** a legacy workspace was already imported by the owner
- **WHEN** the same source is imported again
- **THEN** the existing project is returned
- **AND** no duplicate project is created

#### Scenario: Web sources are confined
- **GIVEN** a web import request names a source with traversal, an absolute path, or a symbolic link under `data/imports`
- **WHEN** the import is attempted
- **THEN** the request is rejected before any file is read

#### Scenario: Legacy structure contract
- **GIVEN** a directory without `story.yaml`
- **WHEN** import is attempted
- **THEN** the request is rejected with an explicit error
- **AND** for a valid workspace, chapters are ordered by filename and titled `Chapter 1` through `Chapter N`

### Requirement: Lazy session expiry
Session expiry MUST be enforced at validation time. A presented session past
its expiry MUST be invalidated server-side and treated as unauthenticated,
and each successful validation MUST refresh the session's last-seen
timestamp.

#### Scenario: Expired session is rejected on next use
- **GIVEN** an owner session whose 30-day expiry has passed
- **WHEN** a request presents its token
- **THEN** the API responds 401 on authenticated surfaces
- **AND** the session record is deleted so the token cannot authenticate again

#### Scenario: Valid use refreshes the session
- **GIVEN** an active owner session last seen at time T
- **WHEN** it authenticates a request at time T+10 minutes
- **THEN** the request succeeds
- **AND** the session's last-seen advances to T+10 minutes

### Requirement: Authentication endpoint rate limiting
The setup and login endpoints MUST be rate limited per client IP with a
token bucket defaulting to five requests per minute. Excess requests MUST
receive 429 with a `Retry-After` header in seconds under the unified error
envelope, and MUST NOT trigger authentication side effects. Client identity
MUST use the first `X-Forwarded-For` entry only when the immediate peer is a
configured trusted proxy (IP, CIDR network, or host); otherwise the peer
address itself. Preflight `OPTIONS` requests are exempt.

#### Scenario: Burst exhausted
- **GIVEN** the default five-per-minute limit
- **WHEN** a sixth setup or login request arrives from the same client IP within the window
- **THEN** the status is 429 with a `Retry-After` of at least one second
- **AND** no session or owner state changes

#### Scenario: Untrusted proxy cannot shuffle identity
- **GIVEN** no trusted proxies are configured
- **WHEN** requests from one peer address present differing `X-Forwarded-For` values
- **THEN** they share a single bucket keyed by the peer address

### Requirement: Entry flow session probe
The Studio entry MUST probe the session on mount and take one of two paths:
a valid session replaces navigation into the project library; otherwise a
form renders — a unified setup and login form when the owner is
unconfigured (single submit creates the owner and establishes the session),
the login form when the owner exists. The form prefills the username
`author`, enforces the ten-character password minimum, and switches
autocomplete between new-password and current-password according to setup
status.

#### Scenario: Valid session skips to the library
- **GIVEN** a valid session exists
- **WHEN** the entry page mounts
- **THEN** navigation replaces into the project library without rendering the form

#### Scenario: First-run single submit sets up and logs in
- **GIVEN** no owner is configured
- **WHEN** the author submits the unified form once with valid credentials
- **THEN** the owner is created and the session established in one flow
- **AND** navigation proceeds to the project library

### Requirement: Complete single-author Studio
The system MUST provide project library, manuscript, outline, character, world,
review, history, export, and settings surfaces.

#### Scenario: Authoring flow
- **GIVEN** an owner project
- **WHEN** the author edits a Markdown document and pauses for 1.5 seconds
- **THEN** the Studio saves a new revision
- **AND** shows saved, saving, or conflict state

## REMOVED Requirements

### Requirement: Principal-scoped data isolation

## ADDED Requirements

### Requirement: Owner data isolation
Every project-scoped query MUST be bound to the single owner principal, and
every project resource MUST resolve only within the owner's data.
Identifiers that do not resolve MUST return not-found without disclosing
existence.

#### Scenario: Unknown identifiers are not found
- **GIVEN** any project-scoped resource address
- **WHEN** an identifier that does not exist in the owner's data is requested
- **THEN** the status is 404 and no data is disclosed

### Requirement: Volume hierarchy
Chapters MUST be organized into volumes — the level between the project and
its chapters. A project MUST always hold at least one volume, and a freshly
created or imported project MUST start with a single default volume
containing its chapters. Reading order MUST be volume order, then chapter
order within each volume; reordering MUST operate on that order. Exports
MUST follow the same order. Non-chapter documents MUST stay outside
volumes.

#### Scenario: New project starts with a default volume
- **GIVEN** a newly created project
- **WHEN** its structure is read
- **THEN** it contains one volume holding its chapters in reading order

#### Scenario: Export order follows volumes
- **GIVEN** a project whose chapters span two volumes
- **WHEN** an export is written
- **THEN** chapters appear in volume order, then in-volume order

### Requirement: Chapter beat association
Each chapter MUST be associable with exactly one beat of the project's
outline document, and the association MUST be readable and editable through
the chapter. Generation for a chapter MUST include its linked beat's content
in the prompt; an unlinked chapter MUST generate without a beat.

#### Scenario: Generation includes the linked beat
- **GIVEN** a chapter linked to an outline beat describing the storm scene
- **WHEN** a proposal is drafted for that chapter
- **THEN** the provider prompt contains the beat's content

#### Scenario: Unlinked chapter generates without a beat
- **GIVEN** a chapter with no beat association
- **WHEN** a proposal is drafted for that chapter
- **THEN** the prompt contains no beat section

### Requirement: Resident context injection
Every proposal generation MUST assemble the resident context ahead of the
target manuscript: the outline (with the current beat position), a rolling
summary of the prior chapters, and the tail of the most recent chapter. The
assembly MUST draw only from the project's own documents, and the rolling
summary MUST cover every prior chapter in reading order.

#### Scenario: Continuation sees the prior story
- **GIVEN** a project with an outline and three completed chapters
- **WHEN** a proposal is drafted for the next chapter
- **THEN** the provider prompt contains the outline, a summary covering chapters 1 through 3, and the tail of chapter 3
- **AND** the target chapter's manuscript follows the resident context

### Requirement: Keyword-triggered lore entries
Character and world documents MUST serve as lore entries: the entry keys are
the document title plus aliases declared in the document's metadata, and the
entry content is the document's current markdown. When a key occurs in the
resident context or the target manuscript, the entry MUST be injected into
the prompt; lore entries without a key occurrence MUST be omitted.

#### Scenario: Alias triggers injection
- **GIVEN** a character document titled `Mara` declaring the alias `the archivist`
- **WHEN** the target manuscript mentions `the archivist`
- **THEN** the document's content is injected into the prompt

#### Scenario: No key hit, no injection
- **GIVEN** a world document whose keys never occur in the resident context or manuscript
- **WHEN** a proposal is drafted
- **THEN** that document's content is not injected

### Requirement: LLM editorial review
A review MUST snapshot the project's current revisions (reason `review`) and
MUST run the editorial review provider step over that snapshot, producing
findings that each carry a severity (`blocker` or `warning`), a review
dimension from the server-owned closed dimension set, a message, and a
suggestion. Findings MUST be ordered by severity, then dimension, then
document position. The review stays snapshot-bound: later edits MUST NOT
rewrite recorded findings. A provider failure during review MUST produce a
failed job under the existing terminal semantics and MUST NOT fabricate
findings.

#### Scenario: Dimensioned findings are reported
- **GIVEN** a snapshot whose chapters contain pacing and continuity problems
- **WHEN** a review runs
- **THEN** each finding reports a dimension from the closed set with a severity, message, and suggestion

#### Scenario: Provider failure fails the job
- **GIVEN** the editorial review provider step fails with a known provider error
- **WHEN** the review request completes
- **THEN** the job records status `failed` with the error
- **AND** no findings are recorded for that review

### Requirement: Project usage surface
The API MUST expose `GET /api/projects/:projectId/usage` to the owner,
aggregating the project's recorded usage events: total prompt tokens, total
completion tokens, request count, and a per-model breakdown.

#### Scenario: Aggregates reflect recorded events
- **GIVEN** recorded usage events across two models
- **WHEN** the usage surface is read
- **THEN** the totals equal the recorded sums
- **AND** the per-model breakdown separates the two models

### Requirement: Whole-book generation loop
The Studio MUST offer a whole-book generation mode driven by the frontend
over the existing synchronous proposal and accept endpoints: it drafts a
proposal for the next chapter needing one, accepts it automatically, and
proceeds in reading order. The loop MUST be stoppable at any moment and
resumable; already-accepted chapters MUST be preserved, and a stop MUST
leave every completed chapter intact.

#### Scenario: The loop advances chapter by chapter
- **GIVEN** a project with an outline and one completed chapter
- **WHEN** the whole-book loop runs
- **THEN** each subsequent chapter receives a generated proposal that is accepted automatically in reading order

#### Scenario: Stop preserves completed work
- **GIVEN** the loop has accepted two chapters
- **WHEN** the author stops the loop
- **THEN** the two accepted chapters remain, and no further chapters are generated
