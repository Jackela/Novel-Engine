# Frosted-glass redesign — 2026-09-10

Full-campaign evidence for the glassmorphism visual overhaul executed per the
approved plan (light frosted, zero new dependencies, subagent implementation
batches, main-agent design/acceptance). Decision record: ADR-0009; design
SSOT: root `DESIGN.md` v2.

## Batch ledger

| Batch | Commit | Executor | Validation |
|---|---|---|---|
| Stage 0 DESIGN.md v2 + ADR-0009 | `dd516a2d` | main agent | design.md lint 0 errors; diff = 7 colors added, 2 components modified, no removals |
| T1 token foundation | `466e49b6` | general-purpose subagent | frontend suite green; browser: gradient + tokens + button material verified |
| T2 studio chrome glass | `3ba0c2fa` | general-purpose subagent | suite green; browser: 4 panes blur(14px), editor opaque, tabs no-blur |
| T4 entry + library glass | `63f146d4` | general-purpose subagent | suite green; browser: panel blur(24px)/r12/shadow |
| T3 CodeMirror theme → tokens | `51f1394b` | general-purpose subagent | suite green; react-doctor totalDiagnosticCount 0; 135 lines; independent code-reviewer pass: no findings (var() resolves via light-DOM StyleModule, values equal, no drift) |
| T5 near-miss tokenization | `a11fa2de` | general-purpose subagent + main | 59 mapped replacements + 4 new tokens (`--danger-line`, `--warn`, `--warn-soft`, `--warn-ink`); 2 mapping gaps (`#f4fbfa`, `#ced4d4`) fixed by main; design lint 0 errors |
| T6 hard gates + visual acceptance | (this commit) | main agent | below |

## T6 evidence

- **e2e smoke** (`pnpm --dir frontend test:e2e:smoke`, fresh dist both ends):
  3/3 passed — owner setup, editing + proposal accept flow, login error
  envelope, revision history. This is the runtime proof that the
  var()-based CodeMirror theme renders (covers the reviewer's noted gap).
- **Visual acceptance** (standalone stack `TS_E2E_PORT=4275`, real owner
  setup + project creation, Playwright): first-pass screenshot review found
  the glass effect too subtle (initial hint tints all ≥0.85 luminance —
  nothing to frost). Main-agent taste fix: deepened hint tints
  (#d9eee9/#d7e3f7/#e8def5) and layered two soft radial color fields
  (teal 0.16 top-left, violet 0.14 bottom-right) into `--canvas-gradient`;
  theme-color synced to #d9eee9; second-pass review confirmed perceptible
  frost, color atmosphere, opaque editor, clean rendering.
- **Contrast math** (premultiply approximation, worst case = darkest stop
  #d7e3f7, luminance ≈0.762): glass 0.62 → ink 17.0:1, muted 7.05:1,
  muted-soft 5.75:1; faint 0.45 → muted-soft 5.5:1. All ≥ AA 4.5.
- **Fallback chain**: Chromium in this environment cannot emulate
  `prefers-reduced-transparency` (emulateMedia accepted but matchMedia
  stayed false). Verified instead via CSSOM: both override blocks
  (`@media (prefers-reduced-transparency: reduce)` with 7 token
  declarations; `@supports not (backdrop-filter…)` with 5) parse intact,
  and all glass surfaces consume the tokens through `var()` — proven by
  computed-style probes. Prefixed `-webkit-backdrop-filter` lines carry
  literal blur values (Safari var() limitation), 9 application sites
  total, no nesting (children of glass panes use fills only).
- **Final sweep**: react-doctor 0 diagnostics on the only touched .tsx
  (T3; later batches were CSS/HTML only), server gates 6/6 clean
  (ssot 0.6.0, hygiene, file-size 691, migration-channel, llms-txt 21,
  OpenAPI 1/1), `pnpm spec:validate` 2/2, frontend lint/format/type-check
  clean, unit 567/567, build identity 0.6.0.

## Skips and residuals

- OpenSpec change deliberately not created: the 72 spec requirements are
  behavioral; grep found zero coverage of color/material/contrast/motion
  properties (exploration agent evidence, 2026-09-10).
- Dark mode out of scope (`@google/design.md` alpha has no themes syntax).
- Accepted one-off literals, documented: badge family in studio-nav.css
  (incl. the two `#0f6862` AA exceptions with in-file comments) and
  `.library__project-row:hover` `#8dbab6`.
- design.md lint warnings (24) are the known orphaned-tokens pattern for
  tokens not referenced by the five button/input components; errors 0.
- Commits are local on `main`; push/release not requested.
