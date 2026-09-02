# Tasks

## 1. Coherent proposal source

- [ ] 1.1 Add red two-connection SQLite tests with a deterministic interleave
      checkpoint proving one capture contains wholly the pre-commit or
      post-commit document/revision, outline/beat, volume, and Lore state.
- [ ] 1.2 Add the immutable proposal-context source port and one scoped Drizzle
      read transaction; keep the transaction closed before prompt or Provider
      work begins.
- [ ] 1.3 Derive target, resident context, linked beat, and Lore inputs purely
      from the captured value, with no later individual store reads.

## 2. Shared proposal pipeline

- [ ] 2.1 Add red sync/SSE/retry parity tests whose legacy store reads fail and
      whose Provider records the exact captured task.
- [ ] 2.2 Route `buildProposalTask` and all three entry points through one
      proposal-context capture and complete source/prompt admission before
      Provider construction and pre-SSE hijack.
- [ ] 2.3 Prove benign prompt bytes, system/data boundaries, digest limits,
      Lore lifecycle/matching/promotion, and exact/plus-one capacity behavior
      remain unchanged.

## 3. Retry base-revision fidelity

- [ ] 3.1 Add red tests for an unchanged base A and an advanced target B,
      including a retry whose source is itself a prior retry Job.
- [ ] 3.2 Keep the inherited base A authoritative; on A/B mismatch land one
      failed retry outcome with the fixed error and closed base/current evidence
      before prompt assembly or Provider construction.
- [ ] 3.3 Prove same-key stale replay performs no capture, Provider, Job, event,
      proposal, revision, or usage work; a different key is a separate failed
      attempt under the same base rule.

## 4. Integrated evidence

- [ ] 4.1 Run focused context/prompt/provider/pipeline/retry/SSE tests, server
      type-check/lint/arch/size/full tests, frontend type/unit/build, Playwright,
      API-types drift, and strict OpenSpec validation.
- [ ] 4.2 Record fixed-SHA evidence and all skips, explicitly naming project
      detail decomposition and project/job/review/export pagination as later
      changes.
- [ ] 4.3 Keep the change active until required CI is green, then merge it into
      the canonical specification and archive it.
