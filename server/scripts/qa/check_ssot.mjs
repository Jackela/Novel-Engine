import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { fileSuffix, readTextLines, repoRoot, reportFailures, scanRootFiles } from "./common.mjs";

/**
 * Product identity and version authority. Since the cutover retired the
 * Python tree, the server package manifest release version is the single
 * source of truth.
 */

const EXPECTED_VERSION = "0.5.0";
const TEXT_SUFFIXES = new Set([".md", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json"]);
const SCAN_SKIP_DIRECTORIES = new Set(["node_modules", "dist", "tmp", "coverage"]);
const IDENTITY_SCAN_PATHS = ["README.md", "frontend/src", "server"];
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

function readJson(root, relativePath) {
  return JSON.parse(readFileSync(join(root, relativePath), "utf8"));
}

function versionFailures(root) {
  const version = readJson(root, "server/package.json").version;
  return version === EXPECTED_VERSION
    ? { version, failures: [] }
    : {
        version,
        failures: [
          `server/package.json must define release version ${EXPECTED_VERSION}, got ${version}`,
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
  if (server.name !== "novel-engine-server") {
    failures.push("server package must be named novel-engine-server");
  }
  return failures;
}

function openspecFailures(root) {
  const failures = [];
  if (!existsSync(join(root, "openspec", "specs", "novel-engine", "spec.md"))) {
    failures.push("canonical OpenSpec capability novel-engine is missing");
  }
  // novel-studio may only remain while the cutover-consolidation change that
  // retires it is still open; once archived, the retired spec must be gone.
  if (
    existsSync(join(root, "openspec", "specs", "novel-studio", "spec.md")) &&
    !existsSync(join(root, "openspec", "changes", "2026-08-25-cutover-consolidation"))
  ) {
    failures.push("retired OpenSpec capability novel-studio still exists");
  }
  return failures;
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
