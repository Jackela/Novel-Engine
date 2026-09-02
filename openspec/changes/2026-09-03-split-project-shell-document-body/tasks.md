# Tasks

## 1. Contract-first project resource coverage

- [ ] 1.1 Add failing payload/store/API tests for the exact strict project
      shell, exact document-summary fields, required ordered volumes and
      documents, and the absence—not nullability—of `content_markdown`,
      `metadata`, and `revision_source` from detail and creation responses.
- [ ] 1.2 Add failing current-document GET tests for exact complete fidelity,
      one selected body only, valid-shape unauthenticated 401 before lookup,
      and identical code/message/body 404 responses for missing,
      cross-project, and out-of-scope documents.
- [ ] 1.3 Add execution-trace and query-plan failures proving shell reads no
      body/metadata columns in at most three SQL statements, current Document
      reads at most one body in at most two statements, both budgets stay
      independent of project size, and indexed scope/current-revision access
      avoids revision-history scans.
- [ ] 1.4 Add failing reorder coverage proving validation and atomic whole-set
      positions are unchanged while its response contains summaries only and
      performs no response-time body/metadata hydration.

## 2. Server shell and current-document seams

- [ ] 2.1 Introduce strict `DocumentSummary` and `ProjectShell` payload schemas,
      builders, records, and store/application ports separate from complete
      `DocumentWithCurrent`; keep persisted current-revision identity and exact
      word count as summary authority.
- [ ] 2.2 Replace project detail and creation materialization with the bounded
      ordered shell projection, preserving scalar settings/import fields,
      volume semantics, owner scope, and stable list ordering.
- [ ] 2.3 Add the authenticated scoped current-document application read and
      GET route at the existing document path; keep historical revision bodies
      private and normalize all scoped misses to the same existing 404.
- [ ] 2.4 Make reorder return ordered summaries without changing whole-set
      request validation, mutation atomicity, revision identity, or position
      rules.
- [ ] 2.5 Deliberately regenerate the OpenAPI baseline and frontend types; prove
      strict shell/current-document/reorder shapes, body exclusion, auth/error
      responses, and zero schema/migration drift.

## 3. Causally owned frontend project state

- [ ] 3.1 Split strict frontend contract parsing/types into Project shell,
      Document summary, and complete Document; reject legacy body-bearing shell
      rows and summary-shaped current-document responses.
- [ ] 3.2 Refactor project bootstrap to publish the shell first and fetch at
      most the route-compatible active Document, with no sibling-body prefetch
      and readable independent shell/editor failure and Retry states.
- [ ] 3.3 Implement the one-active-owner accepted-document state machine:
      validate project/document/current-revision identity, coalesce only equal
      expected revisions, reject stale/aborted/late responses, notify surviving
      subscribers, and clear request/body bookkeeping on owner change or final
      unmount.
- [ ] 3.4 Apply complete mutation responses causally to shell plus active body,
      apply reorder summaries without rolling back a newer body, and prove an
      older read or mutation can never overwrite a newer current revision.
- [ ] 3.5 Separate Draft from accepted cache state: keep the 1.5-second save
      trigger, retain a conflicted Draft while active, discard it on explicit
      switch/reload, and prevent late save/conflict results from crossing
      project or document ownership.

## 4. Lazy Inspector ownership

- [ ] 4.1 Remove Review and Export reads from project bootstrap; activate only
      the route-selected panel, including direct navigation and Back/Forward,
      and prove selecting either never requests the other.
- [ ] 4.2 Give shell, active Document, Review, and Export independent pending,
      error, abort, stale-response, and Retry state so one failure preserves the
      other surfaces and no failure is rendered as an empty document/history.
- [ ] 4.3 Preserve accessible Inspector selection, busy naming, retry focus,
      deliberate focus movement, and Stop visibility while panels hydrate
      lazily.

## 5. Integrated evidence and release boundary

- [ ] 5.1 Run project create/open, section fallback, document create/save/
      restore/accept/delete, lore/beat/volume placement, reorder, search,
      conflict, shell/current-document authorization, query-budget, and
      OpenAPI/type-drift regressions.
- [ ] 5.2 Run server type-check/lint/arch/size/full tests, frontend
      lint/format/type/unit/build, React diagnostics, strict OpenSpec, and
      TypeScript-backend Playwright project-open/switch/reorder/Review/Export/
      failure/retry/keyboard/Back/Forward workflows; record exact results and
      every skip.
- [ ] 5.3 Obtain independent standards, architecture, concurrency/security,
      and UX/accessibility reviews against one fixed SHA; repair findings and
      repeat until each fixed-SHA review is clean.
- [ ] 5.4 Keep the change active until required CI is green, then merge it into
      the canonical specification and archive it. Keep Review pagination/N+1,
      Export pagination, and project-catalog pagination as separately owned
      later changes.
