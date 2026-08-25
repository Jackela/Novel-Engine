# Cutover consolidation

## What

Retires the `novel-studio` OpenSpec capability and consolidates the product
contract under `novel-engine` (#277, per the #254 cutover resolution):

- Carries the six pure-frontend Requirements from `novel-studio` into
  `novel-engine` verbatim (Complete single-author Studio, Route-driven
  project surfaces, Editor-first responsive and touch layout, APG-compliant
  Inspector tabs, Explicit asynchronous operation state, Recoverable
  document save conflicts). The other twelve `novel-studio` Requirements
  are superseded by the `novel-engine` Requirements delivered by the four
  archived rewrite slices; `Owner and temporary guest isolation` is replaced
  by the principal-scoping Requirement from surfaces-ops.
- Removes the Python tree (`src/`, `alembic/`, Python tests and scripts) in
  this PR; the pre-cutover state is preserved by the protected git tag
  `python-final`. One backend in the tree — SSOT; history is the archive.
- Switches `compose.yaml`/`Dockerfile` to the single TS image (SPA + API,
  `/health/ready` healthcheck path unchanged), rewrites README/Makefile/
  justfile for pnpm/Node operations, and retires the Python-bound CI jobs
  (pytest/mypy/ruff/bandit/import-linter, pip-audit, python-freeze guard,
  the Python CodeQL language).
- Regenerates the OpenAPI baseline from the TS server (v0.4.0) and pivots
  frontend codegen to it; the diff against the frozen Python snapshot was
  reviewed and equals the adjudicated deviation set (#246: cookieAuth
  cookie name, `/version` runtime field, the absent dead routes; #245:
  the unified envelope; the workflows-spec terminal-job shapes) plus the
  in-session adjudications recorded on #277: the single-document GET route
  was removed to honor #246's ACCEPT-LOSS, and camelCase path-parameter
  naming is accepted as a documentation-level mechanism difference (URLs
  are unchanged).
- Moves the release-version authority to `server/package.json` (`0.4.0`)
  and removes `pyproject.toml`.

## Why

The TS rewrite (#233, ADR-0002) is complete and green; the charter's
terminal step is the empty-DB cutover — a one-way door for data written
after it. Rollback = revert this PR; post-cutover writes do not survive
rollback. Legacy data re-enters through the read-only idempotent import
(#273); this is stated in the v0.4.0 release notes.

## Impact

- `novel-engine` gains six carried Requirements; `novel-studio` is removed
  from `openspec/specs/` when this change archives.
- No runtime behavior change beyond the reviewed OpenAPI deviations; the
  frontend drops its Python-compat parsing branches (dual CSRF cookie
  fallback, legacy `{detail}` error shape) — the unified envelope and
  `novel_engine_*` cookies are the only contract now.
