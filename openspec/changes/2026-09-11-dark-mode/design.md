# Design: dual-theme token architecture

## Decision overview

Ship dark mode as a second value set for the existing `:root` custom
properties in `frontend/src/styles/base.css`, selected by a `data-theme`
attribute on `<html>` plus a pure-CSS `prefers-color-scheme` fallback, with
selection state owned by one small theme module. No CSS framework, no
build-step token pipeline, no new dependency. ADR-0009's material rules are
preserved unchanged: glass on chrome and floating layers only, an opaque
editor surface, blur capped at 14px/24px, and the
reduced-transparency / no-`backdrop-filter` fallback chain — now in both
themes.

## Alternatives considered

- **Per-surface dark stylesheets** (feature CSS carries `.dark` overrides):
  rejected — it scatters theme knowledge across eight files, violates the
  "tokens live once in `base.css`" rule, and cannot keep every surface in
  sync.
- **Always-resolve-in-JS** (the inline script always sets `data-theme` to a
  concrete `light`/`dark`, CSS has a single `[data-theme="dark"]` block, a
  `matchMedia` listener re-resolves `system`): simplest CSS, but theme
  correctness then depends on script execution in every path, and the
  no-JS first paint loses OS following entirely. Rejected in favor of the
  dual entry below, which keeps `system` mode script-free.
- **CSS-in-JS or build-time theme generation**: rejected — no new
  dependencies (ADR-0009 constraint), and the plain-CSS token block is the
  auditable SSOT the glass campaign established.
- **Wait for `@google/design.md` themes schema support**: rejected — the
  alpha schema has no themes syntax and the campaign cannot block on an
  external schema; the representation below works with the current lint.

## Token layering: light stays in `:root`, dark gets two entries

Light values remain the `:root` block exactly as shipped (zero diff to the
existing cascade baseline). Dark values are declared once per entry in two
selector contexts:

```css
:root { /* existing light tokens, unchanged */ }

[data-theme="dark"] { /* dark token set */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* same dark token set */ }
}
```

Semantics: an explicit `data-theme="light"` lock suppresses the media entry
(`:not([data-theme="light"])`), so a light lock holds under a dark OS; a
`data-theme="dark"` lock forces dark under a light OS; no attribute means
the OS decides. The `system` path therefore requires no JavaScript at all —
CSS resolves it before first paint.

The two dark blocks are necessarily duplicated literals (CSS has no token
mixing). Drift between them is guarded by a frontend unit test that parses
`base.css`, extracts both blocks, and asserts equality after
normalization; the same test covers the duplicated dark fallback blocks in
the reduced-transparency and `@supports` overrides.

Non-color material tokens (`--glass-blur`, `--glass-blur-strong`) are
theme-invariant and stay in `:root` only.

## FOUC prevention

A blocking inline script in `index.html` `<head>` (before the module
script) applies a stored lock before the first frame:

```html
<script>
  try {
    var t = localStorage.getItem("novel_engine_theme");
    if (t === "light" || t === "dark") {
      document.documentElement.dataset.theme = t;
    }
  } catch (e) { /* storage unavailable: system path, CSS decides */ }
</script>
```

- Stored `system` (and absent/invalid/unreadable storage): the script does
  nothing; the media-query entry resolves the OS preference with zero JS.
- Stored `light`/`dark`: the attribute is set synchronously in `<head>`, so
  the first painted frame already carries the locked theme. No flash.
- The script is intentionally minimal and total: it cannot throw into the
  page (all storage access is wrapped), it reads one key, and it writes one
  attribute. If a strict CSP is ever introduced it must carry this script's
  hash — recorded as a consequence in ADR-0010.

`theme-color`: the existing single meta becomes two, letting the browser
sync the OS-following path natively:

```html
<meta name="theme-color" content="#d9eee9" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#122b28" media="(prefers-color-scheme: dark)" />
```

The theme module overrides the active meta's content when an explicit lock
contradicts the OS preference.

## `color-scheme`

`:root` declares `color-scheme: light`; both dark entries declare
`color-scheme: dark`. Native form controls, scrollbars, and
`Canvas`/`CanvasText` system colors then follow the active theme without
per-widget rules.

## Storage: key, values, fallback

- Key: `novel_engine_theme` — follows the product's existing
  `novel_engine_` storage-naming family (`novel_engine_session`,
  `novel_engine_csrf`). This is the first `localStorage` key in the
  frontend; the family precedent comes from cookies.
- Values: exactly `system` | `light` | `dark`. `system` is written
  explicitly when the owner returns to the default, so the control's state
  is always reconstructible.
- Read path (module and inline script): any absence, invalid value, or
  thrown access error (privacy modes, blocked storage) degrades silently to
  `system` behavior — never to a console error or broken render. Writes
  that throw are swallowed by the same contract; the selection just does
  not persist for the session.
- No cookie, no server-side preference, no cross-device sync.

## Theme selection UI

One three-state segmented control (`system` / `light` / `dark`) as a new
cross-feature primitive (`ui-theme-switch` styles in `base.css`, component
shipped once, mounted by each page shell: entry page, project library, and
the studio top bar). The control shows the stored state, labels `system`
with the resolved target (e.g. "System (dark)"), and writes the value on
activation. It honors the existing interactive-control contract: 44px
target, visible focus, `prefers-reduced-motion` respected.

## Glass material family in dark

Elevated dark, same anatomy as the light language:

- **Canvas hint tints** invert from pale washes to deep desaturated fields
  (`#122b28` teal / `#16232f` blue / `#1e1a2e` violet) so the gradient
  stays perceptibly multi-hue without lifting local luminance.
- **Radial color fields** switch from dark-glass-over-light (dark teal
  0.16 alpha) to bright-source-over-dark: `rgba(45, 212, 191, 0.09)` teal
  top-left, `rgba(139, 122, 235, 0.09)` violet bottom-right. Bright sources
  at low alpha keep the glow perceptible while the composited region stays
  far below text-contrast harm (worst composited region L ≈ 0.034).
- **Glass fills** keep the light theme's alpha tiers (0.62 / 0.80 / 0.45)
  with dark fills (`rgba(16,20,21,…)`, `rgba(22,27,28,…)`), so frost
  strength and the one-glass-layer-per-region rules are untouched; dark
  fills make chrome read as *darker than* the glow regions, inverting the
  light theme's white-frost-over-color into the elevated-dark equivalent.
- **`glass-border`** flips from white 0.65 to white 0.14 (hairline
  highlight on dark glass); **`glass-shadow`** deepens to
  `0 8px 32px rgba(0, 0, 0, 0.45)`. Both are non-text decoration.
- **Fallback chain dual-themed**: the
  `@media (prefers-reduced-transparency: reduce)` block and the
  `@supports not (backdrop-filter…)` block each gain a dark twin (dark
  near-opaque fills, blur 0, solid borders, no shadow) selected with the
  same `[data-theme="dark"]` / media dual entry nested inside the existing
  conditional blocks. Browsers without `backdrop-filter` keep solid
  surfaces in both themes.

## Dark token draft table

Complete dark value set (all 30 DESIGN.md color tokens — note: the brief
said "19"; the current DESIGN.md frontmatter declares 30 color tokens, and
the table covers all of them). Derivation rules: (1) neutral ramp lightens
with elevation — canvas < surface-muted < surface < panel < hover; (2) text
tokens invert to a cool light ramp; (3) tinted families shift to deep
desaturated fields; (4) the teal accent brightens and `on-accent` flips to
dark teal ink; (5) hue identities are preserved so the dark theme reads as
the same product.

Contrast estimates use the glass campaign's premultiplied approximation
(text tokens vs the worst-case backdrop: brightest gradient region,
glass-composited at the token's tier; floor pair highlighted). Estimates
are locked as executable fact by the T1 contrast unit test, which parses
`base.css` and asserts WCAG ratios; values below may shift by ±0.2 when
the test measures exactly.

| Token | Light | Dark draft | Contrast (worst-case pair) | Purpose |
|---|---|---|---|---|
| `ink` | `#18181b` | `#e6eaeb` | 12.2:1 vs faint-glass composite; 14.6:1 on opaque editor | Primary text |
| `ink-soft` | `#27272a` | `#c7ced0` | 9.3:1 | Strong secondary text, control labels |
| `surface` | `#ffffff` | `#15191a` | bg for `ink` 14.6:1 | Opaque editor page, inputs |
| `canvas` | `#f7f8f8` | `#101415` | base under gradient | Gradient base |
| `canvas-hint-teal` | `#d9eee9` | `#122b28` | bg (L≈0.020) | Gradient stop 0/100% |
| `canvas-hint-blue` | `#d7e3f7` | `#16232f` | bg (L≈0.015) | Gradient stop 38% |
| `canvas-hint-violet` | `#e8def5` | `#1e1a2e` | bg (L≈0.012) | Gradient stop 68% |
| `surface-glass` | `rgba(255,255,255,0.62)` | `rgba(16,20,21,0.62)` | pane fill | Pane chrome frost |
| `surface-glass-strong` | `rgba(255,255,255,0.80)` | `rgba(22,27,28,0.80)` | card fill | Floating cards, controls |
| `surface-glass-faint` | `rgba(255,255,255,0.45)` | `rgba(12,16,17,0.45)` | ambient fill | Ambient chrome |
| `surface-muted` | `#fafbfb` | `#171c1d` | bg | Subdued fills |
| `surface-panel` | `#fcfcfc` | `#1a1f21` | bg | Panel/card composite base |
| `surface-hover` | `#f4f5f5` | `#252c2e` | `ink-soft` on hover 8.9:1 | Hover elevation |
| `line-strong` | `#bfc5c6` | `#475355` | non-text | Strong hairlines |
| `line` | `#dfe2e3` | `#2f383a` | non-text | Hairlines (relative subtlety mirrors light) |
| `glass-border` | `rgba(255,255,255,0.65)` | `rgba(255,255,255,0.14)` | non-text | Glass hairline highlight |
| `muted` | `#4b5556` | `#aeb9bb` | 7.4:1 | Secondary text (strongest tier) |
| `muted-soft` | `#626a6b` | `#a2adb0` | 6.4:1 | Tertiary text |
| `muted-faint` | `#697172` | `#97a3a5` | **5.7:1 — floor pair** (target ≥5.5) | Faint text, timestamps |
| `teal-soft` | `#dff3f1` | `#11312d` | `teal-strong` on it 7.5:1 | Soft selected/active wash |
| `teal-strong` | `#0f766e` | `#2dd4bf` | as text on glass 7.9:1 | Accent: actions, selection, focus |
| `teal-hover` | `#115e59` | `#5eead4` | hover lightens (dark convention) | Primary hover |
| `focus-ring` | `#ccfbf1` | `#113b36` | `ink` on it 10.2:1 | Focus halo, CM selection bg |
| `danger` | `#b91c1c` | `#f08c8c` | 6.2:1 on glass; 6.9:1 on `danger-soft` | Error text/icons |
| `danger-soft` | `#fff1f2` | `#381415` | bg | Error wash |
| `danger-line` | `#fecaca` | `#6f2c2e` | non-text | Error borders |
| `warn` | `#d8a62a` | `#e3b041` | 7.4:1 on glass | Warning text/icons |
| `warn-soft` | `#fdf6e3` | `#322712` | bg | Warning wash |
| `warn-ink` | `#6b5410` | `#eed9a3` | 10.5:1 on `warn-soft` | Warning text on wash |
| `on-accent` | `#ffffff` | `#0b2f2a` | 7.7:1 on `teal-strong` | Text on accent fill |

Theme-invariant: `--glass-blur: 14px`, `--glass-blur-strong: 24px`.
Dark `--canvas-gradient`:

```css
radial-gradient(1100px 700px at 8% -10%, rgba(45, 212, 191, 0.09), transparent 60%),
radial-gradient(900px 650px at 105% 112%, rgba(139, 122, 235, 0.09), transparent 62%),
linear-gradient(135deg,
  var(--canvas-hint-teal) 0%,
  var(--canvas-hint-blue) 38%,
  var(--canvas-hint-violet) 68%,
  var(--canvas-hint-teal) 100%);
```

`--glass-shadow` (dark): `0 8px 32px rgba(0, 0, 0, 0.45)`.

## CodeMirror and the writing surface

The glass campaign already tokenized the CM theme (`MarkdownEditor.tsx`
resolves `var(--surface)`, `var(--teal-strong)`, `var(--focus-ring)` via
light-DOM StyleModule), so the editor re-renders dark with no theme code.
T3 verifies a live theme switch re-renders CM correctly in the browser.
ADR-0009's editor exception is preserved: `--surface` is opaque in both
themes, no `backdrop-filter` on the editor, and the serif writing stack is
untouched.

## Raw-color discipline

The existing rule stands: raw colors belong only in `base.css`. Dark mode
makes the two recorded light-theme exceptions (glass campaign ledger)
product bugs rather than accepted debts, so the implementing tickets
tokenize them:

- `studio-nav.css` badge family (`#e2e8e8`, `#5a6465`, `#cfe4e2`,
  `#0f6862` incl. its AA exception comments) → named tokens with dark
  variants, dark AA re-verified.
- `library.css` `.library__project-row:hover` `#8dbab6` → named token with
  a dark variant.

No new raw color may appear outside `base.css`; the token drift-guard test
and repo hygiene gates stay the enforcement surface.

## DESIGN.md representation

The `@google/design.md` alpha schema has no themes syntax (ADR-0009
finding), and the frontmatter must stay lint-clean. Representation chosen:

- Frontmatter keeps the canonical single (light) value per token — the
  validated shape is unchanged, so `npx @google/design.md lint DESIGN.md`
  keeps passing with 0 errors.
- Dark values land as a `## Dark theme values` body appendix: a markdown
  table mirroring the draft table above (token → dark value → notes), plus
  the dual-entry selector contract and the selection/persistence rules.
- `npx @google/design.md diff` gates the update deliberately (additive body
  section, no token removals) like the OpenAPI snapshot; the implementing
  ticket runs lint + diff and records output.

Alternative rejected: dual values inside frontmatter (`token: "light |
dark"`) — unknown value syntax risks the lint and silently degrades the
machine-readable contract.
