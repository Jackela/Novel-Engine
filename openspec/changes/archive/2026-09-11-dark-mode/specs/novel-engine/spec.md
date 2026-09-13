## ADDED Requirements

### Requirement: Theme selection and dual-theme rendering
The Studio MUST offer a three-state theme selection — `system`, `light`,
and `dark` — and MUST default to `system`. In the `system` state the
rendered theme MUST follow the operating system's
`prefers-color-scheme`, including preference changes made while the app is
open. A manual `light` or `dark` selection MUST override the operating
system preference, MUST persist across sessions under the `localStorage`
key `novel_engine_theme` with exactly the values `system`, `light`, or
`dark`, and MUST apply before the first painted frame so no incorrectly
themed flash is visible. An absent, invalid, or unreadable stored value
MUST behave as `system` without surfacing an error. When the dark theme
renders, every painted surface — entry, project library, studio chrome,
manuscript editor, inspector, and usage panels — MUST use the dark token
set, and every text/background pair MUST hold a WCAG AA contrast ratio of
at least 4.5:1 against the worst-case backdrop for its surface tier. The
dark theme MUST preserve the material rules of ADR-0009: backdrop blur on
chrome and floating layers only, an opaque editor surface with no
`backdrop-filter`, and working `prefers-reduced-transparency` and
no-`backdrop-filter` fallbacks in both themes.

#### Scenario: System selection follows the OS preference
- **GIVEN** no manual theme selection is stored
- **WHEN** the operating system prefers dark (`prefers-color-scheme: dark`)
- **THEN** every Studio surface renders the dark theme
- **AND** an OS preference change while the app is open switches the rendering without a manual reload

#### Scenario: Manual selection locks and persists
- **GIVEN** the owner selects `dark` (or `light`) in the theme control
- **WHEN** the app is reloaded in a later session
- **THEN** the selected theme renders regardless of the OS preference
- **AND** the selection is stored under `novel_engine_theme` as one of `system`, `light`, or `dark`

#### Scenario: Explicit light overrides a dark OS preference
- **GIVEN** the OS prefers dark and the stored selection is `light`
- **WHEN** any page loads
- **THEN** every surface renders the light theme from the first painted frame
- **AND** no incorrectly themed flash appears before the tokens apply

#### Scenario: Dark contrast holds AA over glass
- **GIVEN** the dark theme is active
- **WHEN** any text renders on glass chrome over the brightest gradient region of its surface tier
- **THEN** the text/background contrast ratio is at least 4.5:1 under the premultiplied worst-case approximation
- **AND** the token-level ratios are enforced by the frontend contrast test

#### Scenario: Writing surface follows the dark theme
- **GIVEN** the dark theme is active
- **WHEN** a manuscript is opened in the editor
- **THEN** the CodeMirror editor, its syntax theme, and the surrounding studio chrome all render dark
- **AND** the editor surface remains opaque with no `backdrop-filter` applied
