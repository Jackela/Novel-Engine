# Roadmap

Owner-decided direction from the 2026-10-01 devil-advocate review
(`docs/audits/2026-10-01-devil-advocate-review-report.md`). Nothing here is a
dated promise; it records what the product optimizes for next and why.

## Release gate before 0.9.0

The review's top risk is that no user validation has ever happened. Before
0.9.0 ships, the owner runs the interviews and the cold-start measurement
prepared in [docs/research/interview-kit.md](research/interview-kit.md): ten
conversations with target authors plus one timed first-value run on a clean
machine, archived with conclusions (retention candidates ≥ 3). If the
candidates do not materialize, the writer-facing positioning narrows further
rather than widening (see DEC-02 in the audit backlog).

## 0.9.0 — Local generation first, diffs before accepting

The core loop is the product's load-bearing selling point and its least
ergonomic part: immutable revisions and export snapshots exist, but accepting
a whole chapter is still a blind signature. The next release focuses on:

- **Partial generation** — generate into a selection or a paragraph instead of
  a whole chapter, leaving the rest of the draft untouched.
- **Diff before accepting** — the revision preview and line diff delivered in
  this cycle (DR-011/DR-042) become the default path for every proposal: read
  the diff, then accept.
- **One-shot undo** — accepting offers a single explicit undo (DR-010) and the
  UI documents it.
- **Whole-book runs confirm per chapter** — already the shipped default
  (DR-007): only empty chapters generate automatically; chapters holding author
  text are replaced only after an explicit confirmation.

## Provider policy

Two providers (DashScope and OpenAI-compatible endpoints, plus the trial
`mock`) are supported and documented. The adapter layer stays as thin as it is
today and will not grow a plugin market for providers that do not exist:
DashScope's protocol has broken compatibility twice, and the abstraction earns
its keep only for the providers actually in use (DEC-06).
