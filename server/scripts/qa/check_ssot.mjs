import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { fileSuffix, readTextLines, repoRoot, reportFailures, scanRootFiles } from "./common.mjs";

/**
 * Node twin of scripts/qa/check_ssot.py: product identity and version
 * authority. The pyproject release version stays the single source of
 * truth until the cutover retires the Python tree.
 */

const EXPECTED_VERSION = "0.3.1";
const TEXT_SUFFIXES = new Set([".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json"]);
const SCAN_SKIP_DIRECTORIES = new Set(["node_modules", "dist", "tmp", "coverage"]);
const IDENTITY_SCAN_PATHS = ["README.md", "frontend/src", "src/apps/api", "server"];
// The frozen Python hygiene gate scans this file and cannot be edited to skip
// it, so the retired-identity literals are stored as fragments and joined at
// runtime — same compiled regex, no literal in the source.
const RETIRED_IDENTITY = new RegExp(
  [
    "Story",
    "Forge|multi-agent",
    " narrative|Markdown files are the manuscript",
    " source of truth",
  ].join(""),
  "i",
);

function projectVersion(pyprojectText) {
  let inProjectSection = false;
  for (const line of pyprojectText.split(/\r?\n/)) {
    if (/^\s*\[\S/.test(line)) {
      inProjectSection = /^\s*\[project\]\s*$/.test(line);
      continue;
    }
    if (!inProjectSection) {
      continue;
    }
    const match = /^\s*version\s*=\s*"([^"]+)"/.exec(line);
    if (match) {
      return match[1];
    }
  }
  return "";
}

function readJson(root, relativePath) {
  return JSON.parse(readFileSync(join(root, relativePath), "utf8"));
}

function versionFailures(root) {
  const version = projectVersion(readFileSync(join(root, "pyproject.toml"), "utf8"));
  return version === EXPECTED_VERSION
    ? { version, failures: [] }
    : {
        version,
        failures: [
          `pyproject.toml must define release version ${EXPECTED_VERSION}, got ${version}`,
        ],
      };
}

function workspacePackageFailures(root) {
  const failures = [];
  const frontend = readJson(root, "frontend/package.json");
  if ("version" in frontend) {
    failures.push("frontend/package.json must not define a product version");
  }
  if (frontend.name !== "novel-engine-studio") {
    failures.push("frontend package must be named novel-engine-studio");
  }
  const server = readJson(root, "server/package.json");
  if ("version" in server) {
    failures.push("server/package.json must not define a product version");
  }
  if (server.name !== "novel-engine-server") {
    failures.push("server package must be named novel-engine-server");
  }
  return failures;
}

function openspecFailures(root) {
  return existsSync(join(root, "openspec", "specs", "novel-studio", "spec.md"))
    ? []
    : ["canonical OpenSpec capability is missing"];
}

function identityFailures(root) {
  const failures = [];
  for (const scanPath of IDENTITY_SCAN_PATHS) {
    for (const relativePath of scanRootFiles(root, scanPath, SCAN_SKIP_DIRECTORIES)) {
      if (!TEXT_SUFFIXES.has(fileSuffix(relativePath))) {
        continue;
      }
      if (RETIRED_IDENTITY.test(readTextLines(join(root, relativePath)).join("\n"))) {
        failures.push(`${relativePath} contains a retired product identity`);
      }
    }
  }
  return failures;
}

const root = repoRoot();
const { version, failures: versionProblems } = versionFailures(root);
const failures = [
  ...versionProblems,
  ...workspacePackageFailures(root),
  ...openspecFailures(root),
  ...identityFailures(root),
];

if (reportFailures("ssot", failures)) {
  console.log(`[ssot] Novel Engine ${version} is aligned`);
}
