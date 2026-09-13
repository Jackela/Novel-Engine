# Backend Excellence — backlog clearance continuation — 2026-09-13

Direct continuation of the 2026-09-12 campaign (see
`backend-excellence-2026-09-12.md`). Owner directive: "进行编排彻底完成全部遗留问题" —
orchestrate the complete clearance of every remaining backlog ticket
(#502, #534, #535, #536, #537, #538, #539, #561). Same discipline: orchestrator
only; implementer (flash) subagents; surgical PRs; strict up-to-date merge rings.

## Owner decisions

- **#537 (asked, answered 2026-09-12): remove the alembic startup guard — the
  Python-era support window is closed.** Landed as #576 (guard + test deleted,
  README upgrade section reworded, ADR-0003 amendment note).
- **#539 capacity half (orchestrator ruling during execution, direction B)**:
  domain-layer capacity messages inline resource/limit for humans/logs; every
  wire face pins the historical literal (HTTP envelope via `*_CAPACITY_MESSAGE`
  constants; retry-outcome persisted `job.error` pins the protocol constant —
  a live invariant, since replay recognition matches that literal). Rationale:
  `details` already serves agents; B preserves all wire contracts.

## Ledger — all remaining tickets cleared

| Ticket | Disposition | PR(s) |
|---|---|---|
| #502 DashScope official Responses path + apiBase pass-through | fixed | #575 |
| #534 jobs/usage schema ownership → studio (drizzle: "No schema changes, nothing to migrate") | fixed | #589 (import conflict with #582 resolved) |
| #535 a) depcruise ai-exemptions narrowed to named wiring files | fixed | #588 |
| #535 b) studio_store type bazaar dissolved (171→17; records to owning ports) | fixed | #598 |
| #535 c) AppOptions extends module interfaces; structured assembly inputs | fixed | #587 |
| #536 (epic, 12 sub-items) landing split / isRecord / naming freeze / durable-fs+isDescendant / pageLimit engine / failed-job assembler / route-response combinators / stream-unwrap phases / capacity-twins protocol / document-seed helper / recovery-chain steps / pipeline decoupling / cursor factory / dashscope extractor / document-route split | all fixed | #571 #572 #573 #578 #574 #580 #581 #577 #579 #582 #583 #584 #586 #585 #592 |
| #537 alembic guard removed (Owner decision) | fixed | #576 |
| #538 needless exports: wave1 contexts 113 / wave2 shared+apps 50 / wave3 frontend 34 (≈197 of ~211 recounted; remainder = deliberate keeps: test seams, SSOT faces, dynamic consumers) | fixed | #601 #600 #603 |
| #539 NOT_FOUND ids (20 sites) + capacity inline (direction B) | fixed | #599 |
| #561 frontend giant-hook family (7 sub-tickets: useDocumentDraft / useStudioProposal / useStudioPageModel / useWholeBookLoop / useDocumentDraftActions / useStudioProject / useStudioActions) | all fixed | #590 #602(supersedes #591) #594 #593 #595 #597 #596 |

Open tickets remaining in the tracker after this continuation: **#454** (a
pre-campaign Cloud Agent environment PR, not this campaign's scope) and #306
(Owner manual 2FA action).

## Numbers

- 27 PRs merged green across the continuation (#571-#603 minus #591 which was
  superseded by #602), 0 P1s shipped, every PR carried targeted-test evidence
  + gates; full-suite authority delegated to CI per the degraded-mode
  discipline below.
- Wire-safety highlights: OpenAPI snapshot byte-identical through every route-
  touching PR (SHA-verified on #581/#586/#592); drizzle itself certified the
  schema move as DDL-identical (#589); cursor wire format pinned by literal
  Base64 token assertions through the factory conversion (#586).
- Invariant saves by the implementer/review layers: replay-recognition literal
  pinning (#599), react-doctor ownership shape on the extracted proposal hook
  (#591→#602), accept-race pending-ledger leak avoided during that fix.

## Environment degradation log (this continuation ran under it)

- Provider model streams stalled repeatedly (3 implementer agents + 2 reviewers
  died mid-flight with 600-900s no-event timeouts) — mitigation: small-ticket
  dispatches, salvage-and-finish in the orchestrator for landed-but-unreported
  work, main-session depth-equivalent reviews (documented per PR).
- Local git transport to github died for ~1h (proxy down + direct blocked):
  #591's fix could not be pushed — re-landed through the GitHub REST API
  (branch created from main tip + 3 files via contents API) as #602, closing
  the stale PR with an explanatory comment.
- Multi-agent full-suite runs starved each other (100-minute suites, random
  timeouts): degraded-mode discipline = targeted vitest + gates locally,
  CI as the full-suite authority; baseline-anchored targeted runs before/after.
- Merge-ring starvation when two rings race: serialize all merges in one loop.

## Skips and residuals

- #538's "~211" R2 count recounted to 197 actionable (waves removed
  113+50+34); the delta is deliberate keeps documented in the wave PRs.
- #536-adjacent notes recorded on the issue before closure: the 5th failed-job
  literal (reviewer-executor, adds `model`), inline envelope maps in five more
  route files (~80 lines, combinators ready), isDescendant's fs-support
  neighbor `errorCode` duplicate, stream_json_unwrapper sibling functions,
  dashscope_protocol.ts at exactly 300/300 (zero headroom), frontend
  useStudioJobs (243) / useStudioPageModel facade (291) as future split
  candidates if the hooks-family work ever resumes.
- #454 left untouched (pre-campaign, unrelated scope — surfaced to Owner).
