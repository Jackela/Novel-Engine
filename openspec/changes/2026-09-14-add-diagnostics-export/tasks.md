# Tasks

Dependency graph: `T1` (server assembly service) blocks `T2` (route) and
`T3` (frontend action); `T2` blocks `T3`; `T4` is workflows and gates,
blocked by `T2`–`T3`. Write sets are disjoint: T1 owns
`server/src/` diagnostics assembly files; T2 owns the new route file and
the regenerated OpenAPI baseline; T3 owns the Settings panel action in
`frontend/src/features/studio/` plus the zh-CN/EN dictionary entries; T4
owns `frontend/tests/e2e-ts/` and evidence docs.

## T1: Diagnostics assembly service

- [ ] T1.1 Add the diagnostics assembly service (shared or studio
      application layering per the architecture policy): product identity
      and version via the release-version authority, runtime environment
      summary, configuration summary built from booleans (resolved
      provider id + label + configured state, recognized keys as
      set/unset), and a generated-at timestamp — with a schema that has no
      field capable of carrying a secret value. Acceptance:
      `pnpm --dir server test -- diagnostics` green, including a test that
      seeds a session secret and a provider API key and asserts neither
      string occurs anywhere in the serialized output.
- [ ] T1.2 Add the database health summary reading the `doctor` field
      family (quick check, journal mode, foreign keys, owner configured)
      through the app's own database handle — no CLI subprocess.
      Acceptance: server tests assert field parity with the doctor
      report fields for a healthy database and an unopenable/corrupt one.
- [ ] T1.3 Add the recent error summary from failed Job records through
      the existing error envelope (error codes + messages, bounded to the
      most recent N), honoring the provider failure diagnostics boundary
      (no provider body). Acceptance: server tests with a failed provider
      job whose response body must not appear; empty history yields an
      explicit empty state.

## T2: HTTP surface

- [ ] T2.1 Add the owner-guarded read-only route (`/api/diagnostics`,
      TypeBox response schema, thin-handler discipline). Acceptance:
      `pnpm --dir server test -- diagnostics` green including
      authentication (401 without session) and error-envelope cases.
- [ ] T2.2 Regenerate the OpenAPI baseline deliberately
      (`pnpm --dir server openapi:snapshot`), review additive-only diffs,
      and regenerate frontend API types (`pnpm --dir frontend
      gen:api-types`). Acceptance: `pnpm --dir server gates` green.

## T3: Settings action and download

- [ ] T3.1 Add the "Export diagnostics" action to the Settings panel with
      the privacy statement copy (EN + zh-CN dictionary entries), busy and
      error states under the explicit asynchronous operation state
      discipline, and a client-derived download
      (`novel-engine-diagnostics-<date>.json`) following the existing
      client-derived export download behavior. Acceptance:
      `pnpm --dir frontend test:unit -- Diagnostics` green (action
      renders the statement, download fires with the derived filename,
      failure surfaces with retry, duplicate-submission guarded).
- [ ] T3.2 Assert the local-only contract at the client: the action's only
      request targets the Studio's own diagnostics endpoint. Acceptance:
      component tests assert the request path family; review confirms no
      other network surface is introduced.

## T4: Workflows, gates, and evidence

- [ ] T4.1 Add a TypeScript-backend Playwright workflow: activate the
      action, capture the download, parse the JSON, assert version and
      database-health fields are present and the configured API key's
      value does not occur in the file. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- diagnostics_export` green.
- [ ] T4.2 Run the full owning gates (`pnpm --dir server gates`;
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`; `pnpm spec:validate`), record exact
      results and skips per `docs/agents/change-evidence.md`, keep the
      change active until required CI is green, then archive it.
