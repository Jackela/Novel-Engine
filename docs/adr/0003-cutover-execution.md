# Cutover executed: TS-only tree, empty-DB one-way door, python-final archive

---
status: accepted
---

On 2026-08-25 the repository cut over to the TypeScript implementation
(ADR-0001/ADR-0002) as its only backend and released it as **v0.4.0**
(PR #301 `2f74b2c3`, spec consolidation PR #302 `2d644984`). The decision
record lives in #254's resolution; this ADR records the executed terms and
the operational postures they leave behind.

- **Empty-DB cutover, one-way for post-cutover writes.** No schema
  migration exists or will be written: the TS server's startup probe
  refuses a database carrying the Python `alembic_version` marker. Legacy
  data re-enters through the read-only, idempotent import CLI (#273).
  Reverting the cutover commit restores the Python stack, but data written
  after the cutover lives only in the new schema and does not survive the
  rollback. The v0.4.0 release notes and the README's upgrade section
  state this door explicitly.
- **`python-final` tag is the archive.** The last Python state is preserved
  by an annotated tag at `1597de37` (protected by a tag-protection rule);
  the tree keeps one backend — SSOT. History is the archive: 210 tracked
  files (src/, alembic/, Python tests/scripts, `pyproject.toml`,
  `uv.lock`, and the Python root configs) were removed in the cutover PR
  under a user-confirmed inventory, not silently.
- **Contract boundary at the switch.** The regenerated TS OpenAPI baseline
  replaced the frozen Python snapshot as the codegen authority; the diff
  between the two equals the adjudicated deviation set (#245 unified
  envelope, #246 cookie scheme + `/version` runtime field + dead-route
  losses, #296 terminal-job shapes) plus two adjudications recorded during
  the cutover review: the single-document GET route was removed to honor
  #246's ACCEPT-LOSS, and camelCase path-parameter naming was accepted as
  a documentation-level mechanism difference (URLs unchanged).
- **Release-version authority moved to `server/package.json`.** The SSOT
  gate flipped from `pyproject.toml` to the server package manifest; the
  frontend package remains forbidden from declaring a version.
- **Ops surface is pnpm/Node-only.** One node:24 image serves SPA + API
  (compose volume renamed to `novel-engine-data`; the old volume is not
  reused by design). The Node QA gates under `server/scripts/qa/` are the
  operative twins of the retired Python gates; CI requires
  `Analyze (javascript-typescript)`, `validate`, and `container`.

## Consequences

- Any future data-migration need between schemas is a new, explicit
  project — the default answer is "import via the legacy CLI", not
  schema translation.
- Security fixes for the Python era are source-only archaeology on the
  `python-final` tag; they do not ship.
- Reintroducing a second backend or a version field outside
  `server/package.json` violates the SSOT gate and this record.
