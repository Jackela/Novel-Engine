# Contributing to Novel Engine

Start with the [quickstart](openwiki/quickstart.md) for local setup and the
[documentation index](docs/README.md) for the relevant product or engineering
contract. Architecture rules and coding constraints live in [AGENTS.md](AGENTS.md);
use [CONTEXT.md](CONTEXT.md) for domain terms.

## Development environment

- Use Node.js 24 and the pnpm version pinned in [package.json](package.json).
- Install from the repository root with `pnpm install --frozen-lockfile`.
  [pnpm-workspace.yaml](pnpm-workspace.yaml) declares the workspace packages;
  commit the root `pnpm-lock.yaml` together with intentional dependency changes.
- Copy the documented environment templates for local configuration. Templates
  are tracked; local values, credentials, databases, and backups stay untracked.

## Git workflow

1. Inspect `git status --short` and the relevant diff before starting. Record a
   fixed baseline commit and preserve unrelated work. Use a short-lived branch
   for one coherent change; agent branches use the `codex/` prefix. Use a separate
   worktree when concurrent changes would overlap.
2. Check the relevant [product specification](openspec/specs/novel-engine/spec.md)
   and decision record before editing. Keep code, tests, and the documentation
   explaining their behavior in the same change. Follow
   [issue conventions](docs/agents/issue-tracker.md) when managing GitHub work.
3. Run the checks owned by the affected surface. Resolve commands from the
   [server](server/package.json) and [frontend](frontend/package.json) package
   scripts and [CI workflow](.github/workflows/ci.yml); use the
   [CI runbooks](docs/agents/ci-gates.md) to interpret failures. Record actual
   results and skips using [Change Evidence](docs/agents/change-evidence.md).
4. Stage explicit paths, inspect `git diff --cached`, and commit a focused change
   with a meaningful message. Include deliberately regenerated API types,
   OpenAPI baselines, and migration files when their source contracts change.
5. Open a PR with the [template](.github/pull_request_template.md). Resolve
   review findings and required checks on the final candidate before the
   maintainer squash-merges it. Read live branch rules for required checks;
   local validation does not establish hosted CI or release approval.

## What belongs in Git

Track source, tests and intentional fixtures, product specs, current guides,
architecture decisions, shared tool configuration and skills, environment
templates, the lockfile, and generated API/migration contracts used for drift
checks. Keep generated builds, dependency installations, local runtime data,
credentials, browser traces, and machine-specific state outside commits.

[.gitignore](.gitignore) holds shared exclusions. Use `.git/info/exclude` for
checkout-specific personal files, or a global `core.excludesFile` for personal
editor preferences. An ignore rule does not remove an already tracked file.
Inspect the file's purpose and owners before changing its tracking state;
history rewrites and removal of shared files need their own reviewed scope.
These distinctions follow the [Git ignore rules](https://git-scm.com/docs/gitignore)
and [GitHub guidance](https://docs.github.com/en/get-started/git-basics/ignoring-files).

When changing ignore rules, verify both sides with
`git check-ignore -v --no-index <path>`: runtime files should be ignored, while
source, fixtures, documentation, templates, and shared configuration should
remain visible. Inspect `git status --short --untracked-files=all` for newly
exposed local files and `git ls-files -ci --exclude-standard` for tracked files
matched by ignore rules. Resolve why a rule matches before force-adding a file.

## Documentation maintenance

Update the nearest owning guide when behavior or commands change, and add a
link in [docs/README.md](docs/README.md) when introducing a new guide. Prefer
relative links to versioned repository files; link to source authority instead
of copying mutable command or status lists into multiple documents. Keep
historical evidence and archived proposals tied to their original dates and
commits. The changelog records version history, not unverified release claims.

Store disposable validation output in an ignored output directory. Preserve
failure traces before rerunning tools that clean their output directories;
record a stable artifact link or its local path and retention limit. Local
temporary paths help replay a run but are not durable shared evidence.

## Reporting problems

Use the issue templates for bugs and feature requests. Include the affected
version or commit, reproducible steps, and expected behavior; remove credentials
and private manuscript content from examples and logs. Follow the
[security policy](.github/SECURITY.md) for vulnerability reports.
