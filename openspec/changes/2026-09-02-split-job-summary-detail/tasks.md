# Tasks

## 1. Contract-first resource coverage

- [ ] 1.1 Add failing store/API tests proving list items contain exactly the
      twelve JobSummary fields with specified nullability/enums/timestamp
      strings, reject missing/wrong-type fields in the frontend parser, and
      exclude request, result, and events rather than making them optional.
- [ ] 1.2 Add sentinel tests proving list SQL, including lookahead, does not
      select request/result JSON or execute event hydration, while pagination
      order, cursor, scope, and high-cardinality behavior remain unchanged. Use
      execution trace evidence from the public store seam to prove zero
      `job_events` SELECT statements; do not substitute copied SQL.
- [ ] 1.3 Add failing detail tests for full JSON/event fidelity, oldest-first
      events, valid-shape unauthenticated 401, matched empty/overlong-param 422
      before auth/application using real Fastify injection, and identical
      code/message/body 404 for missing/cross-project/out-of-scope resources.

## 2. Server summary and detail seams

- [ ] 2.1 Introduce distinct `JobSummaryRecord`/page ports and an explicit
      summary projection using the production keyset query builder; remove the
      list event query without changing the full `findJob` port.
- [ ] 2.2 Map summaries without parsing large JSON and expose one application
      full-Job read over the existing scoped `findJob` behavior, normalizing
      known project/job misses to the stable Job-not-found response only.
- [ ] 2.3 Add strict summary and detail HTTP schemas plus the bounded scoped GET;
      keep complete terminal Job response schemas and retry execution unchanged.
- [ ] 2.4 Replace the deliberate OpenAPI snapshot, regenerate frontend types,
      and prove no schema/migration drift or architecture violation.

## 3. Atomic frontend migration

- [ ] 3.1 Introduce strict `StudioJobSummary` parsing/types for list pages while
      preserving strict complete `StudioJob` parsing for all terminal responses.
- [ ] 3.2 Migrate jobs pagination, inspector models, panel, retry refresh, tests,
      and factories to summaries without optional large fields or detail fetches.
- [ ] 3.3 Prove refresh/older/audit/project-switch ownership and focus behavior
      remain unchanged; audit and whole-book perform one summary first-page read
      and zero detail requests, including when another page exists.
- [ ] 3.4 Migrate server tests that legitimately inspect request/result/events to
      the explicit detail resource; keep scalar-only assertions on summaries.

## 4. Evidence and ordered release

- [ ] 4.1 Re-run pagination, retry, proposal/review/export bridges, provider
      diagnostics, unknown-outcome audit, whole-book, authorization, OpenAPI,
      type drift, and production query-plan regressions.
- [ ] 4.2 Run owning full server/frontend gates, browser workflows, strict
      OpenSpec, and independent fixed-SHA code/UX review; record every skip.
- [ ] 4.3 Keep this change active until required CI is green; archive pagination
      first, revalidate, then archive this change. Record detail UI, event
      pagination, and attempt correlation as separate non-goals.
