import { join } from "node:path";

import { fileSuffix, listRepoFiles, readTextLines, repoRoot } from "./common.mjs";

/**
 * Per-file code-line budget over the TypeScript workspace.
 * Most files share one default limit. A frontend component
 * (frontend/src, every .tsx file except tests) uses a tighter cap and
 * has no exceptions. A file over its cap fails the gate; blank lines
 * and `//` comments do not count.
 */

const MAX_CODE_LINES = 300;
const FRONTEND_COMPONENT_LIMIT = 200;
const FRONTEND_COMPONENT_ROOT = "frontend/src/";
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
/**
 * Tighter cap for product components. Test files stay on the default
 * limit.
 */
function frontendComponentLimit(relativePath) {
  if (!relativePath.startsWith(FRONTEND_COMPONENT_ROOT)) {
    return null;
  }
  if (!relativePath.endsWith(".tsx") || relativePath.endsWith(".test.tsx")) {
    return null;
  }
  return FRONTEND_COMPONENT_LIMIT;
}

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

const root = repoRoot();
const failures = [];
let checkedCount = 0;

for (const relativePath of listRepoFiles(root)) {
  if (!inScope(relativePath)) {
    continue;
  }
  checkedCount += 1;
  const suffix = fileSuffix(relativePath);
  const codeLines = codeLineCount(join(root, relativePath), suffix);
  const limit = frontendComponentLimit(relativePath) ?? MAX_CODE_LINES;
  if (codeLines > limit) {
    failures.push(`${relativePath}: ${codeLines} code lines exceeds limit ${limit}`);
  }
}

if (failures.length > 0) {
  console.error("[file-size] files over the allowed code-line budget:");
  for (const failure of failures) {
    console.error(`  ${failure}`);
  }
  console.error("[file-size] split the file to stay within its code-line budget.");
  process.exitCode = 1;
} else {
  console.log(
    `[file-size] clean: ${checkedCount} files checked; new-file limit ${MAX_CODE_LINES}; frontend component limit ${FRONTEND_COMPONENT_LIMIT}`,
  );
}
