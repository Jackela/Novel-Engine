# Productization campaign — 2026-09-13

Campaign: v0.8.0 "distributable, demonstrable, verifiable" (产品化迭代战役).
Owner directive: the pasted orchestration prompt (2026-09-13), executed as three
iterations (foundation → distribution & release → validation & growth). The
orchestrator schedules, adjudicates, reviews, and accepts; implementer (flash)
subagents write all product code. HITL items are never executed or fabricated
by agents.

## Authorization scope (from the campaign prompt)

- Deployment-surface changes are in scope for this campaign: `compose.yaml`,
  `Dockerfile`, `.env.example`, ghcr publishing workflow, user-facing docs,
  seed/demo content. Normal repo rule ("require authorization") is satisfied by
  the campaign prompt itself; reuse within the campaign, do not widen.
- HITL-only (never agent-executed): real-user acquisition & interviews,
  willingness-to-pay validation, paid deployment of a hosted demo, pricing
  decisions, positioning / LICENSE / release authorization, the final click on
  any external publication (Release, landing). Agents prepare material only.
- Destructive-architecture tripwire: multi-user / collaboration rework requires
  stopping and an ADR draft for the Owner — outside this campaign.

## Baseline

- Fixed comparison SHA: `8e1283ff` (main, 2026-09-13).
- `git status` clean except `?? .zcode/` (harness state, untouched).
- Local baseline gates: see "Baseline gate log" below (filled when complete).

## Campaign evidence log

### Baseline gate log

| Surface | Command | Result |
|---|---|---|
| Server gates | `pnpm -C server gates` | PASS (2026-09-13, SHA 8e1283ff) |
| Frontend lint | `pnpm -C frontend lint` | PASS |
| Frontend format | `pnpm -C frontend format:check` | PASS |
| Frontend types | `pnpm -C frontend type-check` | PASS |
| Frontend unit | `pnpm -C frontend test:unit` | PASS |
| Frontend build | `pnpm -C frontend build` | PASS |
| Spec | `pnpm spec:validate` | PASS |

Full serial chain, background log: `call_2a5434c12b094aff860968a3-stdout.log`
(session-local); exit 0, `ALL BASELINE GATES GREEN` marker present.

### Iteration 1 — Wave A dispatch log (prompt v1, 2026-09-13)

All Wave A agents are read-only (write sets: none; experiments confined to
`/tmp` and isolated docker resources). Unified finding format:
`ID | P1/P2/P3 | evidence | fix direction | confidence | validation method`.

- **A1 cold-start journey audit** — persona: non-technical author with Docker
  Desktop only; reconstruct the documented journey, then live-measure TTFW
  (clone → stack up → setup wizard → first AI-generated chapter → EPUB export)
  in an isolated `/tmp` clone; count commands, time phases, log friction.
- **A2 competitor gap matrix** (research, online) — Sudowrite / NovelAI /
  Novelcrafter / ChatGPT workflows + light scan of SillyTavern, Obsidian+AI,
  Scrivener; unique assets vs real gaps; positioning-sentence check.
- **A3 distribution form-factor research** — compose/Dockerfile/CI current
  state, ghcr feasibility, one-command path, upgrade/healthcheck story;
  recommendation feeding C1/C7.
- **A4 end-user docs & content audit** — README/docs/LICENSE/i18n/demo
  content vs the user journey (obtain → install → write → export → backup →
  troubleshoot).
- **A5 polish-residual inventory** — verify recorded same-family residuals
  from the backend-excellence campaign against current code, plus new P1/P2.

Wave A results: appended below as each agent reports.

### A4 — end-user docs & content audit (reported 2026-09-13)

README is entirely developer-audience (First-Time Setup = pnpm build; Docker
section = 12 lines). No author-facing guide family exists anywhere; openwiki is
contributor/architecture-styled. MIT license (2024 Novel Engine). CHANGELOG
well-maintained to 0.7.0. UI is 100% hardcoded English, no i18n framework.
No screenshots post-0.3-era concept art. No demo/sample project; but
`LLM_PROVIDER=mock` (compose default) + deterministic story provider is a
de-facto undocumented trial mode, and `cli import` (story.yaml + chapter-*.md,
read-only idempotent) is a low-cost demo-seeding vehicle.

| ID | Priority | Summary |
|---|---|---|
| A4-1 | P1 | No author guide family (suggest `openwiki/guides/`); docs are dev/agent-facing |
| A4-2 | P1 | No provider key guide (console links, steps, DeepSeek absent from all public material) |
| A4-3 | P1 | Backup documented as one line; **no restore command, no restore docs** |
| A4-4 | P1 | No Docker/TS→TS upgrade guide (data-volume retention semantics undocumented) |
| A4-5 | P1 | No current UI screenshots/recording (only 0.3-era concept image) |
| A4-6 | P2 | Zero i18n; if target authors are Chinese (DashScope defaults hint so), English UI+docs is a mismatch — Owner call |
| A4-7 | P2 | No troubleshooting/FAQ for users |
| A4-8 | P2 | studio-workspace.md is contributor-styled ("Primary sources" footers) |
| A4-9 | P3 | Demo content: seed a sample legacy workspace + import = cheap demo; document mock as trial mode |
| A4-10 | P3 | LICENSE fact sheet: MIT, compatible with public self-hosted distribution; final call = Owner |
| A4-11 | P3 | CHANGELOG usable directly as release-notes base |
| A4-12 | P3 | Bug template demands Node version/commit — too dev-heavy for authors |

Landing assets: none (no site/, no Pages workflow); repo-static suggestions:
guides under `openwiki/guides/`, screenshots under `docs/design/` (precedent),
README gains a "for writers" section. llms.txt link-drift gate will validate
any new registered links.



### A3 — distribution form-factor research (reported 2026-09-13)

Current state: `compose.yaml` uses `build: .` (no `image:`), forced
`APP_ENVIRONMENT=production`, required `SECURITY_SECRET_KEY` (compose `:?`
error), placeholder CORS, named volume `novel-engine-data`, healthcheck to
`/health/ready`, **no restart policy**. Dockerfile is two-stage
node:24-bookworm-slim; **its python3/make/g++ toolchain is dead weight** —
better-sqlite3@13.0.3 ships N-API prebuilds inside the npm tarball
(linux-x64/arm64 among 8 targets; no install script; verified against local
node_modules + npm packument). No `.dockerignore` (`.git/`, `node_modules/`,
local `data/` enter the build context). CI has 3 workflows only; the
`container` job builds locally (amd64, no push); v0.7.0 tag+Release was
manual. Repo is **PUBLIC** with MIT. Migrations auto-apply on every serve
startup (dir lock → backup → drizzle migrate → reconcile → job recovery,
`startup.ts:51-66`) — image upgrade is just `pull && up -d`, currently
undocumented.

Recommendation (accepted into Wave B): **a+c combo** — C7 ghcr publish
pipeline (tag-triggered, `packages: write`, native amd64 + arm64 runners both
free for public repos, manifest merge via `imagetools create`), then C1
one-liner (`curl …/deploy/compose.yaml | docker compose -f - up -d`) with
in-image first-boot secret bootstrap persisted to the data volume; option d
(desktop packaging) out of scope.

| ID | Priority | Summary |
|---|---|---|
| A3-1 | P2 | Remove dead build toolchain from Dockerfile (smaller image, faster arm64 build) |
| A3-2 | P2 | compose lacks `restart: unless-stopped` and `image:` field |
| A3-3 | P1 | No image publish workflow exists at all → C7 |
| A3-4 | P2 | No `.dockerignore`; local data/ leaks into build context |
| A3-5 | P3 | Secret UX: first-boot generation persisted to volume, injected as process env (guards untouched) |
| A3-6 | P3 | CORS placeholder formally passes guard; same-origin login proven by CI container job — document, don't change |
| A3-7 | P3 | Add OCI labels + tag↔manifest version assertion in the publish workflow |
| A3-8 | P3 | ghcr first-package visibility may default private → publish runbook step to verify anonymous pull |
| A3-9 | P2 | Auto-migration upgrade path is excellent but undocumented → upgrade/backup docs |
| A3-10 | P3 | mock is production-legal and compose-default; document as trial mode + provider switch examples |

Docker compose cannot fetch a plain remote URL (git URL or stdin only);
PowerShell `curl` is an alias (use `curl.exe`). Full C1/C7 file lists,
acceptance drafts, and source URLs captured in the session record.



**Measurement degraded to doc-level + code-level reconstruction: this machine
has no container runtime at all** (no Docker/colima/orbstack/podman; `docker`
not in PATH, no /Applications/Docker.app, no docker.sock). Live TTFW walk and
UI browser pass could not run. Escalated to the Owner checkpoint: local live
verification (C13 re-walk, demo-mode validation) needs a container runtime
installed by the Owner; container behavior otherwise rides CI's container
persistence check.

TTFW baseline (doc-level estimate, code-evidenced): **~15–30 min wall clock,
2 terminal commands** (export secret + `docker compose up --build`), of which
10–20 min is first-build waiting; interactive time to first writing ~5 min.
Target (≤10 min / ≤3 commands) is dominated by the missing prebuilt image.

Findings (agent report, integrator spot-check pending):

| ID | Priority | Summary |
|---|---|---|
| A1-1 | P1 | README's first section is the pnpm developer path; the Docker section lacks code acquisition + access URL — persona cannot follow the first screen |
| A1-2 | P1 (inferred, medium conf.) | Production `secure:true` session cookies (compose forces `APP_ENVIRONMENT=production`) over `http://localhost:8000`: Chrome/Firefox exempt localhost, Safari (inferred) drops the cookie → owner created but never logged in |
| A1-3 | P2 | `SECURITY_SECRET_KEY` taught via session-scoped `export` + placeholder value; next-day restart fails; should be a `.env` file compose auto-reads, with generation one-liner |
| A1-4 | P2 | Port 8000 hardcoded; no documented conflict override |
| A1-5 | P2 | No prebuilt image → 10–20 min local build on first run (drives TTFW) |
| A1-6 | P3 | Compose default CORS `https://app.example.com` formally passes the production guard; same-origin architecture makes it inert |
| A1-7 | P3 | Docker section never says to open http://localhost:8000 |
| A1-8 | P3 | "AI proposal / accept" is unexplained jargon at first use; no placeholder/onboarding hint |
| A1-9 | P3 | No Docker upgrade runbook (existing "Upgrading" section only covers Python→TS) |

Also recorded: mock provider is production-legal (guards only check
SECRET_KEY/CORS/DB_URL), setup wizard creates the local owner on first visit,
EPUB export in Inspector — the core loop is persona-friendly at the code
level; the failures are framing, docs, cookie semantics, and build time.

### A2 — competitor gap matrix (research, reported 2026-09-13)

All four primary competitors (Sudowrite, NovelAI, Novelcrafter, ChatGPT
workflows) are cloud subscription/credits; none self-hosts. Local camp
(SillyTavern, Obsidian) holds "local + model freedom" but neither is an
out-of-the-box novel workbench. The candidate positioning sentence holds; a
stronger variant was proposed: "an AI novel studio that runs on the author's
own computer — the manuscript stays local, the model is your choice (cloud
API or local), no subscription, no per-word billing."

| ID | Priority | Summary |
|---|---|---|
| A2-01 | P1 | "novel workbench × self-hosted × model freedom" intersection is unoccupied — the v0.8.0 distribution window's core asset; put it on the first screen |
| A2-02 | P2 | Immutable revision/rollback packaged as "AI writing with a safety net" |
| A2-03 | P2 | Per-project token/cost usage vs credits black box = direct anti-subscription differentiator |
| A2-04 | P2 | whole-book loop is tellable; do NOT claim "first chapter generation" (Sudowrite owns that mindshare) |
| A2-05 | P1 | Competitors are all "sign up and try free"; NE's Docker friction is the #1 selection hurdle → one-command path, screenshots-based quickstart, "free, no subscription" first screen |
| A2-06 | P1 | Guided lorebook init ("paste draft → extract → resident context") is the biggest product-level onboarding gap (Sudowrite Story Bible / Novelcrafter Codex own this pattern) — candidate for post-0.8.0, not this campaign |
| A2-07 | P2 | Trust language must be "physical data ownership" (files on your machine, SQLite, one-click export-all), not generic "privacy" (NovelAI owns that word) |
| A2-08 | P2 | Remote/multi-device access is a structural self-hosting weakness; document Tailscale/reverse-proxy or explicitly don't promise |
| A2-09 | P2 | Ecosystem signals (sample project, templates, Discussions) matter for adoption |
| A2-11 | P3 | AI review is not unique — phrase as "configurable review bench with traceable suggestions" |

Top-5 borrow list (from the session record): Story Bible guided pipeline,
Codex auto-tracking/progressions, NovelAI trust page + bulk download, BYOK
cost transparency, Projects-style mental model for resident context. Directly
usable this campaign: document mock provider as trial mode; frame backup as
"export all your data". ~20 source URLs captured 2026-09-13 (Sudowrite /
NovelAI / Novelcrafter / OpenAI official pricing & docs pages).



### A5 — polish-residual verification (reported 2026-09-13)

All recorded residuals verified against current code; counts match campaign
docs within ±1 line. TODO/FIXME count in src: zero.

| ID | Priority | Summary |
|---|---|---|
| A5-1 | P1 | `dashscope_protocol.ts` at exactly 300/300 code lines (gate `check_file_sizes.mjs` MAX_CODE_LINES=300, LEGACY_LIMITS={} zero exemptions) — any AI-context change trips the gate; split first (extractors family → `dashscope_extractors.ts`, transport → `dashscope_transport.ts`) |
| A5-3 | P2 | Five route files carry ~61 inline envelope lines (beat/import/lore/project/review_routes); combinators `authedReadResponses`/`authedWriteResponses` already migrated in 7 sibling files — mechanical move, OpenAPI snapshot must stay byte-identical |
| A5-4 | P2 | 5th failed-job literal (reviewer-executor with `model` field) at `job_retry_executor.ts:194-200` not routed through the `failed_job_input.ts` assembler |
| A5-5 | P2 | `errorCode` defined three times (canonical exported in `export_artifact_fs_support.ts:132`; verbatim dup in `database_authority.ts:35`; semantic variant with `String()` coercion in `project_artifact_files.ts:223` — check test lock before merging semantics) |
| A5-2a | P3 | `useStudioPageModel` 279/300 (headroom 21) — watch, split opportunistically when touched |
| A5-2b | P3 | `useStudioJobs` 216/300 — no pressure |
| A5-6 | P3 | `stream_json_unwrap` 251/300 — observation only |
| A5-7 | P3 | "config triple declaration" phrasing not in campaign docs (memory drift); real finding: DB_URL literal consistent in 3 places (no drift, no gate), README env table missing 9 provider vars — fold into docs ticket |

### Wave B adjudication (2026-09-13, orchestrator)

Iteration-1 ticket set finalized. Decisions:

1. **A1-2 (Safari secure-cookie deadlock, inferred)** — no cookie-code change
   now. Rationale: medium-confidence inference; Chrome/Firefox fine; live
   verification blocked (no local container runtime); changing Secure-cookie
   semantics is a security-posture change. Mitigation: browser note in
   getting-started + troubleshooting entry (C3); live Safari verification
   queued into the iteration-3 cold-start re-walk (C13). If proven broken on
   current Safari, revisit as its own ticket.
2. **A2-06 (lorebook init wizard)** — product feature beyond this campaign's
   iteration-1 scope; parked as a post-0.8.0 candidate issue.
3. **Docs/UI language** — English for now (consistent with English UI);
   target-audience + i18n question added to the Owner checkpoint (H).
4. **C1 scope** = clone-path one-command launch: Dockerfile (drop dead
   toolchain per A3-1; first-boot secret bootstrap persisted to the data
   volume), `docker/entrypoint.sh`, compose (`restart: unless-stopped`,
   secret optional via bootstrap), `.dockerignore`, README Docker section
   rewrite. Remote-image one-liner (deploy/compose.yaml) stays with C7 in
   iteration 2.
5. **C6 scope** = `restore` CLI command (integrity-check input, auto-backup
   current DB, atomic replace) + data-lifecycle docs in C3; README table
   update deferred to C3 to keep README in one write set per batch.
6. **Batching** (file-disjoint write sets, ≤4 implementers, single serial
   merge ring): batch 1 = C1 (docker+README) ∥ C2 (frontend studio UX) ∥ C6
   (server CLI restore). Batch 2 = C3 (docs family) ∥ C4 (demo content) ∥
   C5-1 (dashscope split) ∥ C5-2 (routes→combinators). Batch 3 = C5-3
   (assembler) ∥ C5-4 (errorCode SSOT) ∥ campaign-evidence docs PR.
7. **Validation posture** — no local container runtime: container-surface
   evidence rides CI's `container` job (recorded as an explicit local skip
   per the change-evidence contract); everything else runs targeted vitest +
   package gates locally, CI is the full-suite authority.
8. Issue #454 (pre-campaign Cloud Agent PR) remains untouched, out of scope.



### Decision log

- 2026-09-13 baseline anchored, Wave A dispatched (A2 first — network-only,
  overlaps local gate run; A1/A3/A4 after gates green; A5 queued to respect
  the ≤4 concurrent agent cap).

### Prompt revision history

- v1 (2026-09-13): initial dispatch prompts as logged above.
- v2 (2026-09-13, from #615/#616 review rounds): implementers touching
  user-facing copy MUST grep `frontend/tests/e2e-ts/**` for the changed
  literals (specs locate by placeholder/label text) and run one local Playwright
  e2e pass in their own worktree when copy/locators change; implementers must
  always run `pnpm -C server gates` even for frontend-only changes (file-size
  gate covers frontend test files); Docker-surface changes must account for
  `pnpm-workspace.yaml` `allowBuilds` (binding.gyp + allowBuilds ⇒ node-gyp
  runs even without an install script).


## PR ledger

| PR | Concern | Validation | Merge SHA |
|---|---|---|---|
| #615 | C2/#606 first-run UX (trial-mode copy, provider labels, onboarding hint) | CI all green (validate + container e2e after aria-label locator fix); local: lint/type-check/test:unit 111 files 611 tests, server gates green, local Playwright e2e 30/30 | **e96007da** |
| #616 | C1/#605 docker one-command launch (secret bootstrap, lean image, restart, .dockerignore, README) | review fixes: allowBuilds `better-sqlite3: false` (pnpm 11 undecided-build hard-fail), `ports: !override` snippet, umask subshell, pre-existing GC flake in data_directory_lock.test.ts fixed; CI all green incl. container (toolchain-free image build); merge ring in flight | pending |
| #617 | C6/#613 restore CLI (integrity-check, auto-backup, atomic replace) | review fix: replaced-database error semantics on sidecar-cleanup failure + JSDoc contract bounds + stale -wal removal test; CI all green | **84313424** |
| #618 | C5-1/#609 dashscope_protocol split (extractors 140 + transport 166; empty shell deleted — scope change recorded on #609) | review verified line-conserving 333/333 mechanical move; fix round: JsonObject via provider_json (no dup export); CI green | **4d27e938** |
| #619 | C5-2/#610 five route files → response combinators (13 routes; GET/POST /api/projects kept inline — combinator would add 404) | review: zero findings, per-route equivalence table verified; OpenAPI snapshot byte-identical | **c592cab2** |
| #620 | C4/#608 demo workspace + seeding guide + screenshot script | review round: P1 loader fix (@playwright/test from frontend, path depth) with negative controls; P3 owner-guard reachable; demo import test hermetic | **22ea59ef** |
| #621 | C3/#607 author docs family (8 guides + README for-writers/env table/restore + llms.txt) | review round: 4 P2 accuracy fixes (provider filtering, Review tab, health port, secret troubleshooting) + 2 P3 wording | **7196212c** |
| #623 | C5-4/#612 errorCode SSOT (4 definitions → shared/infrastructure/error_code.ts; restore.ts 4th copy absorbed) | review: mergeable, zero P1/P2; behavior delta unreachable and pinned by regression test | **9e842f88** |
| #624 | C5-3/#611 reviewer failed-job literal → shared assembler (overloads; byte-level invariants) | review: mergeable, zero actionable findings (2 optional P3 hardening notes) | **ed36108c** |
| #625 | #622 compose provider env passthrough (18 vars, explicit `${VAR:-}` entries; env_file rejected) | review: mergeable — var set mechanically verified bidirectional, blank→unset semantics confirmed, #616 anchors untouched; 4 P3 follow-ups filed as #626 | **8304e4e3** |

### Appendix: competitor matrix (A2, condensed; sources accessed 2026-09-13)

| Product | Form | Pricing | Long-form affordances | Data/offline | Provider flexibility |
|---|---|---|---|---|---|
| Sudowrite | web | $10–44/mo annual (credits) | Story Bible, guided chapter generation | cloud | closed (no BYOK found) |
| NovelAI | web | free tier; $10/15/25/mo | Memory + Lorebook | cloud, E2E-encrypted stories | closed (in-house models) |
| Novelcrafter | web | 21-day trial; from ~$4/mo | Codex auto-tracking, scene beats | cloud, exportable | **BYOK** (OpenRouter etc.) |
| ChatGPT workflows | web/desktop | free; $8/20/100+/mo | Projects (chat+files+instructions); size limits | cloud | closed |
| SillyTavern | self-host | free (AGPL) | character cards, World Info; not a workbench | local | very flexible |
| Obsidian + AI plugins | desktop | free core | none native (plugins) | local files | BYOK via plugins |

Positioning verified: no occupant of "novel workbench × self-hosted × model
freedom". Stronger variant recorded: "an AI novel studio that runs on the
author's own computer — the manuscript stays local, the model is your choice,
no subscription, no per-word billing." Full source list (~20 URLs) in the
campaign session record.

Transport note (2026-09-13 evening): local git transport to GitHub died
(proxy 127.0.0.1:7897 down + direct HTTPS broken "HTTP2 framing layer"); gh
CLI stayed healthy. Escape route exercised: rebuild local commits on remote
branches via GitHub Git Data API (blobs → tree → commit → ref) with the
created tree SHA verified equal to the local commit tree (`d388ab19…`, C2;
`26d93b19…`, C1) — script `/tmp/ne-rest-push.sh`. Pushes must retry gh-style
until the proxy returns.

(to be filled during Wave C/D)

## Iteration 1 close-out (2026-09-14 — COMPLETE)

**Delivered: 10 PRs merged green** (each with independent review; fix rounds
where findings existed). Final iteration-1 main: `8304e4e3`.

| Concern | PR | Content |
|---|---|---|
| One-command launch | #616 | secret bootstrap, lean image, restart policy, .dockerignore, writer-first README |
| First-run UX | #615 | trial-mode copy, provider labels everywhere, proposal onboarding hint |
| Restore CLI | #617 | integrity-check → auto-backup → atomic replace, honest failure semantics |
| dashscope split | #618 | 300/300 cap cleared (extractors + transport siblings) |
| Route combinators | #619 | 13 routes migrated, OpenAPI byte-identical |
| Demo content | #620 | example workspace, seeding guide, screenshot script (loader verified) |
| Author docs | #621 | 8-page guide family, README env table + restore, llms.txt |
| errorCode SSOT | #623 | 4 definitions → 1 canonical in shared/infrastructure |
| failed-job assembler | #624 | 5th literal routed through shared factory, byte-identical |

**TTFW status (doc-level, honest accounting).** The journey is now: obtain
code (clone or ZIP) → `docker compose up -d` → open http://localhost:8000 →
create owner → generate (trial mode, no key). Terminal commands: **2**.
Manual-secret and README-drift blockers are gone; Safari caveat documented
(verification queued to the iteration-3 re-walk). The remaining TTFW
dominator is first-build time (~10–20 min, no prebuilt image) — that is
exactly iteration 2's C7/C1-remote deliverable (ghcr image + one-liner
compose). Live measurement still blocked: no container runtime on the dev
machine (Owner item).

**Residuals / follow-ups recorded (not scheduled):**
- #614 parked: guided lorebook init wizard (post-0.8.0 candidate)
- #626: guide drift ×2 (upgrading/troubleshooting still name the override
  file as the key home), passthrough regression guard (compose env keys ⊇
  provider_config read set), `.env.example` LLM_MODEL comment-out (forbidden
  zone — Owner action)
- A1-2 Safari secure-cookie live verification → iteration-3 cold-start re-walk
- Screenshots: `scripts/demo/capture-screenshots.mjs` ready but needs a running
  instance (Owner installs a container runtime)
- `server_config.ts` `isMissingFileError` — 5th ENOENT expression, mechanical
  follow-up (#623 review P3)
- CI container job could add a cheap `docker compose config -q` smoke (#616
  review P3-2)
- restore input could assert a minimal NE schema (#617 review P3)
- copying `.env.example` wholesale adopts its placeholder secret + localhost
  CORS (pre-existing substitution semantics, surfaced by #625) — candidate
  docs hardening
- `dashscope_protocol.test.ts` filename now covers two modules (#618 note)



## Iteration 2 (2026-09-14) — distribution & release

Owner checkpoint H answers (recorded 2026-09-14): H1 positioning = the A2
variant ("an AI novel studio that runs on the author's own computer — the
manuscript stays local, the model is your choice, no subscription, no
per-word billing"); H2 = v0.8.0 release authorized (Release draft shown to
Owner before publish); H3 = prepare deploy config, do not deploy; i18n =
bilingual EN/zh UI + docs in v0.8.0; H4 = stay PUBLIC + MIT.

| PR | Concern | Result |
|---|---|---|
| #631 | deploy/compose.yaml one-liner + host-deployment notes (#630) | merged 46f3837c |
| #632 | env-first guide wording + compose-passthrough guard gate (anchors full-set, covers root+deploy, 4 regression tests) (#626) | merged d52bee1b |
| #633 | ghcr multi-arch image pipeline (native runners, version assertion, provenance:false, narrowed perms) (#628) | merged 7aa0ec65 |
| #634 | i18n stage 1: zero-dependency typed dictionaries + core screens (#629) | merged a1e5ccdb |
| #638 | Chinese guide family (8 pages) + README.zh-CN (#636) | merged 816c9633 |
| #639 | i18n stage 2: all studio surfaces + pre-paint language (#635) | merged b2347674 |
| #641 | release PR: version four-piece 0.8.0 + CHANGELOG (86 PRs verified covered) (#640) | merged 1aaa513c |
| #642 | pipeline fix: imagetools source format (found by first rc run) | merged 520be9a8 |

## v0.8.0 release record (2026-09-14)

- rc validation: `workflow_dispatch image_tag=v0.8.0-rc.1` — first attempt
  failed in merge step (`printf '%s@sha256:%s'` dangling-arg malformed
  source; run 34803244517), root-caused to a one-line format bug, fixed in
  #642; second attempt succeeded — `0.8.0-rc.1` manifest lists
  linux/amd64 + linux/arm64 with no attestation noise (run 34804239780).
- tag `v0.8.0` (annotated) pushed at 520be9a8; tag-triggered pipeline
  succeeded (run 34804349594): `ghcr.io/jackela/novel-engine:0.8.0`
  multi-arch manifest verified via the workflow's imagetools inspect.
- C9 on the tag commit: server ✓ validate ✓ CodeQL Analyze ✓ image
  pipeline ✓; container persistence + fresh-install behavior carried by
  the ci container job (green on every merge); no local container runtime
  on the dev machine (recorded skip; live TTFW/Safari/screenshots wait on
  the Owner installing a runtime).
- Release DRAFT created against v0.8.0 (notes = changelog + one-liner
  quickstart + zh pointer); publish click is the Owner's.
- Known follow-ups at release time (Owner actions): flip the first ghcr
  package to public then verify anonymous `docker pull` (the README
  one-liner depends on it); zh docs quality sign-off; optional: disable
  CodeQL default setup (its orphan "configuration not found" check turned
  failure on 2026-09-14 and is excluded from the merge ring as noise);
  `.env.example` `LLM_MODEL` comment-out (absolute forbidden zone).

## Campaign totals (2026-09-13 → 2026-09-14)

- 20 campaign PRs merged green (#615-#625, #627, #631-#634, #638, #639,
  #641, #642) + tag v0.8.0 + draft Release; every PR carried independent
  review, and 8 of them carried review-driven fix rounds.
- TTFW: documented path is now 2 commands (obtain code + one compose
  command) with zero-config trial mode; with the GHCR image live the
  no-build one-liner is a single command. Live timing still pending a
  local container runtime (iteration-3 re-walk).
- Open items after the campaign: #614 (parked lorebook wizard), #637
  (theme first-paint e2e flake), #626 remainder (`.env.example`, Owner),
  iteration-3 HITL work (interviews, feedback channel, retention stats,
  cold-start re-walk).
