# Design: Owner-scoped scalar Project patch

## Request and response boundary

`PATCH /api/projects/:projectId` accepts a strict object with these optional
top-level properties:

- `title`: string, 1 through 240 characters before application normalization;
- `description`: string, at most 10,000 characters;
- `settings`: a non-array JSON object with free-form JSON members.

The object retains `additionalProperties: false` and `minProperties: 1` as its
published schema, but schema declaration alone is insufficient in this app:
Fastify AJV removes additional properties before the handler. The route
therefore runs the principal/CSRF guard and then a route-scoped raw-key
`preValidation` hook before AJV. The hook reads the parsed request object's
original own top-level keys, rejects any key outside `title`, `description`, and
`settings`, and requires at least one original supported key. Thus `{}`,
unknown-only, and allowed-plus-unknown bodies all produce 422
`VALIDATION_ERROR` without relying on a property that AJV may remove. Non-object
bodies and wrong field types remain schema failures. The application trims an
included title and description exactly like project creation. A title that
becomes empty after trimming is 422; the same 240/10,000-character schema bounds
remain authoritative. An included empty description is valid and stores `""`.

Omission is distinct from an explicit value: each omitted field keeps its
stored value. `settings`, when present, is the complete replacement settings
object rather than a recursive merge. This matches the existing Settings action,
which starts from the current Project settings and changes `provider` before
sending. It also avoids inventing ambiguous null/delete semantics for arbitrary
future keys.

Success returns the strict scalar Project payload:

- `id`
- `title`
- `description`
- `settings`
- `import_hash`
- `created_at`
- `updated_at`

It never includes `documents`, `volumes`, current revision fields, metadata, or
Markdown. This is the same Project list-item shape used by the library, not the
Project shell and not a new duplicate DTO.

## Guard and error ordering

The route uses the existing principal guard and PATCH CSRF double-submit as the
first route-scoped `preValidation` hook, followed by the raw-key hook, followed
by normal AJV validation. This makes 401/403 authoritative before body-detail
validation on this write route while still preserving the unmodified body keys
for the closed-contract check. No application/store mutation runs until all
three stages have succeeded. Observable failures use the existing envelopes:

- 401 `UNAUTHORIZED` when no valid Owner session exists;
- 403 `CSRF_TOKEN_MISSING` or `CSRF_TOKEN_INVALID` for a missing or mismatched
  token pair;
- 422 `VALIDATION_ERROR` for an empty body, unknown field, wrong type, bounds
  failure, or a title empty after trimming;
- identical 404 `NOT_FOUND` code, `Project not found.` message, and envelope for
  a missing project and a project outside the authenticated Owner scope;
- 500 `INTERNAL_ERROR` for an unexpected persistence failure and 503
  `SERVICE_UNAVAILABLE` when persistence is unavailable, both without a
  partial update.

The handler never tries to rediscover unknown keys after AJV normalization.
After the guards, project lookup and update stay Owner-scoped so identifiers
never disclose cross-Owner existence.

## Atomic persistence seam

The application maps only present fields into a typed `ProjectUpdateInput`,
normalizes strings, serializes an included settings object, and supplies one
`now` value. The store performs one Owner-scoped SQLite UPDATE containing only
the selected scalar assignments. In that same atomic statement it assigns
`updated_at = max(stored updated_at + 1 millisecond, supplied now)` (or an
equivalent comparison inside one transaction), then returns the updated row.
The timestamp comparison and scalar assignments share the commit boundary;
there is no unlocked read-then-write race.

Every accepted PATCH therefore returns an `updated_at` strictly later than the
stored value, including equal-value commands, multiple commands in one clock
millisecond, and a backwards application clock. This preserves deterministic
updated-descending project-library ordering. A zero-row scoped update maps to
the uniform Project 404. Serialization or validation happens before the update,
and an injected store failure leaves all project fields and timestamp unchanged.

## Frontend merge and lifecycle

The API client parses the response with the strict scalar Project parser rather
than the Project-shell parser. On success, the Settings action first requires
`response.id === captured route project id === current shell id` and requires
the settings intent epoch still to match. A wrong response id is a local
contract error and causes no merge. A current matching response merges only
`title`, `description`, `settings`, and `updated_at`. It never overwrites `id`,
`import_hash`, or `created_at` from the response. The shell's `documents` and
`volumes`, the active accepted Document, Draft, History, Review, and Export
state remain untouched.

Each submit owns a monotonically increasing settings intent for its route
project. The initiating control exposes busy state and duplicate activation is
blocked. A project switch, unmount, or newer settings intent makes an older
response stale; that response cannot update the new project's scalars, form,
success, or error state. Cancellable requests are aborted on final owner release.

A local validation/403/500/503 failure remains readable in the Settings panel
with Retry available. A response 401 replaces to Entry, and a 404 replaces to
the project library because the mutated Project no longer resolves. Success
clears only the Settings error and synchronizes the form from returned scalars.
Focus returns to `Save settings` only when the author did not deliberately move
focus; if the project disappears, navigation owns focus instead.

## Persisted provider behavior

The Settings form sends `{ ...project.settings, provider: selectedProvider }`,
so complete settings replacement preserves unrelated known keys while changing
the provider. A real reload reads the saved Project shell and must show the new
title, description, and provider. Subsequent generation reads that provider from
the reloaded settings under the existing provider-selection behavior; this
change does not add credentials, models, or Provider configuration.

## Compatibility and history

The frontend's pre-existing PATCH call and Settings surface demonstrate the
intended compatibility shape, but they are not backend authority. The
TypeScript cutover shipped without the matching route, leaving an observable
422 `undeclared_body` gap. This change restores the behavior contract-first
without editing ADR-0003's executed cutover record or claiming that the route
existed in the released TypeScript baseline.

No ADR is needed: the update follows the existing Owner scope, unified errors,
Project scalar payload, SQLite authority, CSRF policy, route lifecycle, and
frontend state-ownership decisions. It introduces no new architecture.

## Options rejected

- Returning Project shell would retransmit structural rows after a scalar write
  and couple settings to document state.
- Recursive settings merge has undefined deletion/null semantics and could keep
  stale keys invisibly; complete object replacement is explicit.
- PUT would imply full Project replacement, including server-owned identity and
  timestamps.
- Updating title, description, and settings in separate routes creates partial
  visible outcomes for one form submission.
- Treating the frontend mock tests as sufficient would leave the real API 422
  `undeclared_body` and persistence gap untested.
