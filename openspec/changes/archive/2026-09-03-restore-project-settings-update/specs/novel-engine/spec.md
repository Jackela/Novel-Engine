## ADDED Requirements

### Requirement: Owner-scoped partial Project settings update

The API MUST expose CSRF-protected
`PATCH /api/projects/:projectId` to an authenticated Owner. Its strict request
body MUST allow only optional `title`, `description`, and `settings` fields and
MUST require at least one original supported field. Because AJV may remove
additional properties, the route MUST inspect the parsed request body's original
own top-level keys before AJV normalization. Authentication and CSRF MUST run
first in the route's ordered `preValidation` chain; the next hook MUST reject
unknown-only and allowed-plus-unknown objects and MUST evaluate at-least-one
against the original supported keys. An included title MUST be a string of at
most 240 characters and MUST remain non-empty after trimming. An included
description MUST be a string of at most 10,000 characters and MUST be trimmed
before persistence. Included settings MUST be a non-array JSON object. Unknown
fields, an empty object, invalid types, or violated bounds MUST return the
existing 422 `VALIDATION_ERROR` envelope and MUST NOT enter the update service
or mutate the Project.

Every omitted field MUST retain its current stored value. An included settings
object MUST replace the complete stored settings object; it MUST NOT be merged
recursively. All included normalized fields and exactly one new `updated_at`
MUST commit as one atomic Project update. The new timestamp MUST equal
`max(stored updated_at + 1 millisecond, supplied now)` or an equivalent atomic
calculation, so every successful accepted PATCH advances `updated_at` strictly
even when the value is unchanged, the clock stays in one millisecond, or the
clock moves backwards.

Success MUST return only the strict scalar Project payload: `id`, `title`,
`description`, `settings`, nullable `import_hash`, `created_at`, and
`updated_at`. It MUST NOT return `documents`, `volumes`, current revision data,
metadata, or Markdown. No authentication or CSRF failure may enter the mutation
seam. After valid guards, a missing Project and a Project outside the Principal's
Owner scope MUST return the identical 404 `NOT_FOUND` / `Project not found.`
envelope without disclosure. Unexpected persistence failure MUST return the
opaque 500 `INTERNAL_ERROR` envelope; unavailable persistence MUST return 503
`SERVICE_UNAVAILABLE`; neither failure may partially update the Project.

#### Scenario: Partial title update preserves every omitted field

- **GIVEN** an Owner Project has a description, settings object, import hash, and creation timestamp
- **WHEN** the Owner patches only a title with surrounding whitespace
- **THEN** the trimmed title and one later `updated_at` are persisted atomically
- **AND** description, settings, import hash, and creation timestamp are unchanged
- **AND** the response contains Project scalars only

#### Scenario: Included settings replace the complete object

- **GIVEN** Project settings contain provider `mock` and another key
- **WHEN** the Owner patches settings with only `{ "provider": "dashscope" }`
- **THEN** the stored settings equal exactly the supplied object
- **AND** the omitted Project title and description are unchanged

#### Scenario: Empty or unknown patch is rejected

- **GIVEN** an authenticated Owner with a valid CSRF pair
- **WHEN** the PATCH body is empty or contains an unknown top-level field
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no Project field or timestamp changes

#### Scenario: AJV cannot hide a mixed unknown field

- **GIVEN** an authenticated Owner with a valid CSRF pair
- **WHEN** the original PATCH body contains a supported field plus an unknown top-level field
- **THEN** the raw-key `preValidation` check returns 422 `VALIDATION_ERROR` before AJV removes the unknown field
- **AND** the service and Project update store are not entered

#### Scenario: Unknown-only input does not satisfy at-least-one

- **GIVEN** an authenticated Owner with a valid CSRF pair
- **WHEN** the original PATCH body contains only unknown top-level fields
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no removed property is mistaken for a supported update

#### Scenario: Blank normalized title is rejected

- **GIVEN** an authenticated Owner with a valid CSRF pair
- **WHEN** the PATCH includes a whitespace-only title
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** the existing title and `updated_at` remain unchanged

#### Scenario: Write guards prevent mutation

- **GIVEN** a Project update without a valid session or matching CSRF pair
- **WHEN** the PATCH is submitted
- **THEN** the response uses the exact existing 401 or 403 error code for the failed guard
- **AND** the Project update store is not entered
- **AND** no Project state changes

#### Scenario: Project scope is not disclosed

- **GIVEN** valid authentication and CSRF for an Owner
- **WHEN** the route Project is missing or belongs to another Owner
- **THEN** both requests return the identical 404 `NOT_FOUND` / `Project not found.` envelope
- **AND** no Project is mutated

#### Scenario: Persistence failure is atomic and opaque

- **GIVEN** a valid settings PATCH reaches an unavailable or failing persistence seam
- **WHEN** no Project update commits
- **THEN** the response is 503 `SERVICE_UNAVAILABLE` or opaque 500 `INTERNAL_ERROR` as applicable
- **AND** no selected field or `updated_at` changes

#### Scenario: Updated time is strictly monotonic across clock anomalies

- **GIVEN** an Owner Project has a stored `updated_at`
- **WHEN** accepted PATCH commands receive the same-millisecond or backwards supplied clock
- **THEN** each committed `updated_at` is at least one millisecond later than its immediately stored predecessor
- **AND** the updated-descending Project catalog observes the new timestamp deterministically

#### Scenario: Successful response is not a Project shell

- **GIVEN** a Project with many Documents and volumes
- **WHEN** a valid settings PATCH succeeds
- **THEN** the response contains exactly the seven scalar Project fields
- **AND** no document, volume, revision, metadata, or Markdown field is returned

### Requirement: Recoverable Project settings save

The Studio MUST submit Project settings through the scoped PATCH and parse the
strict scalar Project response. Before any merge it MUST require the response
`id` to equal both the captured route Project id and current shell id. A mismatch
MUST be a local contract error and MUST NOT merge any response field. For a
matching current intent, it MUST merge only returned `title`, `description`,
`settings`, and `updated_at`; it MUST NOT overwrite `id`, `import_hash`, or
`created_at` from the response. The merge MUST preserve document summaries,
volumes, active accepted Document, Draft, and other Inspector state.
The title, description, and selected provider MUST be observable from persisted
Project settings after a full page reload.

Each submission MUST be owned by route Project identity and a settings intent
epoch. The initiating Save settings control MUST expose pending state and MUST
prevent duplicate activation while pending. A response from an earlier Project,
unmounted lifecycle, or older settings intent MUST NOT change the current shell,
form, success, or error state. A cancellable request MUST be aborted when its
final owner releases it.

HTTP 401 MUST replace to Entry and Project 404 MUST replace to the project
library. Validation, CSRF, network, timeout, contract, and server failures MUST
remain readable on the Settings surface with retry available. Success MUST clear
only the current Settings error and synchronize the form from returned scalar
authority. Focus MUST return to the initiating control only if the author did
not deliberately move focus elsewhere.

#### Scenario: Scalar success preserves shell and editor state

- **GIVEN** the current Project shell contains document summaries and volumes and its editor holds the active Document
- **WHEN** a settings PATCH succeeds for that same Project and current intent
- **THEN** returned title, description, settings, and `updated_at` merge into the shell
- **AND** shell id, import hash, and creation timestamp remain locally authoritative
- **AND** document summaries, volumes, active Document, Draft, and other Inspector state are unchanged

#### Scenario: Wrong response identity is rejected

- **GIVEN** a current settings request captured Project A and Project A remains current
- **WHEN** the parsed scalar response carries a different Project id
- **THEN** the Settings surface reports a local contract error
- **AND** no scalar, form, success, or shell field is merged

#### Scenario: Late settings response cannot cross Projects

- **GIVEN** a settings PATCH for Project A is pending
- **WHEN** the route changes to Project B before A responds
- **THEN** A's response cannot change B's shell, Settings form, success, or error state
- **AND** the request is aborted when cancellable and no other owner remains

#### Scenario: Save state is exact and recoverable

- **GIVEN** the author submits Project settings once
- **WHEN** the request is pending
- **THEN** Save settings alone exposes its busy state and duplicate submission is prevented
- **BUT WHEN** the request fails without navigation
- **THEN** the failure remains readable and the control becomes retryable

#### Scenario: Settings persist across reload

- **GIVEN** the author successfully saves a new title, description, and provider
- **WHEN** the Studio page is fully reloaded
- **THEN** the Project shell and Settings form show the saved title and description
- **AND** the saved provider remains selected for subsequent generation

#### Scenario: Settings success respects deliberate focus movement

- **GIVEN** a settings save is pending and the author moves focus away from Save settings
- **WHEN** the request succeeds
- **THEN** the scalar fields and form synchronize
- **AND** focus remains where the author placed it
