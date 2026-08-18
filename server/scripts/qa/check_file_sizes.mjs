import { join } from "node:path";

import { fileSuffix, listRepoFiles, readTextLines, repoRoot } from "./common.mjs";

/**
 * Node twin of scripts/qa/check_file_sizes.py: per-file code-line budget
 * over the TypeScript workspace. The Python scan roots (src/, tests/,
 * scripts/) stay with the Python gate; they cannot grow because the
 * python-freeze CI guard blocks edits without an exception label.
 */

const MAX_CODE_LINES = 300;
const CODE_SUFFIXES = new Set([
  ".py",
  ".pyi",
  ".ts",
  ".tsx",
  ".mts",
  ".cts",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
]);
const TYPESCRIPT_SUFFIXES = new Set([".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"]);
const SCAN_ROOTS = [
  "server/src/",
  "server/tests/",
  "server/scripts/",
  "frontend/src/",
  "frontend/tests/",
  "frontend/scripts/",
];
const SKIP_PARTS = new Set([
  ".git",
  ".mypy_cache",
  ".omo",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "__pycache__",
  "dist",
  "node_modules",
  "playwright-report",
  "test-results",
]);
// Intentional legacy baselines: relative path -> allowed code-line count.
// A baseline is stale when the file shrinks to the default limit or its
// count drifts from the configured value; both must fail loudly.
const LEGACY_LIMITS = {};

function inScope(relativePath) {
  if (!CODE_SUFFIXES.has(fileSuffix(relativePath))) {
    return false;
  }
  if (!SCAN_ROOTS.some((scanRoot) => relativePath.startsWith(scanRoot))) {
    return false;
  }
  return !relativePath.split("/").some((part) => SKIP_PARTS.has(part));
}

function isCodeLine(line, suffix) {
  const stripped = line.trim();
  if (!stripped) {
    return false;
  }
  if (suffix === ".py" || suffix === ".pyi") {
    return !stripped.startsWith("#");
  }
  if (TYPESCRIPT_SUFFIXES.has(suffix)) {
    return !stripped.startsWith("//");
  }
  return true;
}

function codeLineCount(absolutePath, suffix) {
  return readTextLines(absolutePath).filter((line) => isCodeLine(line, suffix)).length;
}

function legacyLimitViolations(root) {
  const violations = [];
  for (const relativePath of Object.keys(LEGACY_LIMITS).sort()) {
    const absolutePath = join(root, relativePath);
    const currentCount = codeLineCount(absolutePath, fileSuffix(relativePath));
    const configuredLimit = LEGACY_LIMITS[relativePath];
    if (currentCount <= MAX_CODE_LINES) {
      violations.push(
        `${relativePath}: stale legacy baseline; ${currentCount} code lines is at or below default limit ${MAX_CODE_LINES}`,
      );
    } else if (configuredLimit !== currentCount) {
      violations.push(
        `${relativePath}: stale legacy baseline; configured limit ${configuredLimit} differs from current count ${currentCount}`,
      );
    }
  }
  return violations;
}

const root = repoRoot();
let failures = legacyLimitViolations(root);
let violationHeader = "[file-size] invalid legacy baselines:";
let checkedCount = 0;

if (failures.length === 0) {
  failures = [];
  violationHeader = "[file-size] files over the allowed code-line budget:";
  for (const relativePath of listRepoFiles(root)) {
    if (!inScope(relativePath)) {
      continue;
    }
    checkedCount += 1;
    const suffix = fileSuffix(relativePath);
    const codeLines = codeLineCount(join(root, relativePath), suffix);
    const limit = LEGACY_LIMITS[relativePath] ?? MAX_CODE_LINES;
    if (codeLines > limit) {
      failures.push(`${relativePath}: ${codeLines} code lines exceeds limit ${limit}`);
    }
  }
}

if (failures.length > 0) {
  console.error(violationHeader);
  for (const failure of failures) {
    console.error(`  ${failure}`);
  }
  console.error(
    "[file-size] split the file or, for an intentional legacy baseline change, update LEGACY_LIMITS with review evidence.",
  );
  process.exitCode = 1;
} else {
  console.log(
    `[file-size] clean: ${checkedCount} files checked; new-file limit ${MAX_CODE_LINES}; legacy baselines ${Object.keys(LEGACY_LIMITS).length}`,
  );
}
