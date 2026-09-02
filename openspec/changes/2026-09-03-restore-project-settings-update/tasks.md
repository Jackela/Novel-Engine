# Tasks

## 1. Contract-first update coverage

- [ ] 1.1 Add real API failures for title-only, description-only,
      settings-only, and combined PATCH requests; prove omitted fields and
      `import_hash`/`created_at` remain unchanged, included settings replaces the
      complete object, and a strictly later `updated_at` is returned and
      persisted under normal, same-millisecond, and backwards clocks.
- [ ] 1.2 Add strict-body failures for `{}`, unknown properties, null/array
      bodies, unknown-only and allowed-plus-unknown objects, wrong field types,
      blank-after-trim title, over-240 title, over-10,000 description, and
      non-object settings; assert the raw-key check runs before AJV removal,
      at-least-one examines original supported keys, and every case returns the
      exact 422 envelope with zero project mutation.
- [ ] 1.3 Add guard/scope failures proving no session returns 401, missing or
      mismatched CSRF returns its exact 403 code, no guard failure enters the
      update store, and missing/cross-Owner projects return byte-identical 404
      `NOT_FOUND` / `Project not found.` envelopes after valid guards.
- [ ] 1.4 Add store/application failures proving normalization occurs before one
      Owner-scoped atomic update, selected scalar assignments plus
      `max(stored + 1 ms, supplied now)` commit together, equal/backwards clocks
      stay strictly monotonic, a zero-row update is not-found, and injected
      failure preserves every field and timestamp.
- [ ] 1.5 Assert the exact success response contains only Project scalar fields
      and never `documents`, `volumes`, revision fields, metadata, or Markdown.

## 2. Server Project PATCH

- [ ] 2.1 Add typed closed request schema and update input with at least one
      property, existing title/description bounds, free-form object settings,
      trim normalization, and no client-owned id/timestamp/import fields.
- [ ] 2.2 Register the principal/CSRF guard and raw original-key checker as
      ordered route `preValidation` hooks ahead of AJV; reject unknown-only,
      allowed-plus-unknown, and no-supported-key inputs without entering the
      service or store.
- [ ] 2.3 Add the Project service update over one Owner-scoped store seam,
      preserving omitted columns, replacing included settings, assigning one
      strictly monotonic `updated_at`, and mapping zero matched rows to uniform
      Project not-found.
- [ ] 2.4 Mount CSRF-protected PATCH on the existing project resource and return
      the existing strict scalar Project payload with exact 401/403/404/422/
      500/503 codes and envelopes.
- [ ] 2.5 Deliberately regenerate the OpenAPI baseline and frontend generated
      types; prove optional closed fields, at-least-one constraint, scalar
      response, error envelopes, and zero schema/migration drift.

## 3. Frontend scalar merge and ownership

- [ ] 3.1 Parse PATCH success as strict scalar Project, not Project shell, and
      reject missing/extra scalar fields or a body-bearing response.
- [ ] 3.2 Require response id to match both captured route Project and current
      shell; treat wrong identity as a contract error with no merge, and merge
      only title, description, settings, and `updated_at`, never id,
      `import_hash`, or `created_at`.
- [ ] 3.3 Preserve documents, volumes, active Document, Draft, and Inspector
      data across the matching mutable-scalar merge.
- [ ] 3.4 Bind each submit to route project plus settings intent epoch, expose
      exact initiating busy state, prevent duplicate activation, abort on final
      owner release, and reject late responses after project change, unmount, or
      a newer intent.
- [ ] 3.5 Keep local errors readable and retryable, route 401 to Entry and 404 to
      the library, clear only the current Settings error on success, synchronize
      the form, and restore focus only when the author did not move it.

## 4. Integrated persistence and release evidence

- [ ] 4.1 Add a TypeScript-backend Playwright workflow that changes title,
      description, and provider through the Settings panel, reloads the page,
      and proves all three persisted and the provider remains selected.
- [ ] 4.2 Run project create/list/shell/delete, Owner isolation, auth/CSRF,
      same-ms/backwards-clock Project ordering, settings-driven generation,
      frontend project switching, wrong-response-id/error ownership, form/focus,
      OpenAPI, and generated-type regressions.
- [ ] 4.3 Run server type-check/lint/arch/size/full tests and gates, frontend
      lint/format/type/unit/build and React diagnostics, browser workflows,
      strict OpenSpec, and independent fixed-SHA standards/security/UX review;
      record exact results and every skip.
- [ ] 4.4 Keep the change active until required CI is green, then merge it into
      the canonical specification and archive it. Do not fold project-shell,
      document-body, Provider configuration, or arbitrary settings-schema work
      into this release.
