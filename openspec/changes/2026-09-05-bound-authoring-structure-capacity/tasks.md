# Tasks

## 1. Contract-first failing coverage

- [x] 1.1 Add store/API failures proving the 2,501st document create is
      refused with 422 `STRUCTURE_CAPACITY_EXCEEDED` (resource
      `project_documents`) while the 2,500th succeeds, with counts, rows,
      and revisions unchanged after refusal.
- [x] 1.2 Add API failures for the 101st volume (resource
      `project_volumes`), the 2,001st chapter placement into one volume
      (resource `volume_chapters`), and a volume deletion whose merge
      would overflow the surviving volume — each with at-limit success
      counterparts and no partial writes.
- [x] 1.3 Add API failures for Project settings and document metadata
      JSON beyond 16,384 serialized bytes (exact-boundary success,
      plus-one refusal) and for outline writes beyond 5,000 beats,
      including a restore and an accepted proposal that would mint an
      over-budget outline revision.
- [x] 1.4 Add envelope-stability failures: fixed message, closed
      `resource` catalog, saturated `observed`, no retry hint, and the
      documented 422 OpenAPI response on every affected structure route.

## 2. Domain and application enforcement

- [x] 2.1 Add the studio-domain structure capacity policy: fixed
      inclusive limits, the closed resource enum, and the validated
      `StructureCapacityExceededError` following the export/generation
      capacity pattern.
- [x] 2.2 Enforce the settings and metadata byte budgets in the owning
      application services after serialization and before any store call.
- [x] 2.3 Register the `STRUCTURE_CAPACITY_EXCEEDED` code, its 422
      status, and the error-mapping branch; document the catalog row.

## 3. Store-transaction enforcement

- [x] 3.1 Assert project-document and volume-chapter counts inside the
      document-creation transaction, project-volume count inside the
      volume-creation transaction, and target-volume chapter count inside
      chapter placement, using bounded `limit + 1` count projections.
- [x] 3.2 Assert the merged chapter count inside volume deletion before
      any orphan moves, and the outline-beat budget at the shared
      revision-minting chokepoint and document creation.

## 4. Contract surfaces and evidence

- [x] 4.1 Add the 422 capacity envelope to the affected structure routes,
      regenerate the deliberate OpenAPI baseline and frontend API types,
      and record the drift checks.
- [x] 4.2 Run the new suites red → green, then server type/lint/arch/
      gates/full tests, frontend lint/format/type/unit/build, and strict
      OpenSpec validation on the fixed candidate SHA; record exact results
      and every skip.
- [ ] 4.3 Keep the change active until required CI is green; browser
      Playwright workflows are intentionally not run locally (CI owns
      them) and human acceptance remains with the owner.
