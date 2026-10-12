import { readdirSync } from "node:fs";
import { join } from "node:path";

import { listRepoFiles, readTextLines, repoRoot } from "./common.mjs";

/**
 * Forbidden-residue scan over the current candidate tree. Forbidden
 * literals are assembled from fragments so the gate does not match its
 * own declarations. API-facing modules also reject private payload fields.
 */

const forbidden = (source) => new RegExp(source.join(""), "i");

const SKIP_PATHS = new Set([
  "docs/api/openapi.current.json",
  "pnpm-lock.yaml",
  "uv.lock",
  "scripts/qa/check_repo_hygiene.py",
  "scripts/qa/check_ssot.py",
  ".github/pull_request_template.md",
]);
const SKIP_PARTS = new Set([
  ".git",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "artifacts",
  "coverage",
  "dist",
  "htmlcov",
  "node_modules",
  "playwright-report",
  "test-results",
]);

const FORBIDDEN_PATTERNS = [
  {
    name: "internal_api_versioning",
    regex: forbidden([
      "/api/",
      "v(?:1|2)(?:/|$)|/api/",
      "versions|x-api-",
      "version|x-supported-",
      "versions",
    ]),
  },
  {
    name: "removed_product_surface",
    regex: forbidden([
      "/api/",
      "workspaces|Story",
      "Forge|Hon",
      "cho|Chro",
      "ma|RPG Char",
      "acter|Knowledge",
      " API|local-first CL",
      "I",
    ]),
  },
  {
    name: "compatibility_residue",
    regex: forbidden([
      "legacy import ",
      "path|compatibility ",
      "export|backward ",
      "compatibility|legacy ",
      "session|legacy ",
      "slot",
    ]),
  },
];
const API_SURFACE_FORBIDDEN = [
  {
    name: "api_private_payload_surface",
    regex: /\braw_model_output\b|\bchapter_markdown\b|artifact\.to_dict\(/,
  },
];
const API_SURFACE_PATHS =
  /^(?:src\/apps\/api\/|server\/src\/apps\/api\/|server\/src\/contexts\/[^/]+\/interface\/http\/|server\/src\/shared\/interface\/http\/|frontend\/src\/app\/types\/studio\.ts$)/;

function shouldSkip(relativePath) {
  if (SKIP_PATHS.has(relativePath) || relativePath.startsWith("openspec/changes/archive/")) {
    return true;
  }
  return relativePath.split("/").some((part) => SKIP_PARTS.has(part));
}

function patternFailures(relativePath, lineNumber, line, patterns) {
  const failures = [];
  for (const pattern of patterns) {
    if (pattern.regex.test(line)) {
      failures.push(`${relativePath}:${lineNumber}: ${pattern.name}: ${line.trim()}`);
    }
  }
  return failures;
}

function lineFailures(relativePath, lineNumber, line) {
  const failures = patternFailures(relativePath, lineNumber, line, FORBIDDEN_PATTERNS);
  if (API_SURFACE_PATHS.test(relativePath)) {
    failures.push(...patternFailures(relativePath, lineNumber, line, API_SURFACE_FORBIDDEN));
  }
  return failures;
}

function temporaryProjectFailures(root) {
  const failures = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.isDirectory() && /^[A-Za-z0-9_-]+_project$/.test(entry.name)) {
      failures.push(`${entry.name}/: temporary top-level *_project directory is not allowed`);
    }
  }
  return failures;
}

const root = repoRoot();
const failures = temporaryProjectFailures(root);
for (const relativePath of listRepoFiles(root)) {
  if (shouldSkip(relativePath)) {
    continue;
  }
  const lines = readTextLines(join(root, relativePath));
  for (let index = 0; index < lines.length; index += 1) {
    failures.push(...lineFailures(relativePath, index + 1, lines[index]));
  }
}

if (failures.length > 0) {
  console.error("[repo-hygiene] forbidden residues found:");
  for (const failure of failures) {
    console.error(`  ${failure}`);
  }
  process.exitCode = 1;
} else {
  console.log("[repo-hygiene] clean");
}
