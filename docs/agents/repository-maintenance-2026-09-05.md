# Repository maintenance — 2026-09-05

## Integration authority and fixed points

The Owner explicitly authorized merging PR #456 after a final review and
cleaning redundant branches. This supersedes the earlier candidate-only merge
boundary. Human acceptance remains **not run**; merge authorization does not
claim human acceptance, a release, or completed OpenSpec archive gates.

- Previously CI-verified candidate: `b061e4dff6af650ca1e91701a4f1654930afc76d`.
- Final Lore repair: `688acfe70cc52b2aa811d0d4e4425292190983d9`.
- Contributor runtime correction: `28fbf8b3`.
- Issue intake label correction: `05a97e17`.
- Development dependency repair: `12a72dd3c9e23a27280349f5541db1ef5ab50e83`.

The [PR evidence record](https://github.com/Jackela/Novel-Engine/pull/456)
records the final head SHA, required checks, merge decision, and resulting
main commit. Later commits require fresh affected checks; the older successful
CI run is historical evidence for the new candidate.

## Final-review finding

The shell task 3.4 review found a P2: after saving a Lore status at the same
Revision, the page still read `savedStatus` from its unchanged full Document.
The shell correctly contained the new status, but the form compared against
the old value and could not directly change back.

The regression uses the real `useStudioPageModel` and `StudioInspectorPanels`
with only API boundaries mocked. On `b061e4df`, it failed with expected
`stable`, received `draft`. The repair reads the matching active shell summary
while keeping the existing body-loaded visibility condition. It neither
replaces the accepted body nor starts another Document request.

Replay: `pnpm --dir frontend test:unit src/features/studio/hooks/useStudioPageModel.lore-status.test.tsx`.
The combined Lore/page/identity suite passed 22 tests before the repair commit;
type, lint, and formatting checks also passed. Independent Standards and Spec
reviews of `b061e4df...688acfe7` found no remaining issue in this bounded fix.
Final candidate full-suite and CI outcomes belong to the PR record.

Shell task 3.4 stays open: this fixes the confirmed Lore display defect, not
the full beat/field-intent ordering matrix. Other unproven OpenSpec scenarios
and the [human acceptance packet](refactor-human-acceptance-2026-09-05.md)
remain open rather than being archived by inference.

## Repository controls and branch hygiene

- The main branch retains its strict required-check and synchronization policy.
- Private vulnerability reporting is enabled, matching `.github/SECURITY.md`.
- Ruleset `22314159` actively restricts updates and deletion of only
  `refs/tags/python-final`, with no bypass actors. Read-back confirmed the tag
  object remains `42dd23f6eed0d8d0300319d97eda797554c0fe98`; no deletion test ran.
- The contribution guide now matches Node 24 CI. Issue templates use the
  existing `needs-triage` label from the canonical label map.
- 53 local branches were verified against merged PR heads/main ancestry and
  removed. Their inventory and a verified recovery bundle are retained locally
  under `.git/branch-backups/2026-09-05-*`.
- Open Cloud Agent PR #454 and its remote branch are retained. The separate
  historical worktree is retained, including its untracked local harness state.

## Dependency audit boundary

The previous fast-uri repair removed the production advisories. The full
development-tool audit still exposed two high Browserslist advisories.
Browserslist 4.28.7 and its four required browser-data package versions are now
locked with registry-verified integrity values. No manifest or dependency
constraint changed; unrelated resolver churn was excluded.

Frozen installation passed. `pnpm audit --audit-level high` now exits 0 while
reporting one remaining moderate transitive esbuild advisory in migration
tooling; `pnpm audit --prod --audit-level high` reports no known vulnerabilities.
The remaining advisory needs its own compatibility assessment and is not
dismissed or represented as a vulnerability-free full dependency tree.

Local supporting logs are in `/tmp/novel-engine-merge-closeout-20260905/`.
They supplement the portable GitHub workflow evidence and do not replace it.
