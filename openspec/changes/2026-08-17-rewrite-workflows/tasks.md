## 1. Specification

- [ ] 1.1 Draft the workflow deltas in the `novel-engine` capability
- [ ] 1.2 `pnpm spec:validate` green

## 2. Server implementation (per `/to-tickets` breakdown)

- [ ] 2.1 Proposal workflow: operation-to-step mapping, metadata-populated deterministic payloads, idempotent accept
- [ ] 2.2 Sanitization tables as single SSOT data plus the untrusted-manuscript prompt block
- [ ] 2.3 Provider contracts: explicit unconfigured failure, server-side model chain, shared structured-field retry module, per-request lifecycle
- [ ] 2.4 Review workflow: snapshot binding, rule set, shared word-count definition
- [ ] 2.5 Export workflow: snapshot reuse, markdown/DOCX/EPUB writers (`docx` + jszip), atomic project-scoped writes, delete-with-project
- [ ] 2.6 Jobs: synchronous execution, verbatim restart recovery, retry chain
- [ ] 2.7 Import: read-only preview, scope-bound idempotency, web source confinement

## 3. Frontend alignment

- [ ] 3.1 Provider selector default stays `project.settings.provider ?? mock`
- [ ] 3.2 No polling introduced: proposal, review, and export stay action-driven (changing the synchronous model reopens this slice and slice 4)

## 4. Verification

- [ ] 4.1 Server contract tests: unconfigured provider fails loudly, unknown step rejected, retry gated to failed/interrupted with import refused, restart recovery, import traversal/symlink rejection
- [ ] 4.2 e2e acceptance: proposal content is prose (F-1/#240 guard), markdown export byte-fidelity, DOCX/EPUB structure, project deletion removes the export directory
- [ ] 4.3 Mock-path unit assertions: proposal is not JSON, has no echo/result keys, and has non-trivial length
