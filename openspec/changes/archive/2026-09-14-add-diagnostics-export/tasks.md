# Tasks

Dependency graph: `T1` (server assembly service) blocks `T2` (route) and
`T3` (frontend action); `T2` blocks `T3`; `T4` is workflows and gates,
blocked by `T2`–`T3`.

Coordination: server assembly files (T1) and the Settings action files
(T3) are file-disjoint within this change. The OpenAPI baseline is a
shared regenerate-once surface across route-adding changes in the same
window (the lorebook-wizard and writing-stats changes also add routes);
regenerate serially, last writer reviews the additive-only diff. This
change touches no Inspector tab union, route state, or panels — it hangs
off the existing Settings surface.

## T1: Diagnostics assembly service

- [x] T1.1 Add the diagnostics assembly service (shared or studio
      application layering per the architecture policy): product identity
      and version via the release-version authority, runtime environment
      summary, configuration summary built from booleans (resolved
      provider id + label + configured state, recognized keys as
      set/unset), and a generated-at timestamp — with a schema that has no
      field capable of carrying a secret value. Acceptance:
      `pnpm --dir server test -- diagnostics` green, including a test that
      seeds a session secret and a provider API key and asserts neither
      string occurs anywhere in the serialized output.
- [x] T1.2 Add the database health summary reading the `doctor` field
      family (quick check, journal mode, foreign keys, owner configured)
      through the app's own database handle — no CLI subprocess.
      Acceptance: server tests assert field parity with the doctor
      report fields for a healthy database and an unopenable/corrupt one.
- [x] T1.3 Add the recent error summary scoped to the requesting project:
      the persisted error messages of that project's most recent failed
      Jobs, bounded to a fixed count. Only durably recorded data is
      presented — the HTTP envelope's error code is response-time-only
      and is not synthesized into the export; the provider failure
      diagnostics boundary keeps provider bodies out. Acceptance: server
      tests with a failed provider job whose discarded body must not
      appear, an assertion that no error-code field is emitted, project
      scoping (another project's failed jobs are absent), and empty
      history yielding an explicit empty state.

## T2: HTTP surface

- [x] T2.1 Add the owner-guarded read-only project-scoped route
      (`/api/projects/:projectId/diagnostics`, TypeBox response schema,
      thin-handler discipline) matching the Settings mount point.
      Acceptance: `pnpm --dir server test -- diagnostics` green including
      authentication (401 without session), owner data isolation (unknown
      identifiers are not found), and error-envelope cases.
- [x] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`), serially with the other
      route-adding changes in the window, review additive-only diffs,
      and regenerate frontend API types (`pnpm --dir frontend
      gen:api-types`). Acceptance: `pnpm --dir server gates` green.

## T3: Settings action and download

- [x] T3.1 Add the "Export diagnostics" action to the Settings panel with
      the privacy statement copy (EN + zh-CN dictionary entries), busy and
      error states under the explicit asynchronous operation state
      discipline, and a client-derived download
      (`novel-engine-diagnostics-<date>.json`) following the existing
      client-derived export download behavior. Acceptance:
      `pnpm --dir frontend test:unit -- Diagnostics` green (action
      renders the statement, download fires with the derived filename,
      failure surfaces with retry, duplicate-submission guarded).
- [x] T3.2 Assert the local-only contract at the client: the action's only
      request targets the Studio's own diagnostics endpoint. Acceptance:
      component tests assert the request path family; review confirms no
      other network surface is introduced.

## T4: Workflows, gates, and evidence

- [x] T4.1 Add a TypeScript-backend Playwright workflow: activate the
      action, capture the download, parse the JSON, assert version and
      database-health fields are present and the configured API key's
      value does not occur in the file. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- diagnostics_export` green.
- [x] T4.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
