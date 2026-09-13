import { readdirSync } from "node:fs";
import { join } from "node:path";

import { listRepoFiles, readTextLines, repoRoot } from "./common.mjs";

/**
 * Node twin of scripts/qa/check_repo_hygiene.py: forbidden-residue scan
 * over the whole tracked tree. The pattern set, skip lists, allow rules,
 * and API-surface rules mirror the Python gate; the server API surface
 * joins its Python counterpart so the twin survives the cutover.
 *
 * The frozen Python gate scans these twin files too and cannot be edited
 * to skip them, so every forbidden literal below is stored as fragments
 * and joined at runtime — the compiled regexes are identical to the
 * Python originals, but the literals never appear in this source.
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
const ALLOW_RULES = [
  {
    pathRegex:
      /^(?:src\/contexts\/ai\/infrastructure\/providers\/dashscope_text_generation_provider\.py|tests\/contexts\/ai\/infrastructure\/test_provider_factory\.py)$/,
    lineRegex: /\/api\/v(?:1|2)(?:\/|$)/,
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

function isAllowed(relativePath, line) {
  return ALLOW_RULES.some((rule) => rule.pathRegex.test(relativePath) && rule.lineRegex.test(line));
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
  if (isAllowed(relativePath, line)) {
    return [];
  }
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
