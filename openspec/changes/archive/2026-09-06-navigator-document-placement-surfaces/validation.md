# Validation evidence

Delivered via [PR #489](https://github.com/Jackela/Novel-Engine/pull/489) (squash-merged
`23444c69`, 2026-09-06). Full record: PR body and
`docs/agents/orchestration-campaign-2026-09-06.md` (Wave D).

- Product semantics derived from the existing server contracts (zero server
  changes): deletion is refused only by snapshot references (409
  `SNAPSHOT_CONFLICT`); volume placement applies the #469 causal contract
  (captured project/document/revision + per-document intent epoch; only
  `volume_id`/`position`/`updated_at` patched; late responses ignored).
- UI: inline confirmation strip for delete (named document + draft-loss
  warning, Escape cancel, deliberate focus movement, focus to surviving
  neighbor on success); native select listing only other volumes; both
  commands wired to `useCommandFocusRestoration` and the shared
  mutation-busy group; inline error envelopes (network / 422 capacity /
  409 snapshot conflict).
- Tests: 26 unit tests (red→green where behavior-defining) + 4 new browser
  workflows (`studio_row_commands.spec.ts`); `test:e2e:ts` 23 passed on
  the candidate; frontend unit 101 files / 554 tests; react-doctor zero
  diagnostics; strict OpenSpec 24/24.
- Required CI green on the rebased PR head (validate/container/Analyze).
- Delegated acceptance: delete/placement surfaces exercised in the
  2026-09-06 packet run (visible, keyboard-reachable, isolated failures).
