# Historical CodeQL alert review — 2026-10-19

This review fixes its source baseline at `d3ccb10645899f4988ff0f781ffe1ccd9c6e7caa`,
with main CodeQL analysis `1977580090` (CodeQL 2.27.2, 87 rules, 14 open results).
It records **one confirmed authentication rate-limit bypass** and **13 false
positives for the reported remote-input/XSS conditions**. GitHub alert state is
the authority for later triage; this document is the fixed-baseline assessment,
not a claim that a scan inferred these dispositions or that all security risks
were eliminated.

## Confirmed finding: 1972

`auth_routes.ts` already uses an early `onRequest` limiter. Its raw-path test,
however, differs from the router's accepted route identity. After the default
five requests exhaust `/api/setup` or `/api/session/login`, an equivalent
percent-encoded spelling still reaches the handler without consuming a bucket.
The complete `buildApp` reproduced unauthenticated repeated password checks and,
with otherwise valid credentials/token, successful Owner/session creation after
the canonical bucket was exhausted. Setup-token, Origin, password and CSRF
boundaries were not bypassed; the defect is rate admission.

The minimal repair uses the route actually matched by Fastify to select the
existing per-client/method bucket. It keeps the same default limit, trusted
proxy identity rules, OPTIONS exemption, early admission, 429 envelope and
Retry-After. No middleware, dependency, configuration or new route is added.

`server/tests/api/auth_rate_limit_encoded_paths.test.ts` exercises the complete
application over synthetic SQLite. Three regressions first failed with
201/200/503 instead of 429, then passed after the patch. They mix canonical,
encoded and query-bearing spellings, verify no Owner/session side effects,
retain peer/method isolation, and cover database-free early admission. The
limiter's monotonic clock is frozen so a slow runner cannot replenish the burst; owned temporary
databases are removed. Related authentication suites preserve the existing
validation, setup, CSRF, session, identity and bucket contracts.

## Alert-by-alert assessment

All locations below refer to the fixed baseline. P means the project deletion
path boundary, E the export publication boundary, and L the legacy HTTP preview
boundary described below. Each row was matched to its SARIF source and sink.

| Alert | Rule and location | Assessment and evidence |
| --- | --- | --- |
| 1959 | `js/bad-tag-filter`, `frontend/src/app/i18n/language.prepaint.test.ts:21` | False positive for XSS: a Vitest-only extractor reads a fixed repository HTML fixture. It is not a sanitizer and has no user-input source; the 5 existing pre-paint language tests pass. No production or test rewrite is justified. |
| 1960 | `js/path-injection`, `export_artifact_files.ts:116`, lstat | E validates identifiers and confines the resolved candidate before this metadata check; false positive for remote path injection. |
| 1961 | `js/path-injection`, `export_artifact_files.ts:120`, mkdir | E permits creation only after confined candidate validation and ENOENT; symlink/type checks run again afterward. False positive for remote path injection. |
| 1962 | `js/path-injection`, `export_artifact_files.ts:124`, lstat | E rechecks the newly created direct child and rejects links/non-directories before realpath. False positive for remote path injection. |
| 1963 | `js/path-injection`, `export_artifact_files.ts:129`, realpath | E's canonical-path validation is itself reported as a sink; identifiers and lexical confinement already apply. False positive for remote path injection. |
| 1964 | `js/path-injection`, `legacy_workspace_fs_guard.ts:34`, realpath | L validates the JSON source as one direct child before any input-dependent filesystem access; false positive for the recorded HTTP flow. |
| 1965 | `js/path-injection`, `legacy_workspace_fs_guard.ts:217`, lstat | L rejects separators/absolute/dot paths first; this no-follow metadata check participates in directory capture. False positive for the recorded HTTP flow. |
| 1966 | `js/path-injection`, `project_artifact_files.ts:135`, realpath | P's identifier/lexical guard precedes directory metadata and canonical confinement. False positive for remote path injection. |
| 1967 | `js/path-injection`, `project_artifact_files.ts:162`, lstat | P confines both project and private quarantine paths; lstat does not follow a leaf link. False positive for remote path injection. |
| 1968 | `js/path-injection`, `project_artifact_files.ts:171`, rename source | P revalidates root/leaf identity before moving the checked leaf; a leaf link is moved as a link. False positive for remote path injection. |
| 1969 | `js/path-injection`, `project_artifact_files.ts:171`, rename destination | P derives a single safe-ID/random-UUID quarantine child and confines it. False positive for remote path injection. |
| 1970 | `js/path-injection`, `project_artifact_files.ts:181`, unlink | P checks the acquired quarantine identity/kind, then unlinks the link itself. External targets remain untouched in existing tests. False positive for remote path injection. |
| 1971 | `js/path-injection`, `project_artifact_files.ts:191`, recursive rm | P permits recursion only after root/leaf/quarantine identity and real-directory checks. False positive for the reported remote-input path. |
| 1972 | `js/missing-rate-limiting`, `auth_routes.ts:171` | Genuine raw-path/matched-route admission mismatch as described above; repaired and tested. The query may still fail to recognize the custom limiter, so a successful workflow is not by itself proof that GitHub closed this alert. |

## Existing filesystem boundaries retained

**P — project removal.** The SARIF source is the project ID at
`DELETE /api/projects/:projectId`. Owner authentication/CSRF and principal-scoped
project lookup run before deletion ownership. Before filesystem access,
`FilesystemProjectArtifactCleaner` validates `^[A-Za-z0-9_-]+$`, confines resolved
paths, rejects an export-root link, and checks real data/export roots. Cleanup
revalidates root/leaf device/inode/kind, quarantines the leaf under a private
name, then validates again before unlink/rm. The database cascade is the
success boundary; cleanup follows ADR-0007 and does not turn a committed delete
into a fabricated failure.

**E — exports.** The SARIF source is the project ID at
`POST /api/projects/:projectId/exports`. Authentication/CSRF and the scoped
source lookup precede publication. `exportArtifactNames` validates project and
artifact IDs plus the format allow list before filesystem access. Each child
uses resolve + `isDescendant`, lstat/type checks and canonical realpath
confinement; links are rejected. Downloads additionally require the canonical
stored relative path, O_NOFOLLOW and regular-file/size/checksum validation.
`isDescendant` uses path.relative, rejecting empty, parent, parent-prefix and
absolute results, rather than an unsafe string-prefix comparison.

**L — legacy preview.** The SARIF source is JSON `source` at authenticated,
CSRF-protected `POST /api/imports/preview`. `assertConfinedSourceName` rejects
blank/dot/dotdot, both separator kinds, NUL and host/Win32 absolute paths before
joining. The adapter captures canonical direct-child directories, rejects
links, checks exact parent equality and device/inode identity, and opens accepted
regular files with O_NOFOLLOW and bounded descriptor reads. JSON percent signs
are literal filename characters, not a later-decoded path. The separate local
CLI `read(source)` intentionally accepts an explicit absolute or relative
workspace; it is not the HTTP entry point and that supported behavior is retained.

Authentication is not treated as a replacement for path confinement. These
findings do not justify removing, relocating or weakening any guard. No blanket
suppression, scan exclusion or security-rule change is introduced.

## Reproducible validation surfaces

- `pnpm --dir server test tests/api/auth_rate_limit_encoded_paths.test.ts tests/api/auth_rate_limit.test.ts tests/api/auth_setup.test.ts tests/api/auth_csrf.test.ts tests/api/auth_session.test.ts tests/infrastructure/token_bucket.test.ts tests/infrastructure/client_identity.test.ts`
- `pnpm --dir server test tests/contexts/project_artifact_files.test.ts tests/contexts/export_artifact_files.test.ts` — fixed-baseline 32 tests passed.
- `pnpm --dir server test tests/contexts/legacy_workspace_reader.test.ts tests/contexts/legacy_workspace_reader_identity.test.ts tests/api/studio_imports_confinement.test.ts` — fixed-baseline 24 tests passed.
- `pnpm --dir frontend test:unit src/app/i18n/language.prepaint.test.ts` — fixed-baseline 5 tests passed.

The bounded review also retained replayable synthetic probes: 10 artifact-path
cases (direct adapters, real HTTP/SQLite, malicious IDs, authorization and normal
export/delete) and 8 legacy-reader cases (separator/absolute/link rejection,
identity replacement, literal percent/Unicode names and local CLI compatibility).
Original SARIF, exact commands, logs, environment, probe code and candidate-level
CI evidence are retained in this task's change-evidence record. Baseline outcomes
are historical after a later commit and must keep their original SHA.

## Limits

ADR-0007 and the archived bounded-import design state Node's lack of portable
openat/directory-fd operations and the single-process local-storage boundary.
The assessment does not promise an atomic snapshot against a privileged local
process continuously swapping every ancestor. Such a new storage threat model
requires an explicit architecture decision, not a remote-input alert rewrite.
Native Windows filesystem behavior was not executed; existing cross-platform
input checks and macOS synthetic tests are distinguished from a Windows run.
Real-provider calls are unrelated and were not performed. No real user database,
backup or environment file was used.

Rule references: [path injection](https://codeql.github.com/codeql-query-help/javascript/js-path-injection/),
[missing rate limiting](https://codeql.github.com/codeql-query-help/javascript/js-missing-rate-limiting/),
[HTML filtering regexp](https://codeql.github.com/codeql-query-help/javascript/js-bad-tag-filter/).
