import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Shared helpers for the Node twins of the Python QA gates
 * (scripts/qa/*.py). The twins live under server/ because the Python
 * tree — including scripts/ — is frozen by the python-freeze CI guard.
 */

export function repoRoot() {
  let directory = dirname(fileURLToPath(import.meta.url));
  while (true) {
    if (existsSync(join(directory, ".git"))) {
      return directory;
    }
    const parent = dirname(directory);
    if (parent === directory) {
      throw new Error("repository root (.git) not found upward of server/scripts/qa");
    }
    directory = parent;
  }
}

/** Tracked + untracked (not ignored) files, relative to the repo root. */
export function listRepoFiles(root) {
  const runLsFiles = (...args) =>
    execFileSync("git", ["ls-files", ...args, "-z"], {
      cwd: root,
      encoding: "utf8",
    })
      .split("\0")
      .filter(Boolean);
  const candidates = runLsFiles("--cached", "--others", "--exclude-standard");
  const deleted = new Set(runLsFiles("--deleted"));
  return candidates.filter((relativePath) => !deleted.has(relativePath));
}

/**
 * Files under a scan root (a file path or a directory), relative to the
 * repo root. Missing paths yield nothing; generated trees are skipped.
 */
export function scanRootFiles(root, relativePath, skipDirectories) {
  const absolute = join(root, relativePath);
  if (!existsSync(absolute)) {
    return [];
  }
  if (statSync(absolute).isFile()) {
    return [relativePath.split("\\").join("/")];
  }
  const found = [];
  const walk = (directory, prefix) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        if (!skipDirectories.has(entry.name)) {
          walk(join(directory, entry.name), `${prefix}${entry.name}/`);
        }
      } else if (entry.isFile()) {
        found.push(`${prefix}${entry.name}`);
      }
    }
  };
  walk(absolute, `${relativePath}/`);
  return found;
}

/** File lines; read failures are fatal so gates cannot silently skip candidates. */
export function readTextLines(absolutePath) {
  return readFileSync(absolutePath, "utf8").split(/\r?\n/);
}

export function fileSuffix(relativePath) {
  const dot = relativePath.lastIndexOf(".");
  return dot === -1 ? "" : relativePath.slice(dot);
}

export function reportFailures(gate, failures) {
  if (failures.length > 0) {
    for (const failure of failures) {
      console.error(`[${gate}] ${failure}`);
    }
    process.exitCode = 1;
    return false;
  }
  return true;
}
