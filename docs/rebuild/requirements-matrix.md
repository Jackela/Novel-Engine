# Requirement → 切片映射

> 阶段 0 产出 · 2026-10-24
> 来源：`openspec/specs/novel-engine/spec.md`，共 114 条
> 说明：`web` 指前端行为契约（验收在前端），`platform` 指跨切片的平台约束。

## 归属统计

| 归属 | 条数 |
|---|---|
| generation | 21 |
| web | 17 |
| platform | 15 |
| manuscript | 13 |
| journal | 9 |
| library | 9 |
| delivery | 8 |
| identity | 8 |
| review | 7 |
| lore | 4 |
| ? | 3 |

## 逐条映射

| # | Requirement | 归属 | 处置 |
|---|---|---|---|
| 1 | One product and version authority | platform | 保留 |
| 2 | Unified error envelope | platform | 保留 |
| 3 | Session cookie contract | identity | 保留 |
| 4 | CSRF double-submit protection | identity | 保留 |
| 5 | Session and provider surface | platform | 保留 |
| 6 | Health and version surface | platform | 保留 |
| 7 | Request validation constraints | platform | 保留 |
| 8 | SQLite authoring authority and immutable revisions | manuscript | 保留 |
| 9 | Save request semantics | manuscript | 保留 |
| 10 | Full-text search over current content | manuscript | 保留 |
| 11 | Document identity and revision uniqueness | manuscript | 保留 |
| 12 | Stable list ordering | manuscript | 保留 |
| 13 | Durable single-file operation | platform | 保留 |
| 14 | Restart recovery without invented leases | platform | 保留 |
| 15 | Startup schema migration | platform | 保留 |
| 16 | Explicit AI proposals | generation | 保留 |
| 17 | Server-mapped provider steps | generation | 保留 |
| 18 | Prose proposal content | generation | 保留 |
| 19 | Untrusted manuscript boundary | platform | 保留 |
| 20 | Proposal output sanitization | generation | 保留 |
| 21 | Explicit provider configuration failure | generation | 保留 |
| 22 | Server-side model resolution | generation | 保留 |
| 23 | Provider transient failure handling | generation | 保留 |
| 24 | Untrusted Provider failure diagnostics boundary | generation | 保留 |
| 25 | Per-request provider lifecycle | generation | 保留 |
| 26 | Snapshot-bound deterministic review | review | 保留 |
| 27 | Snapshot-bound export with reuse | delivery | 保留 |
| 28 | Export format contracts | delivery | 保留 |
| 29 | Project-scoped export artifacts | delivery | 保留 |
| 30 | Synchronous job execution model | journal | 保留 |
| 31 | Job retry chain | journal | 保留 |
| 32 | Read-only idempotent legacy import | manuscript | 保留 |
| 33 | Usage accounting for AI requests | journal | 保留 |
| 34 | Constant-time owner authentication | identity | 保留 |
| 35 | Owner setup policy and single-owner invariant | identity | 保留 |
| 36 | Lazy session expiry | identity | 保留 |
| 37 | Logout terminates the session | identity | 保留 |
| 38 | Setup same-origin validation | identity | 保留 |
| 39 | First-boot setup token gate | identity | 保留 |
| 40 | Authentication endpoint rate limiting | identity | 保留 |
| 41 | Production configuration guards | platform | 保留 |
| 42 | CORS origin contract | platform | 保留 |
| 43 | Environment configuration surface | platform | 保留 |
| 44 | CLI operational surface | platform | 保留 |
| 45 | Entry flow session probe | identity | 保留 |
| 46 | In-memory document drafts | manuscript | 保留 |
| 47 | Terminal-state job list without polling | journal | 保留 |
| 48 | Frontend API client timeout | web | 保留 |
| 49 | Section-filtered document views | web | 保留 |
| 50 | Generated document naming | manuscript | 保留 |
| 51 | Client-derived export download | delivery | 保留 |
| 52 | Complete single-author Studio | web | 保留 |
| 53 | Route-driven project surfaces | web | 保留 |
| 54 | Editor-first responsive and touch layout | web | 保留 |
| 55 | APG-compliant Inspector tabs | web | 保留 |
| 56 | Explicit asynchronous operation state | web | 保留 |
| 57 | Recoverable document save conflicts | manuscript | 保留 |
| 58 | Owner data isolation | platform | 保留 |
| 59 | Volume hierarchy | library | 保留 |
| 60 | Chapter beat association | library | 保留 |
| 61 | Resident context injection | generation | 保留 |
| 62 | Keyword-triggered lore entries | lore | 保留 |
| 63 | Document-scoped Lore lifecycle editing | lore | 保留 |
| 64 | LLM editorial review | review | 保留 |
| 65 | Project usage surface | journal | 保留 |
| 66 | Whole-book generation loop | generation | 保留 |
| 67 | Streaming proposal generation | generation | 保留 |
| 68 | Recoverable project loading | web | 保留 |
| 69 | Recoverable project-library loading | web | 保留 |
| 70 | Bounded provider response lifecycle | generation | 保留 |
| 71 | Bounded export source and rendering | delivery | 保留 |
| 72 | Export capacity failure protocol | delivery | 保留 |
| 73 | Bounded export artifact proof and delivery | delivery | 保留 |
| 74 | Bounded inbound HTTP request receipt | platform | 保留 |
| 75 | App-local expensive-workflow capacity admission | generation | 保留 |
| 76 | Proposal stream downstream backpressure | generation | 保留 |
| 77 | Bounded project job-history traversal | journal | 保留 |
| 78 | Bounded generation prompt capacity | generation | 保留 |
| 79 | Bounded prior-story digests | generation | 保留 |
| 80 | Linear bounded Lore planning | lore | 保留 |
| 81 | Coherent proposal context capture | generation | 保留 |
| 82 | Proposal retry base-revision fidelity | generation | 保留 |
| 83 | Bounded document revision-history traversal | manuscript | 保留 |
| 84 | Exact immutable revision word counts | manuscript | 保留 |
| 85 | Bounded revision refresh and exact restore | manuscript | 保留 |
| 86 | Owner-scoped partial Project settings update | library | 保留 |
| 87 | Recoverable Project settings save | library | 保留 |
| 88 | Bounded project shell and explicit current Document | library | 保留 |
| 89 | Causally owned active Document loading | web | 保留 |
| 90 | Lazy and independent Review and Export hydration | web | 保留 |
| 91 | Project-scoped Studio resource lifecycle | web | 保留 |
| 92 | Authoring structure capacity | library | 保留 |
| 93 | Bounded export catalog traversal | delivery | 保留 |
| 94 | Bounded project catalog traversal | library | 保留 |
| 95 | Bounded review-history traversal | review | 保留 |
| 96 | Scoped review-detail read | review | 保留 |
| 97 | Bounded Studio review-history state | review | 保留 |
| 98 | Navigator document deletion | manuscript | 保留 |
| 99 | Navigator chapter volume placement | library | 保留 |
| 100 | Project-scoped complete Job detail | journal | 保留 |
| 101 | Generation reference-data authority | generation | 保留 |
| 102 | Theme selection and dual-theme rendering | web | 保留 |
| 103 | Local writing statistics | journal | 保留 |
| 104 | Opt-in diagnostics export | journal | 保留 |
| 105 | Guided lorebook initialization | lore | 保留 |
| 106 | Saved-source and completed Review feedback | web | 保留 |
| 107 | Recoverable generated-text copy feedback | web | 保留 |
| 108 | Volume deletion updates project recency | library | 保留 |
| 109 | Complete saved chapter input for editorial Review | review | 保留 |
| 110 | Bounded Review prompt capacity and retry replay | review | 保留 |
| 111 | Valid Chinese trial Proposal prose | generation | 保留 |
| 112 | Review findings identify captured chapters only | review | 保留 |
| 113 | Project search result navigation | web | 保留 |
| 114 | Committed Proposal refresh ordering | web | 保留 |

未归类：0 条。全部 114 条已归属。

| # | Requirement |
|---|---|
| 3 | Session cookie contract |
| 4 | CSRF double-submit protection |
| 109 | Complete saved chapter input for editorial Review |
