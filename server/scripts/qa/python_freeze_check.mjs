import { execFileSync } from "node:child_process";
import { pathToFileURL } from "node:url";

import { repoRoot } from "./common.mjs";

/**
 * Python-freeze guard for the TS rewrite (#261; enforcement adjudicated in
 * #254). During the rewrite the Python implementation is frozen — PRs may
 * not touch the paths below unless a human approves the PR with the
 * `python-freeze-exception` label (reserved for security/data-loss fixes).
 * The label check lives in the CI job that invokes this script; this script
 * only reports whether frozen paths changed.
 *
 * Frozen paths (posix, repo-root relative) — per #254 this is the whole
 * scripts/ tree, not just its Python files, which is why the Node twins of
 * the QA gates live under server/scripts/qa instead:
 *   src/**, tests/**, alembic/**, scripts/**, pyproject.toml, uv.lock
 *
 * Usage:
 *   node server/scripts/qa/python_freeze_check.mjs --base-ref origin/main --head-ref HEAD
 *   node server/scripts/qa/python_freeze_check.mjs --paths src/a.py docs/b.md  # self-test mode
 */

const FROZEN_PATH_PATTERNS = [
  /^src\//,
  /^tests\//,
  /^alembic\//,
  /^scripts\//,
  /^pyproject\.toml$/,
  /^uv\.lock$/,
];

/** Returns the subset of changed paths that fall under the Python freeze. */
export function selectFrozenPaths(changedPaths) {
  return changedPaths.filter((changedPath) =>
    FROZEN_PATH_PATTERNS.some((pattern) => pattern.test(changedPath)),
  );
}

function changedPathsBetween(root, baseRef, headRef) {
  const stdout = execFileSync(
    "git",
    ["diff", "--name-status", "--diff-filter=ACDMRT", `${baseRef}...${headRef}`],
    { cwd: root, encoding: "utf8" },
  );
  const paths = [];
  for (const line of stdout.split("\n")) {
    if (line.length === 0) {
      continue;
    }
    const [status, ...fields] = line.split("\t");
    if (status.startsWith("R")) {
      // Renames carry both sides; moving a frozen file out is still a freeze hit.
      paths.push(...fields.filter((field) => field.length > 0));
    } else if (fields[0] !== undefined) {
      paths.push(fields[0]);
    }
  }
  return paths;
}

function parseArgs(argv) {
  const mode = { kind: "none" };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--base-ref" || arg === "--head-ref") {
      index += 1;
      const value = argv[index];
      if (value === undefined) {
        throw new Error(`${arg} requires a value`);
      }
      mode[arg.slice(2)] = value;
    } else if (arg === "--paths") {
      mode.kind = "paths";
    } else if (mode.kind === "paths") {
      mode.paths = [...(mode.paths ?? []), arg];
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  if (mode.kind === "none" && mode.baseRef !== undefined && mode.headRef !== undefined) {
    mode.kind = "refs";
  }
  if (mode.kind === "none") {
    throw new Error("pass either --base-ref and --head-ref, or --paths <path...>");
  }
  return mode;
}

function main() {
  const mode = parseArgs(process.argv.slice(2));
  const root = repoRoot();
  const changedPaths =
    mode.kind === "paths"
      ? (mode.paths ?? [])
      : changedPathsBetween(root, mode.baseRef, mode.headRef);
  const frozen = selectFrozenPaths(changedPaths);

  if (frozen.length > 0) {
    console.error("[python-freeze] frozen Python paths touched:");
    for (const frozenPath of frozen) {
      console.error(`  - ${frozenPath}`);
    }
    console.error(
      "[python-freeze] the Python tree is frozen for the TS rewrite (#254); " +
        "security/data-loss fixes need a human-approved python-freeze-exception label.",
    );
    process.exit(1);
  }
  console.log(
    `[python-freeze] clean: ${changedPaths.length} changed path(s), none under the Python freeze.`,
  );
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
