import { execFileSync } from "node:child_process";

import { readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Link drift gate for the root llms.txt. Every link must point at
 * https://raw.githubusercontent.com/Jackela/Novel-Engine/main/<path> and the
 * referenced path must exist at git HEAD, so the published index never
 * rots when files move or get renamed.
 */

const EXPECTED_PREFIX = "https://raw.githubusercontent.com/Jackela/Novel-Engine/main/";
const MARKDOWN_LINK = /\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;

function extractTargets(lines) {
  const targets = [];
  for (const line of lines) {
    for (const match of line.matchAll(MARKDOWN_LINK)) {
      const url = match[1];
      if (!url.startsWith(EXPECTED_PREFIX)) {
        targets.push({ url, path: null });
        continue;
      }
      targets.push({ url, path: url.slice(EXPECTED_PREFIX.length) });
    }
  }
  return targets;
}

function pathExistsAtHead(root, relativePath) {
  try {
    execFileSync("git", ["cat-file", "-e", `HEAD:${relativePath}`], { cwd: root, stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

const root = repoRoot();
const lines = readTextLines(`${root}/llms.txt`);
const targets = extractTargets(lines);
const failures = [];

if (targets.length === 0) {
  failures.push("llms.txt contains no markdown links; the drift gate found nothing to check");
}

for (const { url, path } of targets) {
  if (path === null) {
    failures.push(`llms.txt link must start with ${EXPECTED_PREFIX}, got ${url}`);
  } else if (!pathExistsAtHead(root, path)) {
    failures.push(`llms.txt link target missing from git HEAD: ${url} (path: ${path})`);
  }
}

if (reportFailures("llms-txt", failures)) {
  console.log(`[llms-txt] clean: ${targets.length} link targets verified against git HEAD`);
}
