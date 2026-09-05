# Error codes

Every API failure renders through the unified error envelope:

```json
{ "error": { "code": "STABLE_CODE", "message": "human-readable", "details": {} } }
```

`details` is optional and code-specific. The catalog below is the agent-facing
view of the code SSOT in `server/src/shared/domain/error_codes.ts`
(`ERROR_CODES`) and its HTTP status mapping in
`server/src/shared/interface/http/error_envelope.ts` (`ERROR_HTTP_STATUS`); the
OpenAPI document declares the same shape as the shared `ErrorEnvelope`
component schema. Keep them in lockstep — never restate a code as a bare
literal.

## Catalog

| Code | HTTP | Meaning | What an agent should do |
| --- | --- | --- | --- |
| `UNAUTHORIZED` | 401 | Session cookie missing, expired, or invalid; the surface requires an Owner session. | `POST /api/session/login` with owner credentials; the response sets the session and CSRF cookies. Retry with the cookie jar attached. |
| `FORBIDDEN` | 403 | Authenticated but not permitted: a non-owner principal on an owner-only surface (provider catalog, legacy import), or a foreign browser origin on `POST /api/setup`. | Log in as the Owner, or run owner-only operations through the CLI on the host. For setup, send no `Origin`/`Referer` (non-browser clients are accepted) or one matching the server origin / `SECURITY_CORS_ORIGINS`. |
| `CSRF_TOKEN_MISSING` | 403 | Authenticated write without the double-submit token. | Echo the `novel_engine_csrf` cookie value in the `x-csrf-token` header and retry. First-contact paths (`/api/setup`, `/api/session/login`) are exempt. |
| `CSRF_TOKEN_INVALID` | 403 | The `x-csrf-token` header does not match the `novel_engine_csrf` cookie (mismatched or stale pair). | Re-login via `POST /api/session/login` to mint a fresh pair, then retry the write. |
| `RATE_LIMIT_EXCEEDED` | 429 | The per-IP rate limit on the first-contact paths (`/api/setup`, `/api/session/login`) tripped. | Sleep `details.retry_after_seconds` (mirrored in the `retry-after` header), then retry once. Do not hot-loop. |
| `NOT_FOUND` | 404 | The addressed resource does not exist in the addressed scope, or it exists in a different project — the two are indistinguishable by design. Messages name the resource type and both ids. | Re-check the id and the project path from your records. Cross-project probing is pointless: other scopes are invisible, not an error. Also used for unknown routes (`Route <method> <url> is not known...`). |
| `INVALID_OPERATION` | 422 | The request is well-formed but the domain rejects it: unmet preconditions (export needs a chapter, accept needs a completed proposal), illegal values (non-lore alias writes, unknown beat titles), non-retryable job states, or wrong credentials at login. | Read the message — it names the missing precondition or the offending value. Fix the input or advance the domain state first; retrying unchanged will fail identically. |
| `EXPORT_CAPACITY_EXCEEDED` | 422 | A fresh export exceeded its fixed source-document, source-byte, or artifact-byte budget. `details` contains only the closed `resource`, inclusive `limit`, and bounded `observed` value. | Reduce the project or requested export below the reported limit before retrying. Repeating the unchanged fresh export cannot succeed, and there is no unlimited override. |
| `GENERATION_CAPACITY_EXCEEDED` | 422 | A complete Provider prompt exceeded the fixed 8 MiB UTF-8 budget. `details` contains only `resource: prompt_bytes`, the inclusive `limit`, and saturated `observed` value. | Reduce the manuscript or reference context before retrying. A keyed retry with the same key replays the permanent refusal; use a new key only after reducing the context. |
| `IMPORT_CAPACITY_EXCEEDED` | 422 | A legacy workspace exceeded its fixed story, chapter, total-byte, chapter-count, or directory-entry inspection budget. `details` contains only `resource`, `limit`, and `observed`. | Shrink or split the workspace before retrying. Replaying the unchanged import cannot succeed, and there is no unlimited override. |
| `STRUCTURE_CAPACITY_EXCEEDED` | 422 | A gated authoring-structure write would exceed one fixed inclusive budget (documents per project, volumes per project, chapters per volume, serialized Project settings or document metadata bytes, or outline beats per outline write). `details` contains only the closed `resource`, inclusive `limit`, and `observed` saturated to at most `limit + 1`. | Remove structure (or shrink the settings/metadata/outline content) below the reported limit, then resubmit. The refusal is permanent for unchanged input: there is no retry hint and no override. |
| `VALIDATION_ERROR` | 422 | Request failed schema validation. | Fix the fields listed in `details.errors` (each carries `field`, `type`, `message`), then resend once. |
| `REVISION_CONFLICT` | 409 | Optimistic concurrency: the save was based on a revision that is no longer current. No write occurred. | Re-read the document, use `details.current_revision_id` as the new `base_revision_id`, and reapply the change. |
| `VOLUME_CONFLICT` | 409 | A volume with this title already exists in the project. | Pick a different title; the message quotes the colliding one. |
| `DOCUMENT_CONFLICT` | 409 | A document with the same (project, kind, title) identity already exists. | Pick a different title; the message quotes kind and title. |
| `SNAPSHOT_CONFLICT` | 409 | An immutable export snapshot still references the document; deletion is refused. | Treat as permanent — snapshots are immutable references. Do not retry; the referencing export snapshot would have to stop existing first. |
| `OPERATION_IN_FLIGHT` | 409 | Either an identical pipeline operation (generation, review, export, retry) is already running, or project deletion currently owns the project-wide transition and cleanup window. | Inspect `details.operation`. For ordinary pipeline operations, do not resubmit; poll `GET /api/projects/{projectId}/jobs`. When it is `project deletion` and `document_id` is `null`, do not poll jobs or start new project work: wait for deletion cleanup to release the project, then re-read the project; `404` means deletion completed. |
| `OPERATION_CAPACITY_EXCEEDED` | 503 | The app-wide or per-project expensive-workflow limit is full. `details.scope`, `limit`, and `in_flight` identify the saturated counter; `retry_after_seconds` is mirrored in `Retry-After`. | Wait at least the indicated seconds, refresh job history, and let the Owner decide whether to retry. Do not retry automatically: the hint does not guarantee capacity will be available. |
| `SERVICE_UNAVAILABLE` | 503 | The persistence layer is not configured (database-free app instance, e.g. API-only boot or missing data directory). | Start the server with a configured data directory; do not retry against the same instance. |
| `INTERNAL_ERROR` | 500 | Unexpected failure, opaque by design; the stack never reaches the response. | Do not parse the body beyond `details.error_id`. Report the `error_id` (it equals the `x-request-id` header) together with the reproduction; the server log holds the stack under the same correlation id. |

## Notes

- Status and code are stable contract: a rewrite of a message text never
  changes them, and a 4xx never silently becomes a success.
- Fastify transport failures (malformed JSON bodies, unsupported media types)
  pass through under their native `FST_ERR_*` codes with the same envelope
  shape; they are transport-level, outside the catalog.
- `POST /api/session/login` answers wrong credentials with 422
  `INVALID_OPERATION` (constant-time path); it never distinguishes unknown
  user from wrong password.
